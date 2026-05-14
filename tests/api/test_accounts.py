import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import UserProfile

User = get_user_model()

@pytest.mark.django_db
class TestAccountsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.username = "profileuser"
        self.password = "profilepass123"
        self.user = User.objects.create_user(
            username=self.username, 
            email=f"{self.username}@example.com", 
            password=self.password
        )
        # UserProfile is automatically created by signals
        self.profile = self.user.profile

    def test_get_my_profile(self):
        # 1. Get JWT Token
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {
            "username": self.username, 
            "password": self.password
        })
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 2. Request /api/accounts/me/
        url = reverse("accounts:api_me")
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Nickname is automatically set to username by signal if not provided
        assert response.data["nickname"] == self.username
        assert response.data["user_email"] == f"{self.username}@example.com"

    def test_update_my_profile(self):
        # 1. Get JWT Token
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {
            "username": self.username, 
            "password": self.password
        })
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 2. Update nickname
        url = reverse("accounts:api_me")
        response = self.client.patch(url, {"nickname": "Updated Nickname"})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["nickname"] == "Updated Nickname"
        self.profile.refresh_from_db()
        assert self.profile.nickname == "Updated Nickname"

    def test_update_trust_score_forbidden(self):
        # 1. Get JWT Token
        token_url = reverse("token_obtain_pair")
        token_res = self.client.post(token_url, {
            "username": self.username, 
            "password": self.password
        })
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 2. Try to update trust_score (should be read-only)
        url = reverse("accounts:api_me")
        response = self.client.patch(url, {"trust_score": 9999})
        
        assert response.status_code == status.HTTP_200_OK
        # trust_score should remain 0 (default)
        assert response.data["trust_score"] == 0
        self.profile.refresh_from_db()
        assert self.profile.trust_score == 0

    def test_get_profile_unauthenticated(self):
        url = reverse("accounts:api_me")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
