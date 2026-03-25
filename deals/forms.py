"""
交易申請表單。
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field

from .models import Deal


class DealApplicationForm(forms.ModelForm):
    """交易申請表單。"""

    deal_type = forms.CharField(widget=forms.HiddenInput())
    shared_book = forms.UUIDField(widget=forms.HiddenInput())
    note = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
            }
        ),
        required=False,
        label="備註",
        help_text="可填寫面交時間地點或其他說明",
    )

    class Meta:
        model = Deal
        fields = ["deal_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("deal_type"),
            Field("shared_book"),
            Field("note"),
        )


class RatingForm(forms.Form):
    """評價表單。"""

    integrity_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer",
                "type": "range",
            }
        ),
        label="誠信評分",
    )
    punctuality_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer",
                "type": "range",
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
        self.helper.layout = Layout(
            Field("integrity_score", template="forms/widgets/rating_slider.html"),
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
        min_value=7,
        max_value=30,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "7-30 天",
                "min": 7,
                "max": 30,
            }
        ),
        label="延長天數",
        help_text="請輸入 7 至 30 天的延長天數",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
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
        self.helper.layout = Layout(
            Field("resolution"),
            Field("note"),
        )
