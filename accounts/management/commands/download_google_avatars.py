"""
下載 Google OAuth 用戶頭像的管理指令。

使用方式：
    python manage.py download_google_avatars
    python manage.py download_google_avatars --force  # 強制重新下載
"""

import os
import uuid
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from allauth.socialaccount.models import SocialAccount

from accounts.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "從 Google OAuth 下載用戶頭像"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="強制重新下載（即使已有頭像）",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="只下載特定用戶（email）",
        )

    def handle(self, *args, **options):
        force = options["force"]
        user_email = options.get("user")

        # 取得所有 Google SocialAccount
        accounts = SocialAccount.objects.filter(provider="google").select_related(
            "user", "user__profile"
        )

        if user_email:
            accounts = accounts.filter(user__email=user_email)

        self.stdout.write(f"找到 {accounts.count()} 個 Google 帳號")

        success_count = 0
        skip_count = 0
        error_count = 0

        for account in accounts:
            user = account.user
            extra_data = account.extra_data or {}
            picture_url = extra_data.get("picture")

            if not picture_url:
                self.stdout.write(
                    self.style.WARNING(f"  {user.email}: 沒有 picture URL")
                )
                skip_count += 1
                continue

            # 取得或建立 profile
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(
                    user=user,
                    nickname=user.first_name or user.email.split("@")[0],
                )

            # 檢查是否需要下載
            if profile.avatar and not force:
                self.stdout.write(f"  {user.email}: 已有頭像，跳過")
                skip_count += 1
                continue

            # 下載頭像
            try:
                response = requests.get(picture_url, timeout=10)
                if response.status_code == 200:
                    parsed_url = urlparse(picture_url)
                    ext = (
                        os.path.splitext(parsed_url.path)[1]
                        if "os" in dir()
                        else ".jpg"
                    )
                    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                        ext = ".jpg"
                    filename = f"google_avatar_{uuid.uuid4().hex[:8]}{ext}"
                    profile.avatar.save(
                        filename, ContentFile(response.content), save=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {user.email}: 頭像已下載 → {profile.avatar.name}"
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  {user.email}: 下載失敗 (HTTP {response.status_code})"
                        )
                    )
                    error_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  {user.email}: 錯誤 - {e}"))
                error_count += 1

        self.stdout.write(
            f"\n完成：成功 {success_count}，跳過 {skip_count}，失敗 {error_count}"
        )
