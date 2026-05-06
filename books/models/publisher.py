from django.db import models

from core.models import UpdatableModel


class Publisher(UpdatableModel):
    """出版社（正規化）；既有字串欄位 OfficialBook.publisher 仍保留供過渡。"""

    name = models.CharField(max_length=200, unique=True, verbose_name="名稱")

    class Meta:
        db_table = "exbook_publisher"
        verbose_name = "出版社"
        verbose_name_plural = "出版社"
        ordering = ["name"]

    def __str__(self):
        return self.name
