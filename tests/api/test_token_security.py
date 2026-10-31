"""
/api/token/ 安全性回歸測試（H-4）。

- 未完成 Email 驗證的帳號不能透過 JWT 繞過 allauth 的 mandatory 驗證。
- token 端點有獨立的 scoped throttle，且 IP 以 NUM_PROXIES 取用，
  偽造 X-Forwarded-For 不能繞過。
"""

import pytest
from allauth.account.models import EmailAddress
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from tests.api._auth import mark_email_verified
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "testpass123"  # UserFactory 預設密碼


def _obtain(client, user, password=PASSWORD, **extra):
    return client.post(
        reverse("token_obtain_pair"),
        {"username": user.username, "password": password},
        **extra,
    )


class TestTokenRequiresVerifiedEmail:
    def test_unverified_user_is_rejected(self):
        user = UserFactory()
        res = _obtain(APIClient(), user)
        assert res.status_code == 401
        assert "access" not in res.data

    def test_unverified_email_address_row_is_rejected(self):
        user = UserFactory()
        EmailAddress.objects.create(
            user=user, email=user.email, verified=False, primary=True
        )
        res = _obtain(APIClient(), user)
        assert res.status_code == 401

    def test_verified_user_gets_token(self):
        user = mark_email_verified(UserFactory())
        res = _obtain(APIClient(), user)
        assert res.status_code == 200
        assert "access" in res.data and "refresh" in res.data


class TestTokenThrottle:
    def test_num_proxies_configured(self):
        assert settings.REST_FRAMEWORK.get("NUM_PROXIES") == 1

    def test_token_endpoint_is_throttled_even_with_spoofed_xff(self):
        user = UserFactory()
        client = APIClient()
        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["token_obtain"]
        limit = int(rate.split("/")[0])
        statuses = [
            _obtain(
                client,
                user,
                password="wrong-password",
                # 攻擊者每次換一個偽造的前段 IP；nginx 附加的最後一段不變
                HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.7",
            ).status_code
            for i in range(limit + 1)
        ]
        assert statuses[-1] == 429
        assert set(statuses[:-1]) == {401}
