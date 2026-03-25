import pytest
from django.db import IntegrityError

from accounts.models import Appeal, UserProfile
from tests.factories import UserFactory


pytestmark = pytest.mark.django_db


class TestAppeal:
    """Appeal 模型測試"""

    def test_create_appeal_with_default_status(self):
        """測試建立申訴時預設狀態為已提交"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="測試申訴標題",
            description="這是一個測試申訴的詳細描述內容，至少需要五十個字元才能通過驗證。",
        )
        assert appeal.pk is not None
        assert appeal.status == Appeal.Status.SUBMITTED

    def test_appeal_uuid_primary_key(self):
        """測試申訴使用 UUID 主鍵"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="測試",
            description="這是一個測試申訴的詳細描述內容，至少需要五十個字元才能通過驗證。",
        )
        assert isinstance(appeal.id.__class__, type)
        assert len(str(appeal.id)) == 36  # UUID format

    def test_appeal_status_choices_valid(self):
        """測試所有狀態選項皆有效"""
        valid_statuses = [choice[0] for choice in Appeal.Status.choices]
        assert Appeal.Status.SUBMITTED in valid_statuses
        assert Appeal.Status.UNDER_REVIEW in valid_statuses
        assert Appeal.Status.APPROVED in valid_statuses
        assert Appeal.Status.REJECTED in valid_statuses
        assert Appeal.Status.CLOSED in valid_statuses

    def test_appeal_type_choices_valid(self):
        """測試所有申訴類型皆有效"""
        valid_types = [choice[0] for choice in Appeal.AppealType.choices]
        assert Appeal.AppealType.ACCOUNT_SUSPENSION in valid_types
        assert Appeal.AppealType.RATING_DISPUTE in valid_types
        assert Appeal.AppealType.OVERDUE_DISPUTE in valid_types
        assert Appeal.AppealType.OTHER in valid_types

    def test_appeal_str_representation(self):
        """測試字串表示正確"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="測試申訴",
            description="這是一個測試申訴的詳細描述內容，至少需要五十個字元才能通過驗證。",
        )
        assert "測試申訴" in str(appeal)

    def test_can_transition_to_valid_status(self):
        """測試狀態轉換驗證方法"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="測試",
            description="這是一個測試申訴的詳細描述內容，至少需要五十個字元才能通過驗證。",
        )
        # SUBMITTED can transition to UNDER_REVIEW or CLOSED
        assert appeal.can_transition_to(Appeal.Status.UNDER_REVIEW) is True
        assert appeal.can_transition_to(Appeal.Status.CLOSED) is True
        assert appeal.can_transition_to(Appeal.Status.APPROVED) is False

    def test_appeal_user_cascade_delete(self):
        """測試刪除用戶時申訴一併刪除"""
        user = UserFactory()
        appeal = Appeal.objects.create(
            user=user,
            appeal_type=Appeal.AppealType.OTHER,
            title="測試",
            description="這是一個測試申訴的詳細描述內容，至少需要五十個字元才能通過驗證。",
        )
        appeal_id = appeal.id
        user.delete()
        assert not Appeal.objects.filter(id=appeal_id).exists()

    def test_appeal_db_table(self):
        """測試資料表名稱"""
        assert Appeal._meta.db_table == "exbook_appeal"


class TestUserProfile:
    def test_create(self):
        """Signal 自動建立 UserProfile。"""
        user = UserFactory()
        profile = user.profile
        assert profile.pk is not None
        assert profile.user == user
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_default_transferability(self):
        user = UserFactory()
        assert (
            user.profile.default_transferability == UserProfile.Transferability.RETURN
        )

    def test_str_nickname(self):
        user = UserFactory()
        profile = user.profile
        profile.nickname = "小明"
        profile.save(update_fields=["nickname"])
        assert str(profile) == "小明"

    def test_str_fallback_full_name(self):
        user = UserFactory(first_name="明", last_name="王")
        profile = user.profile
        profile.nickname = ""
        profile.save(update_fields=["nickname"])
        result = str(profile)
        # Falls back to get_full_name() or username
        assert result  # Non-empty

    def test_str_fallback_username(self):
        user = UserFactory(first_name="", last_name="")
        profile = user.profile
        profile.nickname = ""
        profile.save(update_fields=["nickname"])
        # Falls back to email since username is no longer used
        assert str(profile) == user.email

    def test_one_to_one_user(self):
        """Signal 已建立 profile，手動再建一個應衝突。"""
        user = UserFactory()
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=user)

    def test_transferability_choices(self):
        assert UserProfile.Transferability.TRANSFER == "TRANSFER"
        assert UserProfile.Transferability.RETURN == "RETURN"

    def test_available_schedule_default(self):
        user = UserFactory()
        assert user.profile.available_schedule == []

    def test_db_table(self):
        assert UserProfile._meta.db_table == "exbook_user_profile"
