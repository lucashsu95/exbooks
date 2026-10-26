"""
交易申請表單。
"""

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field

from .models import Deal, LoanExtension


def _extra_days_bounds() -> tuple[int, int]:
    """延長天數上下限，以 LoanExtension.extra_days 欄位 validator 為唯一來源。"""
    min_days = max_days = None
    for validator in LoanExtension._meta.get_field("extra_days").validators:
        if isinstance(validator, MinValueValidator):
            min_days = validator.limit_value
        elif isinstance(validator, MaxValueValidator):
            max_days = validator.limit_value
    if min_days is None or max_days is None:
        raise RuntimeError("LoanExtension.extra_days 缺少 Min/MaxValueValidator")
    return min_days, max_days


_EXTRA_DAYS_MIN, _EXTRA_DAYS_MAX = _extra_days_bounds()


class DealApplicationForm(forms.ModelForm):
    """交易申請表單。"""

    deal_type = forms.CharField(widget=forms.HiddenInput())
    shared_book = forms.UUIDField(widget=forms.HiddenInput())
    meeting_location = forms.CharField(
        max_length=200,
        required=False,
        label="面交地點",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "請輸入面交地點",
            }
        ),
    )
    meeting_time = forms.DateTimeField(
        required=False,
        label="面交時間",
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
            }
        ),
    )
    note = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
            }
        ),
        required=False,
        label="備註",
        help_text="可填寫額外說明",
    )

    class Meta:
        model = Deal
        fields = ["deal_type", "meeting_location", "meeting_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("deal_type"),
            Field("shared_book"),
            Field("meeting_location"),
            Field("meeting_time"),
            Field("note"),
        )


class RatingForm(forms.Form):
    """評價表單。"""

    friendliness_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer",
                "type": "range",
                "min": 1,
                "max": 5,
                "aria-valuemin": 1,
                "aria-valuemax": 5,
                "aria-valuenow": 3,
                "role": "slider",
            }
        ),
        label="友善評分",
    )
    punctuality_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer",
                "type": "range",
                "min": 1,
                "max": 5,
                "aria-valuemin": 1,
                "aria-valuemax": 5,
                "aria-valuenow": 3,
                "role": "slider",
            }
        ),
        label="準時評分",
    )
    accuracy_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer",
                "type": "range",
                "min": 1,
                "max": 5,
                "aria-valuemin": 1,
                "aria-valuemax": 5,
                "aria-valuenow": 3,
                "role": "slider",
            }
        ),
        label="書況準確度評分",
    )
    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "分享您的交易體驗...",
            }
        ),
        required=False,
        label="評語",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("friendliness_score", template="forms/widgets/rating_slider.html"),
            Field("punctuality_score", template="forms/widgets/rating_slider.html"),
            Field("accuracy_score", template="forms/widgets/rating_slider.html"),
            Field("comment"),
        )


class DealMessageForm(forms.Form):
    """交易留言表單。"""

    content = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary",
                "placeholder": "輸入訊息...",
            }
        ),
        max_length=1000,
        label="訊息內容",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("content"),
        )


class ExtensionRequestForm(forms.Form):
    """延長借閱申請表單。"""

    extra_days = forms.IntegerField(
        min_value=_EXTRA_DAYS_MIN,
        max_value=_EXTRA_DAYS_MAX,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": f"{_EXTRA_DAYS_MIN}-{_EXTRA_DAYS_MAX} 天",
                "min": _EXTRA_DAYS_MIN,
                "max": _EXTRA_DAYS_MAX,
                "aria-valuemin": _EXTRA_DAYS_MIN,
                "aria-valuemax": _EXTRA_DAYS_MAX,
                "aria-label": f"延長天數，最少{_EXTRA_DAYS_MIN}天最多{_EXTRA_DAYS_MAX}天",
            }
        ),
        label="延長天數",
        help_text=f"請輸入 {_EXTRA_DAYS_MIN} 至 {_EXTRA_DAYS_MAX} 天的延長天數",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("extra_days"),
        )


# ============================================
# 例外處理相關表單
# ============================================


class ExceptionDealForm(forms.Form):
    """例外處理申請表單（EX 交易）。"""

    REASON_CHOICES = [
        ("lost", "書籍遺失"),
        ("damaged", "書籍損毀"),
        ("found", "書籍尋獲"),
    ]

    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.RadioSelect(
            attrs={
                "class": "h-4 w-4 border-slate-300 text-primary focus:ring-primary",
            }
        ),
        label="例外原因",
        help_text="請選擇例外處理的原因",
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "請詳細說明情況...",
            }
        ),
        required=False,
        label="詳細說明",
        help_text="請描述書籍狀況或遺失/損毀原因",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("reason"),
            Field("description"),
        )


class ExceptionResolveForm(forms.Form):
    """例外處理處置表單（Owner 審核）。"""

    RESOLUTION_CHOICES = [
        ("lost", "確認遺失"),
        ("destroyed", "確認損毀"),
        ("found", "確認尋獲歸還"),
    ]

    resolution = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        widget=forms.RadioSelect(
            attrs={
                "class": "h-4 w-4 border-slate-300 text-primary focus:ring-primary",
            }
        ),
        label="處置方式",
        help_text="請選擇處置結果",
    )
    note = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "備註說明（選填）",
            }
        ),
        required=False,
        label="備註",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("resolution"),
            Field("note"),
        )


class MultipleFileInput(forms.ClearableFileInput):
    """支援多檔案上傳的 Widget。"""

    allow_multiple_selected = True

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.setdefault("multiple", True)
        super().__init__(attrs=attrs)

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)

    def use_required_attribute(self, initial):
        return False


class DealPhotoUploadForm(forms.Form):
    """面交後書況照片上傳表單。"""

    photos = forms.FileField(
        widget=MultipleFileInput(
            attrs={
                "class": "block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20",
                "accept": "image/*",
                "capture": "environment",
            }
        ),
        required=True,
        label="書況照片",
        help_text="上傳 JPG 或 PNG 格式，每張最大 5MB",
    )
    caption = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "照片說明（選填）",
            }
        ),
        required=False,
        label="照片說明",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("photos"),
            Field("caption"),
        )
