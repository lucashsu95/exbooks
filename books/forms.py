from django import forms
from django.urls import reverse
from django.db.models import Q
from django.forms.widgets import Input
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, HTML

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
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
            }
        ),
    )
    transferability = forms.ChoiceField(
        required=False,
        label="流通性",
        choices=[("", "全部流通性")] + list(SharedBook.Transferability.choices),
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
            }
        ),
    )
    category = forms.ChoiceField(
        required=False,
        label="分類",
        choices=[("", "全部分類")] + list(OfficialBook.Category.choices),
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
            }
        ),
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
                "placeholder": "請輸入 10 或 13 位 ISBN",
                "class": "form-input",
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
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
            }
        ),
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
        help_text="請至少上傳一張書況照片",
    )
    transferability = forms.ChoiceField(
        choices=SharedBook.Transferability.choices,
        label="流通性",
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
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
            Div(
                Field("isbn", wrapper_class="flex-1 mb-0"),
                HTML(
                    f'<button type="button" '
                    f'hx-get="{reverse("books:isbn_lookup")}" '
                    "hx-include=\"[name='isbn']\" "
                    'hx-target="#isbn-result" '
                    'hx-swap="outerHTML" '
                    'hx-indicator=".htmx-indicator" '
                    'class="h-11 px-4 bg-slate-100 text-slate-700 font-medium rounded-xl border border-slate-200 hover:bg-slate-200 transition-colors">'
                    "查詢"
                    "</button>"
                ),
                css_class="flex gap-2 items-end mb-4",
            ),
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

    def clean(self):
        """驗證表單資料，確保至少上傳一張書況照片"""
        cleaned_data = super().clean()

        # 檢查是否有上傳照片
        photos = self.files.getlist("photos")

        if not photos:
            raise forms.ValidationError("請至少上傳一張書況照片")

        return cleaned_data


class BookEditForm(forms.ModelForm):
    title = forms.CharField(max_length=200, label="書名")
    author = forms.CharField(max_length=200, required=False, label="作者")
    publisher = forms.CharField(max_length=100, required=False, label="出版社")
    category = forms.ChoiceField(
        choices=OfficialBook.Category.choices,
        label="分類",
        initial=OfficialBook.Category.OTHER,
        widget=forms.Select(
            attrs={
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
            }
        ),
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
                "class": "appearance-none w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-primary focus:border-primary transition-colors cursor-pointer"
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


class BookSelectWidget(forms.CheckboxSelectMultiple):
    """自訂書籍選擇 widget，支援縮圖與卡片佈局"""

    template_name = "forms/widgets/book_selection.html"

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        if hasattr(label, "instance"):
            # ModelChoiceIteratorValue 包含 instance
            option["book"] = label.instance
        return option


class BookSetCreateForm(forms.ModelForm):
    """建立/編輯套書表單"""

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
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

        # 加入多選書籍欄位
        self.fields["books"] = forms.ModelMultipleChoiceField(
            queryset=SharedBook.objects.none(),
            required=False,
            label="選擇書籍加入此套書",
            widget=BookSelectWidget(),
            help_text="只有尚未加入任何套書的書籍會顯示在此",
        )

        if user:
            # 取得用戶擁有的書籍且尚未加入其他套書
            # 如果是編輯現有套書，要包含已經在此套書中的書
            queryset = SharedBook.objects.filter(owner=user).select_related(
                "official_book"
            )
            if self.instance.pk:
                queryset = queryset.filter(Q(book_set=None) | Q(book_set=self.instance))
                self.initial["books"] = self.instance.books.all()
            else:
                queryset = queryset.filter(book_set=None)

            self.fields["books"].queryset = queryset

        self.helper.layout = Layout(
            Field("name"),
            Field("description"),
            Field("books"),
        )


class BookSetManageForm(forms.Form):
    """管理套書書籍表單"""

    book_ids = forms.ModelMultipleChoiceField(
        queryset=SharedBook.objects.none(),  # type: ignore[attr-defined]
        required=False,
        label="選擇書籍",
        widget=BookSelectWidget(),
        help_text="只有尚未加入任何套書的書籍會顯示在此",
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
