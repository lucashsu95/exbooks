"""
借閱延長申請服務。

此模組封裝 LoanExtension 的狀態轉換邏輯，使用 django-fSM。
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django_fsm import can_proceed

from books.models import SharedBook
from deals.models import Deal, LoanExtension, ExchangeEvent
from deals.services.exchange_event_service import record_exchange_event
from deals.services.notification_service import (
    notify_extend_requested,
    notify_extend_result,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def request_extension(deal, applicant, extra_days):
    """
    申請延長借閱。

    Rules:
    - 僅限借閱狀態為 O（借閱中）的書籍
    - BR-2: 延長天數 7~30 天（service 層執行 extra_days 欄位 validator）
    - 同一筆交易同時只允許一筆待審核的延長申請，核准或拒絕後才能再申請
    - 申請者必須是 Deal 的 applicant（借入者）

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

    # 先鎖定 deal 列再查 PENDING，並發申請會串行化，不會同時通過檢查
    deal = Deal.objects.select_for_update().get(pk=deal.pk)
    if deal.extensions.filter(status=LoanExtension.Status.PENDING).exists():
        raise ValidationError("該交易已有待審核的延長申請，請等待審核完成")

    LoanExtension._meta.get_field("extra_days").clean(extra_days, None)

    extension = LoanExtension.objects.create(
        deal=deal,
        requested_by=applicant,
        extra_days=extra_days,
        status=LoanExtension.Status.PENDING,
    )

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


def _is_owner_or_keeper_reviewer(deal, reviewer):
    """檢查審核者是否為該書籍的 Owner 或 Keeper。"""
    shared_book = deal.shared_book
    return reviewer in {shared_book.owner, shared_book.keeper}


@transaction.atomic
def approve_extension(extension, reviewer):
    """
    核准延長申請。

    使用 FSM 狀態轉換：PENDING → APPROVED

    - 審核者需為 SharedBook 的 Owner 或 Keeper
    - 審核後，延長 Deal.due_date

    副作用（由 signal 處理）：
    - 發送通知
    """
    deal = extension.deal

    if not _is_owner_or_keeper_reviewer(deal, reviewer):
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

    notify_extend_result(extension)

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


def reject_extension(extension, reviewer):
    """
    拒絕延長申請。

    使用 FSM 狀態轉換：PENDING → REJECTED
    """
    deal = extension.deal

    if not _is_owner_or_keeper_reviewer(deal, reviewer):
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

    notify_extend_result(extension)

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


def cancel_extension(extension, applicant):
    """
    取消延長申請。

    BR-16: 延長申請狀態為 PENDING 時，申請者可取消。

    使用 FSM 狀態轉換：PENDING → REJECTED
    """
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
