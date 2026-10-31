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


# ---------------------------------------------------------------------------
# 審查後修正：交易當事人單一規則 + 子路由對非當事人一律 404
# ---------------------------------------------------------------------------


def _isolated_party_deal(**kwargs):
    """owner / keeper / applicant / responder 各為不同人的交易。"""
    owner = UserFactory()
    keeper = UserFactory()
    deal = DealFactory(
        shared_book__owner=owner,
        shared_book__keeper=keeper,
        responder=UserFactory(),
        **kwargs,
    )
    return deal, owner, keeper


class TestDealPartyRule:
    def test_is_deal_party_is_composed_from_existing_predicates(self):
        from deals import rules as deal_rules

        assert deal_rules.is_deal_party.name == "((is_involved | is_owner) | is_keeper)"

    @pytest.mark.parametrize("who", ["applicant", "responder", "owner", "keeper"])
    def test_every_party_matches(self, who):
        from deals.rules import is_deal_party

        deal, owner, keeper = _isolated_party_deal()
        user = {
            "applicant": deal.applicant,
            "responder": deal.responder,
            "owner": owner,
            "keeper": keeper,
        }[who]
        assert is_deal_party(user, deal) is True

    def test_outsider_and_anonymous_do_not_match(self):
        from django.contrib.auth.models import AnonymousUser

        from deals.rules import is_deal_party

        deal, _, _ = _isolated_party_deal()
        assert is_deal_party(UserFactory(), deal) is False
        assert is_deal_party(AnonymousUser(), deal) is False
        assert is_deal_party(UserFactory(), None) is False


DEAL_SUB_ROUTES = [
    ("deals:accept", "post"),
    ("deals:reject", "post"),
    ("deals:cancel", "post"),
    ("deals:complete", "post"),
    ("deals:message_send", "post"),
    ("deals:rating_create", "get"),
    ("deals:confirm_return", "post"),
    ("deals:exception_resolve", "get"),
    ("deals:upload_photos", "get"),
]


class TestDealSubRoutesHideFromOutsiders:
    @pytest.mark.parametrize("name, method", DEAL_SUB_ROUTES)
    def test_outsider_gets_404(self, client, name, method):
        deal, _, _ = _isolated_party_deal()
        client.force_login(UserFactory())
        res = getattr(client, method)(reverse(name, kwargs={"pk": deal.pk}))
        assert res.status_code == 404
        deal.refresh_from_db()
        assert deal.status == Deal.Status.REQUESTED

    def test_extension_request_outsider_gets_404(self, client):
        deal, _, _ = _isolated_party_deal()
        client.force_login(UserFactory())
        res = client.get(
            reverse("deals:extension_request", kwargs={"deal_pk": deal.pk})
        )
        assert res.status_code == 404

    @pytest.mark.parametrize(
        "name",
        ["deals:extension_approve", "deals:extension_reject", "deals:extension_cancel"],
    )
    def test_extension_actions_outsider_gets_404(self, client, name):
        from deals.models import LoanExtension

        deal, _, _ = _isolated_party_deal()
        extension = LoanExtension.objects.create(
            deal=deal, requested_by=deal.applicant, extra_days=7
        )
        client.force_login(UserFactory())
        res = client.post(reverse(name, kwargs={"extension_pk": extension.pk}))
        assert res.status_code == 404
        extension.refresh_from_db()
        assert extension.status == LoanExtension.Status.PENDING

    def test_party_without_action_permission_keeps_redirect(self, client):
        deal, _, _ = _isolated_party_deal()
        client.force_login(deal.applicant)
        res = client.post(reverse("deals:accept", kwargs={"pk": deal.pk}))
        assert res.status_code == 302
        deal.refresh_from_db()
        assert deal.status == Deal.Status.REQUESTED

    def test_owner_party_can_send_message(self, client):
        deal, owner, _ = _isolated_party_deal()
        client.force_login(owner)
        res = client.post(
            reverse("deals:message_send", kwargs={"pk": deal.pk}),
            {"content": "owner 留言"},
        )
        assert res.status_code == 200
