from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError

from deals.models import LoanExtension, Notification
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
        approve_extension(ext, owner)
        assert Notification.objects.filter(
            recipient=applicant,
            notification_type="EXTEND_APPROVED",
        ).exists()


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
        reject_extension(ext, responder)
        assert Notification.objects.filter(
            recipient=ext.requested_by,
            notification_type="EXTEND_REJECTED",
        ).exists()


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
