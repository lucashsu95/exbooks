from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ai.services.tool_registry import (
    ConsentRequirement,
    ToolDefinition,
    ToolRegistry,
    get_borrowing_status,
    get_user_books,
    request_renewal,
)
from deals.models import Deal, LoanExtension
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    SharedBookFactory,
    UserFactory,
)


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
        get_books = ToolRegistry.get_tool("get_user_books")
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)

        result = get_books.func(owner, status="OWNED")
        self.assertIn(book.official_book.title, result)
        self.assertIn(f"#{book.pk}", result)

        renewal = ToolRegistry.get_tool("request_renewal")
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)

        result = renewal.func(user=borrower, deal_id=deal.pk)
        self.assertIn(str(deal.pk), result)
        self.assertIn("待審核", result)


class GetUserBooksTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_owned(self):
        book = SharedBookFactory(owner=self.user, keeper=UserFactory())
        result = get_user_books(self.user, status="OWNED")
        self.assertIn(book.official_book.title, result)
        self.assertIn(f"#{book.pk}", result)
        self.assertIn(book.get_status_display(), result)
        self.assertIn(f"持有者：{book.keeper.username}", result)

    def test_held(self):
        book = SharedBookFactory(owner=UserFactory(), keeper=self.user)
        result = get_user_books(self.user, status="HELD")
        self.assertIn(book.official_book.title, result)

    def test_all_union_without_duplicate(self):
        both = SharedBookFactory(owner=self.user, keeper=self.user)
        owned_only = SharedBookFactory(owner=self.user, keeper=UserFactory())
        held_only = SharedBookFactory(owner=UserFactory(), keeper=self.user)

        result = get_user_books(self.user, status="ALL")
        self.assertIn(f"#{both.pk}", result)
        self.assertIn(f"#{owned_only.pk}", result)
        self.assertIn(f"#{held_only.pk}", result)
        # owner==keeper 的書在 ALL 只出現一次
        self.assertEqual(result.count(f"#{both.pk}"), 1)

    def test_empty(self):
        other = UserFactory()
        SharedBookFactory(owner=other, keeper=other)
        self.assertEqual(get_user_books(self.user, status="OWNED"), "你沒有擁有的書籍。")
        self.assertEqual(get_user_books(self.user, status="HELD"), "你沒有持有的書籍。")
        self.assertEqual(get_user_books(self.user, status="ALL"), "你沒有符合的書籍。")

    def test_truncation_at_20(self):
        for _ in range(25):
            SharedBookFactory(owner=self.user)
        result = get_user_books(self.user, status="OWNED")
        lines = result.split("\n")
        self.assertEqual(len(lines), 21)  # 20 本書 + 1 行尾注
        self.assertIn("另有 5 本未列出", lines[-1])

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_user_books(self.user, status="JUNK")
        message = str(ctx.exception)
        for value in ("OWNED", "HELD", "ALL"):
            self.assertIn(value, message)

    def test_status_case_insensitive(self):
        book = SharedBookFactory(owner=self.user, keeper=UserFactory())
        self.assertEqual(
            get_user_books(self.user, status="owned"),
            get_user_books(self.user, status="OWNED"),
        )
        self.assertIn(f"#{book.pk}", get_user_books(self.user, status="owned"))


class GetBorrowingStatusTests(TestCase):
    def test_active_loan_line(self):
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(
            owner, borrower, due_date=timezone.localdate() + timedelta(days=7)
        )
        result = get_borrowing_status(borrower)
        line = next(line for line in result.split("\n") if f"#{deal.pk}" in line)
        self.assertIn(deal.shared_book.official_book.title, line)
        self.assertIn(deal.get_status_display(), line)
        self.assertIn("到期日", line)
        self.assertIn("剩 7 天", line)

    def test_responder_sees_own_loans(self):
        """出借者視角也要列得出（答「誰借了我的書」）。"""
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)
        result = get_borrowing_status(owner)
        self.assertIn(f"#{deal.pk}", result)

    def test_excludes_terminal_deals(self):
        owner = UserFactory()
        borrower = UserFactory()
        _, active = _make_borrowing(owner, borrower)
        book_done = SharedBookFactory(owner=UserFactory())
        done = DealFactory(shared_book=book_done, status="D")
        book_cancelled = SharedBookFactory(owner=UserFactory())
        cancelled = DealFactory(shared_book=book_cancelled, status="X")
        other_transfer = DealFactory(
            shared_book=SharedBookFactory(owner=UserFactory()),
            applicant=UserFactory(),
            deal_type=Deal.DealType.TRANSFER,
            status="M",
        )

        result = get_borrowing_status(borrower)
        self.assertIn(f"#{active.pk}", result)
        self.assertNotIn(f"#{done.pk}", result)
        self.assertNotIn(f"#{cancelled.pk}", result)
        self.assertNotIn(f"#{other_transfer.pk}", result)

    def _line_of(self, result, deal):
        return next(line for line in result.split("\n") if f"#{deal.pk}" in line)

    def test_pending_extension_shown(self):
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)
        LoanExtensionFactory(deal=deal, extra_days=14, status=LoanExtension.Status.PENDING)

        result = get_borrowing_status(borrower)
        self.assertIn("你已申請延長 14 天（待審核）", result)

    def test_pending_extension_borrower_view(self):
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)
        LoanExtensionFactory(deal=deal, extra_days=14, status=LoanExtension.Status.PENDING)

        line = self._line_of(get_borrowing_status(borrower), deal)
        self.assertIn("你已申請延長 14 天（待審核）", line)
        self.assertIn(f"借閱者：{borrower.username}", line)

    def test_pending_extension_lender_view(self):
        """出借者視角：pending 是借閱者建的，不能寫成「你已申請」，也要看得出是誰借的。"""
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(owner, borrower)
        LoanExtensionFactory(deal=deal, extra_days=14, status=LoanExtension.Status.PENDING)

        line = self._line_of(get_borrowing_status(owner), deal)
        self.assertIn("借閱者已申請延長 14 天（待你審核）", line)
        self.assertNotIn("你已申請", line)
        self.assertIn(f"借閱者：{borrower.username}", line)

    def test_overdue_flag(self):
        owner = UserFactory()
        borrower = UserFactory()
        _, deal = _make_borrowing(
            owner, borrower, due_date=timezone.localdate() - timedelta(days=3)
        )
        result = get_borrowing_status(borrower)
        line = next(line for line in result.split("\n") if f"#{deal.pk}" in line)
        self.assertIn("已逾期 3 天", line)

    def test_no_due_date_omits_segment(self):
        """Q/P 階段 deal 沒有到期日，行內不寫到期日片段。"""
        owner = UserFactory()
        book = SharedBookFactory(owner=owner, status="T")
        deal = DealFactory(shared_book=book, applicant=UserFactory(), responder=owner)
        result = get_borrowing_status(deal.applicant)
        line = next(line for line in result.split("\n") if f"#{deal.pk}" in line)
        self.assertNotIn("到期日", line)

    def test_empty(self):
        result = get_borrowing_status(UserFactory())
        self.assertEqual(result, "你目前沒有進行中的借閱交易。")


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
        self.assertEqual(
            (LoanExtension.MIN_EXTRA_DAYS, LoanExtension.MAX_EXTRA_DAYS), (7, 30)
        )
