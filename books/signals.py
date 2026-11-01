"""
SharedBook 自訂封面（cover_image）的檔案清理。

- SharedBook 刪除時（含 cascade）刪掉它的封面檔
- 封面被換掉時刪掉舊檔
刪檔一律經 transaction.on_commit：事務回滾時資料庫仍指向舊檔，不能先刪。
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from books.models import SharedBook

_LOADED_COVER_ATTR = "_loaded_cover_name"


def _delete_file_on_commit(storage, name: str) -> None:
    transaction.on_commit(lambda: storage.delete(name))


def _current_cover_name(instance: SharedBook) -> str | None:
    """目前 cover_image 的檔名；欄位被 defer 時回傳 None（不觸發額外查詢）。"""
    if "cover_image" not in instance.__dict__:
        return None
    value = instance.__dict__["cover_image"]
    return getattr(value, "name", value) or ""


@receiver(post_init, sender=SharedBook)
def remember_loaded_cover(sender, instance: SharedBook, **kwargs) -> None:
    setattr(instance, _LOADED_COVER_ATTR, _current_cover_name(instance))


@receiver(post_save, sender=SharedBook)
def delete_replaced_cover(sender, instance: SharedBook, **kwargs) -> None:
    old_name = getattr(instance, _LOADED_COVER_ATTR, None)
    new_name = _current_cover_name(instance)
    if old_name and new_name is not None and old_name != new_name:
        _delete_file_on_commit(instance.cover_image.storage, old_name)
    setattr(instance, _LOADED_COVER_ATTR, new_name)


@receiver(post_delete, sender=SharedBook)
def delete_cover_with_book(sender, instance: SharedBook, **kwargs) -> None:
    name = _current_cover_name(instance)
    if name:
        _delete_file_on_commit(instance.cover_image.storage, name)
