import pytest
from django.db import IntegrityError

from accounts.models import UserProfile
from tests.factories import UserFactory, UserProfileFactory


pytestmark = pytest.mark.django_db


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
        assert str(profile) == user.username

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
