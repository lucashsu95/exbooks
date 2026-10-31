import pytest
from uuid import uuid4
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.api._auth import mark_email_verified
from django.contrib.auth import get_user_model
from books.models.official_book import OfficialBook
from books.models.shared_book import SharedBook
from deals.models.deal import Deal
from deals.models.deal_message import DealMessage

User = get_user_model()


@pytest.mark.django_db
class TestDealsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username="user_a", password="password123", email="a@example.com"
        )
        mark_email_verified(self.user_a)
        self.user_b = User.objects.create_user(
            username="user_b", password="password123", email="b@example.com"
        )
        mark_email_verified(self.user_b)

        self.off_book = OfficialBook.objects.create(
            isbn="5556667778889", title="Deal Book", author="Deal Author"
        )
        self.shared_book = SharedBook.objects.create(
            official_book=self.off_book,
            owner=self.user_b,
            keeper=self.user_b,
            status=SharedBook.Status.TRANSFERABLE,
            condition_description="Good",
        )

        # Create a deal: User A requests to borrow from User B
        self.deal = Deal.objects.create(
            shared_book=self.shared_book,
            deal_type=Deal.DealType.LOAN,
            applicant=self.user_a,
            responder=self.user_b,
            status=Deal.Status.REQUESTED,
        )

    def _get_token(self, user):
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url, {"username": user.username, "password": "password123"}
        )
        return res.data["access"]

    def test_list_my_deals(self):
        token = self._get_token(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:deal-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Check results in pagination
        results = response.data.get("results", response.data)
        assert len(results) >= 1
        assert str(results[0]["id"]) == str(self.deal.id)

    def test_create_message_via_service(self):
        token = self._get_token(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:message-list")
        response = self.client.post(
            url, {"deal": str(self.deal.pk), "content": "面交見"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert DealMessage.objects.filter(
            deal=self.deal, sender=self.user_a, content="面交見"
        ).exists()

    def test_create_message_rejects_non_party(self):
        outsider = User.objects.create_user(
            username="user_c", password="password123", email="c@example.com"
        )
        mark_email_verified(outsider)
        token = self._get_token(outsider)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:message-list")
        response = self.client.post(
            url, {"deal": str(self.deal.pk), "content": "hi"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not DealMessage.objects.filter(deal=self.deal).exists()

    def test_create_message_rejects_finished_deal(self):
        self.deal.decline()
        self.deal.save()
        self.deal.refresh_from_db()
        assert self.deal.status == Deal.Status.CANCELLED

        token = self._get_token(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:message-list")
        response = self.client.post(
            url, {"deal": str(self.deal.pk), "content": "too late"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not DealMessage.objects.filter(deal=self.deal).exists()

    def test_create_message_rejects_blank_content(self):
        token = self._get_token(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:message-list")
        response = self.client.post(
            url, {"deal": str(self.deal.pk), "content": "   "}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not DealMessage.objects.filter(deal=self.deal).exists()

    def test_complete_meeting(self):
        # Correctly transition to RESPONDED state using FSM method
        self.deal.accept()
        self.deal.save()

        token = self._get_token(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("deals:deal-complete-meeting", kwargs={"pk": self.deal.pk})
        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK
        self.deal.refresh_from_db()
        assert self.deal.status == Deal.Status.MEETED
        self.shared_book.refresh_from_db()
        # LOAN deal should result in OCCUPIED status and keeper = applicant
        assert self.shared_book.status == SharedBook.Status.OCCUPIED
        assert self.shared_book.keeper == self.user_a


@pytest.mark.django_db
class TestDealCreateApplicantIdentity:
    """F-7: 每類型 applicant 身分驗證（API 面安全邊界）。

    矩陣：RG→Owner、RS→Keeper、EX→Keeper、LG/TF→第三人（owner/keeper 皆不可）。
    註：DealViewSet.create 將 service 的 PermissionDenied/ValidationError
    統一映射為 400，故拒絕格斷言 400。
    """

    def setup_method(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="f7_owner", password="password123", email="f7o@example.com"
        )
        mark_email_verified(self.owner)
        self.keeper = User.objects.create_user(
            username="f7_keeper", password="password123", email="f7k@example.com"
        )
        mark_email_verified(self.keeper)
        self.other = User.objects.create_user(
            username="f7_other", password="password123", email="f7x@example.com"
        )
        mark_email_verified(self.other)

    def _make_book(self, status, transferability=None):
        book = SharedBook.objects.create(
            official_book=OfficialBook.objects.create(
                isbn=str(uuid4().int % 10**13), title="F7 Book", author="F7 Author"
            ),
            owner=self.owner,
            keeper=self.keeper,
            status=status,
            condition_description="Good",
        )
        if transferability is not None:
            book.transferability = transferability
            book.save()
        return book

    def _post_deal(self, user, book, deal_type):
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url, {"username": user.username, "password": "password123"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return self.client.post(
            reverse("deals:deal-list"),
            {
                "shared_book": book.id,
                "deal_type": deal_type,
                # 註：applicant/responder 為唯讀欄位，送了也會被忽略
                # （applicant 恆為 request.user、responder 由 service 判定）。
                "applicant": user.id,
                "responder": self.owner.id,
            },
        )

    def test_f7_regress_owner_only(self):
        book = self._make_book(
            SharedBook.Status.TRANSFERABLE, SharedBook.Transferability.TRANSFER
        )
        assert (
            self._post_deal(self.owner, book, "RG").status_code
            == status.HTTP_201_CREATED
        )
        assert (
            self._post_deal(self.keeper, book, "RG").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert (
            self._post_deal(self.other, book, "RG").status_code
            == status.HTTP_400_BAD_REQUEST
        )

    def test_f7_restore_keeper_only(self):
        book = self._make_book(
            SharedBook.Status.RESTORABLE, SharedBook.Transferability.RETURN
        )
        assert (
            self._post_deal(self.keeper, book, "RS").status_code
            == status.HTTP_201_CREATED
        )
        assert (
            self._post_deal(self.owner, book, "RS").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert (
            self._post_deal(self.other, book, "RS").status_code
            == status.HTTP_400_BAD_REQUEST
        )

    def test_f7_except_keeper_only(self):
        book = self._make_book(SharedBook.Status.OCCUPIED)
        assert (
            self._post_deal(self.keeper, book, "EX").status_code
            == status.HTTP_201_CREATED
        )
        assert (
            self._post_deal(self.owner, book, "EX").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert (
            self._post_deal(self.other, book, "EX").status_code
            == status.HTTP_400_BAD_REQUEST
        )

    def test_f7_loan_third_party_only(self):
        book = self._make_book(
            SharedBook.Status.TRANSFERABLE, SharedBook.Transferability.RETURN
        )
        assert (
            self._post_deal(self.other, book, "LN").status_code
            == status.HTTP_201_CREATED
        )
        assert (
            self._post_deal(self.owner, book, "LN").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert (
            self._post_deal(self.keeper, book, "LN").status_code
            == status.HTTP_400_BAD_REQUEST
        )
