"""
用戶統計服務。

提供用戶評價摘要、活動統計等聚合計算功能。
根據 DR-5，信用積分不獨立建表，透過聚合計算。
"""

from django.db.models import Avg, Count, Q

from books.models import SharedBook
from deals.models import Deal, Rating


def get_user_rating_summary(user):
    """
    計算用戶評價摘要。

    Args:
        user: 用戶實例

    Returns:
        dict: {
            'total_ratings': 總評價數,
            'average_integrity': 誠信平均分,
            'average_punctuality': 準時平均分,
            'average_accuracy': 書況準確度平均分,
            'overall_average': 整體平均分,
        }
    """
    ratings = Rating.objects.filter(ratee=user)

    result = ratings.aggregate(
        total_ratings=Count("id"),
        average_integrity=Avg("friendliness_score"),
        average_punctuality=Avg("punctuality_score"),
        average_accuracy=Avg("accuracy_score"),
    )

    # 計算整體平均
    if result["total_ratings"] > 0:
        result["overall_average"] = (
            (result["average_integrity"] or 0)
            + (result["average_punctuality"] or 0)
            + (result["average_accuracy"] or 0)
        ) / 3
    else:
        result["overall_average"] = None

    return result


def get_user_rating_history(user, page=1, per_page=10):
    """
    取得用戶評價歷史（分頁）。

    Args:
        user: 用戶實例
        page: 頁碼
        per_page: 每頁筆數

    Returns:
        Page: 分頁物件
    """
    from django.core.paginator import Paginator

    ratings = (
        Rating.objects.filter(ratee=user)
        .select_related("rater", "deal__shared_book__official_book")
        .order_by("-created_at")
    )

    paginator = Paginator(ratings, per_page)
    return paginator.get_page(page)


def get_user_activity_stats(user):
    """
    計算用戶活動統計。

    Args:
        user: 用戶實例

    Returns:
        dict: {
            'books_contributed': 貢獻書籍數,
            'books_borrowed': 借閱次數,
            'books_lent': 出借次數,
            'deals_completed': 完成交易總數,
            'books_holding': 目前持有書籍數,
            'rejected_lending_count': 拒絕借出次數,
            'contributed_books_status': 貢獻書籍狀態統計,
            'held_books_status': 持有他人書籍狀態統計,
        }
    """
    return {
        "books_contributed": get_contributed_books_count(user),
        "books_borrowed": Deal.objects.filter(
            applicant=user,
            status=Deal.Status.DONE,
        ).count(),
        "books_lent": Deal.objects.filter(
            responder=user,
            status=Deal.Status.DONE,
        ).count(),
        "deals_completed": get_completed_deals_count(user),
        "books_holding": SharedBook.objects.filter(keeper=user).count(),
        "rejected_lending_count": Deal.objects.filter(
            responder=user,
            status=Deal.Status.CANCELLED,
        ).count(),
        "contributed_books_status": list(
            SharedBook.objects.filter(owner=user)
            .values("status")
            .annotate(count=Count("id"))
        ),
        "held_books_status": list(
            SharedBook.objects.filter(keeper=user)
            .exclude(owner=user)
            .values("status")
            .annotate(count=Count("id"))
        ),
    }


def get_contributed_books_count(user):
    """
    取得用戶貢獻的書籍數量。
    """
    return SharedBook.objects.filter(owner=user).count()


def get_completed_deals_count(user):
    """
    取得用戶完成的交易數量。
    """
    return Deal.objects.filter(
        Q(applicant=user) | Q(responder=user),
        status=Deal.Status.DONE,
    ).count()


def get_rating_stats(user):
    """
    取得用戶評價統計。
    """
    summary = get_user_rating_summary(user)

    # 取得給出的評價數
    ratings_given = Rating.objects.filter(rater=user).count()

    # 計算各項詳細統計
    return {
        "average_rating": summary.get("overall_average") or 0.0,
        "ratings_given": ratings_given,
        "ratings_received": summary.get("total_ratings") or 0,
        "details": summary,
    }


def get_overdue_count(user):
    """
    取得用戶的逾期次數。

    Args:
        user: 用戶實例

    Returns:
        int: 逾期次數
    """
    return user.profile.overdue_count


def get_violation_count(user):
    """
    取得用戶的生效違規次數。

    計算用戶收到的所有已生效（is_active=True）違規處分次數，
    包括警告、暫時停權、永久停權。
    已解除（is_active=False）的處分不計入。

    Args:
        user: 用戶實例

    Returns:
        int: 生效違規次數
    """
    from accounts.models import Violation

    return Violation.objects.filter(user=user, is_active=True).count()
