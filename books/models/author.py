from django.db import models

from core.models import UpdatableModel


class Author(UpdatableModel):
    """作者／貢獻者（正規化）。display_name 唯一以避免重複建立。"""

    display_name = models.CharField(max_length=200, unique=True, verbose_name="顯示名稱")
    sort_key = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="排序鍵",
        help_text="空白時以顯示名稱小寫排序",
    )

    class Meta:
        db_table = "exbook_author"
        verbose_name = "作者"
        verbose_name_plural = "作者"
        ordering = ["sort_key", "display_name"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.sort_key:
            self.sort_key = self.display_name.lower()
        super().save(*args, **kwargs)
