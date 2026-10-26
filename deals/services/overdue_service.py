import logging

from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from books.models import SharedBook
from deals.models import Deal

logger = logging.getLogger(__name__)


# ============================================================================
# BR-12 到期查詢骨架（全部到期查詢共用的單一來源）
# ============================================================================


def meeted_deals(
    due_date_q: Q,
    *,
    book_must_be_occupied: bool = False,
    applicant=None,
):
    """
    BR-12 骨架查詢：MEETED 狀態 + 日期條件（due_date_q）。

    各 caller 只傳自己的差異：
    - due_date_q: 日期語意（lt 門檻 / lte 今日 / 等於某天 / 區間）
    - book_must_be_occupied: 只算書在 O（借閱中）的交易
    - applicant: 個人視角

    回傳 queryset；caller 自行鏈接 select_related / order_by。
    """
    qs = Deal.objects.filter(status=Deal.Status.MEETED, due_date__isnull=False).filter(
        due_date_q
    )
    if book_must_be_occupied:
        qs = qs.filter(shared_book__status=SharedBook.Status.OCCUPIED)
    if applicant is not None:
        qs = qs.filter(applicant=applicant)
    return qs


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
    overdue_deals = meeted_deals(
        Q(due_date__lt=threshold)
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


def is_overdue(deal) -> bool:
    """交易是否已過到期日（含到期日的交易類型才適用）。"""
    if not deal.due_date:
        return False
    if deal.deal_type not in (
        Deal.DealType.LOAN,
        Deal.DealType.RESTORE,
        Deal.DealType.REGRESS,
    ):
        return False
    return timezone.now().date() > deal.due_date


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
    overdue_deals = meeted_deals(
        Q(due_date__lte=today), book_must_be_occupied=True
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


def get_due_soon_deals(user, days=7):
    """
    借閱者視角的「即將到期」交易。

    條件：applicant = user、MEETED（已面交借閱中）、
    now < due_date <= now + days。

    Args:
        user: 借閱者
        days: 提醒窗口（天）

    Returns:
        list[dict]: [{'deal', 'days_left'}]，依 due_date 排序
    """
    now = timezone.now()
    deadline = now + timedelta(days=days)

    due_soon_deals = (
        meeted_deals(
            Q(due_date__gt=now) & Q(due_date__lte=deadline), applicant=user
        )
        .select_related("shared_book__official_book", "responder__profile")
        .order_by("due_date")
    )

    result = []
    for deal in due_soon_deals:
        days_left = (deal.due_date - now.date()).days
        result.append({"deal": deal, "days_left": days_left})

    logger.debug(
        "due soon deals queried",
        extra={"user_id": user.pk, "days": days, "count": len(result)},
    )
    return result
