from django.conf import settings
from django.db import models

from core.models import UpdatableModel


class BookSet(UpdatableModel):
    """
    套書綁定。同一 Owner 可將多本書綁定為套書，
    系統將限制以整套方式借出。
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='book_sets',
        verbose_name='擁有者',
    )
    name = models.CharField(max_length=100, verbose_name='套書名稱')
    description = models.TextField(blank=True, verbose_name='套書說明')

    class Meta:
        db_table = 'exbook_book_set'
        verbose_name = '套書'
        verbose_name_plural = '套書'

    def __str__(self):
        return self.name
