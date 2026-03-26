"""
django-allauth 自定義 Adapters。

包含：
- ExbookAccountAdapter: 處理 email 登入、現有用戶補填 birth_date
- ExbookSocialAccountAdapter: 處理 Google OAuth 整合
"""

import logging
import uuid
import os
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse

import requests

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class ExbookAccountAdapter(DefaultAccountAdapter):
    """
    自定義 Account Adapter。

    處理：
    1. Email 登入配置
    2. 現有用戶補填 birth_date 流程
    3. 註冊後的導向
    """

    def get_login_redirect_url(self, request):
        """登入後的導向 URL"""
        user = request.user

        # 檢查現有用戶是否需要補填 birth_date
        if user.is_authenticated:
            try:
                profile = user.profile
                # 如果沒有 birth_date，導向補填頁面
                if not profile.birth_date:
                    logger.info(f"User {user.email} needs to fill birth_date")
                    return reverse("accounts:complete_profile")
            except UserProfile.DoesNotExist:
                # 如果沒有 profile，導向補填頁面
                return reverse("accounts:complete_profile")

        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        """註冊後的導向 URL"""
        # 註冊後導向 email 驗證提示頁
        return reverse("account_email_verification_sent")

    def is_open_for_signup(self, request):
        """是否開放註冊"""
        return True

    def save_user(self, request, user, form, commit=True):
        """
        儲存用戶時，同步處理 UserProfile。

        確保 UserProfile 在 User 儲存後立即建立。
        """
        user = super().save_user(request, user, form, commit=commit)

        if commit:
            # 確保 UserProfile 存在（signal 應該已經處理，但這裡做雙重保險）
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "nickname": user.email.split("@")[0],
                },
            )

        return user


class ExbookSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    自定義 Social Account Adapter。

    處理：
    1. Google OAuth 登入
    2. 首次 OAuth 登入時建立 UserProfile
    3. 年齡驗證（BR-11）
    """

    def populate_user(self, request, sociallogin, data):
        """
        從社交帳號資料填充用戶資訊。

        重要：生成唯一的 username，因為 Django User 模型需要此欄位。
        """
        user = super().populate_user(request, sociallogin, data)

        # 從 Google 資料取得額外資訊
        extra_data = sociallogin.account.extra_data if sociallogin.account else {}

        # 設定用戶姓名
        user.first_name = extra_data.get("given_name", "")
        user.last_name = extra_data.get("family_name", "")

        # 生成唯一的 username（使用 email 前綴 + UUID）
        email = extra_data.get("email", "") or data.get("email", "")
        if email:
            # 使用 email 前綴作為基礎，加上短 UUID 確保唯一
            base_username = email.split("@")[0][:30]  # username 最大長度 150
            unique_suffix = str(uuid.uuid4())[:8]
            user.username = f"{base_username}_{unique_suffix}"
        else:
            # 沒有 email 的情況（應該不會發生）
            user.username = f"user_{uuid.uuid4().hex[:12]}"

        # email 由 allauth 自動處理
        logger.debug(
            f"Populating user from Google: {extra_data.get('email')}, username: {user.username}"
        )

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        儲存新用戶並建立 UserProfile。
        """
        user = super().save_user(request, sociallogin, form)

        # 建立 UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "nickname": user.first_name or user.email.split("@")[0],
            },
        )

        # 下載 Google 頭像
        if sociallogin.account:
            extra_data = sociallogin.account.extra_data
            picture_url = extra_data.get("picture")
            if picture_url and not profile.avatar:
                try:
                    response = requests.get(picture_url, timeout=10)
                    if response.status_code == 200:
                        # 從 URL 取得副檔名
                        parsed_url = urlparse(picture_url)
                        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"
                        filename = f"google_avatar_{uuid.uuid4().hex[:8]}{ext}"

                        profile.avatar.save(
                            filename, ContentFile(response.content), save=True
                        )
                        logger.info(f"Downloaded Google avatar for {user.email}")
                except Exception as e:
                    logger.warning(f"Failed to download Google avatar: {e}")

        logger.info(f"{'Created' if created else 'Found'} UserProfile for {user.email}")

        return user

    def pre_social_login(self, request, sociallogin):
        """
        社交登入前的處理。

        檢查：
        1. 是否已有相同 email 的本地帳號（自動連結）
        2. 用戶是否需要補填 birth_date
        3. 下載 Google 頭像（如果沒有的話）
        """
        email = sociallogin.user.email

        if email:
            try:
                # 嘗試找到現有用戶
                existing_user = User.objects.get(email=email)

                # 自動連結現有帳號
                if sociallogin.is_existing:
                    logger.debug(f"Social account already linked to {email}")
                else:
                    sociallogin.connect(request, existing_user)
                    logger.info(f"Linked social account to existing user: {email}")

                # 為既有用戶下載 Google 頭像（如果沒有的話）
                if sociallogin.account:
                    extra_data = sociallogin.account.extra_data
                    picture_url = extra_data.get("picture")
                    if picture_url:
                        try:
                            profile = existing_user.profile
                            if not profile.avatar:
                                response = requests.get(picture_url, timeout=10)
                                if response.status_code == 200:
                                    parsed_url = urlparse(picture_url)
                                    ext = os.path.splitext(parsed_url.path)[1] or ".jpg"
                                    filename = (
                                        f"google_avatar_{uuid.uuid4().hex[:8]}{ext}"
                                    )
                                    profile.avatar.save(
                                        filename,
                                        ContentFile(response.content),
                                        save=True,
                                    )
                                    logger.info(
                                        f"Downloaded Google avatar for existing user: {email}"
                                    )
                        except UserProfile.DoesNotExist:
                            logger.debug(
                                f"No profile for {email}, will be created in save_user"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to download avatar for existing user: {e}"
                            )

            except User.DoesNotExist:
                logger.debug(f"New user from social login: {email}")

    def is_open_for_signup(self, request, sociallogin):
        """
        檢查是否開放社交帳號註冊。

        年齡驗證將在後續流程中處理（因為 Google 不提供出生日期）。
        """
        return True

    def get_connect_redirect_url(self, request, socialaccount):
        """
        社交帳號連結後的導向。

        檢查是否需要補填 birth_date。
        """
        user = request.user

        try:
            profile = user.profile
            # 如果沒有 birth_date，導向補填頁面
            if not profile.birth_date:
                return reverse("accounts:complete_profile")
        except (AttributeError, UserProfile.DoesNotExist):
            return reverse("accounts:complete_profile")

        return reverse("books:list")

    def authentication_error(
        self, request, provider_id, error, exception, extra_context
    ):
        """
        處理認證錯誤。
        """
        logger.error(
            f"Social auth error: provider={provider_id}, error={error}, "
            f"exception={exception}, context={extra_context}"
        )
