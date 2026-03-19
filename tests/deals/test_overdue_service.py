"""
逾期公開服務測試。
"""

from datetime import date, timedelta
from django.test import TestCase
from deals.services.overdue_service import (
    get_overdue_books,
    get_public_overdue_info,
    get_overdue_status,
)
from deals.models import Deal
from tests.factories import (
    DealFactory,
    UserProfileFactory,
    OfficialBookFactory,
    SharedBookFactory,
)


class OverdueServiceTest(TestCase):
    def setUp(self):
        self.borrower = UserProfileFactory().user
        self.lender = UserProfileFactory().user
        self.official_book = OfficialBookFactory()
        self.shared_book = SharedBookFactory(
            official_book=self.official_book,
            owner=self.lender,
            keeper=self.borrower,
        )

    def test_get_overdue_books_returns_overdue_deals(self):
        """測試取得逾期書籍"""
        # 建立逾期 10 天的交易
        overdue_date = date.today() - timedelta(days=10)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=overdue_date,
        )

        # 取得逾期 7 天以上的書籍
        overdue_deals = get_overdue_books(days=7)
        self.assertIn(deal, overdue_deals)

    def test_get_overdue_books_excludes_recent_deals(self):
        """測試不包含未逾期的交易"""
        # 建立逾期 2 天的交易
        recent_date = date.today() - timedelta(days=2)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=recent_date,
        )

        # 取得逾期 7 天以上的書籍
        overdue_deals = get_overdue_books(days=7)
        self.assertNotIn(deal, overdue_deals)

    def test_get_public_overdue_info_returns_correct_data(self):
        """測試取得可公開的逾期資訊"""
        overdue_date = date.today() - timedelta(days=10)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=overdue_date,
        )

        info = get_public_overdue_info(deal)
        self.assertEqual(info["nickname"], self.borrower.profile.nickname)
        self.assertEqual(info["book_title"], self.official_book.title)
        self.assertEqual(info["overdue_days"], 10)
        self.assertFalse(info["is_severe"])

    def test_get_public_overdue_info_severe_overdue(self):
        """測試嚴重逾期（≥14天）標記"""
        overdue_date = date.today() - timedelta(days=15)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=overdue_date,
        )

        info = get_public_overdue_info(deal)
        self.assertTrue(info["is_severe"])

    def test_get_public_overdue_info_uses_email_prefix_when_no_nickname(self):
        """測試無暱稱時使用 Email 前綴"""
        self.borrower.profile.nickname = ""
        self.borrower.profile.save()

        overdue_date = date.today() - timedelta(days=5)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=overdue_date,
        )

        info = get_public_overdue_info(deal)
        expected_nickname = self.borrower.email.split("@")[0]
        self.assertEqual(info["nickname"], expected_nickname)

    def test_get_overdue_status_none(self):
        """測試逾期狀態：無逾期"""
        due_date = date.today() - timedelta(days=2)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=due_date,
        )

        status = get_overdue_status(deal)
        self.assertEqual(status, "none")

    def test_get_overdue_status_warning(self):
        """測試逾期狀態：警告（3-6天）"""
        due_date = date.today() - timedelta(days=5)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=due_date,
        )

        status = get_overdue_status(deal)
        self.assertEqual(status, "warning")

    def test_get_overdue_status_public(self):
        """測試逾期狀態：公開（7-13天）"""
        due_date = date.today() - timedelta(days=10)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=due_date,
        )

        status = get_overdue_status(deal)
        self.assertEqual(status, "public")

    def test_get_overdue_status_severe(self):
        """測試逾期狀態：嚴重（≥14天）"""
        due_date = date.today() - timedelta(days=15)
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=due_date,
        )

        status = get_overdue_status(deal)
        self.assertEqual(status, "severe")

    def test_get_overdue_status_no_due_date(self):
        """測試無到期日的交易"""
        deal = DealFactory(
            applicant=self.borrower,
            responder=self.lender,
            shared_book=self.shared_book,
            status=Deal.Status.MEETED,
            due_date=None,
        )

        status = get_overdue_status(deal)
        self.assertEqual(status, "none")
