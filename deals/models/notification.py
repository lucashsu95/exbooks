from django.conf import settings
from django.db import models

from core.models import BaseModel


class Notification(BaseModel):
    """
    系統通知（到期提醒、交易通知等）。
    """

    class NotificationType(models.TextChoices):
        DEAL_REQUESTED = "DEAL_REQUESTED", "收到交易申請"
        DEAL_RESPONDED = "DEAL_RESPONDED", "交易已被回應"
        DEAL_CANCELLED = "DEAL_CANCELLED", "交易被取消"
        DEAL_MEETED = "DEAL_MEETED", "面交完成，請評價"
        BOOK_DUE_SOON = "BOOK_DUE_SOON", "書籍即將到期"
        BOOK_OVERDUE = "BOOK_OVERDUE", "書籍已逾期"
        BOOK_AVAILABLE = "BOOK_AVAILABLE", "願望書籍已可借閱"
        EXTEND_REQUESTED = "EXTEND_REQUESTED", "收到延長申請"
        EXTEND_APPROVED = "EXTEND_APPROVED", "延長申請已核准"
        EXTEND_REJECTED = "EXTEND_REJECTED", "延長申請已拒絕"
        APPEAL_SUBMITTED = "APPEAL_SUBMITTED", "申訴已送出"
        APPEAL_RESOLVED = "APPEAL_RESOLVED", "申訴審核完成"
        RATING_CREATED = "RATING_CREATED", "收到新的評價"
        VIOLATION_CREATED = "VIOLATION_CREATED", "收到違規處分"
        APPEAL_STATUS_UPDATED = "APPEAL_STATUS_UPDATED", "申訴狀態更新"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="接收者",
    )
    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="相關交易",
    )
    shared_book = models.ForeignKey(
        "books.SharedBook",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="相關書籍",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        verbose_name="通知類型",
    )
    title = models.CharField(
        max_length=200,
        verbose_name="通知標題",
    )
    message = models.TextField(blank=True, verbose_name="通知訊息")
    is_read = models.BooleanField(default=False, verbose_name="是否已讀")

    class Meta:
        db_table = "exbook_notification"
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(
                fields=["recipient", "notification_type"], name="idx_recipient_type"
            ),
        ]

    def __str__(self):
        return f"{self.recipient} - {self.get_notification_type_display()}"
