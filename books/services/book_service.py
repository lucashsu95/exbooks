from django.core.exceptions import ValidationError
from django.utils import timezone

from books.models import SharedBook, WishListItem
from deals.services.notification_service import notify_book_available


def list_book(shared_book):
    """
    將書籍狀態從 S（暫不開放）切換為 T（可移轉），開放借閱。
    同時記錄上架時間。

    Rules:
    - 只有狀態為 S 的書籍可以開放
    """
    if shared_book.status != SharedBook.Status.SUSPENDED:
        raise ValidationError(
            f"只有「暫不開放」的書籍可以開放，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.status = SharedBook.Status.TRANSFERABLE
    shared_book.listed_at = timezone.now()
    shared_book.save(update_fields=["status", "listed_at", "updated_at"])

    # 通知願望書車中的使用者此書已可借閱
    wish_items = WishListItem.objects.filter(
        official_book=shared_book.official_book,
    ).select_related("user")
    for item in wish_items:
        notify_book_available(item.user, shared_book)


def suspend_book(shared_book):
    """
    將書籍狀態從 T（可移轉）切換為 S（暫不開放），暫停接受借閱。

    Rules:
    - 只有狀態為 T 的書籍可以暫停
    """
    if shared_book.status != SharedBook.Status.TRANSFERABLE:
        raise ValidationError(
            f"只有「可移轉」的書籍可以暫停，目前狀態為「{shared_book.get_status_display()}」"
        )

    shared_book.status = SharedBook.Status.SUSPENDED
    shared_book.save(update_fields=["status", "updated_at"])


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


def declare_exception(shared_book):
    """
    將書籍狀態切換為 E（例外狀況）。
    適用狀態：T、O、R

    Rules:
    - EX 交易接受後觸發
    """
    valid_statuses = (
        SharedBook.Status.TRANSFERABLE,
        SharedBook.Status.OCCUPIED,
        SharedBook.Status.RESTORABLE,
    )
    if shared_book.status not in valid_statuses:
        raise ValidationError(
            f"書籍目前狀態「{shared_book.get_status_display()}」無法宣告例外"
        )

    shared_book.status = SharedBook.Status.EXCEPTION
    shared_book.save(update_fields=["status", "updated_at"])


def resolve_exception(shared_book, resolution):
    """
    處置例外狀況：遺失、損毀、或尋獲歸還。

    Args:
        shared_book: 書籍實例
        resolution: 'lost' | 'destroyed' | 'found'
    """
    if shared_book.status != SharedBook.Status.EXCEPTION:
        raise ValidationError("只有「例外狀況」的書籍可以處置")

    resolution_map = {
        "lost": SharedBook.Status.LOST,
        "destroyed": SharedBook.Status.DESTROYED,
        "found": SharedBook.Status.SUSPENDED,
    }

    if resolution not in resolution_map:
        raise ValidationError(f"無效的處置方式：{resolution}")

    shared_book.status = resolution_map[resolution]
    shared_book.save(update_fields=["status", "updated_at"])
