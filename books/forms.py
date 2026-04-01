from django import forms
from django.db.models import Q
from django.forms.widgets import Input
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div

from .models import SharedBook, OfficialBook, BookSet


class BookSearchForm(forms.Form):
    """書籍搜尋與篩選表單"""

    q = forms.CharField(
        required=False,
        label="搜尋",
        widget=forms.TextInput(
            attrs={
                "placeholder": "搜尋 ISBN、書名、作者、出版社",
                "class": "form-input",
            }
        ),
    )
    status = forms.ChoiceField(
        required=False,
        label="狀態",
        choices=[("", "全部狀態")] + list(SharedBook.Status.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    transferability = forms.ChoiceField(
        required=False,
        label="流通性",
        choices=[("", "全部流通性")] + list(SharedBook.Transferability.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    category = forms.ChoiceField(
        required=False,
        label="分類",
        choices=[("", "全部分類")] + list(OfficialBook.Category.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("q"),
            Field("status"),
            Field("transferability"),
            Field("category"),
        )


class MultipleFileInput(Input):
    """支援多檔案上傳的自訂 widget"""

    input_type = "file"
    template_name = "django/forms/widgets/file.html"

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs["multiple"] = True
        super().__init__(attrs)


class BookAddForm(forms.ModelForm):
    isbn = forms.CharField(
        max_length=13,
        label="ISBN",
        widget=forms.TextInput(
            attrs={
                "hx-get": "/books/api/isbn-lookup/",
                "hx-trigger": "keyup changed delay:500ms",
                "hx-target": "#isbn-result",
            }
        ),
    )
    title = forms.CharField(max_length=200, label="書名")
    author = forms.CharField(max_length=200, required=False, label="作者")
    publisher = forms.CharField(max_length=100, required=False, label="出版社")
    category = forms.ChoiceField(
        choices=OfficialBook.Category.choices,
        label="分類",
        initial=OfficialBook.Category.OTHER,
    )
    cover_image = forms.ImageField(
        label="封面圖片",
        required=False,
        help_text="若 ISBN 查詢無封面，可手動上傳（JPG / PNG）",
    )
    photos = forms.FileField(
        widget=MultipleFileInput(),
        label="書況照片",
        required=False,
    )
    transferability = forms.ChoiceField(
        choices=SharedBook.Transferability.choices,
        label="流通性",
        widget=forms.Select(
            attrs={
                "class": "appearance-none bg-white border border-slate-200 text-slate-700 text-sm rounded-full px-4 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary/50 cursor-pointer"
            }
        ),
    )

    class Meta:
        model = SharedBook
        fields = ["transferability", "condition_description", "loan_duration_days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("isbn"),
            Field("title"),
            Field("author"),
            Field("publisher"),
            Field("category"),
            Div(Field("cover_image"), css_id="cover-image-wrapper"),
            Field("transferability"),
            Field("condition_description"),
            Field("loan_duration_days"),
            Field("photos"),
        )


class BookEditForm(forms.ModelForm):
    title = forms.CharField(max_length=200, label="書名")
    author = forms.CharField(max_length=200, required=False, label="作者")
    publisher = forms.CharField(max_length=100, required=False, label="出版社")
    category = forms.ChoiceField(
        choices=OfficialBook.Category.choices,
        label="分類",
        initial=OfficialBook.Category.OTHER,
    )
    photos = forms.FileField(
        widget=MultipleFileInput(),
        label="新增書況照片",
        required=False,
    )
    transferability = forms.ChoiceField(
        choices=SharedBook.Transferability.choices,
        label="流通性",
        widget=forms.Select(
            attrs={
                "class": "appearance-none bg-white border border-slate-200 text-slate-700 text-sm rounded-full px-4 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary/50 cursor-pointer"
            }
        ),
    )

    class Meta:
        model = SharedBook
        fields = ["transferability", "condition_description", "loan_duration_days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("title"),
            Field("author"),
            Field("publisher"),
            Field("category"),
            Field("transferability"),
            Field("condition_description"),
            Field("loan_duration_days"),
            Field("photos"),
        )


# ============================================
# 套書相關表單
# ============================================


class BookSetCreateForm(forms.ModelForm):
    """建立套書表單"""

    class Meta:
        model = BookSet
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                    "placeholder": "例如：哈利波特全套",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors",
                    "rows": 3,
                    "placeholder": "套書說明（選填）",
                }
            ),
        }
        labels = {
            "name": "套書名稱",
            "description": "套書說明",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("name"),
            Field("description"),
        )


class BookSetManageForm(forms.Form):
    """管理套書書籍表單"""

    book_ids = forms.ModelMultipleChoiceField(
        queryset=SharedBook.objects.none(),  # type: ignore[attr-defined]
        required=False,
        label="選擇書籍",
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "rounded border-slate-300 text-primary focus:ring-primary",
            }
        ),
    )

    def __init__(self, *args, user=None, book_set=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.book_set = book_set
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("book_ids"),
        )

        # 只顯示用戶擁有的書籍
        if user:
            queryset = SharedBook.objects.filter(owner=user).select_related(  # type: ignore[attr-defined]
                "official_book"
            )
            # 如果是編輯現有套書，排除已屬於其他套書的書籍
            if book_set:
                queryset = queryset.filter(Q(book_set=None) | Q(book_set=book_set))
            else:
                queryset = queryset.filter(book_set=None)
            self.fields["book_ids"].queryset = queryset

    def clean_book_ids(self):
        book_ids = self.cleaned_data.get("book_ids", [])
        for book in book_ids:
            if book.owner != self.user:
                raise forms.ValidationError("只能加入自己擁有的書籍")
            if self.book_set and book.book_set and book.book_set != self.book_set:
                raise forms.ValidationError(f"{book} 已屬於其他套書")
        return book_ids
