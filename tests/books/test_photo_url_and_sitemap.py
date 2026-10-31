"""
功能性 bug 回歸測試：
- BookPhoto.serve_url 反解析受保護照片路由時漏了 books: namespace。
- /sitemap.xml 反解析不存在的 books:public_list / books:public_detail。
"""

import pytest
from django.urls import reverse

from books.models import SharedBook
from tests.factories import BookPhotoFactory, DealFactory, SharedBookFactory

pytestmark = pytest.mark.django_db


def test_serve_url_for_deal_photo():
    deal = DealFactory()
    photo = BookPhotoFactory(shared_book=deal.shared_book, deal=deal)
    assert photo.serve_url == reverse(
        "books:serve_protected_photo", kwargs={"pk": photo.pk}
    )


def test_book_detail_renders_with_deal_photo(client):
    deal = DealFactory()
    BookPhotoFactory(shared_book=deal.shared_book, deal=deal)
    client.force_login(deal.shared_book.owner)
    res = client.get(reverse("books:detail", kwargs={"pk": deal.shared_book.pk}))
    assert res.status_code == 200


def test_sitemap_renders(client):
    SharedBookFactory(status=SharedBook.Status.TRANSFERABLE)
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    assert b"<urlset" in res.content
