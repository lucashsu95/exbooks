"""
Deal 狀態轉換 Signal 處理。

此處只處理 Deal 狀態轉換後的副作用：
- 發送通知
- 使用 transaction.on_commit 確保資料庫寫入後才發送通知
"""

from django.dispatch import receiver
from django.db import transaction
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

    根據轉換方法名稱觸發對應通知。
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
    """
    transaction.on_commit(lambda: notify_deal_responded(deal))

    # 通知被自動取消的申請者
    if hasattr(deal, '_auto_cancelled_deals'):
        for cancelled_deal in deal._auto_cancelled_deals:
            # capture local variable in lambda
            transaction.on_commit(lambda cd=cancelled_deal: notify_deal_cancelled(cd, deal.responder))


def _handle_decline(deal):
    """
    處理拒絕交易後的副作用。
    """
    transaction.on_commit(lambda: notify_deal_cancelled(deal, deal.responder))


def _handle_cancel_request(deal):
    """
    處理申請者取消後的副作用。
    """
    transaction.on_commit(lambda: notify_deal_cancelled(deal, deal.applicant))


def _handle_complete_meeting(deal):
    """
    處理面交完成後的副作用。
    """
    transaction.on_commit(lambda: notify_deal_meeted(deal))


def _handle_complete(deal):
    """
    處理交易完成後的副作用。
    """
    pass


def _handle_cancel(deal, source_status):
    """
    處理通用取消的副作用。
    """
    if source_status == Deal.Status.REQUESTED:
        _handle_cancel_request(deal)
    elif source_status == Deal.Status.RESPONDED:
        transaction.on_commit(lambda: notify_deal_cancelled(deal, deal.applicant))
    elif source_status == Deal.Status.MEETED:
        transaction.on_commit(lambda: notify_deal_cancelled(deal, deal.applicant))
