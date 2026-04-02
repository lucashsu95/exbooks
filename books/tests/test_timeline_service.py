"""
書籍時間線服務測試 - 測試 BookTimelineService 的所有功能
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from books.models import SharedBook, BookPhoto, OfficialBook
from deals.models import Deal, LoanExtension, DealMessage
from books.services.book_timeline_service import BookTimelineService
from tests.factories import (
    UserFactory,
    SharedBookFactory,
    OfficialBookFactory,
    DealFactory,
    LoanExtensionFactory,
    BookPhotoFactory,
)


@pytest.mark.django_db
class TestBookTimelineService:
    """書籍時間線服務測試類別"""

    def test_get_timeline_events_empty_book(self):
        """測試取得空書籍的時間線事件"""
        book = SharedBookFactory(listed_at=None)

        events = BookTimelineService.get_timeline_events(book)

        # 沒有上架時間，沒有事件
        assert len(events) == 0

    def test_get_timeline_events_with_listing(self):
        """測試取得有上架事件的時間線"""
        book = SharedBookFactory(listed_at=timezone.now())

        events = BookTimelineService.get_timeline_events(book)

        assert len(events) == 1
        assert events[0]["type"] == "listed"
        assert events[0]["title"] == "書籍上架"
        # 驗證描述包含用戶名稱
        assert book.owner.email in events[0]["description"] or (
            book.owner.profile.nickname in events[0]["description"]
        )

    def test_get_timeline_events_with_deals(self):
        """測試取得有交易記錄的時間線"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(
            owner=owner, listed_at=timezone.now() - timedelta(days=10)
        )

        # 建立一筆交易
        deal = DealFactory(
            shared_book=book,
            applicant=applicant,
            deal_type=Deal.DealType.LOAN,
            status=Deal.Status.REQUESTED,
        )

        events = BookTimelineService.get_timeline_events(book)

        # 應該有上架事件 + 交易申請事件
        assert len(events) >= 2

        deal_events = [e for e in events if e["type"] == "deal_created"]
        assert len(deal_events) == 1
        assert deal_events[0]["deal"] == deal
        # 驗證標題包含交易類型
        assert deal.get_deal_type_display() in deal_events[0]["title"]

    def test_get_timeline_events_with_completed_deal(self):
        """測試取得已完成交易的時間線"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner)

        # 建立已完成交易
        deal = DealFactory(
            shared_book=book,
            applicant=applicant,
            deal_type=Deal.DealType.LOAN,
            status=Deal.Status.DONE,
        )

        events = BookTimelineService.get_timeline_events(book)

        # 應該有交易申請和交易完成事件
        deal_created_events = [e for e in events if e["type"] == "deal_created"]
        deal_done_events = [e for e in events if e["type"] == "deal_done"]

        assert len(deal_created_events) == 1
        assert len(deal_done_events) == 1
        assert deal_done_events[0]["title"] == "交易完成"

    def test_get_timeline_events_with_extensions(self):
        """測試取得有延長借閱的時間線"""
        owner = UserFactory()
        applicant = UserFactory()
        book = SharedBookFactory(owner=owner)

        deal = DealFactory(
            shared_book=book,
            applicant=applicant,
            deal_type=Deal.DealType.LOAN,
            status=Deal.Status.MEETED,
        )

        # 建立延長申請
        extension = LoanExtensionFactory(
            deal=deal,
            requested_by=applicant,
            status=LoanExtension.Status.APPROVED,
            extra_days=7,
        )

        events = BookTimelineService.get_timeline_events(book)

        extension_events = [e for e in events if e["type"] == "extension"]
        assert len(extension_events) == 1
        assert "延長 7 天（已核准）" in extension_events[0]["description"]
        assert extension_events[0]["user"] == applicant

    def test_get_timeline_events_with_photos(self):
        """測試取得有書況照片的時間線"""
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)

        # 建立書況照片
        photo = BookPhotoFactory(
            shared_book=book,
            uploader=owner,
            caption="書籍封面照片",
        )

        events = BookTimelineService.get_timeline_events(book)

        photo_events = [e for e in events if e["type"] == "photo_upload"]
        assert len(photo_events) == 1
        assert photo_events[0]["photo"] == photo
        assert "上傳了書況照片" in photo_events[0]["description"]

    def test_get_book_photos_with_limit(self):
        """測試取得書籍照片（限制數量）"""
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)

        # 建立超過限制的照片數量
        for i in range(10):
            BookPhotoFactory(
                shared_book=book,
                uploader=owner,
                caption=f"照片 {i}",
            )

        photos = BookTimelineService.get_book_photos(book)

        # 應該限制在 MAX_PHOTOS_PER_BOOK 張
        from core.constants import MAX_PHOTOS_PER_BOOK

        assert len(photos) == MAX_PHOTOS_PER_BOOK

    def test_check_wishlist_status_authenticated_true(self):
        """測試已登入用戶在願望清單中的檢查"""
        user = UserFactory()
        official_book = OfficialBookFactory()

        # 手動建立願望清單項目
        from books.models import WishListItem

        WishListItem.objects.create(user=user, official_book=official_book)

        result = BookTimelineService.check_wishlist_status(user, official_book.id)
        assert result is True

    def test_check_wishlist_status_authenticated_false(self):
        """測試已登入用戶不在願望清單中的檢查"""
        user = UserFactory()
        official_book = OfficialBookFactory()

        result = BookTimelineService.check_wishlist_status(user, official_book.id)
        assert result is False

    def test_check_wishlist_status_unauthenticated(self):
        """測試未登入用戶的願望清單檢查"""
        official_book = OfficialBookFactory()

        result = BookTimelineService.check_wishlist_status(None, official_book.id)
        assert result is False

    def test_check_wishlist_status_not_authenticated_user(self):
        """測試未登入（用戶物件為 None）的情況"""
        official_book = OfficialBookFactory()

        result = BookTimelineService.check_wishlist_status(None, official_book.id)
        assert result is False

    def test_event_sorting_newest_first(self):
        """測試事件排序（新到舊）"""
        owner = UserFactory()
        book = SharedBookFactory(
            owner=owner,
            listed_at=timezone.now() - timedelta(days=10),
        )

        # 建立較舊的照片
        old_photo = BookPhotoFactory(
            shared_book=book,
            uploader=owner,
            created_at=timezone.now() - timedelta(days=5),
        )

        # 建立較新的交易
        deal = DealFactory(
            shared_book=book,
            applicant=UserFactory(),
            created_at=timezone.now() - timedelta(days=2),
        )

        events = BookTimelineService.get_timeline_events(book)

        # 驗證排序：新的事件在前（交易比照片新）
        assert len(events) >= 3  # 上架 + 照片 + 交易

        # 第一個事件應該是最新的（交易）
        assert events[0]["time"] > events[1]["time"]

        # 有交易事件
        deal_events = [e for e in events if e.get("type") == "deal_created"]
        assert len(deal_events) == 1

    def test_format_user_display_with_nickname(self):
        """測試格式化用戶顯示名稱（有暱稱）"""
        user = UserFactory()
        user.profile.nickname = "測試暱稱"
        user.profile.save()

        result = BookTimelineService._format_user_display(user)
        assert "測試暱稱 分享了這本書" in result

    def test_format_user_display_without_nickname(self):
        """測試格式化用戶顯示名稱（無暱稱）"""
        user = UserFactory()
        user.profile.nickname = ""
        user.profile.save()

        result = BookTimelineService._format_user_display(user)
        assert f"{user.email} 分享了這本書" in result

    def test_format_photo_description_with_caption(self):
        """測試格式化照片描述（有標題）"""
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)
        photo = BookPhotoFactory(
            shared_book=book,
            uploader=owner,
            caption="書籍封面",
        )

        result = BookTimelineService._format_photo_description(photo)
        assert "上傳了書況照片" in result
        assert "：書籍封面" in result

    def test_format_photo_description_without_caption(self):
        """測試格式化照片描述（無標題）"""
        owner = UserFactory()
        book = SharedBookFactory(owner=owner)
        photo = BookPhotoFactory(
            shared_book=book,
            uploader=owner,
            caption="",
        )

        result = BookTimelineService._format_photo_description(photo)
        assert "上傳了書況照片" in result
        assert "：" not in result  # 無標題時不該有冒號
