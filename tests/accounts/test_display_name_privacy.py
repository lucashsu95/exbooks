"""
他人顯示名稱不得洩漏 email：暱稱空白時一律顯示「會員#<pk>」。
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import Appeal
from accounts.services.display_name_service import display_name_for
from accounts.services.export_service import export_user_data
from books.serializers import SharedBookSerializer
from books.services.book_timeline_service import BookTimelineService
from deals.models import Deal, DealMessage, LoanExtension, Notification
from deals.serializers import (
    DealMessageSerializer,
    DealSerializer,
    LoanExtensionSerializer,
)
from deals.services import notification_service as ns
from deals.services.overdue_service import get_public_overdue_info
from tests.factories import (
    DealFactory,
    DealMessageFactory,
    LoanExtensionFactory,
    RatingFactory,
    SharedBookFactory,
    UserFactory,
)

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
        assert display_name_for(hidden) == f"會員#{hidden.pk}"

    def test_nickname_is_used_when_present(self):
        user = UserFactory()
        user.profile.nickname = "小明"
        user.profile.save()
        assert display_name_for(user) == "小明"

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


class TestDisplayNameService:
    def test_blank_nickname(self, hidden):
        assert display_name_for(hidden) == f"會員#{hidden.pk}"

    def test_none(self):
        assert display_name_for(None) == ""

    def test_profile_str_does_not_leak_email(self, hidden):
        text = str(hidden.profile)
        _assert_no_leak(text)
        assert f"會員#{hidden.pk}" in text


class TestNotificationsDoNotLeakEmail:
    """通知文字（站內、API、Email）不得含對方 email／帳號名稱。"""

    def _assert_notifications_clean(self, recipient: User) -> None:
        texts = [
            f"{n.title} {n.message}"
            for n in Notification.objects.filter(recipient=recipient)
        ]
        assert texts
        for text in texts:
            _assert_no_leak(text)
        for message in mail.outbox:
            _assert_no_leak(f"{message.subject} {message.body}")

    def test_deal_requested(self, hidden):
        deal = DealFactory(applicant=hidden)
        ns.notify_deal_requested(deal)
        self._assert_notifications_clean(deal.responder)
        assert mail.outbox  # Email 也有寄出並受檢

        n = Notification.objects.get(recipient=deal.responder)
        assert f"會員#{hidden.pk}" in n.message
        assert deal.shared_book.official_book.title in n.message

    def test_deal_responded_with_hidden_owner(self, hidden):
        applicant = UserFactory()
        deal = DealFactory(
            applicant=applicant,
            responder=hidden,
            shared_book=SharedBookFactory(owner=hidden),
        )
        ns.notify_deal_responded(deal)
        self._assert_notifications_clean(applicant)

    def test_book_texts_do_not_include_owner(self, hidden):
        borrower = UserFactory()
        book = SharedBookFactory(owner=hidden, keeper=borrower)
        deal = DealFactory(
            applicant=borrower,
            responder=hidden,
            shared_book=book,
            due_date=timezone.now().date(),
        )
        ns.notify_deal_cancelled(deal, hidden)
        ns.notify_deal_meeted(deal)
        ns.notify_rating_pending(deal, borrower)
        ns.notify_book_due_soon(deal)
        ns.notify_book_overdue(deal)
        ns.notify_book_available(borrower, book)
        self._assert_notifications_clean(borrower)

    def test_extension_texts(self, hidden):
        owner = UserFactory()
        deal = DealFactory(
            applicant=hidden, responder=owner, shared_book=SharedBookFactory(owner=hidden)
        )
        ns.notify_extend_requested(LoanExtensionFactory(deal=deal, requested_by=hidden))
        self._assert_notifications_clean(owner)

        approved = LoanExtensionFactory(
            deal=DealFactory(
                applicant=owner,
                responder=hidden,
                shared_book=SharedBookFactory(owner=hidden),
            ),
            requested_by=owner,
            status=LoanExtension.Status.APPROVED,
        )
        ns.notify_extend_result(approved)
        self._assert_notifications_clean(owner)


class TestExportDoesNotLeakRaterEmail:
    def test_rating_export_uses_display_name(self, hidden):
        ratee = UserFactory()
        deal = DealFactory(applicant=hidden, shared_book=SharedBookFactory(owner=ratee))
        RatingFactory(deal=deal, rater=hidden, ratee=ratee)
        for fmt in ("json", "csv"):
            text = str(export_user_data(ratee, format=fmt))
            _assert_no_leak(text)
            assert f"會員#{hidden.pk}" in text


class TestApiSerializersUseDisplayName:
    def test_shared_book_serializer(self, hidden):
        data = SharedBookSerializer(SharedBookFactory(owner=hidden)).data
        assert data["owner_nickname"] == f"會員#{hidden.pk}"
        assert data["keeper_nickname"] == f"會員#{hidden.pk}"

    def test_deal_serializers(self, hidden):
        deal = DealFactory(applicant=hidden)
        assert DealSerializer(deal).data["applicant_nickname"] == f"會員#{hidden.pk}"
        msg = DealMessageFactory(deal=deal, sender=hidden)
        assert DealMessageSerializer(msg).data["sender_nickname"] == f"會員#{hidden.pk}"
        ext_data = LoanExtensionSerializer(
            LoanExtensionFactory(deal=deal, requested_by=hidden)
        ).data
        assert ext_data["requested_by_nickname"] == f"會員#{hidden.pk}"
        assert ext_data["approved_by_nickname"] is None


class TestMessageListAvatarAlt:
    def test_avatar_alt_uses_display_name(self, hidden):
        hidden.profile.avatar = SimpleUploadedFile(
            "a.jpg", b"x", content_type="image/jpeg"
        )
        hidden.profile.save()
        deal = DealFactory(applicant=hidden)
        DealMessageFactory(deal=deal, sender=hidden)
        request = RequestFactory().get("/")
        request.user = deal.responder
        html = render_to_string(
            "deals/partials/message_list.html",
            {
                "messages": DealMessage.objects.filter(deal=deal),
                "deal": deal,
                "request": request,
            },
        )
        assert f'alt="會員#{hidden.pk}"' in html
