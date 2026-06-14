import logging

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from books.models import WishListItem

logger = logging.getLogger(__name__)


def add_wish(user, official_book):
    """將書籍加入使用者的願望書車。"""
    try:
        item = WishListItem.objects.create(
            user=user,
            official_book=official_book,
        )
        logger.info(
            "wish added",
            extra={
                "user_id": user.id,
                "official_book_id": official_book.id,
            },
        )
        return item
    except IntegrityError:
        logger.warning(
            "wish already exists",
            extra={
                "user_id": user.id,
                "official_book_id": official_book.id,
            },
        )
        raise ValidationError("此書籍已在您的願望書車中")


def remove_wish(user, official_book):
    """將書籍從使用者的願望書車中移除。"""
    deleted, _ = WishListItem.objects.filter(
        user=user,
        official_book=official_book,
    ).delete()

    if not deleted:
        logger.warning(
            "wish not found for removal",
            extra={
                "user_id": user.id,
                "official_book_id": official_book.id,
            },
        )
        raise ValidationError("此書籍不在您的願望書車中")

    logger.info(
        "wish removed",
        extra={
            "user_id": user.id,
            "official_book_id": official_book.id,
        },
    )
