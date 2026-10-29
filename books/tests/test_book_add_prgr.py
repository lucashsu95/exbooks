"""
book_add 的 POST 回應契約（form resubmission 回歸防護）。

根因背景：瀏覽器只在「top-level POST 收到 2xx 回應」後才會在該 URL
留下 POST 歷史項；之後重新整理或返回時，headful 瀏覽器會彈出
Confirm Form Resubmission 對話框，headless 則直接自動重送 POST
（已用 Playwright 於 .verify-evidence/ 留證）。

成功路徑原本已是 302 PRG（瀏覽器不視為 POST 頁）；失敗路徑原本
回 200 重繪表單，正是對話框的來源。此測試固定失敗路徑的 PRG 契約：

- 非 HTMX 的失敗 POST → 303 回表單頁（絕不可 2xx）
- HTMX 的失敗 POST → 200 表單片段（XHR 不產生歷史項）且保留欄位錯誤
- HTMX 的成功 POST → 204 + HX-Redirect
- 成功 POST → 302 回書架並建立 SharedBook
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from books.models import SharedBook
from tests.factories import UserFactory


def _photo_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 80), (200, 60, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _add_payload(**overrides) -> dict:
    payload = {
        "isbn": "9789861234567",
        "title": "測試書籍",
        "author": "測試作者",
        "publisher": "",
        "category": "小說",
        "transferability": "RETURN",
        "condition_description": "書況良好",
        "loan_duration_days": "30",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestBookAddPostResponse:
    def test_non_hx_invalid_post_returns_303_to_add(self, client):
        """非 HTMX 失敗 POST 不得回 2xx（resubmission 對話框的根因）。"""
        user = UserFactory()
        client.force_login(user)

        resp = client.post(reverse("books:add"), _add_payload())

        assert resp.status_code == 303
        assert resp.url == reverse("books:add")

    def test_hx_invalid_post_returns_200_fragment_with_errors(self, client):
        """HTMX 失敗 POST 回表單片段原地重繪，且保留欄位錯誤訊息。"""
        user = UserFactory()
        client.force_login(user)

        resp = client.post(
            reverse("books:add"), _add_payload(), HTTP_HX_REQUEST="true"
        )

        body = resp.content.decode("utf-8")
        assert resp.status_code == 200
        assert "請至少上傳一張書況照片" in body
        assert "<!doctype html" not in body.lower()

    def test_valid_post_redirects_to_bookshelf_and_creates_book(self, client):
        user = UserFactory()
        client.force_login(user)

        resp = client.post(
            reverse("books:add"),
            {
                **_add_payload(),
                "photos": SimpleUploadedFile("p.jpg", _photo_bytes(), "image/jpeg"),
            },
        )

        assert resp.status_code == 302
        assert resp.url == reverse("books:bookshelf")
        assert SharedBook.objects.filter(owner=user).count() == 1

    def test_hx_valid_post_returns_hx_redirect(self, client):
        user = UserFactory()
        client.force_login(user)

        resp = client.post(
            reverse("books:add"),
            {
                **_add_payload(),
                "photos": SimpleUploadedFile("p.jpg", _photo_bytes(), "image/jpeg"),
            },
            HTTP_HX_REQUEST="true",
        )

        assert resp.status_code == 204
        assert resp["HX-Redirect"] == reverse("books:bookshelf")
        assert SharedBook.objects.filter(owner=user).count() == 1
