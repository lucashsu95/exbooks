from django.conf import settings
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, FSMModelMixin, transition

from core.models import UpdatableModel


class Violation(UpdatableModel):
    """
    違規處分模型。
    管理員可對違規用戶執行警告、暫時停權、永久停權等處分。
    """

    class Severity(models.TextChoices):
        MINOR = "minor", "輕微"
        MODERATE = "moderate", "中等"
        SEVERE = "severe", "嚴重"

    class ActionType(models.TextChoices):
        WARNING = "warning", "警告"
        TEMPORARY_SUSPENSION = "temporary_suspension", "暫時停權"
        PERMANENT_SUSPENSION = "permanent_suspension", "永久停權"

    class ViolationType(models.TextChoices):
        MISSED_MEETING = "missed_meeting", "未依約定面交"
        LATE_RETURN = "late_return", "延遲歸還"
        CONDITION_MISMATCH = "condition_mismatch", "書況描述不符"
        UNJUSTIFIED_CANCELLATION = "unjustified_cancellation", "無正當理由取消"
        FRAUD = "fraud", "詐欺"
        HARASSMENT = "harassment", "騷擾"
        MALICIOUS_DAMAGE = "malicious_damage", "惡意破壞"
        IDENTITY_THEFT = "identity_theft", "冒用身份"
        OTHER = "other", "其他"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="violations",
        verbose_name="違規用戶",
    )
    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        verbose_name="處分類型",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        verbose_name="違規等級",
    )
    violation_type = models.CharField(
        max_length=30,
        choices=ViolationType.choices,
        verbose_name="違規行為",
    )
    description = models.TextField(verbose_name="違規描述")
    suspension_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="停權天數",
        help_text="暫時停權時必填，7-30 天",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否生效中",
        help_text="警告永遠生效；停權在期滿或解除後設為 False",
    )
    related_appeal = models.ForeignKey(
        "Appeal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="violations",
        verbose_name="相關申訴",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="issued_violations",
        verbose_name="處分者",
    )
    lifted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="解除時間",
    )
    lifted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lifted_violations",
        verbose_name="解除者",
    )

    class Meta:
        db_table = "exbook_violation"
        verbose_name = "違規處分"
        verbose_name_plural = "違規處分"
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
        SUBMITTED = "submitted", "已提交"
        UNDER_REVIEW = "under_review", "審核中"
        APPROVED = "approved", "已通過"
        REJECTED = "rejected", "已駁回"
        CLOSED = "closed", "已結案"

    class AppealType(models.TextChoices):
        ACCOUNT_SUSPENSION = "account_suspension", "帳號停權申訴"
        RATING_DISPUTE = "rating_dispute", "評價爭議"
        OVERDUE_DISPUTE = "overdue_dispute", "逾期爭議"
        OTHER = "other", "其他"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appeals",
        verbose_name="申訴人",
    )
    appeal_type = models.CharField(
        max_length=30,
        choices=AppealType.choices,
        verbose_name="申訴類型",
    )
    title = models.CharField(max_length=200, verbose_name="標題")
    description = models.TextField(verbose_name="描述")
    evidence = models.FileField(
        upload_to="appeals/%Y/%m/",
        blank=True,
        verbose_name="證據文件",
    )
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
        verbose_name="狀態",
        protected=True,
    )
    resolution_notes = models.TextField(blank=True, verbose_name="審核備註")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_appeals",
        verbose_name="審核者",
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="審核時間")

    class Meta:
        db_table = "exbook_appeal"
        verbose_name = "申訴"
        verbose_name_plural = "申訴"
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
        pass

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
        pass

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
        pass

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
        pass


class UserProfile(UpdatableModel):
    """
    擴展 Django User 模型。
    儲存用戶暱稱、偏好設定、頭像等非認證資訊。
    """

    class Transferability(models.TextChoices):
        TRANSFER = "TRANSFER", "開放傳遞"
        RETURN = "RETURN", "閱畢即還"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="用戶",
    )
    nickname = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="暱稱",
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="出生日期",
        help_text="用於年齡驗證（需年滿 18 歲）",
    )
    default_transferability = models.CharField(
        max_length=10,
        choices=Transferability.choices,
        default=Transferability.RETURN,
        verbose_name="預設流通性",
    )
    default_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="預設取書地點",
    )
    available_schedule = models.JSONField(
        default=list,
        blank=True,
        verbose_name="可取書時間",
        help_text='格式: [{"weekday": 1, "start": "09:00", "end": "12:00"}, ...]',
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="頭像",
    )
    trust_score = models.IntegerField(
        default=0,
        verbose_name="信用積分",
        help_text="用戶的信用積分，根據交易、評價、逾期等計算",
    )
    successful_returns = models.IntegerField(
        default=0,
        verbose_name="成功歸還次數",
    )
    overdue_count = models.IntegerField(
        default=0,
        verbose_name="逾期次數",
    )
    # 停權相關欄位
    is_suspended = models.BooleanField(
        default=False,
        verbose_name="是否停權中",
        help_text="用戶目前是否處於停權狀態",
    )
    suspension_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="停權結束時間",
        help_text="暫時停權的結束時間，null 表示永久停權",
    )
    suspension_reason = models.TextField(
        blank=True,
        verbose_name="停權原因",
    )

    class Meta:
        db_table = "exbook_user_profile"
        verbose_name = "用戶資料"
        verbose_name_plural = "用戶資料"

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
