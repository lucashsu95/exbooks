"""
交易 Web 端存取控制回歸測試（H-1 / M-1）。

- H-1：交易詳情（含私訊）僅限 applicant / responder / 書籍 owner / keeper。
- M-1：接受 / 拒絕 / 取消交易只接受 POST（防止 <img> GET 觸發 CSRF）；
  allauth 登出不接受 GET。
"""

import pytest
from django.conf import settings
from django.urls import reverse

from deals.models import Deal
from tests.factories import DealFactory, DealMessageFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestDealDetailAccess:
    def setup_method(self):
        self.owner = UserFactory()
        self.keeper = UserFactory()
        self.deal = DealFactory(
            shared_book__owner=self.owner,
            shared_book__keeper=self.keeper,
            responder=self.keeper,
        )
        DealMessageFactory(deal=self.deal, content="私密留言內容 secret-xyz")
        self.url = reverse("deals:detail", kwargs={"pk": self.deal.pk})

    def test_outsider_gets_404(self, client):
        client.force_login(UserFactory())
        res = client.get(self.url)
        assert res.status_code == 404
        assert b"secret-xyz" not in res.content

    @pytest.mark.parametrize("who", ["applicant", "responder", "owner", "keeper"])
    def test_parties_can_view(self, client, who):
        user = {
            "applicant": self.deal.applicant,
            "responder": self.deal.responder,
            "owner": self.owner,
            "keeper": self.keeper,
        }[who]
        client.force_login(user)
        res = client.get(self.url)
        assert res.status_code == 200

    def test_rule_can_view_deal(self):
        assert self.deal.applicant.has_perm("deals.can_view_deal", self.deal)
        assert self.owner.has_perm("deals.can_view_deal", self.deal)
        assert not UserFactory().has_perm("deals.can_view_deal", self.deal)


class TestDealStateChangeRequiresPost:
    @pytest.mark.parametrize(
        "name, actor",
        [("deals:accept", "responder"), ("deals:reject", "responder"), ("deals:cancel", "applicant")],
    )
    def test_get_is_rejected_and_state_unchanged(self, client, name, actor):
        deal = DealFactory()
        client.force_login(getattr(deal, actor))
        res = client.get(reverse(name, kwargs={"pk": deal.pk}))
        assert res.status_code == 405
        deal.refresh_from_db()
        assert deal.status == Deal.Status.REQUESTED

    def test_post_accept_still_works(self, client):
        from books.models import SharedBook

        deal = DealFactory(shared_book__status=SharedBook.Status.TRANSFERABLE)
        client.force_login(deal.responder)
        res = client.post(reverse("deals:accept", kwargs={"pk": deal.pk}))
        assert res.status_code == 302
        deal.refresh_from_db()
        assert deal.status == Deal.Status.RESPONDED


def test_logout_on_get_disabled(client):
    assert settings.ACCOUNT_LOGOUT_ON_GET is False
    user = UserFactory()
    client.force_login(user)
    client.get(reverse("account_logout"))
    # GET 只顯示確認頁，不登出
    assert "_auth_user_id" in client.session
