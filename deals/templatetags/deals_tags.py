from django import template

register = template.Library()

NOTIFICATION_ICONS = {
    "DEAL_REQUESTED": "swap_horiz",
    "DEAL_RESPONDED": "check_circle",
    "DEAL_CANCELLED": "cancel",
    "DEAL_MEETED": "handshake",
    "BOOK_DUE_SOON": "schedule",
    "BOOK_OVERDUE": "warning",
    "BOOK_AVAILABLE": "favorite",
    "EXTEND_REQUESTED": "more_time",
    "EXTEND_APPROVED": "check_circle",
    "EXTEND_REJECTED": "cancel",
    "APPEAL_SUBMITTED": "campaign",
    "APPEAL_RESOLVED": "task_alt",
    "RATING_CREATED": "star",
    "VIOLATION_CREATED": "gavel",
    "APPEAL_STATUS_UPDATED": "info",
}


@register.filter(name="notification_icon")
def notification_icon(notification_type):
    """由通知類型回傳對應的 material symbol 名稱。"""
    return NOTIFICATION_ICONS.get(notification_type, "notifications")
