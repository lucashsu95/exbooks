from django import forms
from django.forms.widgets import Input
from .models import SharedBook, OfficialBook


class MultipleFileInput(Input):
    """支援多檔案上傳的自訂 widget"""

    input_type = "file"
    template_name = "django/forms/widgets/file.html"

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs["multiple"] = True
        super().__init__(attrs)


class BookAddForm(forms.ModelForm):
    # For simplicity, combine OfficialBook and SharedBook fields
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
    photos = forms.FileField(
        widget=MultipleFileInput(),
        label="書況照片",
        required=False,
    )

    class Meta:
        model = SharedBook
        fields = ["transferability", "condition_description", "loan_duration_days"]
