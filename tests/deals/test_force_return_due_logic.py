import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from deals.models import Deal
from deals.services.deal_service import confirm_return
from tests.factories import SharedBookFactory, DealFactory, UserFactory

pytestmark = pytest.mark.django_db

class TestForceReturnDueLogic:
    def test_cannot_force_return_if_not_overdue(self):
        """[P0] 測試：未逾期時，無法強制歸還。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, status="O", transferability="RETURN")
        
        # 設定到期日為明天（尚未逾期）
        due_date = timezone.now().date() + timedelta(days=1)
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=due_date
        )

        with pytest.raises(ValidationError, match="交易尚未逾期"):
            confirm_return(deal, confirmed_by=owner, force=True)

    def test_can_force_return_if_overdue(self):
        """[P0] 測試：已逾期時，可以強制歸還。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, status="O", transferability="RETURN")
        
        # 設定到期日為昨天（已逾期）
        due_date = timezone.now().date() - timedelta(days=1)
        deal = DealFactory(
            shared_book=book,
            deal_type="LN",
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=due_date
        )

        returned_deal = confirm_return(deal, confirmed_by=owner, force=True)
        assert returned_deal.status == "D"
        assert returned_deal.applicant_rated is True
        assert returned_deal.responder_rated is True

    def test_transfer_deal_cannot_force_return(self):
        """[P0] 測試：開放傳遞的 TF 交易永遠無法強制歸還。"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner, status="O", transferability="TRANSFER")
        
        deal = DealFactory(
            shared_book=book,
            deal_type="TF",
            status="M",
            applicant=applicant,
            responder=owner,
            due_date=timezone.now().date() - timedelta(days=10) # 即使逾期
        )

        with pytest.raises(ValidationError, match="不支援強制歸還"):
            confirm_return(deal, confirmed_by=applicant, force=True)

