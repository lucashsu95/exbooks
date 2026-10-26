from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase

from deals.models import Deal, LoanExtension, Notification
from deals.services.extension_service import (
    approve_extension,
    cancel_extension,
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
        request_extension(deal, applicant, extra_days=14)
        assert Notification.objects.filter(
            recipient=owner,
            notification_type="EXTEND_REQUESTED",
        ).exists()


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
