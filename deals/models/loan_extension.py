from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import UpdatableModel


class LoanExtension(UpdatableModel):
    """
    借閱延長申請與核准。
    同一筆交易可多次申請延長，每次需重新審核。

    命名依 Schema 規範：
    - requested_by: 申請延長者
    - approved_by: 審核者（nullable，核准/拒絕時寫入）
    - extra_days: 延長天數
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', '待審核'
        APPROVED = 'APPROVED', '已核准'
        REJECTED = 'REJECTED', '已拒絕'

    deal = models.ForeignKey(
        'deals.Deal',
        on_delete=models.CASCADE,
        related_name='extensions',
        verbose_name='交易',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='loan_extensions',
        verbose_name='申請者',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reviewed_extensions',
        verbose_name='審核者',
    )
    extra_days = models.PositiveIntegerField(
        validators=[MinValueValidator(7), MaxValueValidator(30)],
        verbose_name='延長天數',
        help_text='最少 7 天，最多 30 天',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='申請狀態',
    )

    class Meta:
        db_table = 'exbook_loan_extension'
        verbose_name = '延長申請'
        verbose_name_plural = '延長申請'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.deal} 延長 {self.extra_days} 天 ({self.get_status_display()})'
