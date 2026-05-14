import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from books.models.official_book import OfficialBook
from books.models.shared_book import SharedBook

User = get_user_model()

@pytest.mark.django_db
class TestSharedBookAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="bookowner", password="password123", email="owner@example.com")
        self.other_user = User.objects.create_user(username="otheruser", password="password123", email="other@example.com")
        
        self.off_book = OfficialBook.objects.create(
            isbn="1112223334445",
            title="Shared Book Title",
            author="Shared Author"
        )
        self.shared_book = SharedBook.objects.create(
            official_book=self.off_book,
            owner=self.user,
            keeper=self.user,
            status=SharedBook.Status.SUSPENDED,
            condition_description="Good condition"
        )

    def test_list_shared_books(self):
        url = reverse("books:shared-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        if "results" in response.data:
            assert len(response.data["results"]) >= 1
            assert response.data["results"][0]["official_book"]["title"] == "Shared Book Title"
        else:
            assert len(response.data) >= 1
            assert response.data[0]["official_book"]["title"] == "Shared Book Title"

    def test_get_shared_book_detail(self):
        url = reverse("books:shared-detail", kwargs={"pk": self.shared_book.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["official_book"]["title"] == "Shared Book Title"

    def test_list_for_transfer_action(self):
        # Authenticate as owner
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {"username": "bookowner", "password": "password123"})
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("books:shared-list-for-transfer", kwargs={"pk": self.shared_book.pk})
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        self.shared_book.refresh_from_db()
        assert self.shared_book.status == SharedBook.Status.TRANSFERABLE

    def test_suspend_action(self):
        # Correctly transition to TRANSFERABLE first using FSM method
        self.shared_book.list_for_transfer()
        self.shared_book.save()

        # Authenticate as owner
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {"username": "bookowner", "password": "password123"})
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("books:shared-suspend", kwargs={"pk": self.shared_book.pk})
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        self.shared_book.refresh_from_db()
        assert self.shared_book.status == SharedBook.Status.SUSPENDED

    def test_unauthorized_action(self):
        # Authenticate as other user
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {"username": "otheruser", "password": "password123"})
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("books:shared-list-for-transfer", kwargs={"pk": self.shared_book.pk})
        response = self.client.post(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_shared_book_by_owner(self):
        # Authenticate as owner
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {"username": "bookowner", "password": "password123"})
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("books:shared-detail", kwargs={"pk": self.shared_book.pk})
        response = self.client.patch(url, {"condition_description": "Slightly worn"})
        
        assert response.status_code == status.HTTP_200_OK
        self.shared_book.refresh_from_db()
        assert self.shared_book.condition_description == "Slightly worn"
