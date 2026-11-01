"""
共用書目（OfficialBook）保護：一般使用者只能補空白欄位，不能覆寫他人已填的資料；
使用者上傳的封面只出現在自己的 SharedBook，不取代共用封面。
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from PIL import Image

from books.models import OfficialBook, SharedBook
from books.services import publish_book, update_book
from tests.factories import SharedBookFactory, UserFactory

pytestmark = pytest.mark.django_db

ISBN = "9787770009999"


def _jpeg(
    name: str = "photo.jpg", color: tuple[int, int, int] = (200, 30, 30)
) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _level1(user):
    user.profile.trust_score = 4
    user.profile.save()
    return user


def _publish_data(**overrides) -> dict:
    data = {
        "isbn": ISBN,
        "title": "第二人的書名",
        "author": "第二人的作者",
        "publisher": "第二人的出版社",
        "category": OfficialBook.Category.ART,
        "transferability": SharedBook.Transferability.RETURN,
        "condition_description": "九成新",
        "loan_duration_days": 21,
    }
    data.update(overrides)
    return data


def _edit_data() -> dict:
    return {
        "title": "改書名",
        "author": "改作者",
        "publisher": "改出版社",
        "category": OfficialBook.Category.ART,
        "transferability": SharedBook.Transferability.TRANSFER,
        "min_trust_level": 1,
        "condition_description": "改書況",
        "loan_duration_days": 45,
    }


def _existing_official(**fields) -> OfficialBook:
    defaults = {
        "isbn": ISBN,
        "title": "原書名",
        "author": "原作者",
        "publisher": "原出版社",
        "category": OfficialBook.Category.TECH,
    }
    defaults.update(fields)
    return OfficialBook.objects.create(**defaults)


class TestPublishDoesNotOverwriteSharedCatalog:
    def test_second_publisher_does_not_change_existing_title(self):
        _existing_official()
        publish_book(UserFactory(), _publish_data(), photos=[_jpeg()])

        ob = OfficialBook.objects.get(isbn=ISBN)
        assert ob.title == "原書名"
        assert ob.author == "原作者"
        assert ob.publisher == "原出版社"
        assert ob.category == OfficialBook.Category.TECH

    def test_blank_fields_get_filled(self):
        _existing_official(author="", publisher="", category=OfficialBook.Category.OTHER)
        publish_book(UserFactory(), _publish_data(), photos=[_jpeg()])

        ob = OfficialBook.objects.get(isbn=ISBN)
        assert ob.title == "原書名"
        assert ob.author == "第二人的作者"
        assert ob.publisher == "第二人的出版社"
        assert ob.category == OfficialBook.Category.ART

    def test_new_isbn_still_creates_with_publisher_data(self):
        shared = publish_book(UserFactory(), _publish_data(), photos=[_jpeg()])
        assert shared.official_book.title == "第二人的書名"


class TestUpdateDoesNotOverwriteSharedCatalog:
    def test_editing_own_book_keeps_shared_fields(self):
        user = _level1(UserFactory())
        ob = _existing_official()
        book = SharedBookFactory(owner=user, official_book=ob)

        update_book(book, user, _edit_data())

        ob.refresh_from_db()
        assert ob.title == "原書名"
        assert ob.author == "原作者"
        assert ob.publisher == "原出版社"
        assert ob.category == OfficialBook.Category.TECH
        book.refresh_from_db()
        assert book.min_trust_level == 1
        assert book.loan_duration_days == 45

    def test_editing_own_book_fills_blank_fields(self):
        user = _level1(UserFactory())
        ob = _existing_official(author="", publisher="")
        book = SharedBookFactory(owner=user, official_book=ob)

        update_book(book, user, _edit_data())

        ob.refresh_from_db()
        assert ob.title == "原書名"
        assert ob.author == "改作者"
        assert ob.publisher == "改出版社"


class TestUploadedCoverIsPerSharedBook:
    def _render_cover(self, book: SharedBook) -> str:
        return render_to_string("partials/book_cover.html", {"book": book})

    def test_user_cover_shows_on_own_book_only(self):
        other_book = SharedBookFactory(official_book=_existing_official())
        ob = other_book.official_book
        ob.cover_image.save("original.jpg", _jpeg("original.jpg", (0, 0, 255)), save=True)
        original_url = ob.cover_image.url

        mine = publish_book(
            UserFactory(),
            _publish_data(),
            photos=[_jpeg()],
            cover=_jpeg("mine.jpg", (0, 255, 0)),
        )

        ob.refresh_from_db()
        assert ob.cover_image.url == original_url  # 共用封面不被取代
        assert mine.cover_image  # 存在自己的 SharedBook 上
        assert mine.display_cover.url == mine.cover_image.url
        assert mine.cover_image.url in self._render_cover(mine)

        other_book.refresh_from_db()
        assert other_book.display_cover.url == original_url
        html = self._render_cover(other_book)
        assert original_url in html
        assert mine.cover_image.url not in html

    def test_cover_fills_official_book_when_it_has_none(self):
        _existing_official()
        mine = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg()], cover=_jpeg("mine.jpg")
        )
        ob = OfficialBook.objects.get(isbn=ISBN)
        assert ob.cover_image
        assert not mine.cover_image
        assert mine.display_cover.url == ob.cover_image.url

    def test_book_without_any_cover_has_no_display_cover(self):
        book = SharedBookFactory()
        assert not book.display_cover
        assert "book-placeholder" in self._render_cover(book)
