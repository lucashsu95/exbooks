from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


def book_photo_upload_path(instance, filename):
    """動態生成書況照片儲存路徑，以 UUID 命名避免衝突。"""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    return f"book_photos/{instance.shared_book_id}/{uuid4().hex}.{ext}"


class BookPhoto(BaseModel):
    """
    書籍現況照片。
    上架時或面交取書後由持有者拍攝上傳。
    """

    shared_book = models.ForeignKey(
        "books.SharedBook",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("分享書籍"),
    )
    deal = models.ForeignKey(
        "deals.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
        verbose_name=_("交易"),
        help_text=_("面交時拍攝的照片關聯至交易"),
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_photos",
        verbose_name=_("上傳者"),
    )
    photo = models.ImageField(
        upload_to=book_photo_upload_path,
        verbose_name=_("照片"),
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("照片說明"),
    )

    class Meta:
        db_table = "exbook_book_photo"
        verbose_name = _("書況照片")
        verbose_name_plural = _("書況照片")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.shared_book} 照片 ({self.created_at:%Y-%m-%d})"

    @property
    def serve_url(self):
        """
        根據照片是否與交易關聯，回傳對應的存取 URL。
        - 有關聯交易 (deal_id is not None): 回傳受保護的 serve URL。
        - 無關聯交易: 回傳原媒體檔案 URL。
        """
        if self.deal_id:
            return reverse("serve_protected_photo", kwargs={"pk": self.pk})
        return self.photo.url
