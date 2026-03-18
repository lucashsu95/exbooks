from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """User 建立時自動建立對應的 UserProfile。"""
    if created:
        # 自動設定 nickname：優先使用 first_name，否則使用 email 前綴
        default_nickname = (
            instance.first_name or instance.email.split("@")[0]
            if instance.email
            else ""
        )
        UserProfile.objects.create(user=instance, nickname=default_nickname)
