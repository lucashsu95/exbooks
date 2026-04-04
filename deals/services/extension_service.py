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

    keeper_approved_by = (
        deal.shared_book.keeper if deal.shared_book.keeper == applicant else None
    )
    initial_status = (
        LoanExtension.Status.PARTIALLY_APPROVED
        if keeper_approved_by
        else LoanExtension.Status.PENDING
    )

    extension_manager = getattr(LoanExtension, "objects")
    extension = extension_manager.create(
        deal=deal,
        requested_by=applicant,
        keeper_approved_by=keeper_approved_by,
        extra_days=extra_days,
        status=initial_status,
    )

    notify_extend_requested(extension)

    return extension


def _is_owner_or_keeper_reviewer(deal, reviewer):
    """檢查審核者是否為該書籍的 Owner 或 Keeper。"""
    shared_book = deal.shared_book
    return reviewer in {shared_book.owner, shared_book.keeper}


def _mark_reviewer_approval(extension, reviewer):
    """寫入 Owner / Keeper 審核紀錄。"""
    shared_book = extension.deal.shared_book
    marked = False

    if reviewer == shared_book.owner:
        if extension.owner_approved_by:
            raise ValidationError("Owner 已完成審核，無法重複核准")
        extension.owner_approved_by = reviewer
        marked = True

    if reviewer == shared_book.keeper:
        if extension.keeper_approved_by:
            raise ValidationError("Keeper 已完成審核，無法重複核准")
        extension.keeper_approved_by = reviewer
        marked = True

    if not marked:
        raise ValidationError("只有書籍 Owner 或 Keeper 可以審核延長申請")


@transaction.atomic
def approve_extension(extension, reviewer):
    """
    核准延長申請。

    使用 FSM 狀態轉換：
    - PENDING → PARTIALLY_APPROVED（第一位審核者核准）
    - PARTIALLY_APPROVED → APPROVED（第二位審核者核准）

    - 審核者需為 SharedBook 的 Owner 或 Keeper
    - Owner + Keeper 雙方都核准後，才會延長 Deal.due_date

    副作用（由 signal 處理）：
    - 發送通知
    """
    deal = extension.deal

    if not _is_owner_or_keeper_reviewer(deal, reviewer):
        raise ValidationError("只有書籍 Owner 或 Keeper 可以審核延長申請")

    if reviewer == extension.requested_by:
        raise ValidationError("申請者不可審核自己的延長申請")

    if extension.status not in {
        LoanExtension.Status.PENDING,
        LoanExtension.Status.PARTIALLY_APPROVED,
    }:
        raise ValidationError("只有「待審核／部分核准」的申請可以核准")

    _mark_reviewer_approval(extension, reviewer)

    owner_approved = extension.owner_approved_by is not None
    keeper_approved = extension.keeper_approved_by is not None

    if owner_approved and keeper_approved:
        if not can_proceed(extension.approve):
            raise ValidationError("目前狀態無法核准延長申請")
        extension.approve()
    elif extension.status == LoanExtension.Status.PENDING:
        if not can_proceed(extension.mark_partially_approved):
            raise ValidationError("目前狀態無法進入部分核准")
        extension.mark_partially_approved()

    extension.save()

    # 僅在雙方都核准後延長到期日
    if extension.status == LoanExtension.Status.APPROVED and deal.due_date:
        deal.due_date = deal.due_date + timedelta(days=extension.extra_days)
        deal.save(update_fields=["due_date", "updated_at"])

    if extension.status == LoanExtension.Status.APPROVED:
        notify_extend_result(extension)


def reject_extension(extension, reviewer):
    """
    拒絕延長申請。

    使用 FSM 狀態轉換：PENDING/PARTIALLY_APPROVED → REJECTED
    """
    deal = extension.deal

    if not _is_owner_or_keeper_reviewer(deal, reviewer):
        raise ValidationError("只有書籍 Owner 或 Keeper 可以審核延長申請")

    if reviewer == extension.requested_by:
        raise ValidationError("申請者不可審核自己的延長申請")

    if not can_proceed(extension.reject):
        raise ValidationError("只有「待審核／部分核准」的申請可以拒絕")

    if reviewer == deal.shared_book.owner and not extension.owner_approved_by:
        extension.owner_approved_by = reviewer
    if reviewer == deal.shared_book.keeper and not extension.keeper_approved_by:
        extension.keeper_approved_by = reviewer

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
