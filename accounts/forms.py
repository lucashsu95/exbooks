from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from allauth.account.forms import SignupForm as AllauthSignupForm
from allauth.account.forms import LoginForm as AllauthLoginForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, HTML

from .models import Appeal, UserProfile
from .validators import validate_age_18_or_older

User = get_user_model()


class AppealForm(forms.ModelForm):
    """申訴表單。"""

    class Meta:
        model = Appeal
        fields = ["appeal_type", "title", "description", "evidence"]
        widgets = {
            "appeal_type": forms.Select(
                attrs={
                    "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900"
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900",
                    "placeholder": "申訴標題",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900",
                    "rows": 5,
                    "placeholder": "請詳細描述您的申訴內容（至少 50 字元）",
                }
            ),
            "evidence": forms.FileInput(
                attrs={
                    "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900"
                }
            ),
        }
        error_messages = {
            "title": {"required": "請輸入申訴標題"},
            "description": {"required": "請輸入申訴描述"},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 設定日期上限，防止選擇未成年日期（HTML5 驗證輔助）
        if "birth_date" in self.fields:
            from datetime import date

            today = date.today()
            try:
                max_date = today.replace(year=today.year - 18)
            except ValueError:  # 處理閏年 2/29 的特殊情況
                max_date = today.replace(year=today.year - 18, month=2, day=28)
            self.fields["birth_date"].widget.attrs["max"] = max_date.isoformat()

        self.helper = FormHelper()

        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("appeal_type"),
            Field("title"),
            Field("description"),
            Field("evidence"),
        )

    def clean_description(self):
        """驗證描述至少 50 字元"""
        description = self.cleaned_data.get("description", "")
        if len(description) < 50:
            raise forms.ValidationError("申訴描述需至少 50 字元")
        return description


class CustomLoginForm(AllauthLoginForm):
    """
    自定義登入表單。
    利用 FormHelper 與 Layout 統一處理 non_field_errors 與欄位樣式。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("login", placeholder=_("Email")),
            Field("password", placeholder=_("密碼")),
            HTML(
                """
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center">
                        {% if form.remember.field %}
                            {{ form.remember }}
                            <label for="id_remember" class="ml-2 block text-sm text-slate-700">記住我</label>
                        {% endif %}
                    </div>
                    <div class="text-sm">
                        <a href="{% url 'account_reset_password' %}" class="font-medium text-primary hover:text-primary-hover">忘記密碼？</a>
                    </div>
                </div>
                """
            ),
            Submit(
                "submit",
                _("登入"),
                css_class="relative w-full py-4 bg-primary text-white border-none rounded-xl text-base font-semibold cursor-pointer transition-all duration-200 overflow-hidden hover:bg-primary-hover hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-4px_rgba(19,109,236,0.4)] active:translate-y-0",
            ),
        )


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
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        help_text=_("用於年齡驗證（需年滿 18 歲）"),
    )

    class Meta:
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("email", placeholder=_("Email")),
            Field("password1", placeholder=_("密碼")),
            Field("password2", placeholder=_("再次確認密碼")),
            Field("nickname", placeholder=_("你的暱稱")),
            Field("birth_date"),
            Submit(
                "submit",
                _("註冊"),
                css_class="relative w-full py-4 bg-primary text-white border-none rounded-xl text-base font-semibold cursor-pointer transition-all duration-200 overflow-hidden hover:bg-primary-hover hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-4px_rgba(19,109,236,0.4)] active:translate-y-0",
            ),
        )

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
        profile, created = UserProfile.objects.get_or_create(  # type: ignore[attr-defined]
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("email", readonly=True),
            Field("nickname", placeholder=_("你的暱稱")),
            Field("birth_date"),
            Field("default_location", placeholder=_("例如：台北市大安區")),
            Submit(
                "submit",
                _("完成註冊"),
                css_class="relative w-full py-4 bg-primary text-white border-none rounded-xl text-base font-semibold cursor-pointer transition-all duration-200 overflow-hidden hover:bg-primary-hover hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-4px_rgba(19,109,236,0.4)] active:translate-y-0",
            ),
        )

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
        profile, created = UserProfile.objects.get_or_create(  # type: ignore[attr-defined]
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("nickname", placeholder=_("你的暱稱")),
            Field("birth_date"),
            Submit(
                "submit",
                _("儲存並繼續"),
                css_class="relative w-full py-4 bg-primary text-white border-none rounded-xl text-base font-semibold cursor-pointer transition-all duration-200 overflow-hidden hover:bg-primary-hover hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-4px_rgba(19,109,236,0.4)] active:translate-y-0",
            ),
        )

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
            "available_schedule",
            "avatar",
        )
        widgets = {
            "nickname": forms.TextInput(attrs={"placeholder": "你的暱稱"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "default_location": forms.TextInput(
                attrs={"placeholder": "例：台北市大安區"}
            ),
            "available_schedule": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 設定日期上限，防止選擇未成年日期（HTML5 驗證輔助）
        if "birth_date" in self.fields:
            from datetime import date

            today = date.today()
            try:
                max_date = today.replace(year=today.year - 18)
            except ValueError:  # 處理閏年 2/29 的特殊情況
                max_date = today.replace(year=today.year - 18, month=2, day=28)
            self.fields["birth_date"].widget.attrs["max"] = max_date.isoformat()

        self.helper = FormHelper()

        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("nickname"),
            Field("birth_date"),
            Field("default_transferability"),
            Field("default_location"),
            Field("available_schedule", template="forms/widgets/schedule_picker.html"),
            Field("avatar", template="forms/widgets/image_preview.html"),
        )

    def clean_birth_date(self):
        """驗證年齡是否滿 18 歲"""
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            validate_age_18_or_older(birth_date)
        return birth_date

    def clean_available_schedule(self):
        """驗證可取書時間格式"""
        import json

        schedule = self.cleaned_data.get("available_schedule")
        if not schedule:
            return []

        if isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError:
                raise forms.ValidationError("可取書時間格式錯誤")

        # 驗證每個時段
        for slot in schedule:
            if not isinstance(slot, dict):
                raise forms.ValidationError("每個時段必須是物件")
            if "weekday" not in slot or "start" not in slot or "end" not in slot:
                raise forms.ValidationError("每個時段需包含星期、開始時間、結束時間")

        return schedule
