"""
Deal 狀態轉換 Signal 處理。

此模組處理 Deal 狀態轉換後的副作用：
- 書籍狀態更新
- 通知發送
- 其他模型同步
"""

from datetime import timedelta

from django.dispatch import receiver
from django.utils import timezone
from django_fsm.signals import post_transition

from deals.models import Deal
from deals.services.notification_service import (
    notify_deal_cancelled,
    notify_deal_meeted,
    notify_deal_responded,
)


# ============================================================================
# Deal 狀態轉換 Signal 處理器
# ============================================================================


@receiver(post_transition, sender=Deal)
def handle_deal_state_change(sender, instance, name, source, target, **kwargs):
    """
    Deal 狀態轉換後的統一處理。

    根據轉換方法名稱執行對應的副作用。
    """
    if name == "accept":
        _handle_accept(instance)
    elif name == "decline":
        _handle_decline(instance)
    elif name == "cancel_request":
        _handle_cancel_request(instance)
    elif name == "complete_meeting":
        _handle_complete_meeting(instance)
    elif name == "complete":
        _handle_complete(instance)
    elif name == "cancel":
        _handle_cancel(instance, source)


# ============================================================================
# 各轉換的副作用處理
# ============================================================================


def _handle_accept(deal):
    """
    處理接受交易後的副作用。

    - BR-15: 取消同一冊書的其他申請
    - 更新書籍狀態為 RESERVED（V）
    - 發送通知
    """
    from deals.models import Deal

    shared_book = deal.shared_book

    # BR-15: 取消同一冊書的其他申請
    auto_cancelled = list(
        Deal.objects.filter(
            shared_book=shared_book,
            status=Deal.Status.REQUESTED,
        ).exclude(pk=deal.pk)
    )
    Deal.objects.filter(
        shared_book=shared_book,
        status=Deal.Status.REQUESTED,
    ).exclude(pk=deal.pk).update(status=Deal.Status.CANCELLED)

    # 更新書籍狀態為 V（已被預約）- 使用 FSM 方法
    shared_book.reserve()
    shared_book.save()

    # 通知申請者交易已被接受
    notify_deal_responded(deal)

    # 通知被自動取消的申請者
    for cancelled_deal in auto_cancelled:
        notify_deal_cancelled(cancelled_deal, deal.responder)


def _handle_decline(deal):
    """
    處理拒絕交易後的副作用。

    - 發送拒絕通知
    """
    notify_deal_cancelled(deal, deal.responder)


def _handle_cancel_request(deal):
    """
    處理申請者取消後的副作用。

    - BR-14: 恢復書籍狀態
    - 發送取消通知
    """
    shared_book = deal.shared_book

    # BR-14: 恢復書籍狀態（繞過 FSM，因為狀態可能是任意值）
    if deal.previous_book_status:
        shared_book.status = deal.previous_book_status
        shared_book.save(update_fields=["status", "updated_at"])

    # 通知回應者交易已被取消
    notify_deal_cancelled(deal, deal.applicant)


def _handle_complete_meeting(deal):
    """
    處理面交完成後的副作用。

    - BR-8: 變更 SharedBook.keeper
    - 書籍狀態依交易類別轉移
    - 重新計算到期日
    - 發送面交完成通知
    """
    from deals.services.deal_service import MEET_STATUS_MAP

    shared_book = deal.shared_book

    # BR-8: 變更持有人
    if deal.deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
        # 書從回應者手中到申請者手中
        shared_book.keeper = deal.applicant
    elif deal.deal_type in (Deal.DealType.RESTORE, Deal.DealType.REGRESS):
        # 書從申請者手中到回應者手中（Owner 取回）
        shared_book.keeper = deal.responder

    # 更新書籍狀態 - 使用 FSM 方法
    new_status = MEET_STATUS_MAP.get(deal.deal_type)
    if new_status:
        # 根據目標狀態選擇 FSM 方法
        if new_status == "O":
            shared_book.mark_as_borrowed()
        elif new_status == "S":
            # RESTORE/REGRESS 導向 SUSPENDED，這裡直接設定
            shared_book.status = new_status
        elif new_status == "E":
            shared_book.status = new_status
        else:
            shared_book.status = new_status

    shared_book.save()

    # 重新計算到期日（從面交日起算）
    if deal.deal_type in (Deal.DealType.LOAN, Deal.DealType.TRANSFER):
        deal.due_date = timezone.now().date() + timedelta(
            days=shared_book.loan_duration_days
        )
        deal.save(update_fields=["due_date"])

    # 通知雙方面交完成
    notify_deal_meeted(deal)


def _handle_complete(deal):
    """
    處理交易完成後的副作用。

    - 更新信用等級（延遲處理，避免迴圈）
    - 發送完成通知
    """
    # 信用等級更新由 rating_service 處理
    # 這裡只負責狀態轉換後的清理
    pass


def _handle_cancel(deal, source_status):
    """
    處理通用取消的副作用。

    根據來源狀態決定如何處理。
    """
    if source_status == Deal.Status.REQUESTED:
        _handle_cancel_request(deal)
    elif source_status == Deal.Status.RESPONDED:
        # RESPONDED 狀態取消，需要恢復書籍狀態
        shared_book = deal.shared_book
        if deal.previous_book_status:
            shared_book.status = deal.previous_book_status
            shared_book.save(update_fields=["status", "updated_at"])
        notify_deal_cancelled(deal, deal.applicant)
    elif source_status == Deal.Status.MEETED:
        # MEETED 狀態取消較複雜，需視情況處理
        # 通常由管理員操作，需手動處理書籍狀態
        notify_deal_cancelled(deal, deal.applicant)
