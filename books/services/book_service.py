"""
書籍狀態轉換服務。

此模組封裝 SharedBook 的狀態轉換邏輯，使用 django-fSM。
Service 層負責：
- 權限檢查
- 跨 Model 事務協調
- 觸發 FSM 狀態轉換

副作用（通知）由 Signal 處理。
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from django_fsm import can_proceed

from books.models import SharedBook, WishListItem
from deals.services.notification_service import notify_book_available


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
        raise ValidationError("此套書沒有包含任何書籍")

    unavailable = [b for b in books if b.status != SharedBook.Status.TRANSFERABLE]

    if unavailable:
        titles = ", ".join(str(b) for b in unavailable)
        raise ValidationError(
            f"套書中以下書籍目前無法借出：{titles}。套書必須整套借出。"
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
