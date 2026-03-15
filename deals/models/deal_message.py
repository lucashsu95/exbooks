from django.conf import settings
from django.db import models

from core.models import BaseModel


class DealMessage(BaseModel):
    """
    交易雙方的協商留言。
    用於約定面交時間、地點等細節。
    """

    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="交易",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_deal_messages",
        verbose_name="發送者",
    )
    content = models.TextField(verbose_name="訊息內容")

    class Meta:
        db_table = "exbook_deal_message"
        verbose_name = "交易留言"
        verbose_name_plural = "交易留言"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} @ {self.deal} ({self.created_at:%Y-%m-%d %H:%M})"
