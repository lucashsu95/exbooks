import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
class TestJWTAuth:
    def setup_method(self):
        self.client = APIClient()
        self.username = "testuser"
        self.password = "testpassword123"
        self.user = User.objects.create_user(
            username=self.username, 
            email=f"{self.username}@example.com", 
            password=self.password
        )

    def test_token_obtain_pair(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {
            "username": self.username,
            "password": self.password
        })
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_refresh(self):
        # 1. Get initial tokens
        url_obtain = reverse("token_obtain_pair")
        response_obtain = self.client.post(url_obtain, {
            "username": self.username,
            "password": self.password
        })
        refresh_token = response_obtain.data["refresh"]

        # 2. Use refresh token to get new access token
        url_refresh = reverse("token_refresh")
        response_refresh = self.client.post(url_refresh, {"refresh": refresh_token})
        
        assert response_refresh.status_code == status.HTTP_200_OK
        assert "access" in response_refresh.data

    def test_token_obtain_invalid_credentials(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {
            "username": self.username,
            "password": "wrongpassword"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
