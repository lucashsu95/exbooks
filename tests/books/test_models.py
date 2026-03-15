import uuid

import pytest
from django.db import IntegrityError

from books.models import BookPhoto, BookSet, OfficialBook, SharedBook, WishListItem
from tests.factories import (
    BookPhotoFactory,
    BookSetFactory,
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
    WishListItemFactory,
)


pytestmark = pytest.mark.django_db


class TestOfficialBook:
    def test_create(self):
        book = OfficialBookFactory()
        assert book.pk is not None
        assert isinstance(book.pk, uuid.UUID)
        assert book.created_at is not None
        assert book.updated_at is not None

    def test_isbn_unique(self):
        OfficialBookFactory(isbn="9781234567890")
        with pytest.raises(IntegrityError):
            OfficialBookFactory(isbn="9781234567890")

    def test_str(self):
        book = OfficialBookFactory(title="測試書籍", isbn="9781234567890")
        assert str(book) == "測試書籍 (9781234567890)"

    def test_db_table(self):
        assert OfficialBook._meta.db_table == "exbook_official_book"

    def test_blank_fields(self):
        book = OfficialBookFactory(author="", publisher="", description="")
        assert book.author == ""
        assert book.publisher == ""
        assert book.description == ""


class TestBookSet:
    def test_create(self):
        book_set = BookSetFactory()
        assert book_set.pk is not None
        assert book_set.owner is not None

    def test_str(self):
        book_set = BookSetFactory(name="哈利波特全集")
        assert str(book_set) == "哈利波特全集"

    def test_db_table(self):
        assert BookSet._meta.db_table == "exbook_book_set"

    def test_owner_protect(self):
        """Owner uses PROTECT — cannot delete user with book sets."""
        book_set = BookSetFactory()
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            book_set.owner.delete()


class TestSharedBook:
    def test_create(self):
        book = SharedBookFactory()
        assert book.pk is not None
        assert book.owner is not None
        assert book.keeper == book.owner  # Factory default

    def test_status_choices(self):
        assert SharedBook.Status.SUSPENDED == "S"
        assert SharedBook.Status.TRANSFERABLE == "T"
        assert SharedBook.Status.RESTORABLE == "R"
        assert SharedBook.Status.RESERVED == "V"
        assert SharedBook.Status.OCCUPIED == "O"
        assert SharedBook.Status.EXCEPTION == "E"
        assert SharedBook.Status.LOST == "L"
        assert SharedBook.Status.DESTROYED == "D"

    def test_transferability_choices(self):
        assert SharedBook.Transferability.TRANSFER == "TRANSFER"
        assert SharedBook.Transferability.RETURN == "RETURN"

    def test_default_status(self):
        book = SharedBookFactory()
        assert book.status == SharedBook.Status.SUSPENDED

    def test_default_loan_duration(self):
        book = SharedBookFactory()
        assert book.loan_duration_days == 30

    def test_default_extend_duration(self):
        book = SharedBookFactory()
        assert book.extend_duration_days == 14

    def test_str(self):
        book = SharedBookFactory()
        result = str(book)
        assert book.official_book.title in result

    def test_book_set_nullable(self):
        book = SharedBookFactory(book_set=None)
        assert book.book_set is None

    def test_listed_at_nullable(self):
        book = SharedBookFactory()
        assert book.listed_at is None

    def test_db_table(self):
        assert SharedBook._meta.db_table == "exbook_shared_book"

    def test_owner_protect(self):
        from django.db.models import ProtectedError

        book = SharedBookFactory()
        with pytest.raises(ProtectedError):
            book.owner.delete()

    def test_official_book_protect(self):
        from django.db.models import ProtectedError

        book = SharedBookFactory()
        with pytest.raises(ProtectedError):
            book.official_book.delete()


class TestBookPhoto:
    def test_create(self):
        photo = BookPhotoFactory()
        assert photo.pk is not None
        assert photo.shared_book is not None
        assert photo.uploader is not None
        assert photo.created_at is not None

    def test_no_updated_at(self):
        """BookPhoto uses BaseModel, not UpdatableModel — no updated_at."""
        photo = BookPhotoFactory()
        assert not hasattr(photo, "updated_at") or "updated_at" not in [
            f.name for f in BookPhoto._meta.get_fields()
        ]

    def test_ordering(self):
        assert BookPhoto._meta.ordering == ["-created_at"]

    def test_deal_nullable(self):
        photo = BookPhotoFactory()
        assert photo.deal is None

    def test_db_table(self):
        assert BookPhoto._meta.db_table == "exbook_book_photo"


class TestWishListItem:
    def test_create(self):
        item = WishListItemFactory()
        assert item.pk is not None

    def test_unique_constraint(self):
        user = UserFactory()
        book = OfficialBookFactory()
        WishListItemFactory(user=user, official_book=book)
        with pytest.raises(IntegrityError):
            WishListItemFactory(user=user, official_book=book)

    def test_str(self):
        item = WishListItemFactory()
        result = str(item)
        assert "→" in result

    def test_db_table(self):
        assert WishListItem._meta.db_table == "exbook_wish_list_item"

    def test_user_cascade_delete(self):
        item = WishListItemFactory()
        user = item.user
        user.delete()
        assert not WishListItem.objects.filter(pk=item.pk).exists()
