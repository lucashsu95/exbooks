"""
交易狀態轉換服務。

此模組封裝 Deal 的狀態轉換邏輯，使用 django-fSM。
Service 層負責：
- 權限檢查
- 跨 Model 事務協調
- 觸發 FSM 狀態轉換

副作用（通知、書籍狀態更新）由 Signal 處理。
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django_fsm import can_proceed

from accounts.services.trust_service import get_borrowing_limits
from books.models import SharedBook
from books.services.book_service import validate_book_set_completeness
from deals.models import Deal, DealMessage
from deals.services.notification_service import (
    notify_deal_requested,
    notify_book_overdue,
)


# ============================================================================
# 配置常數（保持向後相容）
# ============================================================================

# --- 交易類別與書籍流通性的合法對應 ---
DEAL_TYPE_TRANSFERABILITY = {
    Deal.DealType.LOAN: SharedBook.Transferability.RETURN,  # BR-3
    Deal.DealType.RESTORE: SharedBook.Transferability.RETURN,  # BR-3
    Deal.DealType.TRANSFER: SharedBook.Transferability.TRANSFER,  # BR-4
    Deal.DealType.REGRESS: SharedBook.Transferability.TRANSFER,  # BR-4
    # EX 不限流通性
}

# --- 交易類別與書籍狀態的合法對應 ---
DEAL_TYPE_REQUIRED_STATUS = {
    Deal.DealType.LOAN: SharedBook.Status.TRANSFERABLE,  # BR-5
    Deal.DealType.TRANSFER: SharedBook.Status.TRANSFERABLE,  # BR-5
    Deal.DealType.RESTORE: SharedBook.Status.RESTORABLE,  # BR-6
    Deal.DealType.REGRESS: SharedBook.Status.TRANSFERABLE,  # RG 需 T 狀態
    # EX: T/O/R 皆可（在 create_deal 中特殊處理）
}

# --- 面交完成後書籍狀態轉移 ---
MEET_STATUS_MAP = {
    Deal.DealType.LOAN: SharedBook.Status.OCCUPIED,  # LN 面交 → O
    Deal.DealType.TRANSFER: SharedBook.Status.OCCUPIED,  # TF 面交 → O
    Deal.DealType.RESTORE: SharedBook.Status.SUSPENDED,  # RS 面交 → S
    Deal.DealType.REGRESS: SharedBook.Status.SUSPENDED,  # RG 面交 → S
    Deal.DealType.EXCEPT: SharedBook.Status.EXCEPTION,  # EX 面交 → E
}


# ============================================================================
# 內部輔助函式
# ============================================================================


def _get_responder(shared_book, deal_type):
    """
    根據交易類別自動判定回應者。

    LN → Owner（借出 Lend）
    RS → Owner（取回 Retrieve）
    TF → Keeper（轉出 Export）
    RG → Keeper（交回 Revert）
    EX → Owner（處置 Resolve）
    """
    if deal_type in (
        Deal.DealType.LOAN,
        Deal.DealType.RESTORE,
        Deal.DealType.EXCEPT,
    ):
        return shared_book.owner
    else:  # TF, RG
        return shared_book.keeper


# ============================================================================
# 交易建立
# ============================================================================


def create_deal(
    applicant,
    shared_book,
    deal_type,
    book_set=None,
    loan_duration_days=None,
    note=None,
):
    """
    建立交易申請。

    Business Rules:
    - BR-3: LN/RS 僅適用於「閱畢即還」書籍
    - BR-4: TF/RG 僅適用於「開放傳遞」書籍
    - BR-5: 只有狀態為 T 的書籍可發起 LN/TF 交易
    - BR-6: 只有狀態為 R 的書籍可發起 RS 交易
    - BR-7: 套書必須整套借出
    - BR-10: 用戶不能借閱自己貢獻或持有的書籍

    Returns:
        Deal: 建立的交易
    """
    # 借閱權限檢查 (Trust Level)
    if deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
        limits = get_borrowing_limits(applicant.profile.trust_level)

        # 檢查借閱數量
        active_deals = Deal.objects.filter(
            applicant=applicant,
            status__in=[
                Deal.Status.REQUESTED,
                Deal.Status.RESPONDED,
                Deal.Status.MEETED,
            ],
        ).count()

        if active_deals >= limits["max_books"]:
            raise ValidationError(
                f"您目前信用等級只能同時借閱 {int(limits['max_books'])} 本書"
            )

        # 檢查借閱天數（如果有指定）
        if loan_duration_days and loan_duration_days > limits["max_days"]:
            raise ValidationError(
                f"您目前信用等級最長只能借閱 {int(limits['max_days'])} 天"
            )

    # BR-10: 不能借閱自己的書
    if deal_type != Deal.DealType.REGRESS:
        # RG 交易的申請者是 Owner，回應者是 Keeper，不受此限制
        if applicant == shared_book.owner or applicant == shared_book.keeper:
            raise ValidationError("不能對自己貢獻或持有的書籍發起此交易")

    # BR-3/BR-4: 驗證交易類別與流通性
    if deal_type in DEAL_TYPE_TRANSFERABILITY:
        required = DEAL_TYPE_TRANSFERABILITY[deal_type]
        if shared_book.transferability != required:
            raise ValidationError(
                f"「{Deal.DealType(deal_type).label}」僅適用於"
                f"「{SharedBook.Transferability(required).label}」書籍"
            )

    # BR-5/BR-6: 驗證書籍狀態
    if deal_type == Deal.DealType.EXCEPT:
        valid_statuses = (
            SharedBook.Status.TRANSFERABLE,
            SharedBook.Status.OCCUPIED,
            SharedBook.Status.RESTORABLE,
        )
        if shared_book.status not in valid_statuses:
            raise ValidationError(
                f"書籍目前狀態「{shared_book.get_status_display()}」無法發起例外處理"
            )
    else:
        required_status = DEAL_TYPE_REQUIRED_STATUS[deal_type]
        if shared_book.status != required_status:
            raise ValidationError(
                f"書籍狀態必須為「{SharedBook.Status(required_status).label}」"
                f"才能發起此交易，目前為「{shared_book.get_status_display()}」"
            )

    # BR-7: 套書驗證
    if shared_book.book_set and deal_type in (
        Deal.DealType.LOAN,
        Deal.DealType.TRANSFER,
    ):
        validate_book_set_completeness(shared_book.book_set)
        book_set = shared_book.book_set

    responder = _get_responder(shared_book, deal_type)

    # 計算到期日（僅 LN/TF 需要）
    due_date = None
    if deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
        # 如果有指定借閱天數，使用指定值；否則使用書籍預設值
        duration = loan_duration_days or shared_book.loan_duration_days
        due_date = timezone.now().date() + timedelta(days=duration)

    deal = Deal.objects.create(
        shared_book=shared_book,
        book_set=book_set,
        deal_type=deal_type,
        status=Deal.Status.REQUESTED,
        previous_book_status=shared_book.status,
        applicant=applicant,
        responder=responder,
        due_date=due_date,
    )

    # 如果有填寫備註，存入第一條交易留言
    if note:
        DealMessage.objects.create(deal=deal, sender=applicant, content=note)

    notify_deal_requested(deal)

    return deal


# ============================================================================
# FSM 狀態轉換封裝
# ============================================================================


@transaction.atomic
def accept_deal(deal):
    """
    回應者接受交易申請。

    使用 FSM 狀態轉換：REQUESTED → RESPONDED

    副作用（由 Signal 處理）：
    - BR-15: 同一冊書其餘 Q 狀態申請自動取消
    - 書籍狀態變更為 V（已被預約）
    - 發送通知

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(deal.accept):
        raise ValidationError("只有「已請求」狀態的交易可以接受")

    deal.accept()
    deal.save()

    return deal


def decline_deal(deal):
    """
    回應者拒絕交易申請。

    使用 FSM 狀態轉換：REQUESTED → CANCELLED

    副作用（由 Signal 處理）：
    - 發送拒絕通知

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(deal.decline):
        raise ValidationError("只有「已請求」狀態的交易可以拒絕")

    deal.decline()
    deal.save()

    return deal


def cancel_deal(deal):
    """
    申請者取消交易申請。

    使用 FSM 狀態轉換：REQUESTED → CANCELLED

    副作用（由 Signal 處理）：
    - BR-14: 取消後書籍狀態恢復為取消前的狀態
    - 發送取消通知

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(deal.cancel_request):
        raise ValidationError("只有「已請求」狀態的交易可以取消")

    deal.cancel_request()
    deal.save()

    return deal


@transaction.atomic
def complete_meeting(deal):
    """
    確認面交完成。

    使用 FSM 狀態轉換：RESPONDED → MEETED

    副作用（由 Signal 處理）：
    - BR-8: 變更 SharedBook.keeper
    - 書籍狀態依交易類別轉移（見 MEET_STATUS_MAP）
    - 重新計算到期日
    - 發送面交完成通知

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(deal.complete_meeting):
        raise ValidationError("只有「已回應」狀態的交易可以確認面交")

    deal.complete_meeting()
    deal.save()

    return deal


@transaction.atomic
def complete_deal(deal):
    """
    完成交易（雙方評價後）。

    使用 FSM 狀態轉換：MEETED → DONE

    前置條件：
    - 申請者和回應者都已評價

    副作用（由 Signal 處理）：
    - 更新信用等級
    - 發送完成通知

    Raises:
        ValidationError: 如果狀態轉換不允許或條件未滿足
    """
    if not can_proceed(deal.complete):
        raise ValidationError("此交易目前無法完成。請確認雙方都已評價。")

    deal.complete()
    deal.save()

    return deal


# ============================================================================
# 非狀態轉換的業務邏輯
# ============================================================================


def process_book_due(deal):
    """
    處理借閱到期（由排程任務呼叫）。

    - 「閱畢即還」書籍到期 → 狀態變 R（應返還）
    - 「開放傳遞」書籍到期 → 狀態變 T（可移轉）
    - BR-12: 「閱畢即還」到期前未提出還書申請即視為逾期

    Note: 此函式不變更 Deal 狀態，只更新 SharedBook 狀態。
    """
    if deal.status != Deal.Status.MEETED:
        return  # 僅處理已面交的交易

    if not deal.due_date or deal.due_date > timezone.now().date():
        return  # 未到期

    shared_book = deal.shared_book

    if shared_book.transferability == SharedBook.Transferability.RETURN:
        shared_book.status = SharedBook.Status.RESTORABLE
    else:  # TRANSFER
        shared_book.status = SharedBook.Status.TRANSFERABLE

    shared_book.save(update_fields=["status", "updated_at"])

    # 通知持有者與貢獻者書籍已逾期
    notify_book_overdue(deal)


@transaction.atomic
def confirm_return(deal, confirmed_by):
    """
    確認書籍歸還並重新上架。

    此函式用於「閱畢即還」模式的書籍歸還流程：
    1. 借閱者完成閱讀，歸還書籍給持有者（Keeper）
    2. 持有者確認收到書籍後，可將書籍重新上架

    Args:
        deal: Deal 物件，必須為 MEETED 狀態
        confirmed_by: 確認歸還的使用者（必須是 deal.responder，即持有者）

    Returns:
        Deal: 更新後的交易物件

    Raises:
        ValidationError: 如果交易狀態不符或權限不足

    Note: Deal 狀態保持 MEETED，等待雙方評價後才會變成 DONE。
    評價流程由 rating_service.create_rating 處理。
    """
    # 狀態檢查：只有 MEETED 狀態可以確認歸還
    if deal.status != Deal.Status.MEETED:
        raise ValidationError("只有「已面交」狀態的交易可以確認歸還")

    # 權限檢查：只有持有者（Responder）可以確認歸還
    if confirmed_by != deal.responder:
        raise ValidationError("只有持有者可以確認歸還")

    # 檢查是否為「閱畢即還」模式
    shared_book = deal.shared_book
    if shared_book.transferability != SharedBook.Transferability.RETURN:
        raise ValidationError("只有「閱畢即還」模式的書籍可以確認歸還")

    # 更新書籍狀態為可移轉（重新上架）
    shared_book.status = SharedBook.Status.TRANSFERABLE
    shared_book.save(update_fields=["status", "updated_at"])

    return deal
