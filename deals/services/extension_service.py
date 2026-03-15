from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from books.models import SharedBook
from deals.models import Deal, LoanExtension
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


@transaction.atomic
def approve_extension(extension, reviewer):
    """
    核准延長申請。

    - 審核者為 Deal 的 responder
    - 核准後自動延長 Deal.due_date
    """
    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以核准")

    deal = extension.deal

    if reviewer != deal.responder:
        raise ValidationError("只有交易回應者可以審核延長申請")

    extension.status = LoanExtension.Status.APPROVED
    extension.approved_by = reviewer
    extension.save(update_fields=["status", "approved_by", "updated_at"])

    # 延長到期日
    if deal.due_date:
        deal.due_date = deal.due_date + timedelta(days=extension.extra_days)
        deal.save(update_fields=["due_date", "updated_at"])

    notify_extend_result(extension)


def reject_extension(extension, reviewer):
    """
    拒絕延長申請。
    """
    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以拒絕")

    deal = extension.deal

    if reviewer != deal.responder:
        raise ValidationError("只有交易回應者可以審核延長申請")

    extension.status = LoanExtension.Status.REJECTED
    extension.approved_by = reviewer
    extension.save(update_fields=["status", "approved_by", "updated_at"])

    notify_extend_result(extension)


def cancel_extension(extension, applicant):
    """
    取消延長申請。

    BR-16: 延長申請狀態為 PENDING 時，申請者可取消。
    """
    if extension.status != LoanExtension.Status.PENDING:
        raise ValidationError("只有「待審核」的申請可以取消")

    if applicant != extension.requested_by:
        raise ValidationError("只有申請者可以取消延長申請")

    extension.status = LoanExtension.Status.REJECTED
    extension.save(update_fields=["status", "updated_at"])
