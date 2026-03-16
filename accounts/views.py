from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, RegisterForm


def register(request):
    """註冊新用戶。"""
    if request.user.is_authenticated:
        return redirect("books:list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "歡迎加入 Exbooks！")
            return redirect("books:list")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    """查看個人資料。"""
    profile_obj = None
    if hasattr(request.user, "profile"):
        profile_obj = request.user.profile

    return render(request, "accounts/profile.html", {"profile": profile_obj})


@login_required
def profile_edit(request):
    """編輯個人資料。"""
    from .models import UserProfile

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "個人資料已更新。")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def public_profile(request, user_id):
    """查看他人公開資料。"""
    from .models import UserProfile

    user = get_object_or_404(User, pk=user_id)

    # 嘗試取得 profile，若無則使用預設值
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    context = {
        "viewed_user": user,
        "profile": profile,
    }
    return render(request, "accounts/public_profile.html", context)
