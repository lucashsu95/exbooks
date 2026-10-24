"""
書籍領域服務。

此模組封裝 SharedBook 的發布（publish）、編輯與狀態轉換邏輯，
使用 django-fsm 管理狀態。
Service 層負責：
- 權限檢查
- 跨 Model 事務協調
- 觸發 FSM 狀態轉換

副作用（通知）由 Signal 處理。
錯誤契約：失敗一律 raise ValidationError / PermissionDenied（訊息為
使用者可讀的中文）；View 層負責轉譯為 messages 與 HTTP 回應。
"""

import logging
import os

import httpx
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django_fsm import can_proceed

from books.models import BookPhoto, OfficialBook, SharedBook, WishListItem
from books.services.photo_service import validate_and_process as process_book_photo
from deals.services.notification_service import notify_book_available

logger = logging.getLogger(__name__)

# ============================================================================
# 書籍上架/下架
# ============================================================================


def list_book(shared_book):
    """
    將書籍狀態從 S（暫不開放）切換為 T（可移轉），開放借閱。

    使用 FSM 狀態轉換：SUSPENDED → TRANSFERABLE

    副作用（由 Signal 處理）：
    - 記錄上架時間
    - 通知願望清單中的使用者

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.list_for_transfer):
        raise ValidationError(
            f"只有「暫不開放」的書籍可以開放，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.list_for_transfer()
    # 記錄上架時間（在 save 之前設定）
    shared_book.listed_at = timezone.now()
    shared_book.save()

    # 通知願望書車中的使用者此書已可借閱
    wish_items = WishListItem.objects.filter(
        official_book=shared_book.official_book,
    ).select_related("user")
    for item in wish_items:
        notify_book_available(item.user, shared_book)

    logger.info(
        "book listed",
        extra={
            "book_id": shared_book.id,
            "owner_id": shared_book.owner_id,
            "wish_notified": wish_items.count(),
        },
    )


def suspend_book(shared_book):
    """
    將書籍狀態從 T（可移轉）切換為 S（暫不開放），暫停接受借閱。

    使用 FSM 狀態轉換：TRANSFERABLE → SUSPENDED

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.suspend):
        raise ValidationError(
            f"只有「可移轉」的書籍可以暫停，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.suspend()
    shared_book.save()

    logger.info("book suspended", extra={"book_id": shared_book.id})


# ============================================================================
# 發布（publish）/ 編輯 / 狀態切換
# ============================================================================


def _attach_cover(official_book, uploaded_cover, cover_url=""):
    """
    為 OfficialBook 附上封面。

    優先序：上傳檔 > 既有封面 > 下載 cover_url。
    下載失敗只記錄日誌、不中斷發布。
    """
    if uploaded_cover:
        official_book.cover_image.save(
            uploaded_cover.name, uploaded_cover, save=True
        )
        return

    if not cover_url or official_book.cover_image:
        return

    try:
        resp = httpx.get(cover_url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        ext = os.path.splitext(cover_url.split("?")[0])[1] or ".jpg"
        official_book.cover_image.save(
            f"{official_book.pk}{ext}",
            ContentFile(resp.content),
            save=True,
        )
    except Exception:
        logger.exception(
            "cover download failed",
            extra={
                "official_book_id": official_book.pk,
                "isbn": official_book.isbn,
                "cover_url": cover_url,
            },
        )


def _create_book_photo(shared_book, uploader, image):
    processed = process_book_photo(image)
    BookPhoto.objects.create(
        shared_book=shared_book,
        uploader=uploader,
        photo=processed,
    )


def publish_book(owner, data, photos=(), cover=None, cover_url=""):
    """
    發布（publish）：將一冊實體書上架為 SharedBook 並進入 TRANSFERABLE 狀態。

    完整流程（單一事務）：
    1. OfficialBook 依 ISBN upsert
    2. 附封面（上傳檔優先，其次下載 cover_url；下載失敗不中斷）
    3. 建立 SharedBook（owner = keeper = 發布者，初始狀態 SUSPENDED）
    4. 寫入書況照片
    5. 透過 list_book() 走合法 FSM 通道 S → T
       （副作用：記錄上架時間、通知願望清單使用者）

    Args:
        owner: 發布者（同時成為 owner 與 keeper）
        data: form 校驗後的 dict，需含 isbn/title/author/publisher/category
              及 SharedBook 欄位 transferability/condition_description/
              loan_duration_days
        photos: 書況照片（上傳檔）的可迭代集
        cover: 手動上傳的封面圖片（可選）
        cover_url: 封面 URL（無上傳封面時下載；失敗不中斷發布）

    Returns:
        SharedBook: 已進入 TRANSFERABLE 狀態的新書

    Raises:
        ValidationError: 照片驗證/處理失敗
    """
    isbn = data["isbn"]
    with transaction.atomic():
        off_book, created = OfficialBook.objects.get_or_create(
            isbn=isbn,
            defaults={
                "title": data["title"],
                "author": data.get("author", ""),
                "publisher": data.get("publisher", ""),
                "category": data["category"],
            },
        )
        if not created:
            off_book.title = data["title"]
            off_book.author = data.get("author", "")
            off_book.publisher = data.get("publisher", "")
            off_book.category = data["category"]
            off_book.save(
                update_fields=[
                    "title",
                    "author",
                    "publisher",
                    "category",
                    "updated_at",
                ]
            )

        _attach_cover(off_book, cover, cover_url)

        shared = SharedBook.objects.create(
            official_book=off_book,
            owner=owner,
            keeper=owner,
            transferability=data["transferability"],
            condition_description=data.get("condition_description", ""),
            loan_duration_days=data.get("loan_duration_days", 30),
        )

        for image in photos:
            _create_book_photo(shared, owner, image)

    # 透過合法 FSM 通道上架；listed_at 與願望清單通知由 list_book 處理
    list_book(shared)

    logger.info(
        "book published",
        extra={"owner_id": owner.pk, "shared_book_id": shared.pk, "isbn": isbn},
    )
    return shared


def update_book(book, user, data, photos=()):
    """
    更新書籍資訊（OfficialBook 基本資料 + SharedBook 欄位 + 新增照片）。

    Args:
        book: 要更新的 SharedBook（ownership 由 View 層以
              get_object_or_404(owner=user) 保證）
        user: 操作者
        data: form 校驗後的 dict，需含 title/author/publisher/category 及
              transferability/min_trust_level/condition_description/
              loan_duration_days
        photos: 新增的書況照片（上傳檔）的可迭代集

    Returns:
        SharedBook: 更新後的書籍

    Raises:
        PermissionDenied: Level 0 使用者
        ValidationError: 照片驗證/處理失敗
    """
    if user.profile.trust_level == 0:
        raise PermissionDenied(
            "新手等級 (Level 0) 尚無權限編輯書籍資訊，請多參與交易提升等級。"
        )

    with transaction.atomic():
        official_book = book.official_book
        official_book.title = data["title"]
        official_book.author = data.get("author", "")
        official_book.publisher = data.get("publisher", "")
        official_book.category = data["category"]
        official_book.save()

        book.transferability = data["transferability"]
        book.min_trust_level = data["min_trust_level"]
        book.condition_description = data.get("condition_description", "")
        book.loan_duration_days = data["loan_duration_days"]
        book.save()

        for image in photos:
            _create_book_photo(book, user, image)

    logger.info(
        "book updated",
        extra={"user_id": user.pk, "shared_book_id": book.pk},
    )
    return book


def toggle_listing(book, user):
    """
    切換書籍借閱狀態 S ↔ T。其他狀態（O/E/R…）不可切換。

    Args:
        book: 要切換的 SharedBook（ownership 由 View 層保證）
        user: 操作者

    Returns:
        str: 切換後的狀態值

    Raises:
        PermissionDenied: Level 0 使用者
        ValidationError: 目前狀態不可切換
    """
    if user.profile.trust_level == 0:
        raise PermissionDenied("新手等級 (Level 0) 尚無權限切換書籍狀態。")

    if book.status == SharedBook.Status.SUSPENDED:
        list_book(book)
    elif book.status == SharedBook.Status.TRANSFERABLE:
        suspend_book(book)
    else:
        raise ValidationError("書籍狀態無法切換")

    logger.info(
        "book listing toggled",
        extra={"user_id": user.pk, "shared_book_id": book.pk, "status": book.status},
    )
    return book.status


# ============================================================================
# 套書驗證
# ============================================================================


def validate_book_set_completeness(book_set):
    """
    BR-7: 驗證套書中所有書籍是否都處於可借出狀態。
    套書必須整套借出，若有任一冊不可借出則拒絕。

    Returns:
        list[SharedBook]: 套書中所有書籍

    Raises:
        ValidationError: 若套書中有書籍不可借出
    """
    books = list(book_set.books.select_related("official_book"))

    if not books:
        logger.warning("validate_book_set_completeness: empty set", extra={"book_set_id": book_set.id})
        raise ValidationError("此套書沒有包含任何書籍")

    unavailable = [b for b in books if b.status != SharedBook.Status.TRANSFERABLE]

    if unavailable:
        titles = ", ".join(str(b) for b in unavailable)
        logger.warning(
            "validate_book_set_completeness: books unavailable",
            extra={
                "book_set_id": book_set.id,
                "unavailable_count": len(unavailable),
            },
        )
        raise ValidationError(
            f"套書中以下書籍目前無法借出：{titles}。套書必須整套借出。"
        )

    logger.debug(
        "validate_book_set_completeness: ok",
        extra={"book_set_id": book_set.id, "book_count": len(books)},
    )
    return books


# ============================================================================
# 例外狀況處理
# ============================================================================


def declare_exception(shared_book):
    """
    將書籍狀態切換為 E（例外狀況）。

    使用 FSM 狀態轉換：TRANSFERABLE/OCCUPIED/RESTORABLE → EXCEPTION

    Raises:
        ValidationError: 如果狀態轉換不允許
    """
    if not can_proceed(shared_book.declare_exception):
        raise ValidationError(
            f"書籍目前狀態「{shared_book.get_status_display()}」無法宣告例外"
        )

    shared_book.declare_exception()
    shared_book.save()

    logger.info("exception declared", extra={"book_id": shared_book.id})


def resolve_exception(shared_book, resolution):
    """
    處置例外狀況：遺失、損毀、或尋獲歸還。

    Args:
        shared_book: 書籍實例
        resolution: 'lost' | 'destroyed' | 'found'

    Raises:
        ValidationError: 如果狀態轉換不允許或處置方式無效
    """
    resolution_methods = {
        "lost": shared_book.mark_as_lost,
        "destroyed": shared_book.mark_as_destroyed,
        "found": shared_book.mark_as_found,
    }

    if resolution not in resolution_methods:
        raise ValidationError(f"無效的處置方式：{resolution}")

    method = resolution_methods[resolution]
    if not can_proceed(method):
        raise ValidationError("只有「例外狀況」的書籍可以處置")

    method()
    shared_book.save()

    logger.info(
        "exception resolved",
        extra={"book_id": shared_book.id, "resolution": resolution},
    )
