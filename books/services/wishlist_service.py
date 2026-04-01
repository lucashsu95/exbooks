from django.core.exceptions import ValidationError
from django.db import IntegrityError

from books.models import WishListItem


def add_wish(user, official_book):
    """將書籍加入使用者的願望書車。"""
    try:
        return WishListItem.objects.create(
            user=user,
            official_book=official_book,
        )
    except IntegrityError:
        raise ValidationError("此書籍已在您的願望書車中")


def remove_wish(user, official_book):
    """將書籍從使用者的願望書車中移除。"""
    deleted, _ = WishListItem.objects.filter(
        user=user,
        official_book=official_book,
    ).delete()

    if not deleted:
        raise ValidationError("此書籍不在您的願望書車中")
