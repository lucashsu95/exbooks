"""
LoanExtension API 測試（#21）：update/destroy 已收為 405。
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from deals.models import LoanExtension
from tests.factories import LoanExtensionFactory

User = get_user_model()


@pytest.mark.django_db
class TestLoanExtensionAPIWriteSurface:
    """合法寫入只走 create（request_extension）與 approve/reject/cancel service；
    預設 ModelViewSet 的 update/destroy 會繞過 service 直接改列
    （如 PATCH 搬移 deal），故一律 405。"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ext_applicant", password="password123", email="ext@example.com"
        )
        self.ext = LoanExtensionFactory(requested_by=self.user)
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url, {"username": self.user.username, "password": "password123"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.url = reverse("deals:extension-detail", kwargs={"pk": self.ext.pk})

    def test_patch_not_allowed(self):
        res = self.client.patch(self.url, {"deal": self.ext.deal_id}, format="json")
        assert res.status_code == 405
        self.ext.refresh_from_db()
        assert LoanExtension.objects.get(pk=self.ext.pk).deal_id == self.ext.deal_id

    def test_put_not_allowed(self):
        res = self.client.put(self.url, {"deal": self.ext.deal_id}, format="json")
        assert res.status_code == 405

    def test_delete_not_allowed(self):
        res = self.client.delete(self.url)
        assert res.status_code == 405
        assert LoanExtension.objects.filter(pk=self.ext.pk).exists()
