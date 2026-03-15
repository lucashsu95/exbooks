from deals.models import Notification


def notify(
    recipient, notification_type, title, message="", deal=None, shared_book=None
):
    """
    建立系統通知。

    統一入口，所有通知透過此函式建立。

    Args:
        recipient: 接收者 (User)
        notification_type: NotificationType 枚舉值
        title: 通知標題
        message: 通知內容（可選）
        deal: 相關交易（可選）
        shared_book: 相關書籍（可選）

    Returns:
        Notification: 建立的通知
    """
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        deal=deal,
        shared_book=shared_book,
    )


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
    if extension.status == "APPROVED":
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
    Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).update(is_read=True)
