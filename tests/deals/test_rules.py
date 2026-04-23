import pytest
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    SharedBookFactory,
    UserFactory,
)
from deals.models import Deal

pytestmark = pytest.mark.django_db


import pytest

pytestmark = pytest.mark.django_db


class TestPredicates:
    """測試 deals/rules.py 中的謂詞 (Predicates)。"""

    def test_is_applicant(self):
        user = UserFactory()
        deal = DealFactory(applicant=user)
        other_user = UserFactory()

        from deals.rules import is_applicant
        assert is_applicant(user, deal) is True
        assert is_applicant(other_user, deal) is False
        assert is_applicant(user, None) is False

    def test_is_responder(self):
        user = UserFactory()
        deal = DealFactory(responder=user)
        other_user = UserFactory()

        from deals.rules import is_responder
        assert is_responder(user, deal) is True
        assert is_responder(other_user, deal) is False

    def test_is_owner(self):
        user = UserFactory()
        book = SharedBookFactory(owner=user)
        deal = DealFactory(shared_book=book)
        other_user = UserFactory()

        from deals.rules import is_owner
        assert is_owner(user, deal) is True
        assert is_owner(other_user, deal) is False

    def test_is_keeper(self):
        user = UserFactory()
        book = SharedBookFactory(keeper=user)
        deal = DealFactory(shared_book=book)
        other_user = UserFactory()

        from deals.rules import is_keeper
        assert is_keeper(user, deal) is True
        assert is_keeper(other_user, deal) is False

    def test_is_involved(self):
        applicant = UserFactory()
        responder = UserFactory()
        deal = DealFactory(applicant=applicant, responder=responder)
        other_user = UserFactory()

        from deals.rules import is_involved
        assert is_involved(applicant, deal) is True
        assert is_involved(responder, deal) is True
        assert is_involved(other_user, deal) is False

    def test_is_extension_applicant(self):
        user = UserFactory()
        extension = LoanExtensionFactory(requested_by=user)
        other_user = UserFactory()

        from deals.rules import is_extension_applicant
        assert is_extension_applicant(user, extension) is True
        assert is_extension_applicant(other_user, extension) is False

    def test_is_extension_reviewer(self):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=keeper)
        deal = DealFactory(shared_book=book)
        extension = LoanExtensionFactory(deal=deal)
        other_user = UserFactory()

        from deals.rules import is_extension_reviewer
        assert is_extension_reviewer(owner, extension) is True
        assert is_extension_reviewer(keeper, extension) is True
        assert is_extension_reviewer(other_user, extension) is False



class TestPermissions:
    """測試 deals/rules.py 中的權限 (Permissions)。"""

    def test_can_accept_deal(self):
        responder = UserFactory()
        deal = DealFactory(responder=responder)
        other_user = UserFactory()

        assert responder.has_perm("deals.can_accept_deal", deal) is True
        assert other_user.has_perm("deals.can_accept_deal", deal) is False

    def test_can_decline_deal(self):
        responder = UserFactory()
        deal = DealFactory(responder=responder)
        assert responder.has_perm("deals.can_decline_deal", deal) is True

    def test_can_cancel_deal(self):
        applicant = UserFactory()
        deal = DealFactory(applicant=applicant)
        assert applicant.has_perm("deals.can_cancel_deal", deal) is True

    def test_can_complete_meeting(self):
        applicant = UserFactory()
        responder = UserFactory()
        deal = DealFactory(applicant=applicant, responder=responder)
        assert applicant.has_perm("deals.can_complete_meeting", deal) is True
        assert responder.has_perm("deals.can_complete_meeting", deal) is True

    def test_can_approve_extension(self):
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)
        deal = DealFactory(shared_book=book)
        extension = LoanExtensionFactory(deal=deal)
        assert owner.has_perm("deals.can_approve_extension", extension) is True

    def test_can_upload_deal_photos(self):
        keeper = UserFactory()
        book = SharedBookFactory(keeper=keeper)
        deal = DealFactory(shared_book=book)
        other_user = UserFactory()

        assert keeper.has_perm("deals.can_upload_deal_photos", deal) is True
        assert other_user.has_perm("deals.can_upload_deal_photos", deal) is False


class TestFSMTransitions:
    """測試 Deal 模型中的 FSM 轉換條件。"""

    def test_both_rated_condition(self):
        deal = DealFactory(status=Deal.Status.MEETED)
        
        # Initially False
        assert deal._both_rated() is False

        # One rated
        deal.applicant_rated = True
        assert deal._both_rated() is False

        # Both rated
        deal.responder_rated = True
        assert deal._both_rated() is True

    def test_accept_deal_side_effects(self):
        """測試 accept_deal 的副作用（BR-15 & 書籍狀態更新）。"""
        book = SharedBookFactory(status="T")  # TRANSFERABLE
        deal1 = DealFactory(shared_book=book, status=Deal.Status.REQUESTED)
        deal2 = DealFactory(shared_book=book, status=Deal.Status.REQUESTED)

        deal1.accept()
        deal1.save()

        # Check deal1
        assert deal1.status == Deal.Status.RESPONDED
        
        # Check deal2 (BR-15: Auto-cancelled)
        deal2.refresh_from_db()
        assert deal2.status == Deal.Status.CANCELLED

        # Check book status
        book.refresh_from_db()
        assert book.status == "V"  # RESERVED

    def test_cancel_request_restores_book_status(self):
        """測試 cancel_request 恢復書籍狀態 (BR-14)。"""
        book = SharedBookFactory(status="R")
        deal = DealFactory(shared_book=book, status=Deal.Status.REQUESTED, previous_book_status="T")
        
        deal.cancel_request()
        
        book.refresh_from_db()
        assert book.status == "T"
