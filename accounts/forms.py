from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile

User = get_user_model()


class RegisterForm(UserCreationForm):
    """註冊表單 — 帳號 + 密碼 + 暱稱。"""

    nickname = forms.CharField(
        max_length=50,
        label='暱稱',
        help_text='顯示在平台上的名稱',
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        labels = {
            'username': '帳號',
            'email': '電子信箱',
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = UserProfile.objects.get(user=user)  # signal 已建立
            profile.nickname = self.cleaned_data['nickname']
            profile.save(update_fields=['nickname'])
        return user


class ProfileForm(forms.ModelForm):
    """個人資料編輯表單。"""

    class Meta:
        model = UserProfile
        fields = (
            'nickname',
            'default_transferability',
            'default_location',
            'avatar',
        )
        widgets = {
            'nickname': forms.TextInput(attrs={'placeholder': '你的暱稱'}),
            'default_location': forms.TextInput(attrs={'placeholder': '例：台北市大安區'}),
        }
