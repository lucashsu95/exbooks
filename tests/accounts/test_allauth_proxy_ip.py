"""M-6：登入限流需以 X-Forwarded-For 的真實用戶端 IP 為鍵（nginx 一層代理）。"""

import ast
from pathlib import Path

import pytest
from allauth.account.adapter import get_adapter
from allauth.core import ratelimit
from django.conf import settings
from django.test import RequestFactory, override_settings

NGINX_IP = "172.18.0.5"
PROD_SETTINGS = Path(settings.BASE_DIR) / "exbook" / "prod_settings.py"


def _prod_setting(name):
    tree = ast.parse(PROD_SETTINGS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    return None


def _request_via_nginx(xff):
    # nginx 的 $proxy_add_x_forwarded_for 會把真實連線 IP 附加在最後
    return RequestFactory().post(
        "/accounts/login/", REMOTE_ADDR=NGINX_IP, HTTP_X_FORWARDED_FOR=xff
    )


def test_prod_settings_trusts_one_proxy_hop():
    assert _prod_setting("ALLAUTH_TRUSTED_PROXY_COUNT") == 1


@override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1)
def test_client_ip_comes_from_last_xff_hop():
    adapter = get_adapter()
    assert adapter.get_client_ip(_request_via_nginx("203.0.113.1")) == "203.0.113.1"
    # 用戶端自行偽造的前段 XFF 不可信，只取 nginx 附加的最後一段
    assert (
        adapter.get_client_ip(_request_via_nginx("1.2.3.4, 203.0.113.2"))
        == "203.0.113.2"
    )


@pytest.mark.django_db
@override_settings(
    ALLAUTH_TRUSTED_PROXY_COUNT=1,
    ACCOUNT_RATE_LIMITS={"login_failed": "2/m/ip"},
)
def test_different_clients_behind_nginx_get_separate_buckets():
    client_a = "203.0.113.10"
    client_b = "198.51.100.20"

    for _ in range(2):
        assert ratelimit.consume(_request_via_nginx(client_a), action="login_failed")
    assert not ratelimit.consume(_request_via_nginx(client_a), action="login_failed")

    # 另一位用戶端經同一個 nginx 進來，不應被 A 的額度拖累
    assert ratelimit.consume(_request_via_nginx(client_b), action="login_failed")
