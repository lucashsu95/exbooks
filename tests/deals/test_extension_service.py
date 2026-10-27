from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from deals.models import Deal, LoanExtension, Notification
from deals.services.extension_service import (
    approve_extension,
    cancel_extension,
    is_extension_eligible,
    reject_extension,
    request_extension,
)
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    SharedBookFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


# ============================================================
# request_extension
# ============================================================
class TestRequestExtension:
    def test_success(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        ext = request_extension(deal, applicant, extra_days=14)
        assert ext.deal == deal
        assert ext.requested_by == applicant
        assert ext.extra_days == 14
        assert ext.status == LoanExtension.Status.PENDING

    def test_non_occupied_raises(self):
        book = SharedBookFactory(status="T")
        deal = DealFactory(shared_book=book, status="M")
        with pytest.raises(ValidationError, match="借閱中"):
            request_extension(deal, deal.applicant, extra_days=14)

    def test_non_applicant_raises(self):
        book = SharedBookFactory(status="O")
        deal = DealFactory(shared_book=book, status="M")
        stranger = UserFactory()
        with pytest.raises(ValidationError, match="借閱者"):
            request_extension(deal, stranger, extra_days=14)

    def test_extra_days_below_min_raises(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with pytest.raises(ValidationError):
            request_extension(deal, applicant, extra_days=6)
        assert not LoanExtension.objects.exists()
        assert not Notification.objects.exists()

    def test_extra_days_above_max_raises(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with pytest.raises(ValidationError):
            request_extension(deal, applicant, extra_days=31)
        assert not LoanExtension.objects.exists()
        assert not Notification.objects.exists()

    def test_non_integer_extra_days_raises_validation_error(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with pytest.raises(ValidationError):
            request_extension(deal, applicant, extra_days="abc")
        assert not LoanExtension.objects.exists()
        assert not Notification.objects.exists()

    def test_none_extra_days_raises_validation_error(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with pytest.raises(ValidationError):
            request_extension(deal, applicant, extra_days=None)

    @patch(
        "deals.services.extension_service.record_exchange_event",
        side_effect=RuntimeError("event boom"),
    )
    def test_rollback_leaves_no_external_side_effects(self, _mock_event):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with (
            patch("deals.tasks.send_push_notification_task") as mock_push,
            patch("deals.tasks.send_email_notification_task") as mock_email,
        ):
            with pytest.raises(RuntimeError):
                request_extension(deal, applicant, extra_days=14)
        assert not LoanExtension.objects.exists()
        assert not Notification.objects.exists()
        mock_push.delay.assert_not_called()
        mock_email.delay.assert_not_called()

    def test_existing_pending_extension_raises(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        LoanExtensionFactory(deal=deal, requested_by=applicant)
        with pytest.raises(ValidationError, match="待審核"):
            request_extension(deal, applicant, extra_days=14)
        assert deal.extensions.count() == 1

    @patch.object(
        LoanExtension.objects,
        "create",
        side_effect=IntegrityError(
            "Duplicate entry for key 'uniq_loan_extension_one_pending_per_deal'"
        ),
    )
    def test_integrity_error_on_race_raises_friendly_validation(self, _mock_create):
        """#21: 非 service 寫入者在 guard 與 INSERT 之間 commit 同 deal PENDING 時，
        DB constraint 的 IntegrityError 轉成友善 ValidationError（不裸 500）。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with pytest.raises(ValidationError, match="待審核"):
            request_extension(deal, applicant, extra_days=14)

    def test_request_allowed_after_rejection(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.REJECTED,
        )
        ext = request_extension(deal, applicant, extra_days=14)
        assert ext.status == LoanExtension.Status.PENDING

    def test_notification_sent_to_responder(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        with TestCase.captureOnCommitCallbacks(execute=True):
            request_extension(deal, applicant, extra_days=14)
        assert Notification.objects.filter(
            recipient=owner,
            notification_type="EXTEND_REQUESTED",
        ).exists()


# ============================================================
# is_extension_eligible — 讀側資格判定（單一來源）
# ============================================================
class TestIsExtensionEligible:
    """讀側判定：web 入口與 AI 標記共用的資格規則。"""

    def _eligible_deal(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        return deal, applicant, owner

    def test_eligible(self):
        deal, applicant, _ = self._eligible_deal()
        assert is_extension_eligible(applicant, deal) is True

    def test_book_not_occupied(self):
        book = SharedBookFactory(status="T")
        deal = DealFactory(shared_book=book, status="M")
        assert is_extension_eligible(deal.applicant, deal) is False

    def test_responder_not_eligible(self):
        deal, _, owner = self._eligible_deal()
        assert is_extension_eligible(owner, deal) is False

    def test_stranger_not_eligible(self):
        deal, _, _ = self._eligible_deal()
        assert is_extension_eligible(UserFactory(), deal) is False

    def test_pending_extension_blocks(self):
        deal, applicant, _ = self._eligible_deal()
        LoanExtensionFactory(deal=deal, requested_by=applicant)
        assert is_extension_eligible(applicant, deal) is False

    def test_rejected_extension_does_not_block(self):
        deal, applicant, _ = self._eligible_deal()
        LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.REJECTED,
        )
        assert is_extension_eligible(applicant, deal) is True

    def test_pending_param_is_trusted_and_skips_db(self):
        """傳入 pending（含明確的 None）時不再查 DB——AI read tool 靠這保住查詢量上界。"""
        deal, applicant, _ = self._eligible_deal()
        deal = Deal.objects.select_related("shared_book", "applicant").get(pk=deal.pk)
        with CaptureQueriesContext(connection) as ctx:
            assert is_extension_eligible(applicant, deal, pending=None) is True
        assert len(ctx.captured_queries) == 0

    def test_pending_object_param_is_trusted_and_skips_db(self):
        deal, applicant, _ = self._eligible_deal()
        ext = LoanExtensionFactory(deal=deal, requested_by=applicant)
        deal = Deal.objects.select_related("shared_book", "applicant").get(pk=deal.pk)
        with CaptureQueriesContext(connection) as ctx:
            assert is_extension_eligible(applicant, deal, pending=ext) is False
        assert len(ctx.captured_queries) == 0

    def test_db_lookup_when_pending_omitted(self):
        deal, applicant, _ = self._eligible_deal()
        deal = Deal.objects.select_related("shared_book", "applicant").get(pk=deal.pk)
        with CaptureQueriesContext(connection) as ctx:
            assert is_extension_eligible(applicant, deal) is True
        assert len(ctx.captured_queries) == 1


class TestEligibilityConsistentWithRequest:
    """讀側判定與寫側 guards 是同一條規則：
    is_extension_eligible 為 True ⟺ request_extension 成功。
    改規則時這張表會同時卡到兩邊，防止再漂移。"""

    def test_eligible_agrees(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        assert is_extension_eligible(applicant, deal) is True
        request_extension(deal, applicant, extra_days=14)  # 不得拋錯

    def test_non_occupied_agrees(self):
        book = SharedBookFactory(status="T")
        deal = DealFactory(shared_book=book, status="M")
        assert is_extension_eligible(deal.applicant, deal) is False
        with pytest.raises(ValidationError):
            request_extension(deal, deal.applicant, extra_days=14)

    def test_non_applicant_agrees(self):
        book = SharedBookFactory(status="O")
        deal = DealFactory(shared_book=book, status="M")
        stranger = UserFactory()
        assert is_extension_eligible(stranger, deal) is False
        with pytest.raises(ValidationError):
            request_extension(deal, stranger, extra_days=14)

    def test_pending_agrees(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
        )
        LoanExtensionFactory(deal=deal, requested_by=applicant)
        assert is_extension_eligible(applicant, deal) is False
        with pytest.raises(ValidationError):
            request_extension(deal, applicant, extra_days=14)


# ============================================================
# approve_extension
# ============================================================
class TestApproveExtension:
    def test_success(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=date.today() + timedelta(days=10),
        )
        ext = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            extra_days=14,
        )
        original_due = deal.due_date
        approve_extension(ext, owner)
        ext.refresh_from_db()
        deal.refresh_from_db()
        assert ext.status == LoanExtension.Status.APPROVED
        assert ext.approved_by == owner
        assert deal.due_date == original_due + timedelta(days=14)

    def test_non_pending_raises(self):
        ext = LoanExtensionFactory(status="APPROVED")
        with pytest.raises(ValidationError, match="待審核"):
            approve_extension(ext, ext.deal.responder)

    def test_non_responder_raises(self):
        ext = LoanExtensionFactory()
        stranger = UserFactory()
        with pytest.raises(ValidationError, match="Owner 或 Keeper"):
            approve_extension(ext, stranger)

    def test_notification_sent_to_applicant(self):
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=date.today() + timedelta(days=10),
        )
        ext = LoanExtensionFactory(deal=deal, requested_by=applicant)
        with TestCase.captureOnCommitCallbacks(execute=True):
            approve_extension(ext, owner)
        assert Notification.objects.filter(
            recipient=applicant,
            notification_type="EXTEND_APPROVED",
        ).exists()

    @patch(
        "deals.services.extension_service.record_exchange_event",
        side_effect=RuntimeError("event boom"),
    )
    def test_rollback_leaves_no_external_side_effects(self, _mock_event):
        """回滾時 Celery 任務不得已外發（通知須延遲到 commit 後）。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=date.today() + timedelta(days=10),
        )
        ext = LoanExtensionFactory(deal=deal, requested_by=applicant)
        with (
            patch("deals.tasks.send_push_notification_task") as mock_push,
            patch("deals.tasks.send_email_notification_task") as mock_email,
        ):
            with pytest.raises(RuntimeError):
                approve_extension(ext, owner)
        ext.refresh_from_db()
        assert ext.status == LoanExtension.Status.PENDING
        deal.refresh_from_db()
        mock_push.delay.assert_not_called()
        mock_email.delay.assert_not_called()

    def test_stale_approve_object_does_not_double_extend_due_date(self):
        """第二個 approve 交易讀到核准前的舊 extension 快照時，
        不得把 due_date 再延長一次。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=applicant, status="O")
        deal = DealFactory(
            shared_book=book,
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=date.today() + timedelta(days=10),
        )
        ext_stale = LoanExtensionFactory(deal=deal, requested_by=applicant, extra_days=14)
        original_due = deal.due_date
        with TestCase.captureOnCommitCallbacks(execute=True):
            approve_extension(LoanExtension.objects.get(pk=ext_stale.pk), owner)
        deal.refresh_from_db()
        assert deal.due_date == original_due + timedelta(days=14)
        # 第二個 approve 交易：extension 是核准前的舊快照（in-memory 仍 PENDING），
        # deal 已是核准後（due 已 +14）
        ext_stale.deal = Deal.objects.get(pk=deal.pk)
        with pytest.raises(ValidationError, match="待審核"):
            approve_extension(ext_stale, owner)
        deal.refresh_from_db()
        assert deal.due_date == original_due + timedelta(days=14)


# ============================================================
# reject_extension
# ============================================================
class TestRejectExtension:
    def test_success(self):
        ext = LoanExtensionFactory()
        responder = ext.deal.responder
        reject_extension(ext, responder)
        ext.refresh_from_db()
        assert ext.status == LoanExtension.Status.REJECTED
        assert ext.approved_by == responder

    def test_non_pending_raises(self):
        ext = LoanExtensionFactory(status="APPROVED")
        with pytest.raises(ValidationError, match="待審核"):
            reject_extension(ext, ext.deal.responder)

    def test_non_responder_raises(self):
        ext = LoanExtensionFactory()
        stranger = UserFactory()
        with pytest.raises(ValidationError, match="Owner 或 Keeper"):
            reject_extension(ext, stranger)

    def test_notification_sent_to_applicant(self):
        ext = LoanExtensionFactory()
        responder = ext.deal.responder
        with TestCase.captureOnCommitCallbacks(execute=True):
            reject_extension(ext, responder)
        assert Notification.objects.filter(
            recipient=ext.requested_by,
            notification_type="EXTEND_REJECTED",
        ).exists()

    @patch(
        "deals.services.extension_service.record_exchange_event",
        side_effect=RuntimeError("event boom"),
    )
    def test_rollback_leaves_no_external_side_effects(self, _mock_event):
        """回滾時狀態不得已 commit、Celery 任務不得已外發。"""
        ext = LoanExtensionFactory()
        responder = ext.deal.responder
        with (
            patch("deals.tasks.send_push_notification_task") as mock_push,
            patch("deals.tasks.send_email_notification_task") as mock_email,
        ):
            with pytest.raises(RuntimeError):
                reject_extension(ext, responder)
        ext.refresh_from_db()
        assert ext.status == LoanExtension.Status.PENDING
        assert not Notification.objects.exists()
        mock_push.delay.assert_not_called()
        mock_email.delay.assert_not_called()


# ============================================================
# cancel_extension — BR-16
# ============================================================
class TestCancelExtension:
    def test_br16_cancel_pending(self):
        ext = LoanExtensionFactory()
        cancel_extension(ext, ext.requested_by)
        ext.refresh_from_db()
        assert ext.status == LoanExtension.Status.REJECTED

    def test_non_pending_raises(self):
        ext = LoanExtensionFactory(status="APPROVED")
        with pytest.raises(ValidationError, match="待審核"):
            cancel_extension(ext, ext.requested_by)

    def test_non_applicant_raises(self):
        ext = LoanExtensionFactory()
        stranger = UserFactory()
        with pytest.raises(ValidationError, match="申請者"):
            cancel_extension(ext, stranger)

    @patch(
        "deals.services.extension_service.record_exchange_event",
        side_effect=RuntimeError("event boom"),
    )
    def test_rollback_leaves_no_persisted_status_change(self, _mock_event):
        """回滾時狀態轉換不得已 commit。"""
        ext = LoanExtensionFactory()
        with pytest.raises(RuntimeError):
            cancel_extension(ext, ext.requested_by)
        ext.refresh_from_db()
        assert ext.status == LoanExtension.Status.PENDING
