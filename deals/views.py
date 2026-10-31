"""
交易相關 Views。
"""

# pyright: reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false

import json
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from books.models import SharedBook
from django.core.exceptions import PermissionDenied, ValidationError

from core.error_messages import service_error_message
from .forms import (
    DealApplicationForm,
    RatingForm,
    ExtensionRequestForm,
    ExceptionDealForm,
    ExceptionResolveForm,
    DealPhotoUploadForm,
)
from .models import (
    Deal,
    DealMessage,
    PushSubscription,
    WebPushConfig,
    LoanExtension,
    Notification,
)
from .services import (
    deal_feed_service,
    deal_service,
    rating_service,
    extension_service,
    notification_service,
)
from .services.api_response import api_success, api_error, ErrorCode

logger = logging.getLogger(__name__)


def _require_deal_party(request, deal):
    """非交易當事人一律 404（與交易詳情一致，不洩漏交易是否存在）。

    當事人但無該動作權限者，仍由各 view 自行回應（維持原行為）。
    """
    if not request.user.has_perm("deals.can_view_deal", deal):
        logger.warning(
            "deal access by non-party",
            extra={"user_id": request.user.pk, "deal_id": str(deal.pk)},
        )
        raise Http404


@login_required
def deal_create(request, book_id, deal_type):
    """建立交易申請。"""
    book = get_object_or_404(SharedBook, pk=book_id)
    logger.info("deal_create", extra={"user_id": request.user.pk, "book_id": str(book_id), "deal_type": deal_type})

    if request.method == "POST":
        form = DealApplicationForm(request.POST)
        if form.is_valid():
            try:
                deal = deal_service.create_deal(
                    deal_type=deal_type,
                    shared_book=book,
                    applicant=request.user,
                    meeting_location=form.cleaned_data.get("meeting_location", ""),
                    meeting_time=form.cleaned_data.get("meeting_time"),
                    note=form.cleaned_data.get("note", ""),
                )
                logger.info("deal_create success", extra={"user_id": request.user.pk, "deal_id": str(deal.id), "deal_type": deal_type})
                messages.success(request, "交易申請已送出！")
                return redirect("deals:detail", deal.id)
            except Exception as e:
                logger.exception("deal_create failed", extra={"user_id": request.user.pk, "book_id": str(book_id), "deal_type": deal_type})
                messages.error(request, service_error_message(e))
    else:
        profile = request.user.profile
        initial_note = ""
        if profile.default_location:
            initial_note += f"建議面交地點：{profile.default_location}\n"

        if profile.schedule_text:
            initial_note += f"可面交時間：{profile.schedule_text}"

        form = DealApplicationForm(
            initial={
                "deal_type": deal_type,
                "shared_book": book_id,
                "meeting_location": profile.default_location,
                "note": initial_note.strip(),
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
    logger.info("deal_detail", extra={"user_id": request.user.pk, "deal_id": str(pk)})
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book__official_book",
            "shared_book__keeper__profile",
            "applicant__profile",
            "responder__profile",
        ).prefetch_related("ratings__rater__profile"),
        pk=pk,
    )
    # 非當事人一律 404（不洩漏交易是否存在，也不暴露私訊）
    _require_deal_party(request, deal)
    messages_list = DealMessage.objects.filter(deal=deal).select_related("sender")[:50]
    extensions_list = LoanExtension.objects.filter(deal=deal).select_related(
        "requested_by__profile",
        "approved_by__profile",
    )[:20]

    from accounts.services.user_stats_service import get_user_rating_summary
    from deals.services.overdue_service import is_overdue as deal_is_overdue

    notification_service.mark_deal_as_read(request.user, deal)

    def get_user_rating_info(user):
        summary = get_user_rating_summary(user)
        if summary["total_ratings"] == 0:
            return None
        return {
            "avg_rating": summary["overall_average"],
            "total_ratings": summary["total_ratings"],
        }

    is_overdue = deal_is_overdue(deal)

    return render(
        request,
        "deals/deal_detail.html",
        {
            "deal": deal,
            "deal_messages": messages_list,
            "extensions": extensions_list,
            "is_applicant": request.user == deal.applicant,
            "is_responder": request.user == deal.responder,
            # 延期申請入口的資格判定（單一來源，見 extension_service）
            "can_request_extension": extension_service.is_extension_eligible(
                request.user, deal
            ),
            "is_owner": request.user == deal.shared_book.owner,
            "is_keeper": request.user == deal.shared_book.keeper,
            "is_force_return_receiver": request.user
            == deal_service.get_force_return_receiver(deal),
            "is_overdue": is_overdue,
            "applicant_rating": get_user_rating_info(deal.applicant),
            "responder_rating": get_user_rating_info(deal.responder),
        },
    )


@login_required
def deal_list(request):
    """交易管理頁面。"""
    logger.info("deal_list", extra={"user_id": request.user.pk, "tab": request.GET.get("tab", "pending")})

    context = deal_feed_service.get_feed(
        request.user, request.GET.get("tab", "pending")
    )

    if request.headers.get("HX-Request"):
        return render(request, "deals/partials/_deal_list_page_wrapper.html", context)

    return render(request, "deals/deal_list.html", context)


@login_required
@require_POST
def deal_accept(request, pk):
    """接受交易申請。"""
    deal = get_object_or_404(Deal, pk=pk)
    _require_deal_party(request, deal)
    if not request.user.has_perm("deals.can_accept_deal", deal):
        logger.warning("deal_accept forbidden", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, "您無權接受此交易。")
        return redirect("deals:detail", pk)
    try:
        deal_service.accept_deal(deal)
        logger.info("deal_accept", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.success(request, "交易已接受！")
    except Exception as e:
        logger.exception("deal_accept failed", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, service_error_message(e))
    return redirect("deals:detail", pk)


@login_required
@require_POST
def deal_reject(request, pk):
    """拒絕交易申請。"""
    deal = get_object_or_404(Deal, pk=pk)
    _require_deal_party(request, deal)
    if not request.user.has_perm("deals.can_decline_deal", deal):
        logger.warning("deal_reject forbidden", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, "您無權拒絕此交易。")
        return redirect("deals:detail", pk)
    try:
        deal_service.decline_deal(deal)
        logger.info("deal_reject", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.success(request, "交易已拒絕。")
    except Exception as e:
        logger.exception("deal_reject failed", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, service_error_message(e))
    return redirect("deals:detail", pk)


@login_required
@require_POST
def deal_cancel(request, pk):
    """取消交易申請。"""
    deal = get_object_or_404(Deal, pk=pk)
    _require_deal_party(request, deal)
    if not request.user.has_perm("deals.can_cancel_deal", deal):
        logger.warning("deal_cancel forbidden", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, "您無權取消此交易。")
        return redirect("deals:detail", pk)
    try:
        deal_service.cancel_deal(deal)
        logger.info("deal_cancel", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.success(request, "交易已取消。")
    except Exception as e:
        logger.exception("deal_cancel failed", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, service_error_message(e))
    return redirect("deals:list")


@login_required
@require_POST
def deal_complete_meeting(request, pk):
    """確認面交完成。"""
    deal = get_object_or_404(Deal, pk=pk)
    _require_deal_party(request, deal)

    if not request.user.has_perm("deals.can_complete_meeting", deal):
        logger.warning("deal_complete_meeting forbidden", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, "您無權執行此操作。")
        return redirect("deals:detail", pk)

    try:
        deal_service.complete_meeting(deal)
        logger.info("deal_complete_meeting", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.success(request, "面交已完成！請進行評價。")
    except Exception as e:
        logger.exception("deal_complete_meeting failed", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, service_error_message(e))
    return redirect("deals:detail", pk)


@login_required
@require_POST
def deal_message_send(request, pk):
    """發送交易留言（HTMX endpoint）。"""
    deal = get_object_or_404(Deal, pk=pk)
    _require_deal_party(request, deal)
    logger.info("deal_message_send", extra={"user_id": request.user.pk, "deal_id": str(pk)})

    # 檢查權限
    if not request.user.has_perm("deals.can_send_message", deal):
        return HttpResponse(
            "您無權發送留言。", status=403, content_type="text/plain; charset=utf-8"
        )

    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponse(
            "請輸入留言內容。", status=400, content_type="text/plain; charset=utf-8"
        )

    try:
        deal_service.send_deal_message(deal, request.user, content)
    except ValidationError as e:
        return HttpResponse(
            service_error_message(e), status=400, content_type="text/plain; charset=utf-8"
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
    logger.info("rating_create", extra={"user_id": request.user.pk, "deal_id": str(pk)})
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book__official_book",
            "applicant__profile",
            "responder__profile",
        ).prefetch_related("shared_book__photos"),
        pk=pk,
    )
    _require_deal_party(request, deal)

    # 檢查權限
    if not request.user.has_perm("deals.can_rate_deal", deal):
        messages.error(request, "您無權評價此交易。")
        return redirect("deals:detail", pk)

    # 判斷被評價者（已評價的 guard 在 rating_service.create_rating）
    ratee = deal.responder if request.user == deal.applicant else deal.applicant

    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            try:
                rating_service.create_rating(
                    deal=deal,
                    rater=request.user,
                    friendliness_score=form.cleaned_data["friendliness_score"],
                    punctuality_score=form.cleaned_data["punctuality_score"],
                    accuracy_score=form.cleaned_data["accuracy_score"],
                    comment=form.cleaned_data.get("comment", ""),
                )
                messages.success(request, "評價已送出！")
                return redirect("deals:detail", pk)
            except ValidationError as e:
                messages.error(request, service_error_message(e))
                return redirect("deals:detail", pk)
        else:
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label}: {error}")
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


def push_vapid_public_key(request):
    """
    取得 VAPID 公開金鑰。

    前端需要此金鑰來註冊 Push 訂閱。
    注意：此端點不需要登入，因為金鑰是公開的。
    """
    try:
        config = WebPushConfig.get_config()
        if not config:
            return api_error(
                message="Web Push 尚未設定",
                code=ErrorCode.SERVICE_UNAVAILABLE,
                status=503,
            )

        return api_success(data={"publicKey": config.vapid_public_key})
    except Exception as e:
        logger.warning("push_vapid_public_key failed", extra={"error": str(e)})
        return api_error(
            message="Web Push 服務暫時無法使用",
            code=ErrorCode.SERVICE_UNAVAILABLE,
            status=503,
        )


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
            return api_error(
                message="缺少必要欄位",
                code=ErrorCode.MISSING_FIELD,
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

        action = "registered" if created else "updated"
        logger.info("push_subscribe", extra={"user_id": request.user.pk, "action": action, "endpoint_prefix": endpoint[:50]})

        return api_success(
            data={"subscription_id": str(subscription_obj.id)},
            message=f"Push 訂閱{action}",
        )

    except json.JSONDecodeError:
        return api_error(
            message="無效的 JSON 資料",
            code=ErrorCode.INVALID_JSON,
            status=400,
        )
    except Exception as e:
        logger.exception("push_subscribe failed", extra={"user_id": request.user.pk})
        return api_error(
            message=str(e),
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
            return api_error(
                message="缺少 endpoint",
                code=ErrorCode.MISSING_FIELD,
                status=400,
            )

        # 找到並停用訂閱
        updated = PushSubscription.objects.filter(
            endpoint=endpoint,
            user=request.user,
        ).update(is_active=False)

        if updated:
            logger.info("push_unsubscribe", extra={"user_id": request.user.pk, "endpoint_prefix": endpoint[:50]})
            return api_success(message="已取消訂閱")
        else:
            return api_error(
                message="找不到訂閱",
                code=ErrorCode.NOT_FOUND,
                status=404,
            )

    except json.JSONDecodeError:
        return api_error(
            message="無效的 JSON 資料",
            code=ErrorCode.INVALID_JSON,
            status=400,
        )
    except Exception as e:
        logger.exception("push_unsubscribe failed", extra={"user_id": request.user.pk})
        return api_error(
            message=str(e),
            status=500,
        )


# ============================================
# 延長借閱相關 Views
# ============================================


@login_required
def extension_request(request, deal_pk):
    """申請延長借閱。"""
    logger.info("extension_request", extra={"user_id": request.user.pk, "deal_id": str(deal_pk)})
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book__official_book",
            "applicant",
            "responder",
        ),
        pk=deal_pk,
    )
    _require_deal_party(request, deal)

    # 權限檢查
    if not request.user.has_perm("deals.can_request_extension", deal):
        messages.error(request, "只有借閱者可以申請延長。")
        return redirect("deals:detail", deal_pk)

    if request.method == "POST":
        form = ExtensionRequestForm(request.POST)
        if form.is_valid():
            try:
                extension_service.request_extension(
                    deal=deal,
                    applicant=request.user,
                    extra_days=form.cleaned_data["extra_days"],
                )
                logger.info("extension_request success", extra={"user_id": request.user.pk, "deal_id": str(deal_pk), "extra_days": form.cleaned_data["extra_days"]})
                messages.success(request, "延長申請已送出！")
                return redirect("deals:detail", deal_pk)
            except Exception as e:
                messages.error(request, service_error_message(e))
    else:
        form = ExtensionRequestForm()

    return render(
        request,
        "deals/extension_request.html",
        {
            "form": form,
            "deal": deal,
        },
    )


@login_required
@require_POST
def extension_approve(request, extension_pk):
    """核准延長申請。"""
    extension = get_object_or_404(
        LoanExtension.objects.select_related(
            "deal",
            "deal__shared_book",
            "deal__shared_book__owner",
            "deal__shared_book__keeper",
        ),
        pk=extension_pk,
    )
    _require_deal_party(request, extension.deal)

    # 權限檢查
    if not request.user.has_perm("deals.can_approve_extension", extension):
        messages.error(request, "您無權核准此申請。")
        return redirect("deals:detail", extension.deal.id)

    try:
        extension_service.approve_extension(
            extension=extension,
            reviewer=request.user,
        )
        logger.info("extension_approve", extra={"user_id": request.user.pk, "extension_id": str(extension_pk), "deal_id": str(extension.deal.id)})
        messages.success(request, "延長申請已核准！")
    except Exception as e:
        logger.exception("extension_approve failed", extra={"user_id": request.user.pk, "extension_id": str(extension_pk)})
        messages.error(request, service_error_message(e))

    return redirect("deals:detail", extension.deal.id)


@login_required
@require_POST
def extension_reject(request, extension_pk):
    """拒絕延長申請。"""
    extension = get_object_or_404(
        LoanExtension.objects.select_related(
            "deal",
            "deal__shared_book",
            "deal__shared_book__owner",
            "deal__shared_book__keeper",
        ),
        pk=extension_pk,
    )
    _require_deal_party(request, extension.deal)

    # 權限檢查
    if not request.user.has_perm("deals.can_reject_extension", extension):
        messages.error(request, "您無權拒絕此申請。")
        return redirect("deals:detail", extension.deal.id)

    try:
        extension_service.reject_extension(
            extension=extension,
            reviewer=request.user,
        )
        logger.info("extension_reject", extra={"user_id": request.user.pk, "extension_id": str(extension_pk), "deal_id": str(extension.deal.id)})
        messages.success(request, "延長申請已拒絕。")
    except Exception as e:
        logger.exception("extension_reject failed", extra={"user_id": request.user.pk, "extension_id": str(extension_pk)})
        messages.error(request, service_error_message(e))

    return redirect("deals:detail", extension.deal.id)


@login_required
@require_POST
def extension_cancel(request, extension_pk):
    """取消延長申請。"""
    extension = get_object_or_404(
        LoanExtension.objects.select_related("deal", "requested_by"),
        pk=extension_pk,
    )
    _require_deal_party(request, extension.deal)

    # 權限檢查
    if not request.user.has_perm("deals.can_cancel_extension", extension):
        messages.error(request, "您無權取消此申請。")
        return redirect("deals:detail", extension.deal.id)

    try:
        extension_service.cancel_extension(
            extension=extension,
            applicant=request.user,
        )
        logger.info("extension_cancel", extra={"user_id": request.user.pk, "extension_id": str(extension_pk), "deal_id": str(extension.deal.id)})
        messages.success(request, "延長申請已取消。")
    except Exception as e:
        logger.exception("extension_cancel failed", extra={"user_id": request.user.pk, "extension_id": str(extension_pk)})
        messages.error(request, service_error_message(e))

    return redirect("deals:detail", extension.deal.id)


# ============================================
# 通知相關 Views
# ============================================


@login_required
def notification_list(request):
    """通知列表頁面。"""
    user = request.user
    tab = request.GET.get("tab", "all")
    logger.info("notification_list", extra={"user_id": user.pk, "tab": tab})

    # 基礎查詢
    notifications = Notification.objects.filter(recipient=user).select_related(
        "deal__shared_book__official_book",
        "shared_book__official_book",
    )

    # 篩選
    if tab == "unread":
        notifications = notifications.filter(is_read=False)
    elif tab == "read":
        notifications = notifications.filter(is_read=True)

    # 分頁
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # 計算未讀數量
    unread_count = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()

    context = {
        "page_obj": page_obj,
        "current_tab": tab,
        "unread_count": unread_count,
    }

    if request.headers.get("HX-Request") and not request.headers.get("HX-Boosted"):
        return render(request, "deals/partials/notification_list_content.html", context)

    return render(request, "deals/notification_list.html", context)


@login_required
def notification_count(request):
    """HTMX endpoint: 返回未讀通知數量。"""
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()
    logger.debug("notification_count", extra={"user_id": request.user.pk, "unread_count": unread_count})
    return render(
        request,
        "deals/partials/notification_badge.html",
        {"unread_count": unread_count},
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    """標記單一通知為已讀。"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    notification_service.mark_as_read(notification)
    logger.debug("notification_mark_read", extra={"user_id": request.user.pk, "notification_id": str(pk)})

    response = render(
        request,
        "deals/partials/notification_item.html",
        {"notification": notification},
    )
    response["HX-Trigger"] = "refreshNotificationBadge"
    return response


@login_required
@require_POST
def notification_mark_all_read(request):
    """標記所有通知為已讀。"""
    notification_service.mark_all_as_read(request.user)
    logger.info("notification_mark_all_read", extra={"user_id": request.user.pk})
    return redirect("deals:notification_list")


# ============================================
# 書籍歸還確認相關 Views
# ============================================


@login_required
@require_POST
def deal_confirm_return(request, pk):
    """確認書籍歸還並重新上架。"""
    logger.info("deal_confirm_return", extra={"user_id": request.user.pk, "deal_id": str(pk)})
    deal = get_object_or_404(
        Deal.objects.select_related(
            "shared_book",
            "shared_book__official_book",
        ),
        pk=pk,
    )
    _require_deal_party(request, deal)

    force = request.POST.get("force") == "true"

    # 權限檢查
    if not force and not request.user.has_perm("deals.can_confirm_return", deal):
        messages.error(request, "只有持有者可以確認歸還。")
        return redirect("deals:detail", pk)

    if force and not request.user.has_perm("deals.can_force_return", deal):
        messages.error(request, "只有收書方可以強制確認歸還。")
        return redirect("deals:detail", pk)

    try:
        deal_service.confirm_return(deal, confirmed_by=request.user, force=force)
        logger.info("deal_confirm_return success", extra={"user_id": request.user.pk, "deal_id": str(pk), "force": force})
        if force:
            messages.success(request, "已強制確認歸還並重新上架。")
        else:
            messages.success(request, "書籍已確認歸還並重新上架！")
    except Exception as e:
        logger.exception("deal_confirm_return failed", extra={"user_id": request.user.pk, "deal_id": str(pk), "force": force})
        messages.error(request, service_error_message(e))

    return redirect("deals:detail", pk)


# ============================================
# 例外處理 Views
# ============================================


@login_required
def exception_create(request, book_id):
    """申請例外處理（EX 交易）"""
    from books.models import SharedBook

    book = get_object_or_404(SharedBook, pk=book_id)
    logger.info("exception_create", extra={"user_id": request.user.pk, "book_id": str(book_id)})

    if not request.user.has_perm("deals.can_create_exception", book):
        logger.warning("exception_create forbidden", extra={"user_id": request.user.pk, "book_id": str(book_id)})
        messages.error(request, "只有持有者可以申請例外處理")
        return redirect("books:detail", pk=book_id)

    if request.method == "POST":
        form = ExceptionDealForm(request.POST)
        if form.is_valid():
            try:
                # 書籍狀態 gate（T/O/R）由 create_deal 負責
                deal = deal_service.create_exception(
                    book,
                    request.user,
                    form.cleaned_data.get("description", ""),
                )
                logger.info("exception_create success", extra={"user_id": request.user.pk, "book_id": str(book_id), "deal_id": str(deal.pk)})
                messages.success(request, "例外處理申請已送出")
                return redirect("deals:detail", pk=deal.pk)
            # 只接 service 層宣告的錯誤（錯誤契約見 GLOSSARY）；
            # 未預期的例外直接拋給 500 handler，不吞掉
            except (ValidationError, PermissionDenied) as e:
                logger.warning("exception_create failed", extra={"user_id": request.user.pk, "book_id": str(book_id)})
                messages.error(request, service_error_message(e))
    else:
        form = ExceptionDealForm()

    return render(
        request,
        "deals/exception_create.html",
        {"form": form, "book": book},
    )


@login_required
def exception_resolve(request, pk):
    """處置例外（Owner 審核）"""
    deal = get_object_or_404(
        Deal.objects.select_related("shared_book"),
        pk=pk,
    )
    _require_deal_party(request, deal)
    logger.info("exception_resolve", extra={"user_id": request.user.pk, "deal_id": str(pk)})

    if not request.user.has_perm("deals.can_resolve_exception", deal.shared_book):
        logger.warning("exception_resolve forbidden", extra={"user_id": request.user.pk, "deal_id": str(pk)})
        messages.error(request, "只有貢獻者可以處置例外")
        return redirect("deals:detail", pk=pk)

    if request.method == "POST":
        form = ExceptionResolveForm(request.POST)
        if form.is_valid():
            try:
                resolution = form.cleaned_data["resolution"]
                # guards（EX 類型、書在 E 狀態）與兩個 transition 都在 service 內
                deal_service.resolve_exception_deal(deal, resolution)
                logger.info("exception_resolve success", extra={"user_id": request.user.pk, "deal_id": str(pk), "resolution": resolution})
                messages.success(
                    request,
                    f"已處置為「{dict(ExceptionResolveForm.RESOLUTION_CHOICES).get(resolution)}」",
                )
                return redirect("books:detail", pk=deal.shared_book.pk)
            # 只接 service 層宣告的錯誤（錯誤契約見 GLOSSARY）；
            # 未預期的例外直接拋給 500 handler，不吞掉
            except (ValidationError, PermissionDenied) as e:
                logger.warning("exception_resolve failed", extra={"user_id": request.user.pk, "deal_id": str(pk)})
                messages.error(request, service_error_message(e))
    else:
        form = ExceptionResolveForm()

    return render(
        request,
        "deals/exception_resolve.html",
        {"form": form, "deal": deal},
    )


# ============================================
# 書況照片上傳 Views
# ============================================


@login_required
def deal_upload_photos(request, pk):
    """面交後上傳書況照片。

    條件：
    - 交易狀態為 M（已面交）
    - 只有「開放傳遞」書籍可上傳照片（記錄流轉書況）
    - 新持有者（keeper）可上傳照片
    """
    logger.info("deal_upload_photos", extra={"user_id": request.user.pk, "deal_id": str(pk)})
    deal = get_object_or_404(
        Deal.objects.select_related("shared_book", "shared_book__official_book"),
        pk=pk,
    )
    _require_deal_party(request, deal)

    # 權限檢查
    if not request.user.has_perm("deals.can_upload_deal_photos", deal):
        messages.error(request, "只有持有者可以上傳照片。")
        return redirect("deals:detail", pk)

    if request.method == "POST":
        form = DealPhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # guards（開放傳遞、MEETED 狀態）在 service 內
                created = deal_service.upload_deal_photos(
                    deal,
                    request.user,
                    request.FILES.getlist("photos"),
                    caption=form.cleaned_data.get("caption", ""),
                )
            except ValidationError as e:
                logger.exception("deal_upload_photos validation error", extra={"user_id": request.user.pk, "deal_id": str(pk)})
                messages.error(request, f"照片上傳失敗：{service_error_message(e)}")
                return render(
                    request,
                    "deals/deal_upload_photos.html",
                    {"form": form, "deal": deal},
                )

            logger.info("deal_upload_photos success", extra={"user_id": request.user.pk, "deal_id": str(pk), "photo_count": len(created)})
            messages.success(request, f"已上傳 {len(created)} 張照片。")
            return redirect("deals:detail", pk)
    else:
        form = DealPhotoUploadForm()

    return render(
        request,
        "deals/deal_upload_photos.html",
        {
            "form": form,
            "deal": deal,
        },
    )
