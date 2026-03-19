from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from books.models import SharedBook
from deals.models import Deal, Rating
from .forms import CompleteProfileForm, ProfileForm
from .models import UserProfile
from .services import user_stats_service


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
    tab = request.GET.get("tab", "books")

    # 嘗試取得 profile，若無則使用預設值
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    # 上架書籍
    books_contributed = (
        SharedBook.objects.filter(owner=user)
        .select_related("official_book", "keeper__profile")
        .order_by("-updated_at")[:20]
    )

    # 借閱紀錄
    deals_history = (
        Deal.objects.filter(
            Q(applicant=user) | Q(responder=user),
            status__in=[Deal.Status.DONE, Deal.Status.CANCELLED],
        )
        .select_related("shared_book__official_book", "applicant", "responder")
        .order_by("-updated_at")[:20]
    )

    # 評價歷史
    ratings_received = (
        Rating.objects.filter(ratee=user)
        .select_related("rater__profile", "deal__shared_book__official_book")
        .order_by("-created_at")[:10]
    )

    # 統計資料
    activity_stats = user_stats_service.get_user_activity_stats(user)
    rating_summary = user_stats_service.get_user_rating_summary(user)

    context = {
        "viewed_user": user,
        "profile": profile,
        "current_tab": tab,
        "books_contributed": books_contributed,
        "deals_history": deals_history,
        "ratings_received": ratings_received,
        "activity_stats": activity_stats,
        "rating_summary": rating_summary,
    }
    return render(request, "accounts/public_profile.html", context)


@login_required
def user_ratings(request, user_id):
    """用戶評價詳情頁。"""
    user = get_object_or_404(User, pk=user_id)

    # 評價摘要
    rating_summary = user_stats_service.get_user_rating_summary(user)

    # 評價歷史（分頁）
    page_number = request.GET.get("page", 1)
    ratings_page = user_stats_service.get_user_rating_history(user, page=page_number)

    # 嘗試取得 profile
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    context = {
        "viewed_user": user,
        "profile": profile,
        "rating_summary": rating_summary,
        "page_obj": ratings_page,
    }
    return render(request, "accounts/user_ratings.html", context)


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
