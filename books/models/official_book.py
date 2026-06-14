from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import UpdatableModel


class OfficialBook(UpdatableModel):
    """官方書目資料，以 ISBN 為唯一鍵。多位用戶可分享同一本書的不同冊。"""

    class Category(models.TextChoices):
        FICTION = "小說", _("小說")
        TECH = "科技", _("科技")
        ART = "藝術", _("藝術")
        SCIENCE = "科學", _("科學")
        OTHER = "其他", _("未分類")

    isbn = models.CharField(
        max_length=13,
        unique=True,
        db_index=True,
        verbose_name=_("ISBN"),
        help_text=_("10 碼或 13 碼 ISBN"),
    )
    title = models.CharField(max_length=200, verbose_name=_("書名"))
    author = models.CharField(max_length=200, blank=True, verbose_name=_("作者"))
    publisher = models.CharField(max_length=100, blank=True, verbose_name=_("出版社"))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name=_("分類"),
    )
    cover_image = models.ImageField(
        upload_to="book_covers/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("封面圖片"),
    )
    description = models.TextField(blank=True, verbose_name=_("書籍簡介"))

    publisher_ref = models.ForeignKey(
        "books.Publisher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="official_books",
        verbose_name=_("出版社（正規化）"),
    )
    authors = models.ManyToManyField(
        "books.Author",
        through="OfficialBookAuthor",
        related_name="official_books",
        verbose_name=_("作者（正規化）"),
    )

    class Meta:
        db_table = "exbook_official_book"
        verbose_name = _("官方書目")
        verbose_name_plural = _("官方書目")
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.isbn})"
