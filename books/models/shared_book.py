from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import UpdatableModel


class SharedBook(UpdatableModel):
    """
    用戶貢獻的特定書冊。
    同一本 OfficialBook 可有多個 SharedBook（不同用戶貢獻的不同冊）。
    """

    class Transferability(models.TextChoices):
        TRANSFER = 'TRANSFER', '開放傳遞'
        RETURN = 'RETURN', '閱畢即還'

    class Status(models.TextChoices):
        SUSPENDED = 'S', '暫不開放'
        TRANSFERABLE = 'T', '可移轉'
        RESTORABLE = 'R', '應返還'
        RESERVED = 'V', '已被預約'
        OCCUPIED = 'O', '借閱中'
        EXCEPTION = 'E', '例外狀況'
        LOST = 'L', '已遺失'
        DESTROYED = 'D', '已損毀'

    official_book = models.ForeignKey(
        'books.OfficialBook',
        on_delete=models.PROTECT,
        related_name='shared_books',
        verbose_name='官方書籍',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_books',
        verbose_name='貢獻者',
    )
    keeper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='kept_books',
        verbose_name='持有者',
    )
    book_set = models.ForeignKey(
        'books.BookSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books',
        verbose_name='所屬套書',
    )
    transferability = models.CharField(
        max_length=10,
        choices=Transferability.choices,
        default=Transferability.RETURN,
        verbose_name='流通性',
    )
    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.SUSPENDED,
        verbose_name='狀態',
    )
    condition_description = models.TextField(
        blank=True,
        verbose_name='書況描述',
    )
    loan_duration_days = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(90)],
        verbose_name='借閱天數',
        help_text='最少 15 天，最多 90 天',
    )
    extend_duration_days = models.PositiveIntegerField(
        default=14,
        validators=[MinValueValidator(7), MaxValueValidator(30)],
        verbose_name='可延長天數',
        help_text='最少 7 天，最多 30 天',
    )
    listed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='上架時間',
    )

    class Meta:
        db_table = 'exbook_shared_book'
        verbose_name = '分享書籍'
        verbose_name_plural = '分享書籍'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['keeper', 'status']),
        ]

    def __str__(self):
        return f'{self.official_book.title} (by {self.owner})'
