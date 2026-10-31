"""
API 寫入面收斂的回歸測試（C-1 / C-2 / H-2 / M-2）。

合法寫入只走 service（create / 自訂 action）；ModelViewSet 預設的
update / partial_update / destroy 會繞過 service 直接改列，一律不允許。
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from books.models import SharedBook
from deals.models import Deal, DealMessage, Notification
from tests.factories import (
    BookSetFactory,
    DealFactory,
    DealMessageFactory,
    NotificationFactory,
    SharedBookFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


# ---------------------------------------------------------------------------
# C-1: DealViewSet 禁止 update / destroy
# ---------------------------------------------------------------------------


class TestDealWriteSurface:
    def setup_method(self):
        self.deal = DealFactory()
        self.applicant = self.deal.applicant
        self.url = reverse("deals:deal-detail", kwargs={"pk": self.deal.pk})

    @pytest.mark.parametrize(
        "payload",
        [
            {"due_date": "2099-01-01"},
            {"applicant_rated": True, "responder_rated": True},
            {"meeting_location": "改地點"},
        ],
    )
    def test_party_cannot_patch_deal(self, payload):
        res = _client(self.applicant).patch(self.url, payload, format="json")
        assert res.status_code == 405
        self.deal.refresh_from_db()
        assert self.deal.due_date is None
        assert self.deal.applicant_rated is False
        assert self.deal.responder_rated is False

    def test_party_cannot_put_deal(self):
        other = UserFactory()
        res = _client(self.applicant).put(
            self.url,
            {
                "shared_book": str(self.deal.shared_book_id),
                "deal_type": "LN",
                "applicant": other.pk,
                "responder": other.pk,
            },
            format="json",
        )
        assert res.status_code == 405
        self.deal.refresh_from_db()
        assert self.deal.applicant == self.applicant

    def test_party_cannot_delete_deal(self):
        res = _client(self.applicant).delete(self.url)
        assert res.status_code == 405
        assert Deal.objects.filter(pk=self.deal.pk).exists()

    def test_retrieve_still_works(self):
        res = _client(self.applicant).get(self.url)
        assert res.status_code == 200
        assert str(res.data["id"]) == str(self.deal.pk)

    def test_serializer_ignores_party_and_rating_fields(self):
        from deals.serializers import DealSerializer

        read_only = {
            name
            for name, field in DealSerializer().fields.items()
            if field.read_only
        }
        assert {
            "applicant",
            "responder",
            "due_date",
            "applicant_rated",
            "responder_rated",
        } <= read_only


# ---------------------------------------------------------------------------
# C-2 / M-2: SharedBookViewSet
# ---------------------------------------------------------------------------


class TestSharedBookWriteSurface:
    def setup_method(self):
        self.owner = UserFactory()
        self.book = SharedBookFactory(owner=self.owner, keeper=self.owner)
        self.url = reverse("books:shared-detail", kwargs={"pk": self.book.pk})

    def test_non_owner_cannot_delete_book(self):
        res = _client(UserFactory()).delete(self.url)
        assert res.status_code == 403
        assert SharedBook.objects.filter(pk=self.book.pk).exists()

    def test_owner_can_delete_book(self):
        res = _client(self.owner).delete(self.url)
        assert res.status_code == 204
        assert not SharedBook.objects.filter(pk=self.book.pk).exists()

    def test_owner_cannot_reassign_owner_keeper_or_book_set(self):
        stranger = UserFactory()
        book_set = BookSetFactory(owner=stranger)
        res = _client(self.owner).patch(
            self.url,
            {
                "owner": stranger.pk,
                "keeper": stranger.pk,
                "book_set": str(book_set.pk),
                "condition_description": "八成新",
            },
            format="json",
        )
        assert res.status_code == 200
        self.book.refresh_from_db()
        assert self.book.owner == self.owner
        assert self.book.keeper == self.owner
        assert self.book.book_set_id is None
        assert self.book.condition_description == "八成新"


# ---------------------------------------------------------------------------
# H-2: DealMessageViewSet / NotificationViewSet
# ---------------------------------------------------------------------------


class TestDealMessageWriteSurface:
    def setup_method(self):
        self.deal = DealFactory()
        self.message = DealMessageFactory(deal=self.deal, sender=self.deal.responder)
        self.url = reverse("deals:message-detail", kwargs={"pk": self.message.pk})

    def test_party_cannot_patch_others_message(self):
        res = _client(self.deal.applicant).patch(
            self.url, {"content": "竄改"}, format="json"
        )
        assert res.status_code == 405
        self.message.refresh_from_db()
        assert self.message.content != "竄改"

    def test_sender_cannot_move_message_to_other_deal(self):
        other_deal = DealFactory(applicant=self.deal.responder)
        res = _client(self.deal.responder).patch(
            self.url, {"deal": str(other_deal.pk)}, format="json"
        )
        assert res.status_code == 405
        self.message.refresh_from_db()
        assert self.message.deal_id == self.deal.pk

    def test_party_cannot_delete_message(self):
        res = _client(self.deal.applicant).delete(self.url)
        assert res.status_code == 405
        assert DealMessage.objects.filter(pk=self.message.pk).exists()

    def test_non_party_cannot_create_message(self):
        res = _client(UserFactory()).post(
            reverse("deals:message-list"),
            {"deal": str(self.deal.pk), "content": "hi"},
            format="json",
        )
        assert res.status_code == 403

    def test_list_and_retrieve_still_work(self):
        client = _client(self.deal.applicant)
        assert client.get(reverse("deals:message-list")).status_code == 200
        assert client.get(self.url).status_code == 200


class TestNotificationWriteSurface:
    def setup_method(self):
        self.user = UserFactory()
        self.notification = NotificationFactory(recipient=self.user, deal=DealFactory())
        self.url = reverse(
            "deals:notification-detail", kwargs={"pk": self.notification.pk}
        )

    def test_create_not_allowed(self):
        res = _client(self.user).post(
            reverse("deals:notification-list"),
            {"notification_type": "DEAL_REQUESTED", "title": "x", "message": "y"},
            format="json",
        )
        assert res.status_code == 405

    def test_cannot_repoint_deal(self):
        other_deal = DealFactory()
        original_deal_id = self.notification.deal_id
        res = _client(self.user).patch(
            self.url, {"deal": str(other_deal.pk)}, format="json"
        )
        assert res.status_code == 405
        self.notification.refresh_from_db()
        assert self.notification.deal_id == original_deal_id

    def test_cannot_delete(self):
        res = _client(self.user).delete(self.url)
        assert res.status_code == 405
        assert Notification.objects.filter(pk=self.notification.pk).exists()

    def test_mark_as_read_still_works(self):
        res = _client(self.user).post(
            reverse(
                "deals:notification-mark-as-read",
                kwargs={"pk": self.notification.pk},
            )
        )
        assert res.status_code == 200
        self.notification.refresh_from_db()
        assert self.notification.is_read is True
