"""
違規處分服務層。
處理用戶違規處分的建立、查詢、解除等業務邏輯。
"""

from typing import Optional, TYPE_CHECKING
from django.utils import timezone
from django.db import transaction
from django.db.models import QuerySet
from django.contrib.auth import get_user_model

from accounts.models import UserProfile, Violation

if TYPE_CHECKING:
    from accounts.models import Appeal

User = get_user_model()


class ViolationService:
    """違規處分服務"""

    @staticmethod
    def create_violation(
        user: User,
        action_type: str,
        severity: str,
        violation_type: str,
        description: str,
        created_by: User,
        suspension_days: Optional[int] = None,
        related_appeal: Optional["Appeal"] = None,
    ) -> Violation:
        """
        建立違規處分。

        Args:
            user: 被處分的用戶
            action_type: 處分類型（warning/temporary_suspension/permanent_suspension）
            severity: 違規等級（minor/moderate/severe）
            violation_type: 違規行為類型
            description: 違規描述
            created_by: 處分者
            suspension_days: 停權天數（暫時停權時必填）
            related_appeal: 相關申訴（選填）

        Returns:
            Violation: 建立的違規處分
        """
        with transaction.atomic():
            violation = Violation.objects.create(
                user=user,
                action_type=action_type,
                severity=severity,
                violation_type=violation_type,
                description=description,
                created_by=created_by,
                suspension_days=suspension_days,
                related_appeal=related_appeal,
            )

            # 如果是停權處分，更新 UserProfile
            if action_type in [
                Violation.ActionType.TEMPORARY_SUSPENSION,
                Violation.ActionType.PERMANENT_SUSPENSION,
            ]:
                profile = UserProfile.objects.get(user=user)
                profile.is_suspended = True
                profile.suspension_reason = description

                if action_type == Violation.ActionType.TEMPORARY_SUSPENSION:
                    profile.suspension_end_date = timezone.now() + timezone.timedelta(
                        days=suspension_days or 7
                    )
                else:
                    profile.suspension_end_date = None

                profile.save(
                    update_fields=[
                        "is_suspended",
                        "suspension_end_date",
                        "suspension_reason",
                        "updated_at",
                    ]
                )

            return violation

    @staticmethod
    def lift_violation(violation: Violation, lifted_by: User) -> None:
        """
        解除處分（提前解權）。

        Args:
            violation: 要解除的違規處分
            lifted_by: 解除者
        """
        with transaction.atomic():
            violation.lift(lifted_by)

            # 檢查是否還有其他生效中的停權處分
            active_suspensions = Violation.objects.filter(
                user=violation.user,
                action_type__in=[
                    Violation.ActionType.TEMPORARY_SUSPENSION,
                    Violation.ActionType.PERMANENT_SUSPENSION,
                ],
                is_active=True,
            ).exclude(pk=violation.pk)

            if not active_suspensions.exists():
                # 沒有其他生效中的停權處分，解除用戶停權狀態
                profile = UserProfile.objects.get(user=violation.user)
                profile.is_suspended = False
                profile.suspension_end_date = None
                profile.suspension_reason = ""
                profile.save(
                    update_fields=[
                        "is_suspended",
                        "suspension_end_date",
                        "suspension_reason",
                        "updated_at",
                    ]
                )

    @staticmethod
    def get_user_violations(
        user: User, is_active: Optional[bool] = None
    ) -> "QuerySet[Violation]":
        """
        取得用戶的違規處分列表。

        Args:
            user: 用戶
            is_active: 是否只查詢生效中的處分（選填）

        Returns:
            QuerySet: 違規處分列表
        """
        queryset = Violation.objects.filter(user=user).select_related(
            "created_by", "lifted_by"
        )

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.order_by("-created_at")

    @staticmethod
    def get_active_suspensions() -> QuerySet[Violation]:
        """
        取得所有生效中的停權處分。

        Returns:
            QuerySet: 生效中的停權處分列表
        """
        return Violation.objects.filter(
            action_type__in=[
                Violation.ActionType.TEMPORARY_SUSPENSION,
                Violation.ActionType.PERMANENT_SUSPENSION,
            ],
            is_active=True,
        ).select_related("user", "created_by")

    @staticmethod
    def check_and_lift_expired_suspensions() -> int:
        """
        檢查並解除已期滿的暫時停權。
        系統定時任務可呼叫此方法。

        Returns:
            int: 解除的停權數量
        """
        now = timezone.now()
        expired_violations = Violation.objects.filter(
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            is_active=True,
            user__profile__suspension_end_date__lt=now,
        ).select_related("user")

        count = 0
        for violation in expired_violations:
            profile = UserProfile.objects.get(user=violation.user)
            profile.is_suspended = False
            profile.suspension_end_date = None
            profile.suspension_reason = ""
            profile.save(
                update_fields=[
                    "is_suspended",
                    "suspension_end_date",
                    "suspension_reason",
                    "updated_at",
                ]
            )

            violation.is_active = False
            violation.lifted_at = now
            violation.save(update_fields=["is_active", "lifted_at", "updated_at"])
            count += 1

        return count


# 模組級匯出
violation_service = ViolationService()
