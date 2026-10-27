"""
借閱延長申請服務。

此模組封裝 LoanExtension 的狀態轉換邏輯，使用 django-fSM。
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_fsm import can_proceed

from books.models import SharedBook
from deals.models import Deal, LoanExtension, ExchangeEvent
from deals.services.exchange_event_service import record_exchange_event
from deals.services.notification_service import (
    notify_extend_requested,
    notify_extend_result,
)

logger = logging.getLogger(__name__)

# Sentinel：區分「呼叫方尚未查 pending」（omitted）與「確認沒有 pending」（None）。
# 避免 pending 參數的 None 二義性。
_UNSET = object()


def is_extension_eligible(user, deal, pending=_UNSET):
    """
    延長申請資格的讀側判定（單一事實來源）。

    與 request_extension 的 guards 同一條規則（改規則時兩者必改）：
    1. 書籍狀態為 OCCUPIED（借閱中）
    2. user 是該交易的 applicant（借閱者）
    3. 該交易沒有 PENDING 的延長申請

    刻意不查 Deal 狀態：寫側 request_extension 同樣只以上列三條件為 guard，
    讀側與寫側對齊，避免「入口藏起來但 service 仍受理」的讀寫分歧。

    Call site（皆只讀不寫，寫入權威仍是 request_extension）：
    - web deal_detail view context → 模板的「新增申請」入口條件
    - ai read tool（get_borrowing_status）→「（可申請延長）」標記

    pending: 該交易的 PENDING 延長申請（DB constraint 保證至多一筆）。
    已取回 pending 的呼叫方（如 AI read tool 的 prefetch）應傳入以避免重複查詢；
    傳 None 代表「已確認沒有 pending」。省略時本函式自行查 DB。
    """
    if deal.shared_book.status != SharedBook.Status.OCCUPIED:
        return False
    if user != deal.applicant:
        return False
    if pending is _UNSET:
        pending = deal.extensions.filter(status=LoanExtension.Status.PENDING).first()
    return pending is None


@transaction.atomic
def request_extension(deal, applicant, extra_days):
    """
    申請延長借閱。

    Rules（單一來源；讀側判定見 is_extension_eligible，改規則時兩者必改）：
    - 僅限借閱狀態為 O（借閱中）的書籍
    - BR-2: 延長天數 7~30 天（service 層執行 extra_days 欄位 validator）
    - 同一筆交易同時只允許一筆待審核的延長申請，核准或拒絕後才能再申請
    - 申請者必須是 Deal 的 applicant（借入者）

    guards 是該規則的執行側：逐條件拋個別錯誤訊息，PENDING 檢查走
    鎖定讀取（MySQL RR 下一致讀取看不到對方剛 commit 的列）。

    原子性：create 與 record_event 在同一 transaction，
    中途中斷整體回滾，不會留孤兒 PENDING。
    通知經 transaction.on_commit 延遲到 commit 後派發，回滾不會外發。

    Returns:
        LoanExtension: 建立的延長申請
    """
    if deal.shared_book.status != SharedBook.Status.OCCUPIED:
        raise ValidationError("只有「借閱中」的書籍可以申請延長")

    if applicant != deal.applicant:
        raise ValidationError("只有借閱者可以申請延長")

    # 鎖定 deal 列串行化並發申請；PENDING 檢查也走鎖定讀取，
    # MySQL RR 下一致讀取會讀舊快照，看不到對方剛 commit 的列
    deal = Deal.objects.select_for_update().get(pk=deal.pk)
    if (
        deal.extensions.filter(status=LoanExtension.Status.PENDING)
        .select_for_update()
        .first()
        is not None
    ):
        raise ValidationError("該交易已有待審核的延長申請，請等待審核完成")

    LoanExtension._meta.get_field("extra_days").clean(extra_days, None)

    try:
        extension = LoanExtension.objects.create(
            deal=deal,
            requested_by=applicant,
            extra_days=extra_days,
            status=LoanExtension.Status.PENDING,
        )
    except IntegrityError:
        # race 兜底：非 service 寫入者在 guard 與 INSERT 之間 commit 了同 deal PENDING，
        # (deal, is_pending) unique constraint 在此擋下（#21）
        raise ValidationError("該交易已有待審核的延長申請，請等待審核完成")

    transaction.on_commit(lambda: notify_extend_requested(extension))

    record_exchange_event(
        shared_book=deal.shared_book,
        event_type=ExchangeEvent.EventType.EXTENSION_REQUESTED,
        deal=deal,
        actor=applicant,
        metadata={"extra_days": extra_days},
    )

    logger.info(
        "extension requested",
        extra={
            "extension_id": extension.id,
            "deal_id": deal.id,
            "applicant_id": applicant.id,
            "extra_days": extra_days,
        },
    )
    return extension


def is_owner_or_keeper_reviewer(shared_book, reviewer):
    """
    延長申請審核資格（單一事實來源）：審核者須為該書籍的 Owner 或 Keeper。

    寫側 approve_extension / reject_extension 與讀側 rules.py 的
    is_extension_reviewer predicate 皆以此為準。
    """
    return reviewer in {shared_book.owner, shared_book.keeper}


@transaction.atomic
def approve_extension(extension, reviewer):
    """
    核准延長申請。

    使用 FSM 狀態轉換：PENDING → APPROVED

    - 審核者需為 SharedBook 的 Owner 或 Keeper
    - 審核後，延長 Deal.due_date
    - 先鎖 deal 列、再鎖 extension 列（與 request 路徑同序）串行化並發核准；
      PENDING 以鎖定讀取判定，in-memory 物件可能是核准前的舊快照
    - 通知經 transaction.on_commit 延遲到 commit 後派發，回滾不會外發
    """
    deal = Deal.objects.select_for_update().get(pk=extension.deal_id)
    extension = LoanExtension.objects.select_for_update().get(pk=extension.pk)

    if not is_owner_or_keeper_reviewer(deal.shared_book, reviewer):
        raise ValidationError("只有書籍 Owner 或 Keeper 可以審核延長申請")

    if reviewer == extension.requested_by:
        raise ValidationError("申請者不可審核自己的延長申請")

    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以核准")

    if not can_proceed(extension.approve):
        raise ValidationError("目前狀態無法核准延長申請")

    extension.approved_by = reviewer
    extension.approve()
    extension.save()

    # 延長到期日
    if deal.due_date:
        deal.due_date = deal.due_date + timedelta(days=extension.extra_days)
        deal.save(update_fields=["due_date", "updated_at"])

    transaction.on_commit(lambda: notify_extend_result(extension))

    record_exchange_event(
        shared_book=deal.shared_book,
        event_type=ExchangeEvent.EventType.EXTENSION_APPROVED,
        deal=deal,
        actor=reviewer,
        metadata={
            "extra_days": extension.extra_days,
            "due_date": str(deal.due_date) if deal.due_date else None,
        },
    )

    logger.info(
        "extension approved",
        extra={
            "extension_id": extension.id,
            "deal_id": deal.id,
            "reviewer_id": reviewer.id,
            "extra_days": extension.extra_days,
        },
    )


@transaction.atomic
def reject_extension(extension, reviewer):
    """
    拒絕延長申請。

    使用 FSM 狀態轉換：PENDING → REJECTED

    先鎖 deal 列、再鎖 extension 列（與 request 路徑同序）串行化並發審核；
    通知經 transaction.on_commit 延遲到 commit 後派發，回滾不會外發。
    """
    deal = Deal.objects.select_for_update().get(pk=extension.deal_id)
    extension = LoanExtension.objects.select_for_update().get(pk=extension.pk)

    if not is_owner_or_keeper_reviewer(deal.shared_book, reviewer):
        raise ValidationError("只有書籍 Owner 或 Keeper 可以審核延長申請")

    if reviewer == extension.requested_by:
        raise ValidationError("申請者不可審核自己的延長申請")

    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以拒絕")

    if not can_proceed(extension.reject):
        raise ValidationError("只有「待審核」的申請可以拒絕")

    extension.approved_by = reviewer
    extension.reject()
    extension.save()

    transaction.on_commit(lambda: notify_extend_result(extension))

    record_exchange_event(
        shared_book=deal.shared_book,
        event_type=ExchangeEvent.EventType.EXTENSION_REJECTED,
        deal=deal,
        actor=reviewer,
        metadata={"extra_days": extension.extra_days},
    )

    logger.info(
        "extension rejected",
        extra={
            "extension_id": extension.id,
            "deal_id": deal.id,
            "reviewer_id": reviewer.id,
        },
    )


@transaction.atomic
def cancel_extension(extension, applicant):
    """
    取消延長申請。

    BR-16: 延長申請狀態為 PENDING 時，申請者可取消。

    使用 FSM 狀態轉換：PENDING → REJECTED

    以鎖定讀取重新取得 extension，in-memory 物件可能是已審核的舊快照
    （舊快照取消會寫入多餘的 CANCELLED 稽核事件）。
    """
    extension = LoanExtension.objects.select_for_update().get(pk=extension.pk)

    if applicant != extension.requested_by:
        raise ValidationError("只有申請者可以取消延長申請")

    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以取消")

    if not can_proceed(extension.reject):
        raise ValidationError("只有「待審核」的申請可以取消")

    extension.reject()
    extension.save()

    deal = extension.deal
    record_exchange_event(
        shared_book=deal.shared_book,
        event_type=ExchangeEvent.EventType.EXTENSION_CANCELLED,
        deal=deal,
        actor=applicant,
        metadata={"extra_days": extension.extra_days},
    )

    logger.info(
        "extension cancelled",
        extra={
            "extension_id": extension.id,
            "deal_id": deal.id,
            "applicant_id": applicant.id,
        },
    )
