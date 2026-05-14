import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from books.models.official_book import OfficialBook
from books.models.shared_book import SharedBook
from deals.models.deal import Deal

User = get_user_model()

@pytest.mark.django_db
class TestDealsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username="user_a", password="password123", email="a@example.com")
        self.user_b = User.objects.create_user(username="user_b", password="password123", email="b@example.com")
        
        self.off_book = OfficialBook.objects.create(
            isbn="5556667778889",
            title="Deal Book",
            author="Deal Author"
        )
        self.shared_book = SharedBook.objects.create(
            official_book=self.off_book,
            owner=self.user_b,
            keeper=self.user_b,
            status=SharedBook.Status.TRANSFERABLE,
            condition_description="Good"
        )
        
        # Create a deal: User A requests to borrow from User B
        self.deal = Deal.objects.create(
            shared_book=self.shared_book,
            deal_type=Deal.DealType.LOAN,
            applicant=self.user_a,
            responder=self.user_b,
            status=Deal.Status.REQUESTED
        )

    def _get_token(self, user):
        token_url = reverse("token_obtain_pair")
        res = self.client.post(token_url, {"username": user.username, "password": "password123"})
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


