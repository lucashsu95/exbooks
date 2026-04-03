# -*- coding: utf-8 -*-
"""Export Service tests"""

import pytest
from django.core.cache import cache

from accounts.services import export_service
from accounts.services.export_service import (
    EXPORT_LIMIT_PER_DAY,
    ExportLimitExceededError,
)
from deals.models import Deal, Rating
from tests.factories import (
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """在每個測試前清除 cache"""
    cache.clear()
    yield
    cache.clear()


pytestmark = pytest.mark.django_db


class TestExportUserData:
    """Test export user data functionality"""

    def test_export_user_data_success(self):
        """Test successful export of user data"""
        user = UserFactory()

        data = export_service.export_user_data(user)

        assert "exported_at" in data
        assert "user_profile" in data
        assert "activity_stats" in data
        assert "ratings_received" in data
        # 根據 3.15 需求，不應包含 books_contributed
        assert "books_contributed" not in data
        # 根據 3.15 需求，不應包含 deals_history（只包含評價歷史）
        assert "deals_history" not in data

    def test_export_user_data_increments_count(self):
        """Test export increments cache count"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, 0, 86400)

        export_service.export_user_data(user)

        assert cache.get(cache_key) == 1

    def test_export_user_data_exceeds_limit(self):
        """Test export raises error when limit exceeded"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY, 86400)

        with pytest.raises(ExportLimitExceededError) as exc_info:
            export_service.export_user_data(user)

        assert "每日最多可匯出" in str(exc_info.value)

    def test_export_user_data_profile_info(self):
        """Test export includes user profile info"""
        user = UserFactory(email="test@example.com")
        profile = user.profile
        profile.nickname = "測試用戶"
        profile.trust_level = 2
        profile.successful_returns = 5
        profile.overdue_count = 1
        profile.save()

        data = export_service.export_user_data(user)

        profile_data = data["user_profile"]
        assert profile_data["email"] == "test@example.com"
        assert profile_data["nickname"] == "測試用戶"
        assert profile_data["trust_level"] == 2
        assert profile_data["successful_returns"] == 5
        assert profile_data["overdue_count"] == 1

    def test_export_user_data_no_profile(self):
        """Test export handles user without profile"""

        user = UserFactory()
        # Delete profile if exists
        if hasattr(user, "profile"):
            user.profile.delete()

        data = export_service.export_user_data(user)

        profile_data = data["user_profile"]
        # If no profile exists, the profile is None so nickname should be None
        # But UserFactory auto-creates profile, so we just verify the values are correct
        assert profile_data["trust_level"] == 1  # default
        assert profile_data["successful_returns"] == 0


class TestCheckExportLimit:
    """Test check export limit functionality"""

    def test_check_export_limit_under_limit(self):
        """Test no error when under limit"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY - 1, 86400)

        # Should not raise
        export_service.check_export_limit(user)

    def test_check_export_limit_at_limit(self):
        """Test error when at limit"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY, 86400)

        with pytest.raises(ExportLimitExceededError):
            export_service.check_export_limit(user)

    def test_check_export_limit_over_limit(self):
        """Test error when over limit"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY + 1, 86400)

        with pytest.raises(ExportLimitExceededError):
            export_service.check_export_limit(user)


class TestIncrementExportCount:
    """Test increment export count functionality"""

    def test_increment_from_zero(self):
        """Test increment from zero"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"

        export_service.increment_export_count(user)

        assert cache.get(cache_key) == 1

    def test_increment_existing_count(self):
        """Test increment existing count"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, 2, 86400)

        export_service.increment_export_count(user)

        assert cache.get(cache_key) == 3


class TestCollectActivityStats:
    """Test collect activity stats functionality"""

    def test_collect_activity_stats(self):
        """Test collect user's activity statistics"""
        user = UserFactory()
        official_book = OfficialBookFactory(title="測試書籍")
        # Create some books owned by user
        SharedBookFactory(official_book=official_book, owner=user, keeper=user)

        data = export_service.collect_user_data(user)
        stats = data["activity_stats"]

        assert "books_contributed_count" in stats
        assert "successful_borrows" in stats
        assert "successful_lends" in stats
        assert "overdue_count" in stats
        assert stats["books_contributed_count"] == 1

    def test_collect_activity_stats_empty(self):
        """Test collect activity stats when user has no activity"""
        user = UserFactory()

        data = export_service.collect_user_data(user)
        stats = data["activity_stats"]

        assert stats["books_contributed_count"] == 0
        assert stats["successful_borrows"] == 0
        assert stats["successful_lends"] == 0
        assert stats["overdue_count"] == 0


class TestCollectRatingsReceived:
    """Test collect ratings received functionality"""

    def test_collect_ratings_received(self):
        """Test collect user's received ratings"""
        user1 = UserFactory()
        user2 = UserFactory()
        official_book = OfficialBookFactory(title="測試書籍")
        shared_book = SharedBookFactory(
            official_book=official_book,
            owner=user1,
            keeper=user1,
        )
        deal = Deal.objects.create(
            shared_book=shared_book,
            deal_type=Deal.DealType.LOAN,
            status=Deal.Status.DONE,
            applicant=user2,
            responder=user1,
        )
        Rating.objects.create(
            deal=deal,
            rater=user2,
            ratee=user1,
            friendliness_score=5,
            punctuality_score=4,
            accuracy_score=5,
            comment="很棒的交易！",
        )

        data = export_service.collect_user_data(user1)
        ratings = data["ratings_received"]

        assert len(ratings) == 1
        assert ratings[0]["rater_email"] == user2.email
        assert ratings[0]["friendliness_score"] == 5
        assert ratings[0]["punctuality_score"] == 4
        assert ratings[0]["accuracy_score"] == 5
        assert abs(ratings[0]["average_score"] - 4.67) < 0.01  # (5+4+5)/3
        assert ratings[0]["comment"] == "很棒的交易！"
        assert ratings[0]["book_title"] == "測試書籍"

    def test_collect_ratings_empty(self):
        """Test collect ratings when user has no ratings"""
        user = UserFactory()

        data = export_service.collect_user_data(user)
        ratings = data["ratings_received"]

        assert len(ratings) == 0


class TestGetRemainingExports:
    """Test get remaining exports functionality"""

    def test_get_remaining_exports_from_zero(self):
        """Test remaining exports from zero"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, 0, 86400)

        remaining = export_service.get_remaining_exports(user)

        assert remaining == EXPORT_LIMIT_PER_DAY

    def test_get_remaining_exports_partial(self):
        """Test remaining exports with partial usage"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, 1, 86400)

        remaining = export_service.get_remaining_exports(user)

        assert remaining == EXPORT_LIMIT_PER_DAY - 1

    def test_get_remaining_exports_at_limit(self):
        """Test remaining exports when at limit"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY, 86400)

        remaining = export_service.get_remaining_exports(user)

        assert remaining == 0

    def test_get_remaining_exports_over_limit(self):
        """Test remaining exports when over limit"""
        user = UserFactory()
        cache_key = f"export_limit_{user.id}"
        cache.set(cache_key, EXPORT_LIMIT_PER_DAY + 5, 86400)

        remaining = export_service.get_remaining_exports(user)

        assert remaining == 0

    def test_get_remaining_exports_no_cache(self):
        """Test remaining exports when no cache entry"""
        user = UserFactory()
        # Ensure no cache entry
        cache.delete(f"export_limit_{user.id}")

        remaining = export_service.get_remaining_exports(user)

        assert remaining == EXPORT_LIMIT_PER_DAY
