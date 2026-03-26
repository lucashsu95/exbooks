from datetime import date, timedelta


from deals.models import Deal


def get_overdue_books(days=7):
    """
    取得逾期 N 天以上的書籍。

    Args:
        days: 逾期天數門檻

    Returns:
        QuerySet: 逾期書籍列表
    """
    today = date.today()
    threshold = today - timedelta(days=days)

    # 找出借閱中（MEETED 狀態）且到期的交易
    overdue_deals = Deal.objects.filter(
        status=Deal.Status.MEETED,  # 已面交但未完成評價
        due_date__lt=threshold,
        due_date__isnull=False,
    ).select_related("shared_book", "applicant")

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
    today = date.today()
    overdue_days = (today - deal.due_date).days if deal.due_date else 0

    # 取得暱稱，若無則使用 Email 前綴
    nickname = deal.applicant.profile.nickname
    if not nickname:
        nickname = deal.applicant.email.split("@")[0]

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

    today = date.today()
    overdue_days = (today - deal.due_date).days

    if overdue_days < 3:
        return "none"
    elif overdue_days < 7:
        return "warning"
    elif overdue_days < 14:
        return "public"
    else:
        return "severe"
