from datetime import timedelta

from django.utils import timezone

from deals.models import Deal, LoanExtension, Notification


def _resolve_notification_url(deal=None, shared_book=None):
    """產生通知點擊跳轉 URL。"""
    from django.urls import reverse

    if deal:
        return reverse("deals:detail", kwargs={"pk": deal.id})
    if shared_book:
        return reverse("books:detail", kwargs={"pk": shared_book.id})
    return "/"


def notify(
    recipient,
    notification_type,
    title,
    message="",
    deal=None,
    shared_book=None,
    send_push=True,
    send_email=True,
):
    """
    建立系統通知並透過 Celery 非同步發送 Push／Email。

    Args:
        recipient: 接收者 (User)
        notification_type: NotificationType 枚舉值
        title: 通知標題
        message: 通知內容（可選）
        deal: 相關交易（可選）
        shared_book: 相關書籍（可選）
        send_push: 是否發送 Web Push（預設 True）
        send_email: 是否發送 Email（預設 True）

    Returns:
        Notification: 建立的通知
    """
    notification = Notification._default_manager.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        deal=deal,
        shared_book=shared_book,
    )

    profile = getattr(recipient, "profile", None)

    if send_push and (not profile or profile.push_enabled):
        from deals.tasks import send_push_notification_task

        url = _resolve_notification_url(deal, shared_book)
        send_push_notification_task.delay(
            user_id=recipient.pk,
            title=title,
            message=message,
            url=url,
            deal_id=str(deal.id) if deal else None,
            book_id=str(shared_book.id) if shared_book else None,
            notification_type=notification_type,
        )

    if send_email and (not profile or profile.email_notifications_enabled):
        from deals.tasks import send_email_notification_task

        send_email_notification_task.delay(
            user_id=recipient.pk,
            title=title,
            message=message,
        )

    return notification


def notify_deal_requested(deal):
    """收到交易申請 → 通知回應者"""
    notify(
        recipient=deal.responder,
        notification_type=Notification.NotificationType.DEAL_REQUESTED,
        title=f"收到{deal.get_deal_type_display()}申請",
        message=f"{deal.applicant} 對書籍「{deal.shared_book}」發起了{deal.get_deal_type_display()}申請",
        deal=deal,
        shared_book=deal.shared_book,
    )


def notify_deal_responded(deal):
    """交易已被回應（接受）→ 通知申請者"""
    notify(
        recipient=deal.applicant,
        notification_type=Notification.NotificationType.DEAL_RESPONDED,
        title=f"{deal.get_deal_type_display()}已被接受",
        message=f"{deal.responder} 已接受您對書籍「{deal.shared_book}」的{deal.get_deal_type_display()}申請",
        deal=deal,
        shared_book=deal.shared_book,
    )


def notify_deal_cancelled(deal, cancelled_by):
    """交易被取消/拒絕 → 通知另一方"""
    if cancelled_by == deal.applicant:
        recipient = deal.responder
    else:
        recipient = deal.applicant

    notify(
        recipient=recipient,
        notification_type=Notification.NotificationType.DEAL_CANCELLED,
        title=f"{deal.get_deal_type_display()}已被取消",
        message=f"書籍「{deal.shared_book}」的{deal.get_deal_type_display()}已被取消",
        deal=deal,
        shared_book=deal.shared_book,
    )


def notify_deal_meeted(deal):
    """面交完成 → 通知雙方進行評價"""
    for recipient in (deal.applicant, deal.responder):
        notify(
            recipient=recipient,
            notification_type=Notification.NotificationType.DEAL_MEETED,
            title="面交完成，請評價交易對象",
            message=f"書籍「{deal.shared_book}」的{deal.get_deal_type_display()}已完成面交，請進行評價",
            deal=deal,
            shared_book=deal.shared_book,
        )


def notify_rating_pending(deal, user):
    """評價逾期提醒：通知尚未評價的一方。"""
    notify(
        recipient=user,
        notification_type=Notification.NotificationType.DEAL_MEETED,
        title="評價提醒：仍有交易待評",
        message=(
            f"書籍「{deal.shared_book}」的{deal.get_deal_type_display()}已逾 3 天仍未完成評價，"
            "請儘速完成。"
        ),
        deal=deal,
        shared_book=deal.shared_book,
        send_push=True,
        send_email=False,
    )


def notify_book_due_soon(deal):
    """書籍即將到期 → 通知持有者"""
    notify(
        recipient=deal.shared_book.keeper,
        notification_type=Notification.NotificationType.BOOK_DUE_SOON,
        title="書籍即將到期",
        message=f"您持有的書籍「{deal.shared_book}」將於 {deal.due_date} 到期，請儘速處理",
        deal=deal,
        shared_book=deal.shared_book,
    )


def batch_send_due_reminders(days: int = 3) -> dict:
    """發送即將到期借閱提醒，跳過當日已發送者。"""
    target_date = timezone.now().date() + timedelta(days=days)
    upcoming_deals = Deal.objects.filter(
        status=Deal.Status.MEETED,
        due_date=target_date,
        shared_book__status="O",
    ).select_related("shared_book__official_book", "applicant", "responder")

    today = timezone.now().date()
    sent = 0
    skipped = 0
    errors = 0

    for deal in upcoming_deals:
        existing = Notification.objects.filter(
            recipient=deal.applicant,
            notification_type=Notification.NotificationType.BOOK_DUE_SOON,
            created_at__date=today,
        ).exists()

        if existing:
            skipped += 1
            continue

        try:
            notify_book_due_soon(deal)
            sent += 1
        except Exception:
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors}


def notify_book_overdue(deal):
    """書籍已逾期 → 通知持有者與貢獻者"""
    shared_book = deal.shared_book

    for recipient in {shared_book.keeper, shared_book.owner}:
        notify(
            recipient=recipient,
            notification_type=Notification.NotificationType.BOOK_OVERDUE,
            title="書籍已逾期",
            message=f"書籍「{shared_book}」已逾期未還",
            deal=deal,
            shared_book=shared_book,
        )


def notify_book_available(user, shared_book):
    """願望書籍已可借閱 → 通知願望書車的讀者"""
    notify(
        recipient=user,
        notification_type=Notification.NotificationType.BOOK_AVAILABLE,
        title="您的願望書籍已可借閱",
        message=f"書籍「{shared_book.official_book}」已有可借閱的冊數上架",
        shared_book=shared_book,
    )


def notify_extend_requested(extension):
    """收到延長申請 → 通知審核者"""
    deal = extension.deal
    notify(
        recipient=deal.responder,
        notification_type=Notification.NotificationType.EXTEND_REQUESTED,
        title="收到借閱延長申請",
        message=f"{extension.requested_by} 申請將書籍「{deal.shared_book}」延長 {extension.extra_days} 天",
        deal=deal,
        shared_book=deal.shared_book,
    )


def notify_extend_result(extension):
    """延長申請結果 → 通知申請者"""
    deal = extension.deal
    if extension.status == LoanExtension.Status.APPROVED:
        ntype = Notification.NotificationType.EXTEND_APPROVED
        title = "延長申請已核准"
        msg = f"您的延長申請已被核准，書籍「{deal.shared_book}」到期日延長至 {deal.due_date}"
    else:
        ntype = Notification.NotificationType.EXTEND_REJECTED
        title = "延長申請已拒絕"
        msg = f"您的延長申請已被拒絕，書籍「{deal.shared_book}」到期日不變"

    notify(
        recipient=extension.requested_by,
        notification_type=ntype,
        title=title,
        message=msg,
        deal=deal,
        shared_book=deal.shared_book,
    )


def mark_as_read(notification):
    """標記通知為已讀"""
    notification.is_read = True
    notification.save(update_fields=["is_read"])


def mark_all_as_read(user):
    """標記使用者所有未讀通知為已讀"""
    Notification._default_manager.filter(
        recipient=user,
        is_read=False,
    ).update(is_read=True)


def notify_rating_created(rating):
    """收到評價 → 通知被評價者。"""
    notify(
        recipient=rating.ratee,
        notification_type=Notification.NotificationType.RATING_CREATED,
        title="您收到新的交易評價",
        message=(
            f"{rating.rater} 已針對書籍「{rating.deal.shared_book}」給予您評價，"
            f"平均分數 {rating.average_score:.1f} 分"
        ),
        deal=rating.deal,
        shared_book=rating.deal.shared_book,
    )


def notify_violation_created(violation):
    """收到違規處分 → 通知被處分用戶。"""
    message = (
        f"您收到一筆{violation.get_action_type_display()}處分"
        f"（違規行為：{violation.get_violation_type_display()}）。"
    )

    if violation.suspension_days:
        message += f" 停權天數：{violation.suspension_days} 天。"

    if violation.description:
        message += f" 說明：{violation.description}"

    notify(
        recipient=violation.user,
        notification_type=Notification.NotificationType.VIOLATION_CREATED,
        title="您收到新的違規處分通知",
        message=message,
    )


def notify_appeal_status_updated(appeal):
    """申訴狀態更新 → 通知申訴人。"""
    notify(
        recipient=appeal.user,
        notification_type=Notification.NotificationType.APPEAL_STATUS_UPDATED,
        title=f"申訴狀態已更新：{appeal.get_status_display()}",
        message=f"您的申訴「{appeal.title}」目前狀態為：{appeal.get_status_display()}。",
    )
