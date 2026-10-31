"""L-3：切換語言時移除語言前綴後不可變成跨站的開放重新導向。"""

from urllib.parse import urlparse

import pytest
from django.urls import reverse


@pytest.mark.django_db
@pytest.mark.parametrize("next_url", ["/en//evil.com/", "/en/\\evil.com", "/ko//evil.com"])
@pytest.mark.parametrize("language", ["zh-hant", "en"])
def test_set_language_does_not_redirect_offsite(client, next_url, language):
    resp = client.post(
        reverse("set_language"), {"language": language, "next": next_url}
    )
    assert resp.status_code == 302
    location = resp["Location"]
    parsed = urlparse(location.replace("\\", "/"))
    assert parsed.netloc in ("", "testserver")
    assert "evil.com" not in parsed.netloc


@pytest.mark.django_db
def test_set_language_keeps_normal_path(client):
    resp = client.post(
        reverse("set_language"), {"language": "en", "next": "/books/"}
    )
    assert resp.status_code == 302
    assert resp["Location"] == "http://testserver/en/books/"
