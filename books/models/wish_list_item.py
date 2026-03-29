from django.conf import settings
from django.db import models

from core.models import BaseModel


class WishListItem(BaseModel):
    """
    讀者的書籍願望清單。
    當願望清單中的書籍有可借閱的 SharedBook 時，系統主動通知。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wish_list",
        verbose_name="用戶",
    )
    official_book = models.ForeignKey(
        "books.OfficialBook",
        on_delete=models.CASCADE,
        related_name="wished_by",
        verbose_name="官方書籍",
    )

    class Meta:
        db_table = "exbook_wish_list_item"
        verbose_name = "願望書車"
        verbose_name_plural = "願望書車"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "official_book"],
                name="unique_user_official_book",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_user_created"),
            models.Index(fields=["official_book"], name="idx_official_book"),
        ]

    def __str__(self):
        return f"{self.user} → {self.official_book}"
