"""申訴服務層

處理申訴的建立、審核、取消等業務邏輯。
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import Appeal
from deals.models import Notification
from deals.services.notification_service import notify


MIN_DESCRIPTION_LENGTH = 50


@transaction.atomic
def create_appeal(user, appeal_type, title, description, evidence=None):
    """建立申訴

    Args:
        user: 申訴用戶
        appeal_type: 申訴類型
        title: 申訴標題
        description: 申訴描述（至少 50 字元）
        evidence: 證據文件（選填）

    Returns:
        Appeal: 建立的申訴物件

    Raises:
        ValidationError: 描述過短
    """
    if len(description) < MIN_DESCRIPTION_LENGTH:
        raise ValidationError("申訴描述需至少 50 字元")

    appeal = Appeal.objects.create(
        user=user,
        appeal_type=appeal_type,
        title=title,
        description=description,
        evidence=evidence,
    )

    # 發送通知給用戶確認
    notify(
        recipient=user,
        notification_type=Notification.NotificationType.APPEAL_SUBMITTED,
        title="申訴已送出",
        message=f"您的申訴「{title}」已送出，我們將儘快處理。",
    )

    return appeal


@transaction.atomic
def submit_for_review(appeal_id):
    """提交審核（管理員開始處理）

    Args:
        appeal_id: 申訴 ID

    Returns:
        Appeal: 更新後的申訴物件

    Raises:
        ValidationError: 申訴狀態無法執行此操作
    """
    appeal = Appeal.objects.select_for_update().get(id=appeal_id)

    if appeal.status != Appeal.Status.SUBMITTED:
        raise ValidationError("申訴狀態無法執行此操作")

    appeal.status = Appeal.Status.UNDER_REVIEW
    appeal.save()

    return appeal


@transaction.atomic
def review_appeal(appeal_id, reviewer, decision, notes=""):
    """審核申訴

    Args:
        appeal_id: 申訴 ID
        reviewer: 審核者
        decision: 審核決定 ("approve" 或 "reject")
        notes: 審核備註

    Returns:
        Appeal: 更新後的申訴物件

    Raises:
        ValidationError: 申訴狀態無法執行此操作
    """
    appeal = Appeal.objects.select_for_update().get(id=appeal_id)

    if appeal.status != Appeal.Status.UNDER_REVIEW:
        raise ValidationError("申訴狀態無法執行此操作")

    new_status = (
        Appeal.Status.APPROVED if decision == "approve" else Appeal.Status.REJECTED
    )
    appeal.status = new_status
    appeal.resolution_notes = notes
    appeal.resolved_by = reviewer
    appeal.resolved_at = timezone.now()
    appeal.save()

    # 發送審核結果通知
    notify(
        recipient=appeal.user,
        notification_type=Notification.NotificationType.APPEAL_RESOLVED,
        title=f"申訴審核結果：{appeal.get_status_display()}",
        message=f"您的申訴「{appeal.title}」審核結果為{appeal.get_status_display()}。",
    )

    return appeal


def get_user_appeals(user, status=None):
    """取得用戶申訴列表

    Args:
        user: 用戶
        status: 狀態篩選（選填）

    Returns:
        QuerySet: 申訴列表
    """
    queryset = Appeal.objects.filter(user=user).select_related("resolved_by")

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


def get_appeal_by_id(appeal_id):
    """取得單一申訴

    Args:
        appeal_id: 申訴 ID

    Returns:
        Appeal: 申訴物件

    Raises:
        Appeal.DoesNotExist: 申訴不存在
    """
    return Appeal.objects.select_related("user", "resolved_by").get(id=appeal_id)


@transaction.atomic
def cancel_appeal(appeal_id, user):
    """取消申訴

    Args:
        appeal_id: 申訴 ID
        user: 取消者

    Returns:
        Appeal: 更新後的申訴物件

    Raises:
        ValidationError: 無權限修改此申訴或申訴狀態無法取消
    """
    appeal = Appeal.objects.select_for_update().get(id=appeal_id)

    if appeal.user != user:
        raise ValidationError("無權限修改此申訴")

    if appeal.status not in [Appeal.Status.SUBMITTED]:
        raise ValidationError("申訴狀態無法取消")

    appeal.status = Appeal.Status.CLOSED
    appeal.save()

    return appeal
