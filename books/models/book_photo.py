from uuid import uuid4

from django.conf import settings
from django.db import models

from core.models import BaseModel


def book_photo_upload_path(instance, filename):
    """動態生成書況照片儲存路徑，以 UUID 命名避免衝突。"""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    return f"book_photos/{instance.shared_book_id}/{uuid4().hex}.{ext}"


class BookPhoto(BaseModel):
    """
    書籍現況照片。
    上架時或面交取書後由持有者拍攝上傳。
    """

    shared_book = models.ForeignKey(
        "books.SharedBook",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="分享書籍",
    )
    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
        verbose_name="交易",
        help_text="面交時拍攝的照片關聯至交易",
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_photos",
        verbose_name="上傳者",
    )
    photo = models.ImageField(
        upload_to=book_photo_upload_path,
        verbose_name="照片",
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="照片說明",
    )

    class Meta:
        db_table = "exbook_book_photo"
        verbose_name = "書況照片"
        verbose_name_plural = "書況照片"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.shared_book} 照片 ({self.created_at:%Y-%m-%d})"
