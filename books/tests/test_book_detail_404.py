"""
book_detail 404 行為測試：不存在的書籍應渲染 book_404.html（書籍下架頁），
而非站點級 404 貓咪頁。
"""

import uuid

import pytest
from django.urls import reverse

from tests.factories import UserFactory


pytestmark = pytest.mark.django_db


class TestBookDetail404:
    def test_missing_book_renders_book_404_page(self, client):
        client.force_login(UserFactory())
        url = reverse("books:detail", kwargs={"pk": uuid.uuid4()})

        response = client.get(url)

        assert response.status_code == 404
        assert "book_404.html" in [t.name for t in response.templates]
        content = response.content.decode("utf-8")
        assert "找不到頁面 - Exbooks" in content
        assert "這本書不存在或已下架" in content
