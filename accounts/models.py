from django.conf import settings
from django.db import models

from core.models import UpdatableModel


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
