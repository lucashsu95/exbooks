import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from books.models import SharedBook
from books.services.book_service import (
    declare_exception,
    list_book,
    resolve_exception,
    suspend_book,
    validate_book_set_completeness,
)
from tests.factories import BookSetFactory, SharedBookFactory


pytestmark = pytest.mark.django_db


class TestListBook:
    def test_list_from_suspended(self):
        book = SharedBookFactory(status="S")
        list_book(book)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.TRANSFERABLE
        assert book.listed_at is not None

    def test_list_from_non_suspended_raises(self):
        book = SharedBookFactory(status="T")
        with pytest.raises(ValidationError, match="暫不開放"):
            list_book(book)

    def test_list_sets_listed_at(self):
        book = SharedBookFactory(status="S")
        before = timezone.now()
        list_book(book)
        book.refresh_from_db()
        assert book.listed_at >= before


class TestSuspendBook:
    def test_suspend_from_transferable(self):
        book = SharedBookFactory(status="T")
        suspend_book(book)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.SUSPENDED

    def test_suspend_from_non_transferable_raises(self):
        book = SharedBookFactory(status="S")
        with pytest.raises(ValidationError, match="可移轉"):
            suspend_book(book)


class TestValidateBookSetCompleteness:
    def test_all_transferable(self):
        owner = SharedBookFactory(status="T").owner
        book_set = BookSetFactory(owner=owner)
        SharedBookFactory(status="T", owner=owner, book_set=book_set)
        SharedBookFactory(status="T", owner=owner, book_set=book_set)
        result = validate_book_set_completeness(book_set)
        assert len(result) == 2

    def test_some_not_transferable_raises(self):
        owner = SharedBookFactory(status="T").owner
        book_set = BookSetFactory(owner=owner)
        SharedBookFactory(status="T", owner=owner, book_set=book_set)
        SharedBookFactory(status="S", owner=owner, book_set=book_set)
        with pytest.raises(ValidationError, match="無法借出"):
            validate_book_set_completeness(book_set)

    def test_empty_book_set_raises(self):
        book_set = BookSetFactory()
        with pytest.raises(ValidationError, match="沒有包含任何書籍"):
            validate_book_set_completeness(book_set)


class TestDeclareException:
    @pytest.mark.parametrize("status", ["T", "O", "R"])
    def test_valid_statuses(self, status):
        book = SharedBookFactory(status=status)
        declare_exception(book)
        book.refresh_from_db()
        assert book.status == SharedBook.Status.EXCEPTION

    @pytest.mark.parametrize("status", ["S", "V", "E", "L", "D"])
    def test_invalid_statuses_raise(self, status):
        book = SharedBookFactory(status=status)
        with pytest.raises(ValidationError, match="無法宣告例外"):
            declare_exception(book)


class TestResolveException:
    def test_resolve_lost(self):
        book = SharedBookFactory(status="E")
        resolve_exception(book, "lost")
        book.refresh_from_db()
        assert book.status == SharedBook.Status.LOST

    def test_resolve_destroyed(self):
        book = SharedBookFactory(status="E")
        resolve_exception(book, "destroyed")
        book.refresh_from_db()
        assert book.status == SharedBook.Status.DESTROYED

    def test_resolve_found(self):
        book = SharedBookFactory(status="E")
        resolve_exception(book, "found")
        book.refresh_from_db()
        assert book.status == SharedBook.Status.SUSPENDED

    def test_non_exception_raises(self):
        book = SharedBookFactory(status="T")
        with pytest.raises(ValidationError, match="例外狀況"):
            resolve_exception(book, "lost")

    def test_invalid_resolution_raises(self):
        book = SharedBookFactory(status="E")
        with pytest.raises(ValidationError, match="無效的處置方式"):
            resolve_exception(book, "invalid")
