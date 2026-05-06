# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from django.conf import settings
from django.db import models

from books.models import SharedBook
from core.models import BaseModel


class ExchangeEvent(BaseModel):
    """
    書籍交換／交易稽核事件（append-only）。
    用於時間軸與稽核；請勿對記錄執行 update/delete。
    """

    class EventType(models.TextChoices):
        DEAL_REQUESTED = "deal_requested", "交易申請"
        DEAL_ACCEPTED = "deal_accepted", "交易接受"
        DEAL_DECLINED = "deal_declined", "交易婉拒"
        DEAL_CANCELLED_REQUEST = "deal_cancelled_request", "申請者取消"
        DEAL_SUPERSEDED = "deal_superseded", "競價替代取消（BR-15）"
        DEAL_MEETING_COMPLETED = "deal_meeting_completed", "面交完成"
        KEEPER_CHANGED = "keeper_changed", "持有者變更"
        BOOK_OVERDUE_PROCESSED = "book_overdue_processed", "到期排程處理"
        DEAL_CONFIRM_RETURN = "deal_confirm_return", "確認歸還／上架"
        DEAL_COMPLETED = "deal_completed", "交易結案（DONE）"
        EXTENSION_REQUESTED = "extension_requested", "延長申請"
        EXTENSION_APPROVED = "extension_approved", "延長核准"
        EXTENSION_REJECTED = "extension_rejected", "延長拒絕"
        EXTENSION_CANCELLED = "extension_cancelled", "延長取消"
        RATING_SUBMITTED = "rating_submitted", "評價送出"

    shared_book = models.ForeignKey(
        SharedBook,
        on_delete=models.CASCADE,
        related_name="exchange_events",
        verbose_name="分享書籍",
    )
    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exchange_events",
        verbose_name="交易",
    )
    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
        verbose_name="事件類型",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exchange_events",
        verbose_name="操作者",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="附加資料",
    )

    class Meta:
        db_table = "exbook_exchange_event"
        verbose_name = "交換事件"
        verbose_name_plural = "交換事件"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shared_book", "-created_at"]),
            models.Index(fields=["deal", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} @ {self.shared_book_id}"
