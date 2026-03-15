from django.db import models

from core.models import UpdatableModel


class OfficialBook(UpdatableModel):
    """
    官方書籍資料，以 ISBN 為唯一鍵。
    多位用戶可分享同一本書的不同冊。
    """

    isbn = models.CharField(
        max_length=13,
        unique=True,
        db_index=True,
        verbose_name="ISBN",
        help_text="10 碼或 13 碼 ISBN",
    )
    title = models.CharField(max_length=200, verbose_name="書名")
    author = models.CharField(max_length=200, blank=True, verbose_name="作者")
    publisher = models.CharField(max_length=100, blank=True, verbose_name="出版社")
    cover_image = models.ImageField(
        upload_to="book_covers/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="封面圖片",
    )
    description = models.TextField(blank=True, verbose_name="書籍簡介")

    class Meta:
        db_table = "exbook_official_book"
        verbose_name = "官方書籍"
        verbose_name_plural = "官方書籍"
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.isbn})"
