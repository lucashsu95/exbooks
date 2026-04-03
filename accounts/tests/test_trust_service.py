"""
信用等級服務測試。
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.services.trust_service import (
    calculate_trust_level,
    update_trust_score,
    get_borrowing_limits,
    initialize_existing_user,
)
from deals.models import Deal
from tests.factories import DealFactory, RatingFactory

User = get_user_model()


class TrustServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="password"
        )

    def test_calculate_trust_level_new_user(self):
        """測試新用戶預設信用等級為 0"""
        level = calculate_trust_level(self.user)
        self.assertEqual(level, 0)

    def test_calculate_trust_level_level_1(self):
        """測試達到 Level 1 的條件（3筆交易，無評價要求，逾期<=2）"""
        # 建立 3 筆完成交易
        for _ in range(3):
            DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 1)

    def test_calculate_trust_level_level_2(self):
        """測試達到 Level 2 的條件（10筆交易，評價>=4.0，逾期<=1）"""
        # 建立 10 筆完成交易
        for _ in range(10):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            # 給予 5 星評價
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                friendliness_score=5,
                punctuality_score=5,
                accuracy_score=5,
            )

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 2)

    def test_calculate_trust_level_level_3(self):
        """測試達到 Level 3 的條件（30筆交易，評價>=4.5，逾期=0）"""
        # 建立 30 筆完成交易
        for _ in range(30):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            # 給予 5 星評價
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                friendliness_score=5,
                punctuality_score=5,
                accuracy_score=5,
            )

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 3)

    def test_calculate_trust_level_with_overdue(self):
        """測試逾期次數對信用等級的影響"""
        # 建立 10 筆完成交易和 5 星評價（本應是 Level 2）
        for _ in range(10):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                friendliness_score=5,
                punctuality_score=5,
                accuracy_score=5,
            )

        # 增加 2 次逾期（Level 2 要求 <= 1，所以會降到 Level 1）
        self.user.profile.overdue_count = 2
        self.user.profile.save()

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 1)

        # 增加 3 次逾期（Level 1 要求 <= 2，所以會降到 Level 0）
        self.user.profile.overdue_count = 3
        self.user.profile.save()

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 0)

    def test_update_trust_score(self):
        """測試更新用戶信用積分"""
        # 建立 3 筆完成交易
        for _ in range(3):
            DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )

        new_score = update_trust_score(self.user)
        self.assertEqual(new_score, 30)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.trust_score, 30)
        self.assertEqual(self.user.profile.trust_stars, 5)
        self.assertEqual(self.user.profile.trust_level, 3)

    def test_get_borrowing_limits_level_0(self):
        """測試 Level 0 借閱限制"""
        limits = get_borrowing_limits(0)
        self.assertEqual(limits["max_books"], 1)
        self.assertEqual(limits["max_days"], 30)

    def test_get_borrowing_limits_level_3(self):
        """測試 Level 3 借閱限制"""
        limits = get_borrowing_limits(3)
        self.assertEqual(limits["max_books"], float("inf"))
        self.assertEqual(limits["max_days"], float("inf"))

    def test_initialize_existing_user(self):
        """測試初始化現有用戶"""
        initial_score = initialize_existing_user(self.user)
        self.assertEqual(initial_score, 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.trust_score, 0)
        self.assertEqual(self.user.profile.trust_level, 1)
