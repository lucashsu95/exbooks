from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CompleteProfileForm, ProfileForm
from .models import UserProfile


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


@login_required
def complete_profile(request):
    """
    補填個人資料頁面。

    用於：
    1. 現有用戶補填 birth_date（BR-11 年齡驗證）
    2. OAuth 登入後收集額外資訊
    """
    # 檢查是否已有完整的 profile
    try:
        profile = request.user.profile
        if profile.birth_date:
            messages.info(request, "您的個人資料已完整。")
            return redirect("books:list")
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        form = CompleteProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "個人資料已更新，歡迎使用 Exbooks！")
            return redirect("books:list")
    else:
        form = CompleteProfileForm(instance=profile)

    return render(request, "accounts/complete_profile.html", {"form": form})
