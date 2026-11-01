"""
他人顯示名稱不得洩漏 email：暱稱空白時一律顯示「會員#<pk>」。
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone

from accounts.models import Appeal
from books.services.book_timeline_service import BookTimelineService
from deals.models import Deal
from deals.services.overdue_service import get_public_overdue_info
from tests.factories import DealFactory, RatingFactory, SharedBookFactory, UserFactory

pytestmark = pytest.mark.django_db

SECRET_EMAIL = "secret.leak@private.test"
SECRET_USERNAME = "secretlogin"


def _assert_no_leak(html: str) -> None:
    assert SECRET_EMAIL not in html
    assert "secret.leak" not in html
    assert SECRET_USERNAME not in html


@pytest.fixture
def hidden() -> User:
    """暱稱空白的會員（signal 會預設暱稱為 email 前綴，這裡刻意清空）。"""
    user = UserFactory(username=SECRET_USERNAME, email=SECRET_EMAIL, first_name="")
    user.profile.nickname = ""
    user.profile.save()
    return user


@pytest.fixture
def viewer_client(client):
    viewer = UserFactory()
    client.force_login(viewer)
    client.viewer = viewer
    return client


class TestDisplayName:
    def test_blank_nickname_shows_member_number(self, hidden):
        assert hidden.profile.display_name == f"會員#{hidden.pk}"

    def test_nickname_is_used_when_present(self):
        user = UserFactory()
        user.profile.nickname = "小明"
        user.profile.save()
        assert user.profile.display_name == "小明"

    def test_template_filter(self, hidden):
        html = Template("{% load user_tags %}{{ u|display_name }}").render(
            Context({"u": hidden})
        )
        assert html == f"會員#{hidden.pk}"

    def test_template_filter_handles_none(self):
        html = Template("{% load user_tags %}[{{ u|display_name }}]").render(
            Context({"u": None})
        )
        assert html == "[]"


class TestPublicPagesDoNotLeakEmail:
    def test_public_profile(self, viewer_client, hidden):
        SharedBookFactory(owner=hidden)
        partner = UserFactory()
        DealFactory(
            applicant=partner,
            shared_book=SharedBookFactory(owner=hidden),
            status=Deal.Status.DONE,
        )
        for tab in ("books", "deals", "ratings"):
            resp = viewer_client.get(
                reverse("accounts:public_profile", args=[hidden.pk]), {"tab": tab}
            )
            assert resp.status_code == 200
            html = resp.content.decode()
            _assert_no_leak(html)
            assert f"會員#{hidden.pk}" in html

    def test_public_profile_deal_counterpart(self, viewer_client, hidden):
        other = UserFactory()
        deal = DealFactory(
            applicant=hidden,
            shared_book=SharedBookFactory(owner=other),
            status=Deal.Status.DONE,
        )
        RatingFactory(deal=deal, rater=hidden, ratee=other)
        for tab in ("deals",):
            resp = viewer_client.get(
                reverse("accounts:public_profile", args=[other.pk]), {"tab": tab}
            )
            html = resp.content.decode()
            _assert_no_leak(html)
            assert f"會員#{hidden.pk}" in html

    def test_book_detail_keeper(self, viewer_client, hidden):
        book = SharedBookFactory(owner=hidden)
        resp = viewer_client.get(reverse("books:detail", args=[book.pk]))
        assert resp.status_code == 200
        html = resp.content.decode()
        _assert_no_leak(html)
        assert f"會員#{hidden.pk}" in html

    def test_user_ratings(self, viewer_client, hidden):
        other = UserFactory()
        deal = DealFactory(applicant=hidden, shared_book=SharedBookFactory(owner=other))
        RatingFactory(deal=deal, rater=hidden, ratee=other)
        resp = viewer_client.get(reverse("accounts:user_ratings", args=[other.pk]))
        html = resp.content.decode()
        _assert_no_leak(html)
        assert f"會員#{hidden.pk}" in html

    def test_user_ratings_of_hidden_user(self, viewer_client, hidden):
        resp = viewer_client.get(reverse("accounts:user_ratings", args=[hidden.pk]))
        html = resp.content.decode()
        _assert_no_leak(html)
        assert f"會員#{hidden.pk}" in html

    def test_appeal_detail_reviewer(self, viewer_client, hidden):
        appeal = Appeal.objects.create(
            user=viewer_client.viewer,
            appeal_type=Appeal.AppealType.OTHER,
            title="申訴",
            description="說明",
            resolved_by=hidden,
            resolved_at=timezone.now(),
        )
        resp = viewer_client.get(reverse("accounts:appeal_detail", args=[appeal.id]))
        html = resp.content.decode()
        _assert_no_leak(html)
        assert f"會員#{hidden.pk}" in html


class TestOverdueInfoDoesNotLeakEmail:
    def _overdue_deal(self, borrower: User) -> Deal:
        return DealFactory(
            applicant=borrower,
            status=Deal.Status.MEETED,
            due_date=timezone.now().date() - timedelta(days=10),
        )

    def test_public_overdue_info_uses_member_number(self, hidden):
        info = get_public_overdue_info(self._overdue_deal(hidden))
        assert info["nickname"] == f"會員#{hidden.pk}"

    def test_overdue_list_page(self, client, hidden):
        self._overdue_deal(hidden)
        resp = client.get(reverse("books:overdue_list"))
        assert resp.status_code == 200
        html = resp.content.decode()
        _assert_no_leak(html)
        assert f"會員#{hidden.pk}" in html


class TestTimelineDoesNotLeakEmail:
    def test_user_display_uses_member_number(self, hidden):
        text = BookTimelineService._format_user_display(hidden)
        assert SECRET_EMAIL not in text
        assert f"會員#{hidden.pk}" in text
