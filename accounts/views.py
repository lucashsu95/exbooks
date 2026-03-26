import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Appeal
from accounts.services import appeal_service, export_service
from books.models import SharedBook
from deals.models import Deal, Rating
from .forms import AppealForm, CompleteProfileForm, ProfileForm
from .models import UserProfile
from .services import user_stats_service


@login_required
def profile(request):
    """查看個人資料。"""
    profile_obj = None
    if hasattr(request.user, "profile"):
        profile_obj = request.user.profile

    # 統計資料
    activity_stats = user_stats_service.get_user_activity_stats(request.user)

    # 信用等級借閱限制
    from accounts.services.trust_service import get_borrowing_limits

    borrowing_limits = get_borrowing_limits(
        profile_obj.trust_level if profile_obj else 1
    )

    context = {
        "profile": profile_obj,
        "activity_stats": activity_stats,
        "borrowing_limits": borrowing_limits,
    }
    return render(request, "accounts/profile.html", context)


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


# ==================== 申訴相關 Views ====================


@login_required
def appeal_list(request):
    """申訴列表"""
    status_filter = request.GET.get("status")
    appeals = appeal_service.get_user_appeals(request.user, status=status_filter)
    return render(request, "accounts/appeal_list.html", {"appeals": appeals})


@login_required
def appeal_create(request):
    """建立申訴"""
    if request.method == "POST":
        form = AppealForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                appeal = appeal_service.create_appeal(
                    user=request.user,
                    appeal_type=form.cleaned_data["appeal_type"],
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    evidence=form.cleaned_data.get("evidence"),
                )
                messages.success(request, "申訴已送出")
                return redirect("accounts:appeal_detail", appeal_id=appeal.id)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = AppealForm()
    return render(request, "accounts/appeal_form.html", {"form": form})


@login_required
def appeal_detail(request, appeal_id):
    """申訴詳情"""
    appeal = get_object_or_404(Appeal, id=appeal_id)
    if appeal.user != request.user:
        return HttpResponseForbidden("您無權查看此申訴")
    return render(request, "accounts/appeal_detail.html", {"appeal": appeal})


@login_required
def appeal_cancel(request, appeal_id):
    """取消申訴"""
    if request.method == "POST":
        try:
            appeal_service.cancel_appeal(appeal_id, request.user)
            messages.success(request, "申訴已取消")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("accounts:appeal_list")


# ==================== 資料匯出 View ====================


@login_required
def export_user_data(request):
    """匯出用戶個人資料 JSON"""
    if request.method != "POST":
        messages.error(request, "請使用 POST 請求")
        return redirect("accounts:profile")

    try:
        # 執行匯出
        data = export_service.export_user_data(request.user)

        # 產生 JSON 檔案名稱
        filename = f"exbook_data_{request.user.id}_{data['exported_at'][:10]}.json"

        # 回傳 JSON 檔案
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        messages.success(request, "資料匯出成功")
        return response

    except export_service.ExportLimitExceededError as e:
        messages.error(request, str(e))
        return redirect("accounts:profile")


@login_required
def get_export_status(request):
    """取得今日剩餘匯出次數"""
    remaining = export_service.get_remaining_exports(request.user)
    return JsonResponse(
        {"remaining": remaining, "limit": export_service.EXPORT_LIMIT_PER_DAY}
    )
