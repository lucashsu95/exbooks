import uuid

from django.db import models


class BaseModel(models.Model):
    """所有實體的抽象基類，提供 UUID 主鍵與建立時間。"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        abstract = True


class UpdatableModel(BaseModel):
    """需要追蹤更新時間的實體基類。"""

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        abstract = True
