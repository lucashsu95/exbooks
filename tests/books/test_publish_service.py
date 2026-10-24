"""
publish / update / toggle_listing / due-soon 服務層測試。

直接打 service interface（不經 HTTP），錯誤契約：
ValidationError / PermissionDenied，訊息為使用者可讀中文。
"""

import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from books.models import BookPhoto, OfficialBook, SharedBook
from books.services import publish_book, toggle_listing, update_book
from deals.models import Deal
from deals.services.overdue_service import get_due_soon_deals
from tests.factories import (
    DealFactory,
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
    WishListItemFactory,
)

pytestmark = pytest.mark.django_db


def _jpeg(name="photo.jpg", color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _level1(user):
    """trust_score 4 → 2 星 → trust_level 1（解開 Level 0 限制）。"""
    user.profile.trust_score = 4
    user.profile.save()
    return user


def _publish_data(isbn="9787770001112", title="新書"):
    return {
        "isbn": isbn,
        "title": title,
        "author": "作者",
        "publisher": "出版社",
        "category": OfficialBook.Category.TECH,
        "transferability": SharedBook.Transferability.RETURN,
        "condition_description": "九成新",
        "loan_duration_days": 21,
    }


def _edit_data():
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


class TestPublishBook:
    def test_publish_creates_official_and_shared_book(self):
        user = UserFactory()
        shared = publish_book(user, _publish_data(), photos=[_jpeg()])

        assert shared.status == SharedBook.Status.TRANSFERABLE
        assert shared.owner == user
        assert shared.keeper == user
        assert shared.listed_at is not None
        assert shared.loan_duration_days == 21
        assert shared.official_book.isbn == "9787770001112"
        assert shared.official_book.title == "新書"
        assert BookPhoto.objects.filter(shared_book=shared).count() == 1

    def test_publish_updates_existing_official_book(self):
        user = UserFactory()
        OfficialBook.objects.create(isbn="9787770001112", title="舊書名")
        shared = publish_book(user, _publish_data(title="新書名"), photos=[_jpeg()])
        assert shared.official_book.title == "新書名"

    def test_publish_uploads_cover(self):
        user = UserFactory()
        shared = publish_book(user, _publish_data(), photos=[_jpeg()], cover=_jpeg("cover.jpg"))
        assert shared.official_book.cover_image

    def test_publish_cover_url_download_failure_does_not_block(self, monkeypatch):
        import books.services.book_service as bs

        def _boom(*args, **kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(bs.httpx, "get", _boom)
        user = UserFactory()
        data = _publish_data()
        data["cover_url"] = "http://cover.test/cover.jpg"
        shared = publish_book(user, data, photos=[_jpeg()])
        assert shared.status == SharedBook.Status.TRANSFERABLE
        assert not shared.official_book.cover_image

    def test_publish_notifies_wish_list_users(self):
        user = UserFactory()
        other = UserFactory()
        off = OfficialBookFactory()
        WishListItemFactory(user=other, official_book=off)

        with patch("books.services.book_service.notify_book_available") as mock_notify:
            shared = publish_book(user, _publish_data(isbn=off.isbn), photos=[_jpeg()])
        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0] == other
        assert mock_notify.call_args[0][1].pk == shared.pk

    def test_publish_invalid_photo_raises_and_rolls_back(self):
        user = UserFactory()
        bad = SimpleUploadedFile("x.exe", b"not an image", content_type="application/octet-stream")
        with pytest.raises(ValidationError):
            publish_book(user, _publish_data(), photos=[bad])
        assert OfficialBook.objects.filter(isbn="9787770001112").count() == 0
        assert SharedBook.objects.count() == 0


class TestUpdateBook:
    def test_level0_cannot_update(self):
        user = UserFactory()  # 預設 trust_score 0 → Level 0
        book = SharedBookFactory(owner=user)
        with pytest.raises(PermissionDenied):
            update_book(book, user, _edit_data())

    def test_update_official_and_shared_fields(self):
        user = _level1(UserFactory())
        book = SharedBookFactory(owner=user)
        update_book(book, user, _edit_data(), photos=[_jpeg()])
        book.refresh_from_db()
        assert book.official_book.title == "改書名"
        assert book.official_book.category == OfficialBook.Category.ART
        assert book.min_trust_level == 1
        assert book.loan_duration_days == 45
        assert BookPhoto.objects.filter(shared_book=book).count() == 1

    def test_update_invalid_photo_raises(self):
        user = _level1(UserFactory())
        book = SharedBookFactory(owner=user)
        bad = SimpleUploadedFile("x.exe", b"not an image", content_type="application/octet-stream")
        with pytest.raises(ValidationError):
            update_book(book, user, _edit_data(), photos=[bad])


class TestToggleListing:
    def test_suspended_to_transferable(self):
        user = _level1(UserFactory())
        book = SharedBookFactory(owner=user)
        assert book.status == SharedBook.Status.SUSPENDED
        assert toggle_listing(book, user) == SharedBook.Status.TRANSFERABLE

    def test_transferable_to_suspended(self):
        user = _level1(UserFactory())
        book = SharedBookFactory(owner=user, status=SharedBook.Status.TRANSFERABLE)
        assert toggle_listing(book, user) == SharedBook.Status.SUSPENDED

    def test_other_status_cannot_toggle(self):
        user = _level1(UserFactory())
        book = SharedBookFactory(owner=user, status=SharedBook.Status.OCCUPIED)
        with pytest.raises(ValidationError):
            toggle_listing(book, user)

    def test_level0_cannot_toggle(self):
        user = UserFactory()
        book = SharedBookFactory(owner=user)
        with pytest.raises(PermissionDenied):
            toggle_listing(book, user)


class TestGetDueSoonDeals:
    def test_lists_meeted_deals_within_window(self):
        user = UserFactory()
        soon = DealFactory(
            applicant=user,
            status=Deal.Status.MEETED,
            due_date=timezone.now().date() + timedelta(days=3),
        )
        far = DealFactory(
            applicant=user,
            status=Deal.Status.MEETED,
            due_date=timezone.now().date() + timedelta(days=30),
        )
        other_user_deal = DealFactory(
            status=Deal.Status.MEETED,
            due_date=timezone.now().date() + timedelta(days=1),
        )

        result = get_due_soon_deals(user, days=7)
        deals = [r["deal"] for r in result]
        assert soon in deals
        assert far not in deals
        assert other_user_deal not in deals

        entry = next(r for r in result if r["deal"] == soon)
        assert entry["days_left"] == 3
        assert entry["is_overdue"] is False

    def test_overdue_deal_not_due_soon(self):
        user = UserFactory()
        DealFactory(
            applicant=user,
            status=Deal.Status.MEETED,
            due_date=timezone.now().date() - timedelta(days=1),
        )
        assert get_due_soon_deals(user, days=7) == []
