"""
Web Push 訂閱模型。

儲存用戶的 Push 訂閱資訊，用於發送 Web Push 通知。
"""

from django.conf import settings
from django.db import models

from core.models import BaseModel


class PushSubscription(BaseModel):
    """
    用戶的 Web Push 訂閱資訊。

    儲存 PushManager.subscribe() 返回的 PushSubscription 物件資訊。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="用戶",
    )
    endpoint = models.URLField(
        max_length=500,
        verbose_name="訂閱端點",
        help_text="Push 服務的唯一端點 URL",
    )
    p256dh = models.CharField(
        max_length=100,
        verbose_name="p256dh 金鑰",
        help_text="用戶端的公開金鑰（ECDH P-256）",
    )
    auth = models.CharField(
        max_length=30,
        verbose_name="auth 金鑰",
        help_text="認證金鑰（16 bytes base64 編碼）",
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="User Agent",
        help_text="瀏覽器識別資訊",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="是否啟用",
        help_text="停用後將不會收到 Push 通知",
    )

    class Meta:
        db_table = "exbook_push_subscription"
        verbose_name = "Push 訂閱"
        verbose_name_plural = "Push 訂閱"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["endpoint"]),
        ]
        # 確保同一個端點不會重複訂閱
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint"],
                name="unique_endpoint",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.endpoint[:50]}..."

    @property
    def subscription_data(self):
        """
        返回符合 web-push 套件格式的訂閱資料。
        """
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth,
            },
        }


class WebPushConfig(BaseModel):
    """
    Web Push 設定（VAPID 金鑰）。

    Singleton 模式，系統只會有一組 VAPID 金鑰。
    """

    vapid_public_key = models.CharField(
        max_length=100,
        verbose_name="VAPID 公開金鑰",
        help_text="用於前端註冊 Push 訂閱",
    )
    vapid_private_key = models.TextField(
        verbose_name="VAPID 私有金鑰",
        help_text="用於後端發送 Push 通知（請勿洩漏）",
    )
    subject = models.URLField(
        max_length=200,
        blank=True,
        verbose_name="主體",
        help_text="聯絡信箱或網站 URL（mailto: 或 https://）",
    )

    class Meta:
        db_table = "exbook_web_push_config"
        verbose_name = "Web Push 設定"
        verbose_name_plural = "Web Push 設定"

    def __str__(self):
        return "Web Push 設定"

    @classmethod
    def get_config(cls):
        """
        取得 Web Push 設定（Singleton）。
        如果不存在，返回 None（需要先產生金鑰）。
        """
        try:
            return cls.objects.first()
        except cls.DoesNotExist:
            return None

    @property
    def vapid_details(self):
        """
        返回符合 pywebpush 套件格式的 VAPID 設定。
        """
        return {
            "subject": self.subject or "mailto:exbooks@example.com",
            "publicKey": self.vapid_public_key,
            "privateKey": self.vapid_private_key,
        }
