"""
交易相關 Views。
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET

from books.models import SharedBook
from .forms import DealApplicationForm, RatingForm, DealMessageForm
from .models import Deal, DealMessage, PushSubscription, WebPushConfig
from .services import deal_service, rating_service

logger = logging.getLogger(__name__)


@login_required
def deal_create(request, book_id, deal_type):
    """建立交易申請。"""
    book = get_object_or_404(SharedBook, pk=book_id)

    if request.method == "POST":
        form = DealApplicationForm(request.POST)
        if form.is_valid():
            try:
                deal = deal_service.create_deal(
                    deal_type=deal_type,
                    shared_book=book,
                    applicant=request.user,
                    note=form.cleaned_data.get("note", ""),
                )
                messages.success(request, "交易申請已送出！")
                return redirect("deals:detail", deal.id)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = DealApplicationForm(
            initial={
                "deal_type": deal_type,
                "shared_book": book_id,
            }
        )

    return render(
        request,
        "deals/deal_create.html",
        {
            "form": form,
            "book": book,
            "deal_type": deal_type,
        },
    )


@login_required
def deal_detail(request, pk):
    """交易詳情頁面。"""
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book__official_book",
            "shared_book__keeper__profile",
            "applicant__profile",
            "responder__profile",
        ),
        pk=pk,
    )
    messages_list = DealMessage.objects.filter(deal=deal).select_related("sender")[:50]

    return render(
        request,
        "deals/deal_detail.html",
        {
            "deal": deal,
            "messages": messages_list,
            "is_applicant": request.user == deal.applicant,
            "is_responder": request.user == deal.responder,
        },
    )


@login_required
def deal_list(request):
    """交易管理頁面。"""
    user = request.user
    tab = request.GET.get("tab", "pending")

    # 待回應（我是回應者）
    pending_responder = Deal.objects.filter(
        responder=user,
        status=Deal.Status.REQUESTED,
    ).select_related("shared_book__official_book", "applicant")

    # 待對方回應（我是申請者）
    pending_applicant = Deal.objects.filter(
        applicant=user,
        status=Deal.Status.REQUESTED,
    ).select_related("shared_book__official_book", "responder")

    # 待面交
    pending_meeting = Deal.objects.filter(
        applicant=user,
        status=Deal.Status.RESPONDED,
    ).select_related("shared_book__official_book", "responder") | Deal.objects.filter(
        responder=user,
        status=Deal.Status.RESPONDED,
    ).select_related("shared_book__official_book", "applicant")

    # 待評價
    pending_rating = Deal.objects.filter(
        applicant=user,
        status=Deal.Status.MEETED,
    ).select_related("shared_book__official_book", "responder") | Deal.objects.filter(
        responder=user,
        status=Deal.Status.MEETED,
    ).select_related("shared_book__official_book", "applicant")

    # 歷史紀錄
    history = Deal.objects.filter(
        applicant=user,
        status__in=[Deal.Status.DONE, Deal.Status.CANCELLED],
    ).select_related("shared_book__official_book", "responder") | Deal.objects.filter(
        responder=user,
        status__in=[Deal.Status.DONE, Deal.Status.CANCELLED],
    ).select_related("shared_book__official_book", "applicant")

    return render(
        request,
        "deals/deal_list.html",
        {
            "current_tab": tab,
            "pending_responder": pending_responder,
            "pending_applicant": pending_applicant,
            "pending_meeting": pending_meeting,
            "pending_rating": pending_rating,
            "history": history,
        },
    )


@login_required
def deal_accept(request, pk):
    """接受交易申請。"""
    deal = get_object_or_404(Deal, pk=pk, responder=request.user)
    try:
        deal_service.accept_deal(deal)
        messages.success(request, "交易已接受！")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("deals:detail", pk)


@login_required
def deal_reject(request, pk):
    """拒絕交易申請。"""
    deal = get_object_or_404(Deal, pk=pk, responder=request.user)
    try:
        deal_service.decline_deal(deal)
        messages.success(request, "交易已拒絕。")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("deals:detail", pk)


@login_required
def deal_cancel(request, pk):
    """取消交易申請。"""
    deal = get_object_or_404(Deal, pk=pk, applicant=request.user)
    try:
        deal_service.cancel_deal(deal)
        messages.success(request, "交易已取消。")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("deals:list")


@login_required
@require_POST
def deal_complete_meeting(request, pk):
    """確認面交完成。"""
    deal = get_object_or_404(
        Deal.objects.filter(status=Deal.Status.RESPONDED).filter(applicant=request.user)
        | Deal.objects.filter(status=Deal.Status.RESPONDED, responder=request.user),
        pk=pk,
    )

    # 檢查權限
    if request.user not in [deal.applicant, deal.responder]:
        messages.error(request, "您無權執行此操作。")
        return redirect("deals:detail", pk)

    try:
        deal_service.complete_meeting(deal)
        messages.success(request, "面交已完成！請進行評價。")
    except Exception as e:
        messages.error(request, str(e))
    return redirect("deals:detail", pk)


@login_required
@require_POST
def deal_message_send(request, pk):
    """發送交易留言（HTMX endpoint）。"""
    deal = get_object_or_404(Deal, pk=pk)

    # 檢查權限
    if request.user not in [deal.applicant, deal.responder]:
        return HttpResponse("您無權發送留言。", status=403)

    # 檢查交易狀態（Q 或 P 狀態可留言）
    if deal.status not in [Deal.Status.REQUESTED, Deal.Status.RESPONDED]:
        return HttpResponse("此交易狀態無法發送留言。", status=400)

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponse("請輸入留言內容。", status=400)

    DealMessage.objects.create(
        deal=deal,
        sender=request.user,
        content=content,
    )

    # 返回更新後的留言列表 partial
    messages_list = DealMessage.objects.filter(deal=deal).select_related("sender")[:50]
    return render(
        request,
        "deals/partials/message_list.html",
        {"messages": messages_list, "deal": deal},
    )


@login_required
def rating_create(request, pk):
    """建立評價。"""
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book__official_book",
            "applicant__profile",
            "responder__profile",
        ),
        pk=pk,
    )

    # 檢查權限
    if request.user not in [deal.applicant, deal.responder]:
        messages.error(request, "您無權評價此交易。")
        return redirect("deals:detail", pk)

    # 檢查是否已評價
    if request.user == deal.applicant and deal.applicant_rated:
        messages.info(request, "您已經評價過此交易。")
        return redirect("deals:detail", pk)
    if request.user == deal.responder and deal.responder_rated:
        messages.info(request, "您已經評價過此交易。")
        return redirect("deals:detail", pk)

    # 判斷被評價者
    ratee = deal.responder if request.user == deal.applicant else deal.applicant

    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            try:
                rating_service.create_rating(
                    deal=deal,
                    rater=request.user,
                    integrity_score=form.cleaned_data["integrity_score"],
                    punctuality_score=form.cleaned_data["punctuality_score"],
                    accuracy_score=form.cleaned_data["accuracy_score"],
                    comment=form.cleaned_data.get("comment", ""),
                )
                messages.success(request, "評價已送出！")
                return redirect("deals:detail", pk)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = RatingForm()

    return render(
        request,
        "deals/rating_create.html",
        {
            "deal": deal,
            "form": form,
            "ratee": ratee,
        },
    )


# ============================================
# Web Push 相關 Views
# ============================================


@login_required
def push_vapid_public_key(request):
    """
    取得 VAPID 公開金鑰。

    前端需要此金鑰來註冊 Push 訂閱。
    """
    config = WebPushConfig.get_config()
    if not config:
        return JsonResponse(
            {"error": "Web Push 尚未設定"},
            status=503,
        )

    return JsonResponse({"publicKey": config.vapid_public_key})


@login_required
@require_POST
def push_subscribe(request):
    """
    註冊 Push 訂閱。

    接收前端 PushManager.subscribe() 返回的訂閱資訊並儲存。
    """
    try:
        data = json.loads(request.body)
        subscription = data.get("subscription", {})

        endpoint = subscription.get("endpoint")
        keys = subscription.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not all([endpoint, p256dh, auth]):
            return JsonResponse(
                {"error": "缺少必要欄位"},
                status=400,
            )

        # 使用 update_or_create 確保同一端點不重複
        subscription_obj, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
                "is_active": True,
            },
        )

        action = "已註冊" if created else "已更新"
        logger.info(f"Push 訂閱{action}: {request.user} - {endpoint[:50]}...")

        return JsonResponse(
            {
                "success": True,
                "message": f"Push 訂閱{action}",
                "subscription_id": str(subscription_obj.id),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "無效的 JSON 資料"},
            status=400,
        )
    except Exception as e:
        logger.error(f"Push 訂閱失敗: {e}")
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )


@login_required
@require_POST
def push_unsubscribe(request):
    """
    取消 Push 訂閱。

    將訂閱標記為不啟用（軟刪除）。
    """
    try:
        data = json.loads(request.body)
        endpoint = data.get("endpoint")

        if not endpoint:
            return JsonResponse(
                {"error": "缺少 endpoint"},
                status=400,
            )

        # 找到並停用訂閱
        updated = PushSubscription.objects.filter(
            endpoint=endpoint,
            user=request.user,
        ).update(is_active=False)

        if updated:
            logger.info(f"Push 訂閱已取消: {request.user} - {endpoint[:50]}...")
            return JsonResponse({"success": True, "message": "已取消訂閱"})
        else:
            return JsonResponse(
                {"error": "找不到訂閱"},
                status=404,
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "無效的 JSON 資料"},
            status=400,
        )
    except Exception as e:
        logger.error(f"取消 Push 訂閱失敗: {e}")
        return JsonResponse(
            {"error": str(e)},
            status=500,
        )
