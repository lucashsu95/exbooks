from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, SmallIntegerField, Value, When
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, FSMModelMixin, transition

from core.models import UpdatableModel


class LoanExtension(FSMModelMixin, UpdatableModel):
    """
    借閱延長申請與核准。
    同一筆交易同時只允許一筆待審核的延長申請，核准或拒絕後才能再申請。

    命名依 Schema 規範：
    - requested_by: 申請延長者
    - approved_by: 審核者（nullable，核准/拒絕時寫入）
    - extra_days: 延長天數
    """

    MIN_EXTRA_DAYS = 7
    MAX_EXTRA_DAYS = 30

    class Status(models.TextChoices):
        PENDING = "PENDING", _("待審核")
        APPROVED = "APPROVED", _("已核准")
        REJECTED = "REJECTED", _("已拒絕")

    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.CASCADE,
        related_name="extensions",
        verbose_name=_("交易"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="loan_extensions",
        verbose_name=_("申請者"),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_extensions",
        verbose_name=_("審核者"),
    )
    extra_days = models.PositiveIntegerField(
        validators=[
            MinValueValidator(MIN_EXTRA_DAYS),
            MaxValueValidator(MAX_EXTRA_DAYS),
        ],
        verbose_name=_("延長天數"),
        help_text=_(
            "最少 %(min_days)s 天，最多 %(max_days)s 天"
        ) % {"min_days": MIN_EXTRA_DAYS, "max_days": MAX_EXTRA_DAYS},
    )
    status = FSMField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("申請狀態"),
        protected=True,
    )
    # DB 層防線（#21）：PENDING 時為 1、否則 NULL 的 generated column，
    # 搭配 (deal, is_pending) unique constraint——MySQL/SQLite 的 unique
    # 皆允許多個 NULL，故結構上保證同一交易同時至多一筆 PENDING。
    # 不依賴「request_extension 是 PENDING 唯一寫入者」的隱性 invariant。
    is_pending = models.GeneratedField(
        expression=Case(
            When(status=Status.PENDING, then=Value(1)),
            default=Value(None),
            output_field=SmallIntegerField(),
        ),
        output_field=SmallIntegerField(null=True),
        db_persist=True,
    )

    class Meta:
        db_table = "exbook_loan_extension"
        verbose_name = _("延長申請")
        verbose_name_plural = _("延長申請")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["deal", "is_pending"],
                name="uniq_loan_extension_one_pending_per_deal",
            ),
        ]

    def __str__(self):
        return f"{self.deal} 延長 {self.extra_days} 天 ({self.get_status_display()})"

    # ========================================================================
    # FSM 狀態轉換方法
    # ========================================================================

    @transition(
        field=status,
        source=Status.PENDING,
        target=Status.APPROVED,
    )
    def approve(self):
        """
        核准延長申請。

        狀態轉換：PENDING → APPROVED
        副作用（由 signal 處理）：
        - 更新 Deal.due_date
        - 發送通知
        """
        pass

    @transition(
        field=status,
        source=Status.PENDING,
        target=Status.REJECTED,
    )
    def reject(self):
        """
        拒絕延長申請。

        狀態轉換：PENDING → REJECTED
        副作用（由 signal 處理）：
        - 發送通知
        """
        pass
