"""
套書管理 Service 層。

處理套書的建立、編輯、刪除及書籍加入/移除等業務邏輯。
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from books.models import BookSet, SharedBook
from deals.models import Deal


# 進行中交易的狀態列表
ACTIVE_DEAL_STATUSES = [
    Deal.Status.REQUESTED,
    Deal.Status.RESPONDED,
    Deal.Status.MEETED,
]


@transaction.atomic
def create_book_set(owner, name, description="", book_ids=None):
    """
    建立套書並加入書籍。

    Args:
        owner: 套書擁有者（User）
        name: 套書名稱
        description: 套書說明（可選）
        book_ids: 要加入的書籍 ID 列表（可選）

    Returns:
        BookSet: 建立的套書

    Raises:
        ValidationError: 如果書籍不屬於該用戶
    """
    book_set = BookSet.objects.create(
        owner=owner,
        name=name,
        description=description,
    )

    if book_ids:
        books = SharedBook.objects.filter(id__in=book_ids)
        for book in books:
            add_book_to_set(book_set, book)

    return book_set


@transaction.atomic
def add_book_to_set(book_set, shared_book):
    """
    將書籍加入套書。

    Args:
        book_set: 套書物件
        shared_book: 要加入的書籍

    Raises:
        ValidationError: 如果書籍不屬於套書擁有者
    """
    if shared_book.owner != book_set.owner:
        raise ValidationError("只能加入自己擁有的書籍到套書")

    if shared_book.book_set and shared_book.book_set != book_set:
        raise ValidationError("此書籍已屬於其他套書，請先從原套書移除")

    shared_book.book_set = book_set
    shared_book.save(update_fields=["book_set", "updated_at"])


@transaction.atomic
def remove_book_from_set(book_set, shared_book):
    """
    從套書移除書籍。

    Args:
        book_set: 套書物件
        shared_book: 要移除的書籍

    Raises:
        ValidationError: 如果書籍有進行中的交易
    """
    if shared_book.book_set != book_set:
        raise ValidationError("此書籍不屬於此套書")

    # 檢查是否有進行中的交易
    has_active_deal = Deal.objects.filter(
        shared_book=shared_book,
        status__in=ACTIVE_DEAL_STATUSES,
    ).exists()

    if has_active_deal:
        raise ValidationError("書籍有進行中的交易，無法從套書移除")

    shared_book.book_set = None
    shared_book.save(update_fields=["book_set", "updated_at"])


@transaction.atomic
def delete_book_set(book_set):
    """
    刪除套書。

    Args:
        book_set: 要刪除的套書

    Raises:
        ValidationError: 如果套書中有書籍存在進行中的交易
    """
    # 檢查套書中是否有書籍存在進行中的交易
    has_active_deal = Deal.objects.filter(
        shared_book__book_set=book_set,
        status__in=ACTIVE_DEAL_STATUSES,
    ).exists()

    if has_active_deal:
        raise ValidationError("套書中有書籍存在進行中的交易，無法刪除")

    # 清除所有書籍的套書關聯
    SharedBook.objects.filter(book_set=book_set).update(book_set=None)

    book_set.delete()


def get_user_book_sets(user):
    """
    取得用戶擁有的所有套書。

    Args:
        user: 用戶物件

    Returns:
        QuerySet: 用戶的套書列表
    """
    return BookSet.objects.filter(owner=user).prefetch_related("books__official_book")


def get_book_set_detail(book_set_id, user=None):
    """
    取得套書詳情。

    Args:
        book_set_id: 套書 ID
        user: 可選，用於驗證權限

    Returns:
        BookSet: 套書物件（含書籍列表）

    Raises:
        ValidationError: 如果套書不存在或無權限
    """
    try:
        book_set = BookSet.objects.prefetch_related(
            "books__official_book",
            "books__keeper",
        ).get(pk=book_set_id)
    except BookSet.DoesNotExist:
        raise ValidationError("套書不存在")

    if user and book_set.owner != user:
        raise ValidationError("您無權查看此套書")

    return book_set
