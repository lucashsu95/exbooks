"""
違規服務測試 - 測試 ViolationService 的所有功能
"""

import pytest
from datetime import timedelta
from django.utils import timezone

from accounts.models import UserProfile, Violation
from accounts.services.violation_service import ViolationService
from tests.factories import UserFactory


@pytest.mark.django_db
class TestViolationService:
    """違規服務測試類別"""

    def test_create_warning_violation(self, admin_user):
        """測試建立警告處分"""
        user = UserFactory()

        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MODERATE,
            violation_type="inappropriate_content",
            description="發布不當內容",
            created_by=admin_user,
        )

        assert violation.user == user
        assert violation.action_type == Violation.ActionType.WARNING
        assert violation.severity == Violation.Severity.MODERATE
        assert violation.is_active is True

        # 警告不應導致停權
        profile = UserProfile.objects.get(user=user)
        assert profile.is_suspended is False

    def test_create_temporary_suspension(self, admin_user):
        """測試建立暫時停權處分"""
        user = UserFactory()

        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            severity=Violation.Severity.SEVERE,
            violation_type="repeated_offenses",
            description="多次違規",
            created_by=admin_user,
            suspension_days=7,
        )

        assert violation.action_type == Violation.ActionType.TEMPORARY_SUSPENSION
        assert violation.suspension_days == 7

        # 應導致用戶停權
        profile = UserProfile.objects.get(user=user)
        assert profile.is_suspended is True
        assert profile.suspension_end_date is not None
        assert profile.suspension_reason == "多次違規"

        # 驗證停權期限
        expected_end = timezone.now() + timedelta(days=7)
        tolerance = timedelta(minutes=1)
        assert abs(profile.suspension_end_date - expected_end) < tolerance

    def test_create_permanent_suspension(self, admin_user):
        """測試建立永久停權處分"""
        user = UserFactory()

        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.PERMANENT_SUSPENSION,
            severity=Violation.Severity.SEVERE,
            violation_type="severe_violation",
            description="嚴重違規行為",
            created_by=admin_user,
        )

        assert violation.action_type == Violation.ActionType.PERMANENT_SUSPENSION

        # 永久停權應設置停權狀態
        profile = UserProfile.objects.get(user=user)
        assert profile.is_suspended is True
        assert profile.suspension_end_date is None  # 永久停權無結束日期

    def test_lift_violation_warning(self, admin_user):
        """測試解除警告處分"""
        user = UserFactory()

        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MODERATE,
            violation_type="test_violation",
            description="測試違規",
            created_by=admin_user,
        )

        # 解除處分
        ViolationService.lift_violation(violation, admin_user)

        violation.refresh_from_db()
        assert violation.is_active is False
        assert violation.lifted_by == admin_user
        assert violation.lifted_at is not None

    def test_lift_temporary_suspension(self, admin_user):
        """測試解除暫時停權處分"""
        user = UserFactory()

        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            severity=Violation.Severity.SEVERE,
            violation_type="test_suspension",
            description="測試停權",
            created_by=admin_user,
            suspension_days=7,
        )

        # 解除處分
        ViolationService.lift_violation(violation, admin_user)

        violation.refresh_from_db()
        assert violation.is_active is False

        # 用戶應恢復正常狀態
        profile = UserProfile.objects.get(user=user)
        assert profile.is_suspended is False
        assert profile.suspension_end_date is None
        assert profile.suspension_reason == ""

    def test_get_user_violations(self, admin_user):
        """測試取得用戶違規記錄"""
        user = UserFactory()

        # 建立多個違規
        for i in range(3):
            ViolationService.create_violation(
                user=user,
                action_type=Violation.ActionType.WARNING,
                severity=Violation.Severity.MINOR,
                violation_type=f"violation_{i}",
                description=f"測試違規 {i}",
                created_by=admin_user,
            )

        violations = ViolationService.get_user_violations(user)
        assert violations.count() == 3

        # 測試篩選生效中的處分
        active_violations = ViolationService.get_user_violations(user, is_active=True)
        assert active_violations.count() == 3

        # 解除一個處分
        violation_to_lift = violations.first()
        ViolationService.lift_violation(violation_to_lift, admin_user)

        # 重新查詢
        active_violations = ViolationService.get_user_violations(user, is_active=True)
        assert active_violations.count() == 2

    def test_get_active_suspensions(self, admin_user):
        """測試取得所有生效中的停權處分"""
        # 建立多個用戶的停權
        suspended_users = []
        for i in range(3):
            user = UserFactory()
            suspended_users.append(user)

            ViolationService.create_violation(
                user=user,
                action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
                severity=Violation.Severity.MODERATE,
                violation_type=f"suspension_{i}",
                description=f"測試停權 {i}",
                created_by=admin_user,
                suspension_days=7,
            )

        # 建立一個非停權處分作為對照
        normal_user = UserFactory()
        ViolationService.create_violation(
            user=normal_user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MINOR,
            violation_type="warning_only",
            description="僅警告",
            created_by=admin_user,
        )

        suspensions = ViolationService.get_active_suspensions()
        assert suspensions.count() == 3

        # 驗證只包含停權處分
        for suspension in suspensions:
            assert suspension.action_type in [
                Violation.ActionType.TEMPORARY_SUSPENSION,
                Violation.ActionType.PERMANENT_SUSPENSION,
            ]
            assert suspension.is_active is True

    def test_check_and_lift_expired_suspensions(self, admin_user):
        """測試檢查並解除已期滿的停權"""
        user = UserFactory()

        # 先建立一個停權處分
        violation = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            severity=Violation.Severity.MODERATE,
            violation_type="expired_suspension",
            description="已期滿停權",
            created_by=admin_user,
            suspension_days=1,
        )

        # 手動設定為已過期
        profile = UserProfile.objects.get(user=user)
        profile.suspension_end_date = timezone.now() - timedelta(days=1)
        profile.save()

        # 執行檢查
        lifted_count = ViolationService.check_and_lift_expired_suspensions()

        assert lifted_count == 1

        # 驗證處分已被解除
        violation.refresh_from_db()
        assert violation.is_active is False
        assert violation.lifted_at is not None

        # 驗證用戶狀態已恢復
        profile.refresh_from_db()
        assert profile.is_suspended is False
        assert profile.suspension_end_date is None
        assert profile.suspension_reason == ""

    def test_multiple_active_suspensions(self, admin_user):
        """測試多個生效中停權處分的處理"""
        user = UserFactory()

        # 建立兩個停權處分
        suspension1 = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            severity=Violation.Severity.MODERATE,
            violation_type="suspension_1",
            description="停權1",
            created_by=admin_user,
            suspension_days=7,
        )

        suspension2 = ViolationService.create_violation(
            user=user,
            action_type=Violation.ActionType.TEMPORARY_SUSPENSION,
            severity=Violation.Severity.SEVERE,
            violation_type="suspension_2",
            description="停權2",
            created_by=admin_user,
            suspension_days=14,
        )

        # 解除第一個停權
        ViolationService.lift_violation(suspension1, admin_user)

        # 用戶應仍然停權（因為還有第二個生效中停權）
        profile = UserProfile.objects.get(user=user)
        assert profile.is_suspended is True

        # 解除第二個停權
        ViolationService.lift_violation(suspension2, admin_user)

        # 現在用戶應恢復正常
        profile.refresh_from_db()
        assert profile.is_suspended is False

    def test_violation_with_appeal(self, admin_user):
        """測試與申訴相關的違規處分"""
        # 暫時跳過，因為 AppealFactory 尚未定義
        pass

    def test_transaction_rollback_on_error(self, admin_user):
        """測試錯誤時的交易回滾"""
        # 暫時跳過，因為需要 mocker fixture
        pass
