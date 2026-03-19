"""
交易申請表單。
"""

from django import forms

from .models import Deal


class DealApplicationForm(forms.ModelForm):
    """交易申請表單。"""

    deal_type = forms.CharField(widget=forms.HiddenInput())
    shared_book = forms.UUIDField(widget=forms.HiddenInput())
    note = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
            }
        ),
        required=False,
        label="備註",
        help_text="可填寫面交時間地點或其他說明",
    )

    class Meta:
        model = Deal
        fields = ["deal_type"]


class RatingForm(forms.Form):
    """評價表單。"""

    integrity_score = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer",
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
                "class": "w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer",
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
                "class": "w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer",
                "type": "range",
            }
        ),
        label="書況準確度評分",
    )
    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "分享您的交易體驗...",
            }
        ),
        required=False,
        label="評語",
    )


class DealMessageForm(forms.Form):
    """交易留言表單。"""

    content = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary focus:border-primary",
                "placeholder": "輸入訊息...",
            }
        ),
        max_length=1000,
        label="訊息內容",
    )


class ExtensionRequestForm(forms.Form):
    """延長借閱申請表單。"""

    extra_days = forms.IntegerField(
        min_value=7,
        max_value=30,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                "placeholder": "7-30 天",
                "min": 7,
                "max": 30,
            }
        ),
        label="延長天數",
        help_text="請輸入 7 至 30 天的延長天數",
    )
