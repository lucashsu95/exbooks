import pytest
from django.core.exceptions import ValidationError

from books.models import WishListItem
from books.services.book_service import list_book
from books.services.wishlist_service import add_wish, remove_wish
from deals.models import Notification
from tests.factories import (
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
    WishListItemFactory,
)


pytestmark = pytest.mark.django_db


# ============================================================
# add_wish
# ============================================================
class TestAddWish:
    def test_success(self):
        user = UserFactory()
        book = OfficialBookFactory()
        item = add_wish(user, book)
        assert item.user == user
        assert item.official_book == book
        assert WishListItem.objects.filter(
            user=user,
            official_book=book,
        ).exists()

    def test_duplicate_raises(self):
        user = UserFactory()
        book = OfficialBookFactory()
        add_wish(user, book)
        with pytest.raises(ValidationError, match="已在"):
            add_wish(user, book)

    def test_different_users_same_book(self):
        """不同使用者可加入同一本書"""
        book = OfficialBookFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        add_wish(user1, book)
        add_wish(user2, book)
        assert WishListItem.objects.filter(official_book=book).count() == 2


# ============================================================
# remove_wish
# ============================================================
class TestRemoveWish:
    def test_success(self):
        user = UserFactory()
        book = OfficialBookFactory()
        WishListItemFactory(user=user, official_book=book)
        remove_wish(user, book)
        assert not WishListItem.objects.filter(
            user=user,
            official_book=book,
        ).exists()

    def test_not_found_raises(self):
        user = UserFactory()
        book = OfficialBookFactory()
        with pytest.raises(ValidationError, match="不在"):
            remove_wish(user, book)


# ============================================================
# list_book → WishList 通知觸發
# ============================================================
class TestListBookWishlistNotification:
    def test_notifies_wishers(self):
        """上架書籍時，通知願望書車中的使用者"""
        official = OfficialBookFactory()
        wisher1 = UserFactory()
        wisher2 = UserFactory()
        WishListItemFactory(user=wisher1, official_book=official)
        WishListItemFactory(user=wisher2, official_book=official)
        book = SharedBookFactory(official_book=official, status="S")
        list_book(book)
        notifs = Notification.objects.filter(
            notification_type="BOOK_AVAILABLE",
        )
        assert notifs.count() == 2
        assert notifs.filter(recipient=wisher1).exists()
        assert notifs.filter(recipient=wisher2).exists()

    def test_no_wishers_no_notification(self):
        """無人在願望書車 → 不發通知"""
        book = SharedBookFactory(status="S")
        list_book(book)
        assert not Notification.objects.filter(
            notification_type="BOOK_AVAILABLE",
        ).exists()

    def test_only_matching_book_wishers(self):
        """只通知對應 OfficialBook 的願望者"""
        official_a = OfficialBookFactory()
        official_b = OfficialBookFactory()
        wisher_a = UserFactory()
        wisher_b = UserFactory()
        WishListItemFactory(user=wisher_a, official_book=official_a)
        WishListItemFactory(user=wisher_b, official_book=official_b)
        book = SharedBookFactory(official_book=official_a, status="S")
        list_book(book)
        notifs = Notification.objects.filter(
            notification_type="BOOK_AVAILABLE",
        )
        assert notifs.count() == 1
        assert notifs.filter(recipient=wisher_a).exists()
