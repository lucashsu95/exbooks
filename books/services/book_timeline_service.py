"""
書籍時間線服務 - 處理書籍詳情頁面的時間線事件邏輯

遵循單一職責原則，將複雜的時間線構建邏輯從視圖中分離出來。
"""

from typing import Dict, List, Any, Optional

from django.db.models import QuerySet
from django.contrib.auth import get_user_model

from books.models import SharedBook, BookPhoto
from deals.models import Deal, LoanExtension
from core.constants import MAX_PHOTOS_PER_BOOK

User = get_user_model()


class BookTimelineService:
    """書籍時間線事件服務"""

    @staticmethod
    def get_timeline_events(book: SharedBook) -> List[Dict[str, Any]]:
        """
        取得書籍的所有時間線事件

        Args:
            book: SharedBook 實例

        Returns:
            按時間排序的時間線事件列表（新到舊）
        """
        timeline_events = []

        # 1. 書籍上架事件
        timeline_events.extend(BookTimelineService._get_listing_events(book))

        # 2. 交易記錄事件
        timeline_events.extend(BookTimelineService._get_deal_events(book))

        # 3. 延長借閱事件
        timeline_events.extend(BookTimelineService._get_extension_events(book))

        # 4. 書況照片上傳事件
        timeline_events.extend(BookTimelineService._get_photo_events(book))

        # 按時間排序（新到舊）
        timeline_events.sort(key=lambda x: x["time"], reverse=True)

        return timeline_events

    @staticmethod
    def _get_listing_events(book: SharedBook) -> List[Dict[str, Any]]:
        """取得書籍上架事件"""
        if not book.listed_at:
            return []

        return [
            {
                "type": "listed",
                "time": book.listed_at,
                "title": "書籍上架",
                "description": BookTimelineService._format_user_display(book.owner),
                "user": book.owner,
            }
        ]

    @staticmethod
    def _get_deal_events(book: SharedBook) -> List[Dict[str, Any]]:
        """取得交易相關事件"""
        deals = (
            Deal.objects.filter(shared_book=book)
            .select_related("applicant__profile", "responder__profile")
            .order_by("created_at")
        )

        events = []
        for deal in deals:
            # 交易申請事件
            if deal.status in [
                Deal.Status.REQUESTED,
                Deal.Status.RESPONDED,
                Deal.Status.MEETED,
                Deal.Status.DONE,
            ]:
                events.append(
                    {
                        "type": "deal_created",
                        "time": deal.created_at,
                        "title": f"{deal.get_deal_type_display()}申請",
                        "description": BookTimelineService._format_deal_creation_description(
                            deal
                        ),
                        "user": deal.applicant,
                        "deal": deal,
                    }
                )

            # 面交完成事件
            if deal.status in [Deal.Status.MEETED, Deal.Status.DONE]:
                events.append(
                    {
                        "type": "deal_meeted",
                        "time": deal.updated_at,
                        "title": "面交完成",
                        "description": BookTimelineService._format_meeting_completion_description(
                            deal
                        ),
                        "user": deal.applicant,
                        "deal": deal,
                    }
                )

            # 交易完成事件
            if deal.status == Deal.Status.DONE:
                events.append(
                    {
                        "type": "deal_done",
                        "time": deal.updated_at,
                        "title": "交易完成",
                        "description": "雙方已完成評價",
                        "deal": deal,
                    }
                )

        return events

    @staticmethod
    def _get_extension_events(book: SharedBook) -> List[Dict[str, Any]]:
        """取得延長借閱事件"""
        extensions = (
            LoanExtension.objects.filter(deal__shared_book=book)
            .select_related("requested_by__profile", "approved_by__profile")
            .order_by("created_at")
        )

        events = []
        for ext in extensions:
            status_display = (
                "（已核准）"
                if ext.status == "APPROVED"
                else f"（{ext.get_status_display()}）"
            )

            events.append(
                {
                    "type": "extension",
                    "time": ext.created_at,
                    "title": "延長借閱",
                    "description": f"延長 {ext.extra_days} 天{status_display}",
                    "user": ext.requested_by,
                }
            )

        return events

    @staticmethod
    def _get_photo_events(book: SharedBook) -> List[Dict[str, Any]]:
        """取得書況照片上傳事件"""
        book_photos = (
            BookPhoto.objects.filter(shared_book=book)
            .select_related("uploader__profile", "deal")
            .order_by("-created_at")
        )

        events = []
        for photo in book_photos:
            description = BookTimelineService._format_photo_description(photo)

            events.append(
                {
                    "type": "photo_upload",
                    "time": photo.created_at,
                    "title": "書況照片",
                    "description": description,
                    "user": photo.uploader,
                    "photo": photo,
                    "deal": photo.deal,
                }
            )

        return events

    @staticmethod
    def get_book_photos(book: SharedBook) -> QuerySet[BookPhoto]:
        """
        取得書籍的照片（限制數量）

        Args:
            book: SharedBook 實例

        Returns:
            照片 QuerySet（已限制數量）
        """
        return book.photos.all()[:MAX_PHOTOS_PER_BOOK]

    @staticmethod
    def check_wishlist_status(user: Optional[User], official_book_id: int) -> bool:
        """
        檢查用戶是否已將書籍加入願望清單

        Args:
            user: 用戶實例（可為 None）
            official_book_id: OfficialBook 的 ID

        Returns:
            True 表示已在願望清單中
        """
        if not user or not user.is_authenticated:
            return False

        from books.models import WishListItem

        return WishListItem.objects.filter(
            user=user,
            official_book_id=official_book_id,
        ).exists()

    @staticmethod
    def _format_user_display(user: User) -> str:
        """格式化用戶顯示名稱"""
        if hasattr(user, "profile") and user.profile.nickname:
            return f"{user.profile.nickname} 分享了這本書"
        return f"{user.email} 分享了這本書"

    @staticmethod
    def _format_deal_creation_description(deal: Deal) -> str:
        """格式化交易創建描述"""
        user_display = BookTimelineService._format_user_display(deal.applicant).replace(
            "分享了這本書", f"發起了{deal.get_deal_type_display()}"
        )
        return user_display

    @staticmethod
    def _format_meeting_completion_description(deal: Deal) -> str:
        """格式化面交完成描述"""
        user_display = BookTimelineService._format_user_display(deal.applicant).replace(
            "分享了這本書", "已收到書籍"
        )
        return f"書籍已交給 {user_display}"

    @staticmethod
    def _format_photo_description(photo: BookPhoto) -> str:
        """格式化照片描述"""
        description = BookTimelineService._format_user_display(photo.uploader).replace(
            "分享了這本書", "上傳了書況照片"
        )

        if photo.caption:
            description += f"：{photo.caption}"

        if photo.deal:
            description += f"（{photo.deal.get_deal_type_display()}）"

        return description
