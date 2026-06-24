import logging

from django.conf import settings
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, FSMModelMixin, transition

from django.utils.translation import gettext_lazy as _

from core.models import UpdatableModel, BaseModel

logger = logging.getLogger(__name__)


class Violation(UpdatableModel):
    """
    違規處分模型。
    管理員可對違規用戶執行警告、暫時停權、永久停權等處分。
    """

    class Severity(models.TextChoices):
        MINOR = "minor", _("輕微")
        MODERATE = "moderate", _("中等")
        SEVERE = "severe", _("嚴重")

    class ActionType(models.TextChoices):
        WARNING = "warning", _("警告")
        TEMPORARY_SUSPENSION = "temporary_suspension", _("暫時停權")
        PERMANENT_SUSPENSION = "permanent_suspension", _("永久停權")

    class ViolationType(models.TextChoices):
        MISSED_MEETING = "missed_meeting", _("未依約定面交")
        LATE_RETURN = "late_return", _("延遲歸還")
        CONDITION_MISMATCH = "condition_mismatch", _("書況描述不符")
        UNJUSTIFIED_CANCELLATION = "unjustified_cancellation", _("無正當理由取消")
        FRAUD = "fraud", _("詐欺")
        HARASSMENT = "harassment", _("騷擾")
        MALICIOUS_DAMAGE = "malicious_damage", _("惡意破壞")
        IDENTITY_THEFT = "identity_theft", _("冒用身份")
        OTHER = "other", _("其他")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="violations",
        verbose_name=_("違規用戶"),
    )
    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        verbose_name=_("處分類型"),
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        verbose_name=_("違規等級"),
    )
    violation_type = models.CharField(
        max_length=30,
        choices=ViolationType.choices,
        verbose_name=_("違規行為"),
    )
    description = models.TextField(verbose_name=_("違規描述"))
    suspension_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("停權天數"),
        help_text=_("暫時停權時必填，7-30 天"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("是否生效中"),
        help_text=_("警告永遠生效；停權在期滿或解除後設為 False"),
    )
    related_appeal = models.ForeignKey(
        "Appeal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="violations",
        verbose_name=_("相關申訴"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="issued_violations",
        verbose_name=_("處分者"),
    )
    lifted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("解除時間"),
    )
    lifted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lifted_violations",
        verbose_name=_("解除者"),
    )

    class Meta:
        db_table = "exbook_violation"
        verbose_name = _("違規處分")
        verbose_name_plural = _("違規處分")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["action_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_action_type_display()}"

    def lift(self, lifted_by):
        """解除處分（提前解權）"""
        self.is_active = False
        self.lifted_at = timezone.now()
        self.lifted_by = lifted_by
        self.save(update_fields=["is_active", "lifted_at", "lifted_by", "updated_at"])


class Appeal(FSMModelMixin, UpdatableModel):
    """
    用戶申訴模型。
    用戶可對帳號停權、評價爭議、逾期爭議等提出申訴。

    狀態機（django-fsm）：
    SUBMITTED ──[start_review]──> UNDER_REVIEW ──[approve]──> APPROVED
        │                               │
        │                               └──[reject]──> REJECTED
        │
        └──[cancel]──> CLOSED

    APPROVED/REJECTED ──[close]──> CLOSED
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", _("已提交")
        UNDER_REVIEW = "under_review", _("審核中")
        APPROVED = "approved", _("已通過")
        REJECTED = "rejected", _("已駁回")
        CLOSED = "closed", _("已結案")

    class AppealType(models.TextChoices):
        ACCOUNT_SUSPENSION = "account_suspension", _("帳號停權申訴")
        RATING_DISPUTE = "rating_dispute", _("評價爭議")
        OVERDUE_DISPUTE = "overdue_dispute", _("逾期爭議")
        OTHER = "other", _("其他")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appeals",
        verbose_name=_("申訴人"),
    )
    appeal_type = models.CharField(
        max_length=30,
        choices=AppealType.choices,
        verbose_name=_("申訴類型"),
    )
    title = models.CharField(max_length=200, verbose_name=_("標題"))
    description = models.TextField(verbose_name=_("描述"))
    evidence = models.FileField(
        upload_to="appeals/%Y/%m/",
        blank=True,
        verbose_name=_("證據文件"),
    )
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
        verbose_name=_("狀態"),
        protected=True,
    )
    resolution_notes = models.TextField(blank=True, verbose_name=_("審核備註"))
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_appeals",
        verbose_name=_("審核者"),
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("審核時間"))

    class Meta:
        db_table = "exbook_appeal"
        verbose_name = _("申訴")
        verbose_name_plural = _("申訴")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    # ========================================================================
    # FSM 狀態轉換方法
    # ========================================================================

    @transition(
        field=status,
        source=Status.SUBMITTED,
        target=Status.UNDER_REVIEW,
    )
    def start_review(self):
        """
        開始審核申訴。

        狀態轉換：SUBMITTED → UNDER_REVIEW
        副作用（由 service 層處理）：
        - 發送通知
        """
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": Appeal.Status.UNDER_REVIEW,
        })

    @transition(
        field=status,
        source=Status.UNDER_REVIEW,
        target=Status.APPROVED,
    )
    def approve(self):
        """
        核准申訴。

        狀態轉換：UNDER_REVIEW → APPROVED
        副作用（由 service 層處理）：
        - 更新 resolution_notes, resolved_by, resolved_at
        - 發送審核結果通知
        """
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": Appeal.Status.APPROVED,
        })

    @transition(
        field=status,
        source=Status.UNDER_REVIEW,
        target=Status.REJECTED,
    )
    def reject(self):
        """
        駁回申訴。

        狀態轉換：UNDER_REVIEW → REJECTED
        副作用（由 service 層處理）：
        - 更新 resolution_notes, resolved_by, resolved_at
        - 發送審核結果通知
        """
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": Appeal.Status.REJECTED,
        })

    @transition(
        field=status,
        source=[Status.SUBMITTED, Status.APPROVED, Status.REJECTED],
        target=Status.CLOSED,
    )
    def close(self):
        """
        結案申訴。

        狀態轉換：SUBMITTED/APPROVED/REJECTED → CLOSED
        - SUBMITTED → CLOSED：用戶取消申訴
        - APPROVED/REJECTED → CLOSED：管理員結案

        副作用（由 service 層處理）：
        - 發送通知（如適用）
        """
        logger.info("FSM transition", extra={
            "model": self.__class__.__name__,
            "pk": str(self.pk),
            "from": self.status,
            "to": Appeal.Status.CLOSED,
        })


class UserProfile(UpdatableModel):
    """
    擴展 Django User 模型。
    儲存用戶暱稱、偏好設定、頭像等非認證資訊。
    """

    class Transferability(models.TextChoices):
        TRANSFER = "TRANSFER", _("開放傳遞")
        RETURN = "RETURN", _("閱畢即還")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("用戶"),
    )
    nickname = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("暱稱"),
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("出生日期"),
        help_text=_("用於年齡驗證（需年滿 18 歲）"),
    )
    default_transferability = models.CharField(
        max_length=10,
        choices=Transferability.choices,
        default=Transferability.RETURN,
        verbose_name=_("預設流通性"),
    )
    default_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("預設取書地點"),
    )
    available_schedule = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("可取書時間"),
        help_text=_('格式: [{"weekday": 1, "start": "09:00", "end": "12:00"}, ...]'),
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("頭像"),
    )
    trust_score = models.IntegerField(
        default=0,
        verbose_name=_("信用積分"),
        help_text=_("用戶的信用積分，根據交易、評價、逾期等計算"),
    )
    successful_returns = models.IntegerField(
        default=0,
        verbose_name=_("成功歸還次數"),
    )
    overdue_count = models.IntegerField(
        default=0,
        verbose_name=_("逾期次數"),
    )
    # 停權相關欄位
    is_suspended = models.BooleanField(
        default=False,
        verbose_name=_("是否停權中"),
        help_text=_("用戶目前是否處於停權狀態"),
    )
    suspension_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("停權結束時間"),
        help_text=_("暫時停權的結束時間，null 表示永久停權"),
    )
    suspension_reason = models.TextField(
        blank=True,
        verbose_name=_("停權原因"),
    )
    trust_level_protected_since = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("等級保護起始時間"),
        help_text=_("記錄用戶積分跌破門檻後，降級保護期開始計時的時間點"),
    )
    push_enabled = models.BooleanField(
        default=True,
        verbose_name=_("啟用推播通知"),
        help_text=_("關閉後將不會收到瀏覽器 Push 通知"),
    )
    email_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name=_("啟用 Email 通知"),
        help_text=_("關閉後將不會收到 Email 通知"),
    )

    class Meta:
        db_table = "exbook_user_profile"
        verbose_name = _("用戶資料")
        verbose_name_plural = _("用戶資料")

    def __str__(self):
        return self.nickname or self.user.get_full_name() or self.user.email

    @property
    def age(self):
        """計算用戶年齡"""
        if not self.birth_date:
            return None
        from datetime import date

        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    @property
    def is_adult(self):
        """檢查是否年滿 18 歲"""
        return self.age is not None and self.age >= 18

    @property
    def is_currently_suspended(self):
        """
        檢查用戶目前是否處於停權狀態。
        考慮停權結束時間，自動判斷是否仍有效。
        """
        if not self.is_suspended:
            return False
        # 永久停權（無結束時間）
        if self.suspension_end_date is None:
            return True
        # 暫時停權，檢查是否已期滿
        from django.utils import timezone

        return timezone.now() < self.suspension_end_date

    @property
    def trust_stars(self):
        """
        計算信用星等（1-5星）。
        公式：floor(sqrt(score))
        """
        import math

        if self.trust_score <= 0:
            return 1  # 最低1星
        stars = int(math.floor(math.sqrt(self.trust_score)))
        return min(max(stars, 1), 5)  # 限制在1-5星

    @property
    def trust_level(self) -> int:
        """根據 trust_score 計算信用等級（0-3）"""
        stars = self.trust_stars
        if stars <= 1:
            return 0
        elif stars == 2:
            return 1
        elif stars == 3:
            return 2
        else:  # 4-5星
            return 3


class TrustLevelConfig(models.Model):
    """
    信用等級配置模型。
    定義各等級的積分門檻、借閱限制與降級保護期。
    """

    level = models.PositiveSmallIntegerField(unique=True, verbose_name=_("等級"))
    group_name = models.CharField(max_length=50, verbose_name=_("對應群組名稱"))
    display_name = models.CharField(max_length=50, verbose_name=_("顯示名稱"))
    min_score = models.IntegerField(verbose_name=_("最低積分門檻"))
    max_books = models.PositiveSmallIntegerField(verbose_name=_("最大持書數量"))
    max_days = models.PositiveSmallIntegerField(verbose_name=_("最大借閱天數"))
    demotion_protection_weeks = models.PositiveSmallIntegerField(
        default=26,
        verbose_name=_("降級保護週數"),
        help_text=_("達到此等級後的保護期限，期間內若積分不足也不會降級"),
    )
    badge_icon = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("徽章圖標"),
        help_text=_("CSS class 或圖片路徑"),
    )

    class Meta:
        db_table = "exbook_trust_level_config"
        verbose_name = _("信用等級配置")
        verbose_name_plural = _("信用等級配置")
        ordering = ["level"]

    def __str__(self):
        return f"Lv{self.level}: {self.display_name}"


class TrustScoreLedger(BaseModel):
    """信用積分稽核條目（append-only）。"""

    class Source(models.TextChoices):
        RECALCULATE = "recalculate", _("批次／手動重算")
        RATING = "rating", _("收到評價")
        DEAL_COMPLETED = "deal_completed", _("交易結案")
        OVERDUE_ADJUST = "overdue_adjust", _("逾期處理")
        VIOLATION = "violation", _("違規處分")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trust_score_ledgers",
        verbose_name=_("用戶"),
    )
    trust_score = models.IntegerField(verbose_name=_("當下積分"))
    trust_level = models.PositiveSmallIntegerField(verbose_name=_("當下等級（0-3）"))
    formula_version = models.CharField(max_length=40, verbose_name=_("公式版本"))
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        verbose_name=_("來源"),
        db_index=True,
    )
    trace_id = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("追蹤ID"),
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("摘要指標"))

    class Meta:
        db_table = "exbook_trust_score_ledger"
        verbose_name = _("信用積分稽核")
        verbose_name_plural = _("信用積分稽核")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.source} @ {self.created_at}"
