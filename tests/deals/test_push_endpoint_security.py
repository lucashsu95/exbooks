"""M-4：Web Push 訂閱端點 SSRF 防護。"""

import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from deals.models import PushSubscription, WebPushConfig
from deals.services import push_service
from deals.services.push_service import is_allowed_push_endpoint


VALID_ENDPOINTS = [
    "https://fcm.googleapis.com/fcm/send/abc123",
    "https://updates.push.services.mozilla.com/wpush/v2/abc",
    "https://web.push.apple.com/QGuQyavXutnMai",
    "https://api.push.apple.com/3/device/abc",
    "https://wns2-par02p.notify.windows.com/w/?token=abc",
    "https://FCM.googleapis.com/fcm/send/abc",
]

INVALID_ENDPOINTS = [
    "http://fcm.googleapis.com/fcm/send/abc",  # 非 https
    "https://evilfcm.googleapis.com.attacker.com/x",  # 子字串偽裝
    "https://fcm.googleapis.com.attacker.com/x",
    "https://evilfcm.googleapis.com/x",  # 非正當子網域
    "https://sub.fcm.googleapis.com/x",  # fcm 僅允許完全相符
    "https://push.apple.com.evil.com/x",
    "https://notpush.apple.com/x",
    "https://push.apple.com/x",  # 萬用字元僅允許子網域
    "https://user:pass@fcm.googleapis.com/x",  # userinfo
    "https://fcm.googleapis.com@169.254.169.254/x",
    "https://fcm.googleapis.com:8443/x",  # 非預設埠
    "https://fcm.googleapis.com:443/x",  # 明確指定埠也拒絕
    "https://127.0.0.1/x",
    "https://169.254.169.254/latest/meta-data/",
    "https://localhost/x",
    "ftp://fcm.googleapis.com/x",
    "https:///x",
    "not a url",
    "",
    None,
]


@pytest.mark.parametrize("endpoint", VALID_ENDPOINTS)
def test_allowed_push_endpoint_accepts_known_services(endpoint):
    assert is_allowed_push_endpoint(endpoint) is True


@pytest.mark.parametrize("endpoint", INVALID_ENDPOINTS)
def test_allowed_push_endpoint_rejects_unsafe(endpoint):
    assert is_allowed_push_endpoint(endpoint) is False


def _subscribe_payload(endpoint):
    return json.dumps(
        {
            "subscription": {
                "endpoint": endpoint,
                "keys": {"p256dh": "p" * 20, "auth": "a" * 10},
            }
        }
    )


@pytest.mark.django_db
class TestPushSubscribeView:
    def _post(self, client, endpoint):
        return client.post(
            reverse("deals:push_subscribe"),
            _subscribe_payload(endpoint),
            content_type="application/json",
        )

    def test_rejects_internal_endpoint_with_400(self, authenticated_client):
        resp = self._post(
            authenticated_client, "http://169.254.169.254/latest/meta-data/"
        )
        assert resp.status_code == 400
        assert not PushSubscription.objects.exists()

    def test_rejects_lookalike_host_with_400(self, authenticated_client):
        resp = self._post(
            authenticated_client, "https://evilfcm.googleapis.com.attacker.com/x"
        )
        assert resp.status_code == 400
        assert not PushSubscription.objects.exists()

    def test_accepts_valid_endpoint(self, authenticated_client):
        resp = self._post(authenticated_client, "https://fcm.googleapis.com/fcm/send/a")
        assert resp.status_code == 200
        assert PushSubscription.objects.count() == 1

    def test_500_does_not_leak_exception_message(self, authenticated_client):
        with patch(
            "deals.views.PushSubscription.objects.update_or_create",
            side_effect=RuntimeError("secret-internal-detail"),
        ):
            resp = self._post(
                authenticated_client, "https://fcm.googleapis.com/fcm/send/a"
            )
        assert resp.status_code == 500
        body = resp.content.decode()
        assert "secret-internal-detail" not in body


@pytest.mark.django_db
class TestSendPushRechecksEndpoint:
    def test_skips_and_deactivates_invalid_stored_endpoint(self, test_user):
        sub = PushSubscription.objects.create(
            user=test_user,
            endpoint="http://169.254.169.254/latest/meta-data/",
            p256dh="p" * 20,
            auth="a" * 10,
        )
        with (
            patch.object(push_service, "WEBPUSH_AVAILABLE", True),
            patch.object(
                WebPushConfig, "get_config", return_value=WebPushConfig()
            ),
            patch.object(push_service, "webpush", create=True) as mock_webpush,
        ):
            result = push_service.send_push_notification(sub, "t", "m")
        assert result is False
        mock_webpush.assert_not_called()
        sub.refresh_from_db()
        assert sub.is_active is False
