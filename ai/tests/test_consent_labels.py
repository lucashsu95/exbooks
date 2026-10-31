import uuid

import pytest

from ai.services.consent_labels import describe_consent
from tests.factories import DealFactory, SharedBookFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_renewal_with_own_deal_includes_title():
    user = UserFactory()
    book = SharedBookFactory(keeper=user, status="O", official_book__title="小王子")
    deal = DealFactory(shared_book=book, applicant=user, status="M")
    text = describe_consent(user, "request_renewal", {"deal_id": str(deal.pk), "days": 7})
    assert text == "申請延長借閱《小王子》7 天"


def test_renewal_other_users_deal_hides_title():
    user = UserFactory()
    deal = DealFactory(
        shared_book=SharedBookFactory(status="O", official_book__title="別人的書"),
        status="M",
    )
    text = describe_consent(user, "request_renewal", {"deal_id": str(deal.pk), "days": 14})
    assert text == "申請延長借閱 14 天"


@pytest.mark.parametrize("deal_id", ["not-a-uuid", None, str(uuid.uuid4())])
def test_renewal_unknown_deal_generic(deal_id):
    assert describe_consent(UserFactory(), "request_renewal", {"deal_id": deal_id}) == "申請延長借閱 7 天"


def test_unknown_tool_generic():
    assert describe_consent(UserFactory(), "mystery", {}) == "執行這項操作"
