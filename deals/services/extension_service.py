"""
借閱延長申請服務。

此模組封裝 LoanExtension 的狀態轉換邏輯，使用 django-fSM。
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django_fsm import can_proceed

from books.models import SharedBook
from deals.models import LoanExtension
from deals.services.notification_service import (
    notify_extend_requested,
    notify_extend_result,
)


def request_extension(deal, applicant, extra_days):
    """
    申請延長借閱。

    Rules:
    - 僅限借閱狀態為 O（借閱中）的書籍
    - BR-2: 延長天數 7~30 天（Model validator 保障）
    - 同一筆交易可多次申請
    - 申請者必須是 Deal 的 applicant（借入者）

    Returns:
        LoanExtension: 建立的延長申請
    """
    if deal.shared_book.status != SharedBook.Status.OCCUPIED:
        raise ValidationError("只有「借閱中」的書籍可以申請延長")

    if applicant != deal.applicant:
        raise ValidationError("只有借閱者可以申請延長")

    extension = LoanExtension.objects.create(
        deal=deal,
        requested_by=applicant,
        extra_days=extra_days,
        status=LoanExtension.Status.PENDING,
    )

    notify_extend_requested(extension)

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
