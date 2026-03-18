from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from allauth.account.forms import SignupForm as AllauthSignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm

from .models import UserProfile
from .validators import is_adult, validate_age_18_or_older

User = get_user_model()


class CustomSignupForm(AllauthSignupForm):
    """
    自定義註冊表單 — Email + 密碼 + 暱稱 + 出生日期。

    繼承 allauth 的 SignupForm，新增：
    - nickname（暱稱）
    - birth_date（出生日期，用於 BR-11 年齡驗證）
    """

    nickname = forms.CharField(
        max_length=50,
        label=_("暱稱"),
        help_text=_("顯示在平台上的名稱"),
    )
    birth_date = forms.DateField(
        label=_("出生日期"),
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("用於年齡驗證（需年滿 18 歲）"),
    )

    class Meta:
        model = User

    def clean_birth_date(self):
        """驗證年齡是否滿 18 歲"""
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            validate_age_18_or_older(birth_date)
        return birth_date

    def save(self, request):
        """
        儲存用戶並建立 UserProfile。
        """
        # 呼叫父類的 save 方法建立 User
        user = super().save(request)

        # 更新 UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "nickname": self.cleaned_data.get("nickname", user.email.split("@")[0]),
                "birth_date": self.cleaned_data.get("birth_date"),
            },
        )

        # 如果 profile 已存在（由 signal 建立），更新欄位
        if not created:
            profile.nickname = self.cleaned_data.get("nickname", profile.nickname)
            profile.birth_date = self.cleaned_data.get("birth_date")
            profile.save(update_fields=["nickname", "birth_date", "updated_at"])

        return user


class CustomSocialSignupForm(SocialSignupForm):
    """
    自定義社交登入註冊表單 — OAuth 後收集額外資訊。

    用於：
    - 收集出生日期（BR-11 年齡驗證）
    - 收集暱稱
    - 設定預設取書地點
    """

    nickname = forms.CharField(
        max_length=50,
        label=_("暱稱"),
        help_text=_("顯示在平台上的名稱"),
    )
    birth_date = forms.DateField(
        label=_("出生日期"),
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("用於年齡驗證（需年滿 18 歲）"),
    )
    default_location = forms.CharField(
        max_length=200,
        label=_("預設取書地點"),
        required=False,
        help_text=_("例如：台北市大安區"),
    )

    class Meta:
        model = User

    def clean_birth_date(self):
        """驗證年齡是否滿 18 歲"""
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            validate_age_18_or_older(birth_date)
        return birth_date

    def save(self, request):
        """
        儲存用戶並更新 UserProfile。
        """
        # 呼叫父類的 save 方法
        user = super().save(request)

        # 更新 UserProfile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "nickname": self.cleaned_data.get("nickname", user.email.split("@")[0]),
                "birth_date": self.cleaned_data.get("birth_date"),
                "default_location": self.cleaned_data.get("default_location", ""),
            },
        )

        if not created:
            profile.nickname = self.cleaned_data.get("nickname", profile.nickname)
            profile.birth_date = self.cleaned_data.get("birth_date")
            profile.default_location = self.cleaned_data.get(
                "default_location", profile.default_location
            )
            profile.save(
                update_fields=[
                    "nickname",
                    "birth_date",
                    "default_location",
                    "updated_at",
                ]
            )

        return user


class CompleteProfileForm(forms.ModelForm):
    """
    補填個人資料表單 — 用於現有用戶補填 birth_date。
    """

    birth_date = forms.DateField(
        label=_("出生日期"),
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("用於年齡驗證（需年滿 18 歲）"),
    )
    nickname = forms.CharField(
        max_length=50,
        label=_("暱稱"),
        required=False,
        help_text=_("顯示在平台上的名稱"),
    )

    class Meta:
        model = UserProfile
        fields = ["nickname", "birth_date"]

    def clean_birth_date(self):
        """驗證年齡是否滿 18 歲"""
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            validate_age_18_or_older(birth_date)
        return birth_date


class ProfileForm(forms.ModelForm):
    """個人資料編輯表單。"""

    class Meta:
        model = UserProfile
        fields = (
            "nickname",
            "birth_date",
            "default_transferability",
            "default_location",
            "avatar",
        )
        widgets = {
            "nickname": forms.TextInput(attrs={"placeholder": "你的暱稱"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "default_location": forms.TextInput(
                attrs={"placeholder": "例：台北市大安區"}
            ),
        }

    def clean_birth_date(self):
        """驗證年齡是否滿 18 歲"""
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            validate_age_18_or_older(birth_date)
        return birth_date


# 保留舊的 RegisterForm 以向後相容（將被逐步淘汰）
class RegisterForm(forms.ModelForm):
    """舊版註冊表單 — 僅用於向後相容。"""

    nickname = forms.CharField(
        max_length=50,
        label="暱稱",
        help_text="顯示在平台上的名稱",
    )

    class Meta:
        model = User
        fields = ("username", "email")
        labels = {
            "username": "帳號",
            "email": "電子信箱",
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = UserProfile.objects.get(user=user)  # signal 已建立
            profile.nickname = self.cleaned_data["nickname"]
            profile.save(update_fields=["nickname"])
        return user
