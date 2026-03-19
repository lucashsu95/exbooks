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
        average_integrity=Avg("integrity_score"),
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
        }
    """
    # 貢獻書籍數（owner）
    books_contributed = SharedBook.objects.filter(owner=user).count()

    # 借閱次數（作為申請者完成交易）
    books_borrowed = Deal.objects.filter(
        applicant=user,
        status=Deal.Status.DONE,
    ).count()

    # 出借次數（作為回應者完成交易）
    books_lent = Deal.objects.filter(
        responder=user,
        status=Deal.Status.DONE,
    ).count()

    # 完成交易總數
    deals_completed = Deal.objects.filter(
        Q(applicant=user) | Q(responder=user),
        status=Deal.Status.DONE,
    ).count()

    # 目前持有書籍數（keeper）
    books_holding = SharedBook.objects.filter(keeper=user).count()

    return {
        "books_contributed": books_contributed,
        "books_borrowed": books_borrowed,
        "books_lent": books_lent,
        "deals_completed": deals_completed,
        "books_holding": books_holding,
    }
