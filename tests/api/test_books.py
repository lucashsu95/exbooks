import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from books.models.official_book import OfficialBook

@pytest.mark.django_db
class TestOfficialBookAPI:
    def setup_method(self):
        self.client = APIClient()
        self.book = OfficialBook.objects.create(
            isbn="1234567890123",
            title="Test Django Book",
            author="Test Author",
            publisher="Test Publisher",
            category=OfficialBook.Category.TECH,
            description="A book about Django"
        )

    def test_list_official_books(self):
        url = reverse("books:official-list")
        response = self.client.get(url)

    def test_search_official_books(self):
        url = reverse("books:official-list")
        # Search by title
        response = self.client.get(url, {"search": "Django"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        assert "Test Django Book" in response.data["results"][0]["title"]

        # Search by ISBN
        response = self.client.get(url, {"search": "1234567890123"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Search for non-existent book
        response = self.client.get(url, {"search": "NonExistentBook"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_create_official_book_forbidden(self):
        url = reverse("books:official-list")
        response = self.client.post(url, {
            "isbn": "9876543210987",
            "title": "Forbidden Book",
            "author": "Forbidden Author"
        })
        # Unauthenticated users should get 401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


