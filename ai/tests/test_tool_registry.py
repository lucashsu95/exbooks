from django.test import TestCase

from ai.services.tool_registry import (
    ConsentRequirement,
    ToolDefinition,
    ToolRegistry,
    _extension_day_bounds,
    request_renewal,
)
from deals.models import LoanExtension
from tests.factories import DealFactory, SharedBookFactory, UserFactory


def _make_borrowing(owner, borrower, due_date=None):
    """「借閱中」組態：書在 borrower 手上、LOAN deal 已面交。"""
    book = SharedBookFactory(owner=owner, keeper=borrower, status="O")
    deal = DealFactory(
        shared_book=book,
        applicant=borrower,
        responder=owner,
        status="M",
    )
    if due_date is not None:
        deal.due_date = due_date
        deal.save(update_fields=["due_date"])
    return book, deal


class ToolRegistryTests(TestCase):
    def test_registry_contains_predefined_tools(self):
        """Ensure the registry contains the three required tools."""
        tools = ToolRegistry.get_all_tools()
        tool_names = [t.name for t in tools]

        self.assertIn("get_user_books", tool_names)
        self.assertIn("get_borrowing_status", tool_names)
        self.assertIn("request_renewal", tool_names)

    def test_get_tool_by_name(self):
        """Ensure we can retrieve a specific tool by name."""
        tool = ToolRegistry.get_tool("get_user_books")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "get_user_books")
        self.assertIsInstance(tool, ToolDefinition)

    def test_tool_consent_requirements(self):
        """Ensure consent requirements are correctly set."""
        get_books = ToolRegistry.get_tool("get_user_books")
        renewal = ToolRegistry.get_tool("request_renewal")

        self.assertEqual(get_books.consent, ConsentRequirement.NOT_REQUIRED)
        self.assertEqual(renewal.consent, ConsentRequirement.USER_CONFIRM)

    def test_tool_execution(self):
        """Tools run with injected user and return the real book data."""
        renewal = ToolRegistry.get_tool("request_renewal")
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)

        result = renewal.func(user=borrower, deal_id=deal.pk)
        self.assertIn(str(deal.pk), result)
        self.assertIn("待審核", result)


class RequestRenewalTests(TestCase):
    def setUp(self):
        self.owner = UserFactory()
        self.borrower = UserFactory()
        self.book, self.deal = _make_borrowing(self.owner, self.borrower)

    def _pending_count(self):
        return self.deal.extensions.filter(status=LoanExtension.Status.PENDING).count()

    def test_creates_pending_extension(self):
        result = request_renewal(self.borrower, self.deal.pk, days=14)
        self.assertEqual(self._pending_count(), 1)
        self.assertIn(f"#{self.deal.pk}", result)
        self.assertIn(self.book.official_book.title, result)
        self.assertIn("14 天", result)
        self.assertIn("待審核", result)
        self.assertNotIn("已延長", result)

    def test_days_defaults_to_7(self):
        request_renewal(self.borrower, self.deal.pk)
        extension = self.deal.extensions.get()
        self.assertEqual(extension.extra_days, 7)

    def test_days_out_of_range_raises_without_creating(self):
        for bad_days in (5, 31):
            with self.subTest(days=bad_days):
                with self.assertRaises(ValueError) as ctx:
                    request_renewal(self.borrower, self.deal.pk, days=bad_days)
                self.assertIn("7~30", str(ctx.exception))
        self.assertEqual(self._pending_count(), 0)

    def test_days_non_numeric_raises(self):
        with self.assertRaises(ValueError) as ctx:
            request_renewal(self.borrower, self.deal.pk, days="abc")
        self.assertIn("整數", str(ctx.exception))
        self.assertEqual(self._pending_count(), 0)

    def test_deal_id_passed_as_string(self):
        result = request_renewal(self.borrower, str(self.deal.pk))
        self.assertIn(f"#{self.deal.pk}", result)
        self.assertEqual(self._pending_count(), 1)

    def test_missing_deal_raises(self):
        import uuid

        with self.assertRaises(ValueError) as ctx:
            request_renewal(self.borrower, uuid.uuid4())
        self.assertIn("不存在", str(ctx.exception))
        self.assertIn("get_borrowing_status", str(ctx.exception))

    def test_malformed_deal_id_raises_friendly_message(self):
        """非 UUID 字串不能走到 UUIDField 的 raw ValidationError。"""
        with self.assertRaises(ValueError) as ctx:
            request_renewal(self.borrower, "not-a-uuid")
        message = str(ctx.exception)
        self.assertIn("不存在", message)
        self.assertIn("get_borrowing_status", message)
        self.assertEqual(self._pending_count(), 0)

    def test_responder_rejected(self):
        """responder（出借者）與路人同吃 service 的權限錯誤，tool 不複寫檢查。"""
        for caller in (self.owner, UserFactory()):
            with self.subTest(caller=caller):
                with self.assertRaises(ValueError) as ctx:
                    request_renewal(caller, self.deal.pk)
                self.assertIn("只有借閱者", str(ctx.exception))
                self.assertNotIn("[", str(ctx.exception))
        self.assertEqual(self._pending_count(), 0)

    def test_book_not_occupied_raises_service_message(self):
        book = SharedBookFactory(owner=self.owner, keeper=self.borrower, status="T")
        deal = DealFactory(shared_book=book, applicant=self.borrower, responder=self.owner)
        with self.assertRaises(ValueError) as ctx:
            request_renewal(self.borrower, deal.pk)
        self.assertIn("借閱中", str(ctx.exception))
        self.assertNotIn("[", str(ctx.exception))

    def test_second_request_allowed(self):
        """領域規則：同一筆交易可多次申請，每筆獨立審核。"""
        request_renewal(self.borrower, self.deal.pk)
        request_renewal(self.borrower, self.deal.pk, days=30)
        self.assertEqual(self._pending_count(), 2)

    def test_extension_day_bounds_pinned_to_model(self):
        self.assertEqual(_extension_day_bounds(), (7, 30))
