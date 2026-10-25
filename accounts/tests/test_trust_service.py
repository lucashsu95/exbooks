"""
信用等級服務測試。
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from accounts.models import TrustLevelConfig
from accounts.services.trust_service import (
    calculate_trust_level,
    update_trust_score,
    get_borrowing_limits,
    get_upgrade_progress,
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

        # 建立信用等級配置與對應 Group
        limits = {0: (1, 30), 1: (3, 60), 2: (5, 90), 3: (999, 999)}
        for level in range(4):
            Group.objects.get_or_create(name=f"trust_lv{level}")
            TrustLevelConfig.objects.get_or_create(
                level=level,
                defaults={
                    "group_name": f"trust_lv{level}",
                    "display_name": f"Level {level}",
                    "min_score": level * 10,
                    "max_books": limits[level][0],
                    "max_days": limits[level][1],
                    "demotion_protection_weeks": 26,
                },
            )

    def test_calculate_trust_level_new_user(self):
        """測試新用戶預設信用等級為 0"""
        level = calculate_trust_level(self.user)
        self.assertEqual(level, 0)

    def test_calculate_trust_level_level_1(self):
        """測試達到 Level 1 的條件（4-8 分）"""
        # 建立 1 筆完成交易與 1 分評價，分數 15
        deal = DealFactory(
            applicant=self.user, responder=self.other_user, status=Deal.Status.DONE
        )
        RatingFactory(
            deal=deal,
            rater=self.other_user,
            ratee=self.user,
            friendliness_score=1,
            punctuality_score=1,
            accuracy_score=1,
        )

        # 加入 1 次逾期，分數 15-10=5，對應 Level 1
        self.user.profile.overdue_count = 1
        self.user.profile.save(update_fields=["overdue_count", "updated_at"])

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 1)

    def test_calculate_trust_level_level_2(self):
        """測試達到 Level 2 的條件（9-15 分）"""
        # 建立 1 筆完成交易與 5 星評價，分數 35 -> 星等 5 -> Level 3
        for _ in range(1):
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

        # 以逾期降低分數至 15，對應 Level 2
        self.user.profile.overdue_count = 2
        self.user.profile.save(update_fields=["overdue_count", "updated_at"])

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
        # 建立 1 筆完成交易和 5 星評價（基礎分數 35）
        for _ in range(1):
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

        # 增加 3 次逾期，分數 35-30=5，對應 Level 1
        self.user.profile.overdue_count = 3
        self.user.profile.save(update_fields=["overdue_count", "updated_at"])

        level = calculate_trust_level(self.user)
        self.assertEqual(level, 1)

        # 增加 4 次逾期，分數 35-40=0（最低為 0），對應 Level 0
        self.user.profile.overdue_count = 4
        self.user.profile.save(update_fields=["overdue_count", "updated_at"])

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
        # trust_level is no longer updated by update_trust_score() (COMMIT 2)

    def test_get_borrowing_limits_level_0(self):
        """測試 Level 0 借閱限制"""
        limits = get_borrowing_limits(0)
        self.assertEqual(limits["max_books"], 1)
        self.assertEqual(limits["max_days"], 30)

    def test_upgrade_progress_requirements_text(self):
        """升級進度文案是使用者可見文字，需有斷言防回歸（曾發生編碼損傷）。"""
        progress = get_upgrade_progress(self.user)
        # 0 分 → 下一星等 2 星，門檻 4 分
        self.assertEqual(
            progress["requirements"][0],
            "再累積 4 分即可升級（門檻 4 分）",
        )

    def test_get_borrowing_limits_level_3(self):
        """測試 Level 3 借閱限制（999 = 無限制哨兵）"""
        limits = get_borrowing_limits(3)
        self.assertEqual(limits["max_books"], 999)
        self.assertEqual(limits["max_days"], 999)

    def test_borrowing_limits_single_source_is_db_config(self):
        """借閱限制只讀 TrustLevelConfig，改 DB 即生效。"""
        TrustLevelConfig.objects.filter(level=0).update(max_books=7)
        limits = get_borrowing_limits(0)
        self.assertEqual(limits["max_books"], 7)
