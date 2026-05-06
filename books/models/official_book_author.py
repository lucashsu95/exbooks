# pyright: reportArgumentType=false

from django.db import models

from core.models import BaseModel


class OfficialBookAuthor(BaseModel):
    """OfficialBook 與 Author 之多對多中介（含排序與角色）。"""

    class Role(models.TextChoices):
        AUTHOR = "author", "作者"
        TRANSLATOR = "translator", "譯者"

    official_book = models.ForeignKey(
        "books.OfficialBook",
        on_delete=models.CASCADE,
        related_name="author_links",
        verbose_name="官方書目",
    )
    author = models.ForeignKey(
        "books.Author",
        on_delete=models.CASCADE,
        related_name="book_links",
        verbose_name="作者",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.AUTHOR,
        verbose_name="角色",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="排序",
    )

    class Meta:
        db_table = "exbook_official_book_author"
        verbose_name = "書目作者關聯"
        verbose_name_plural = "書目作者關聯"
        constraints = [
            models.UniqueConstraint(
                fields=["official_book", "author"],
                name="uniq_official_book_author",
            ),
        ]
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.official_book_id} — {self.author_id}"
