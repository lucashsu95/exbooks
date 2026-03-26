"""
信用等級服務測試。
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.services.trust_service import (
    calculate_trust_level,
    update_trust_level,
    get_borrowing_limits,
    initialize_existing_user,
)
from deals.models import Deal
from tests.factories import DealFactory, RatingFactory, UserProfileFactory

User = get_user_model()


class TrustServiceTest(TestCase):
    def setUp(self):
        self.user = UserProfileFactory().user
        self.other_user = UserProfileFactory().user

    def test_initialize_existing_user(self):
        """測試初始化現有用戶信用等級"""
        level = initialize_existing_user(self.user)
        self.assertEqual(level, 1)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.trust_level, 1)

    def test_calculate_trust_level_new_user(self):
        """測試新用戶信用等級 (Level 0)"""
        level = calculate_trust_level(self.user)
        self.assertEqual(level, 0)

    def test_calculate_trust_level_general_user(self):
        """測試一般用戶信用等級 (Level 1)"""
        # 建立 3 筆完成交易
        for _ in range(3):
            deal = DealFactory(  # noqa: F841
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 1)

    def test_calculate_trust_level_reliable_user(self):
        """測試可信用戶信用等級 (Level 2)"""
        # 建立 10 筆完成交易
        deals = []
        for _ in range(10):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            deals.append(deal)

        # 建立評價，平均分數 >= 4
        for deal in deals[:5]:  # 給其中 5 筆交易評價
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                integrity_score=4,
                punctuality_score=4,
                accuracy_score=4,
            )

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 2)

    def test_calculate_trust_level_excellent_user(self):
        """測試優良用戶信用等級 (Level 3)"""
        # 建立 30 筆完成交易
        deals = []
        for _ in range(30):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            deals.append(deal)

        # 建立評價，平均分數 >= 4.5
        for deal in deals[:15]:  # 給其中 15 筆交易評價
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                integrity_score=5,
                punctuality_score=5,
                accuracy_score=4,
            )  # 平均分數 = (5+5+4)/3 = 4.67

        # 確保沒有逾期
        self.user.profile.overdue_count = 0
        self.user.profile.save()

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 3)

    def test_calculate_trust_level_demoted_for_overdue(self):
        """測試因逾期次數過多而降級"""
        # 建立 10 筆完成交易和良好評價 (本應為 Level 2)
        deals = []
        for _ in range(10):
            deal = DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )
            deals.append(deal)

        for deal in deals[:5]:
            RatingFactory(
                deal=deal,
                rater=self.other_user,
                ratee=self.user,
                integrity_score=4,
                punctuality_score=4,
                accuracy_score=4,
            )

        # 但有 3 次逾期，應該降為 Level 0
        self.user.profile.overdue_count = 3
        self.user.profile.save()

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 0)

    def test_update_trust_level(self):
        """測試更新用戶信用等級"""
        # 建立 3 筆完成交易使用戶達到 Level 1
        for _ in range(3):
            DealFactory(
                applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
            )

        new_level = update_trust_level(self.user)
        self.assertEqual(new_level, 1)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.trust_level, 1)

    def test_get_borrowing_limits_level_0(self):
        """測試 Level 0 借閱限制"""
        limits = get_borrowing_limits(0)
        self.assertEqual(limits["max_books"], 1)
        self.assertEqual(limits["max_days"], 30)

    def test_get_borrowing_limits_level_1(self):
        """測試 Level 1 借閱限制"""
        limits = get_borrowing_limits(1)
        self.assertEqual(limits["max_books"], 3)
        self.assertEqual(limits["max_days"], 60)

    def test_get_borrowing_limits_level_2(self):
        """測試 Level 2 借閱限制"""
        limits = get_borrowing_limits(2)
        self.assertEqual(limits["max_books"], 5)
        self.assertEqual(limits["max_days"], 90)

    def test_get_borrowing_limits_level_3(self):
        """測試 Level 3 借閱限制"""
        limits = get_borrowing_limits(3)
        self.assertEqual(limits["max_books"], float("inf"))
        self.assertEqual(limits["max_days"], float("inf"))

    def test_get_borrowing_limits_invalid_level(self):
        """測試無效等級的借閱限制"""
        limits = get_borrowing_limits(99)
        # 應該回傳 Level 0 的限制
        self.assertEqual(limits["max_books"], 1)
        self.assertEqual(limits["max_days"], 30)
