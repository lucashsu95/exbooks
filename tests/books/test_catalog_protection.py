"""
共用書目（OfficialBook）保護：一般使用者只能補空白欄位，不能覆寫他人已填的資料；
使用者上傳的封面只出現在自己的 SharedBook，不取代共用封面。
"""

import io
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from PIL import Image

from books.models import OfficialBook, SharedBook
from books.services import publish_book, update_book
from books.services.book_service import _attach_cover, fill_blank_catalog_fields
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


def _png(name: str = "cover.png") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGBA", (40, 40), (0, 120, 0, 255)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def _gif(name: str = "cover.gif") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40)).save(buf, format="GIF")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/gif")


def _fake_jpeg() -> SimpleUploadedFile:
    return SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")


def _stored_files(prefix: str, storage: Storage = default_storage) -> list[str]:
    """遞迴列出 storage 中 prefix 底下的所有檔案。"""
    if not storage.exists(prefix):
        return []
    dirs, files = storage.listdir(prefix)
    found = [f"{prefix}/{f}" for f in files]
    for d in dirs:
        found.extend(_stored_files(f"{prefix}/{d}", storage))
    return found


def _official_with_cover(**fields) -> OfficialBook:
    ob = _existing_official(**fields)
    ob.cover_image.save("shared.jpg", _jpeg("shared.jpg", (0, 0, 255)), save=True)
    return ob


class TestFillBlankRechecksAfterLock:
    """併發發布：記憶體中的舊 instance 不可覆寫別人剛補上的欄位。"""

    def test_stale_instance_does_not_overwrite_concurrent_fill(self):
        ob = _existing_official(author="")
        stale = OfficialBook.objects.get(pk=ob.pk)
        OfficialBook.objects.filter(pk=ob.pk).update(author="先到者")

        filled = fill_blank_catalog_fields(stale, {"author": "後到者"})

        ob.refresh_from_db()
        assert ob.author == "先到者"
        assert filled == []
        assert stale.author == "先到者"  # 呼叫端 instance 與資料庫同步

    def test_filled_values_are_stripped(self):
        ob = _existing_official(author="", publisher="")
        fill_blank_catalog_fields(ob, {"author": "  新作者  ", "publisher": "   "})
        ob.refresh_from_db()
        assert ob.author == "新作者"
        assert ob.publisher == ""

    def test_new_official_book_values_are_stripped(self):
        shared = publish_book(
            UserFactory(),
            _publish_data(title="  書名  ", author=" 作者 "),
            photos=[_jpeg()],
        )
        assert shared.official_book.title == "書名"
        assert shared.official_book.author == "作者"


class TestCoverRechecksAfterLock:
    def test_upload_goes_to_shared_book_when_cover_filled_concurrently(self):
        ob = _existing_official()
        stale = OfficialBook.objects.get(pk=ob.pk)
        fresh = OfficialBook.objects.get(pk=ob.pk)
        fresh.cover_image.save("first.jpg", _jpeg("first.jpg"), save=True)
        shared = SharedBookFactory(official_book=ob)

        _attach_cover(stale, shared, _jpeg("mine.jpg"))

        ob.refresh_from_db()
        assert ob.cover_image.name == fresh.cover_image.name
        shared.refresh_from_db()
        assert shared.cover_image

    def test_downloaded_cover_discarded_when_cover_filled_concurrently(self):
        ob = _existing_official()
        stale = OfficialBook.objects.get(pk=ob.pk)
        fresh = OfficialBook.objects.get(pk=ob.pk)
        fresh.cover_image.save("first.jpg", _jpeg("first.jpg"), save=True)
        shared = SharedBookFactory(official_book=ob)

        downloaded = ContentFile(_jpeg().read(), name="dl.jpg")
        with patch(
            "books.services.book_service.cover_service.fetch_cover_image",
            return_value=downloaded,
        ):
            _attach_cover(stale, shared, None, "https://example.com/c.jpg")

        ob.refresh_from_db()
        assert ob.cover_image.name == fresh.cover_image.name
        shared.refresh_from_db()
        assert not shared.cover_image


class TestSharedBookCoverPipeline:
    def test_png_cover_is_reencoded_to_jpg(self):
        _official_with_cover()
        mine = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg()], cover=_png()
        )
        assert mine.cover_image.name.endswith(".jpg")
        with mine.cover_image.open("rb") as fh:
            assert Image.open(fh).format == "JPEG"

    def test_official_cover_upload_also_reencoded(self):
        _existing_official()
        mine = publish_book(
            UserFactory(), _publish_data(), photos=[_jpeg()], cover=_png()
        )
        assert mine.official_book.cover_image.name.endswith(".jpg")

    @pytest.mark.parametrize("make_bad", [_gif, _fake_jpeg])
    def test_invalid_cover_rejected_and_nothing_persisted(self, make_bad):
        _official_with_cover()
        owner = UserFactory()
        before = set(_stored_files("shared_book_covers"))
        with pytest.raises(ValidationError):
            publish_book(owner, _publish_data(), photos=[_jpeg()], cover=make_bad())
        assert not SharedBook.objects.filter(owner=owner).exists()
        assert set(_stored_files("shared_book_covers")) == before

    def test_cover_file_deleted_when_publish_rolls_back(self):
        _official_with_cover()
        owner = UserFactory()
        before = set(_stored_files("shared_book_covers"))
        with pytest.raises(ValidationError):
            # 封面合法、書況照片不合法 → 整筆回滾，已存的封面檔也要清掉
            publish_book(
                owner, _publish_data(), photos=[_gif()], cover=_jpeg("m.jpg")
            )
        assert not SharedBook.objects.filter(owner=owner).exists()
        assert set(_stored_files("shared_book_covers")) == before

    def test_official_cover_file_deleted_when_publish_rolls_back(self):
        ob = _existing_official()
        prefix = OfficialBook._meta.get_field("cover_image").upload_to.split("/")[0]
        before = set(_stored_files(prefix))
        with pytest.raises(ValidationError):
            publish_book(
                UserFactory(), _publish_data(), photos=[_gif()], cover=_jpeg("m.jpg")
            )
        ob.refresh_from_db()
        assert not ob.cover_image
        assert set(_stored_files(prefix)) == before


class TestSharedBookCoverFileCleanup:
    def _book_with_cover(self) -> SharedBook:
        book = SharedBookFactory()
        book.cover_image.save("own.jpg", _jpeg("own.jpg"), save=True)
        book = SharedBook.objects.get(pk=book.pk)
        assert default_storage.exists(book.cover_image.name)
        return book

    def test_file_deleted_with_shared_book(self, django_capture_on_commit_callbacks):
        book = self._book_with_cover()
        name = book.cover_image.name
        with django_capture_on_commit_callbacks(execute=True):
            book.delete()
        assert not default_storage.exists(name)

    def test_old_file_deleted_when_cover_replaced(
        self, django_capture_on_commit_callbacks
    ):
        book = self._book_with_cover()
        old_name = book.cover_image.name
        with django_capture_on_commit_callbacks(execute=True):
            book.cover_image.save("new.jpg", _jpeg("new.jpg"), save=True)
        assert not default_storage.exists(old_name)
        assert default_storage.exists(book.cover_image.name)

    def test_unrelated_save_keeps_file(self, django_capture_on_commit_callbacks):
        book = self._book_with_cover()
        name = book.cover_image.name
        with django_capture_on_commit_callbacks(execute=True):
            book.condition_description = "改書況"
            book.save()
        assert default_storage.exists(name)
