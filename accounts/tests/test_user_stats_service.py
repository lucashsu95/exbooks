"""
用戶統計服務測試。
"""

import pytest
from django.contrib.auth.models import User

from accounts.models import Violation
from accounts.services import user_stats_service


@pytest.mark.django_db
def test_get_violation_count_only_active():
    """只計算 is_active=True 的違規"""
    # 建立測試用戶
    user = User.objects.create_user(username="testuser", email="test@example.com")

    # 建立 3 個生效違規
    for i in range(3):
        Violation.objects.create(
            user=user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MINOR,
            violation_type=Violation.ViolationType.LATE_RETURN,
            description=f"Test violation {i + 1}",
            is_active=True,
        )

    # 建立 2 個已解除違規
    for i in range(2):
        violation = Violation.objects.create(
            user=user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MINOR,
            violation_type=Violation.ViolationType.LATE_RETURN,
            description=f"Test violation {i + 4}",
            is_active=True,
        )
        violation.is_active = False
        violation.save()

    # 測試：應該只計算 3 個生效違規
    count = user_stats_service.get_violation_count(user)
    assert count == 3


@pytest.mark.django_db
def test_get_violation_count_empty():
    """無違規時返回 0"""
    user = User.objects.create_user(username="testuser2", email="test2@example.com")
    count = user_stats_service.get_violation_count(user)
    assert count == 0


@pytest.mark.django_db
def test_get_violation_count_all_inactive():
    """全部已解除違規時返回 0"""
    user = User.objects.create_user(username="testuser3", email="test3@example.com")

    # 建立多個已解除違規
    for i in range(3):
        Violation.objects.create(
            user=user,
            action_type=Violation.ActionType.WARNING,
            severity=Violation.Severity.MINOR,
            violation_type=Violation.ViolationType.LATE_RETURN,
            description=f"Test violation {i + 1}",
            is_active=False,
        )

    count = user_stats_service.get_violation_count(user)
    assert count == 0
