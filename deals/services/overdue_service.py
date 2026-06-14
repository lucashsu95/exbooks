import logging

from django.utils import timezone
from datetime import timedelta


from deals.models import Deal

logger = logging.getLogger(__name__)


def get_overdue_books(days=7):
    """
    取得逾期 N 天以上的書籍。

    Args:
        days: 逾期天數門檻

    Returns:
        QuerySet: 逾期書籍列表
    """
    today = timezone.now().date()
    threshold = today - timedelta(days=days)

    # 找出借閱中（MEETED 狀態）且到期的交易
    overdue_deals = Deal.objects.filter(
        status=Deal.Status.MEETED,  # 已面交但未完成評價
        due_date__lt=threshold,
        due_date__isnull=False,
    ).select_related("shared_book", "applicant")

    logger.debug(
        "overdue books queried",
        extra={"days": days, "count": overdue_deals.count()},
    )
    return overdue_deals


def get_public_overdue_info(deal):
    """
    取得可公開的逾期資訊。

    Args:
        deal: Deal 實例

    Returns:
        dict: {
            'nickname': 持有人暱稱,
            'book_title': 書名,
            'overdue_days': 逾期天數,
            'is_severe': 是否嚴重逾期（≥14天）
        }
    """
    today = timezone.now().date()
    overdue_days = (today - deal.due_date).days if deal.due_date else 0

    # 取得暱稱，若無則使用 Email 前綴
    nickname = deal.applicant.profile.nickname
    if not nickname:
        nickname = deal.applicant.email.split("@")[0]

    logger.debug(
        "public overdue info",
        extra={
            "deal_id": deal.id,
            "overdue_days": overdue_days,
        },
    )
    return {
        "nickname": nickname,
        "book_title": deal.shared_book.official_book.title,
        "overdue_days": overdue_days,
        "is_severe": overdue_days >= 14,
    }


def get_overdue_status(deal):
    """
    取得逾期狀態。

    Returns:
        str: 'none' | 'warning' | 'public' | 'severe'
    """
    if not deal.due_date:
        return "none"

    today = timezone.now().date()
    overdue_days = (today - deal.due_date).days

    if overdue_days < 3:
        return "none"
    elif overdue_days < 7:
        return "warning"
    elif overdue_days < 14:
        return "public"
    else:
        return "severe"


def batch_process_due_books() -> dict:
    """處理所有已到期借閱交易，回傳處理結果摘要。"""
    from deals.services import deal_service

    today = timezone.now().date()
    overdue_deals = Deal.objects.filter(
        status=Deal.Status.MEETED,
        due_date__lte=today,
        shared_book__status="O",
    ).select_related("shared_book__official_book", "applicant", "responder")

    processed, errors = 0, 0
    for deal in overdue_deals:
        try:
            deal_service.process_book_due(deal)
            processed += 1
        except Exception:
            errors += 1
    logger.info(
        "batch_process_due_books",
        extra={
            "processed": processed,
            "errors": errors,
        },
    )
    return {"processed": processed, "errors": errors}
