"""資料匯出服務

處理用戶個人資料匯出功能，包含頻率限制。
支援 JSON 和 CSV 格式匯出。
"""

import csv
import io
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from books.models import SharedBook
from deals.models import Deal, Rating


EXPORT_LIMIT_KEY_PREFIX = "export_limit"
EXPORT_LIMIT_PER_DAY = 3
EXPORT_LIMIT_TTL = 86400  # 24 小時


class ExportLimitExceededError(Exception):
    """匯出次數超過每日限制"""

    pass


@transaction.atomic
def export_user_data(user, format="json"):
    """匯出用戶個人資料

    Args:
        user: 用戶實例
        format: 匯出格式 ('json' 或 'csv')

    Returns:
        dict 或 str: 用戶資料（JSON 格式返回 dict，CSV 格式返回字串）

    Raises:
        ExportLimitExceededError: 超過每日匯出次數限制
        ValueError: 無效的格式參數
    """
    if format not in ("json", "csv"):
        raise ValueError(f"無效的匯出格式: {format}，必須是 'json' 或 'csv'")

    # 檢查頻率限制
    check_export_limit(user)

    # 收集用戶資料
    data = collect_user_data(user)

    # 增加匯出次數
    increment_export_count(user)

    if format == "csv":
        return convert_to_csv(data, user)

    return data


def check_export_limit(user):
    """檢查用戶是否超過每日匯出次數限制

    Args:
        user: 用戶實例

    Raises:
        ExportLimitExceededError: 超過每日限制
    """
    cache_key = f"{EXPORT_LIMIT_KEY_PREFIX}_{user.id}"
    count = cache.get(cache_key, 0)

    if count >= EXPORT_LIMIT_PER_DAY:
        raise ExportLimitExceededError(
            f"每日最多可匯出 {EXPORT_LIMIT_PER_DAY} 次，請明天再試"
        )


def increment_export_count(user):
    """增加用戶匯出次數

    Args:
        user: 用戶實例
    """
    cache_key = f"{EXPORT_LIMIT_KEY_PREFIX}_{user.id}"
    count = cache.get(cache_key, 0)
    cache.set(cache_key, count + 1, EXPORT_LIMIT_TTL)


def collect_user_data(user):
    """收集用戶資料

    根據 3.15 需求規格：
    - 匯出範圍：交易評價歷史、活動統計
    - 不在匯出範圍：書籍資料、書況照片、交易留言內容

    Args:
        user: 用戶實例

    Returns:
        dict: 用戶資料
    """
    # 獲取用戶 profile
    profile = getattr(user, "profile", None)

    # 收集各類資料（依 3.15 需求，不包含 books_contributed）
    user_profile_data = collect_user_profile(user, profile)
    activity_stats = collect_activity_stats(user)
    ratings_received = collect_ratings_received(user)

    return {
        "exported_at": timezone.now().isoformat(),
        "user_profile": user_profile_data,
        "activity_stats": activity_stats,
        "ratings_received": ratings_received,
    }


def collect_activity_stats(user):
    """收集用戶活動統計

    根據 3.15 需求，活動統計包含：
    - 貢獻書籍總數
    - 成功借入次數
    - 成功借出次數
    - 逾期次數

    Args:
        user: 用戶實例

    Returns:
        dict: 活動統計資料
    """

    # 貢獻書籍總數（用戶擁有的書籍數量）
    books_contributed_count = SharedBook.objects.filter(owner=user).count()

    # 成功借入次數（作為申請者完成的交易）
    borrow_count = Deal.objects.filter(
        applicant=user,
        status=Deal.Status.DONE,
    ).count()

    # 成功借出次數（作為回應者完成的交易）
    lend_count = Deal.objects.filter(
        responder=user,
        status=Deal.Status.DONE,
    ).count()

    # 逾期次數（從 profile 獲取）
    profile = getattr(user, "profile", None)
    overdue_count = profile.overdue_count if profile else 0

    return {
        "books_contributed_count": books_contributed_count,
        "successful_borrows": borrow_count,
        "successful_lends": lend_count,
        "overdue_count": overdue_count,
    }


def collect_user_profile(user, profile):
    """收集用戶基本資料

    Args:
        user: 用戶實例
        profile: 用戶 profile 實例

    Returns:
        dict: 用戶基本資料
    """
    return {
        "email": user.email,
        "nickname": profile.nickname if profile else None,
        "trust_level": profile.trust_level if profile else 1,
        "successful_returns": profile.successful_returns if profile else 0,
        "overdue_count": profile.overdue_count if profile else 0,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def collect_books_contributed(user):
    """收集用戶貢獻的書籍

    Args:
        user: 用戶實例

    Returns:
        list: 書籍列表
    """
    books = SharedBook.objects.filter(owner=user).select_related(
        "official_book", "keeper"
    )

    return [
        {
            "id": str(book.id),
            "title": book.official_book.title if book.official_book else None,
            "isbn": book.official_book.isbn if book.official_book else None,
            "author": book.official_book.author if book.official_book else None,
            "publisher": book.official_book.publisher if book.official_book else None,
            "status": book.get_status_display(),
            "transferability": book.get_transferability_display(),
            "condition_description": book.condition_description,
            "loan_duration_days": book.loan_duration_days,
            "extend_duration_days": book.extend_duration_days,
            "keeper_email": book.keeper.email if book.keeper else None,
            "listed_at": book.listed_at.isoformat() if book.listed_at else None,
            "created_at": book.created_at.isoformat() if book.created_at else None,
        }
        for book in books
    ]


def collect_deals_history(user):
    """收集用戶交易歷史

    Args:
        user: 用戶實例

    Returns:
        list: 交易歷史列表
    """
    from django.db.models import Q

    deals = Deal.objects.filter(Q(applicant=user) | Q(responder=user)).select_related(
        "shared_book__official_book", "applicant", "responder"
    )

    return [
        {
            "id": str(deal.id),
            "deal_type": deal.get_deal_type_display(),
            "status": deal.get_status_display(),
            "book_title": (
                deal.shared_book.official_book.title
                if deal.shared_book and deal.shared_book.official_book
                else None
            ),
            "applicant_email": deal.applicant.email if deal.applicant else None,
            "responder_email": deal.responder.email if deal.responder else None,
            "meeting_location": deal.meeting_location,
            "meeting_time": deal.meeting_time.isoformat()
            if deal.meeting_time
            else None,
            "due_date": deal.due_date.isoformat() if deal.due_date else None,
            "created_at": deal.created_at.isoformat() if deal.created_at else None,
            "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
        }
        for deal in deals
    ]


def collect_ratings_received(user):
    """收集用戶收到的評價

    Args:
        user: 用戶實例

    Returns:
        list: 評價列表
    """
    ratings = Rating.objects.filter(ratee=user).select_related(
        "rater", "deal__shared_book__official_book"
    )

    return [
        {
            "id": str(rating.id),
            "rater_email": rating.rater.email if rating.rater else None,
            "friendliness_score": rating.friendliness_score,
            "punctuality_score": rating.punctuality_score,
            "accuracy_score": rating.accuracy_score,
            "average_score": rating.average_score,
            "comment": rating.comment,
            "book_title": (
                rating.deal.shared_book.official_book.title
                if rating.deal
                and rating.deal.shared_book
                and rating.deal.shared_book.official_book
                else None
            ),
            "created_at": rating.created_at.isoformat() if rating.created_at else None,
        }
        for rating in ratings
    ]


def get_remaining_exports(user):
    """取得用戶今日剩餘匯出次數

    Args:
        user: 用戶實例

    Returns:
        int: 剩餘匯出次數
    """
    cache_key = f"{EXPORT_LIMIT_KEY_PREFIX}_{user.id}"
    count = cache.get(cache_key, 0)
    return max(0, EXPORT_LIMIT_PER_DAY - count)


def convert_to_csv(data, user):
    """將用戶資料轉換為 CSV 格式

    CSV 包含三個部分：
    1. 用戶基本資訊
    2. 交易評價統計
    3. 活動統計

    Args:
        data: 收集的用戶資料
        user: 用戶實例

    Returns:
        str: CSV 格式的字串
    """
    output = io.StringIO()
    writer = csv.writer(output, encoding="utf-8")

    # 標題行
    writer.writerow(["Exbooks 個人資料匯出"])
    writer.writerow([f"匯出時間: {data['exported_at'][:10]}"])
    writer.writerow([])

    # 1. 用戶基本資訊
    profile_data = data["user_profile"]
    writer.writerow(["用戶基本資訊"])
    writer.writerow(["項目", "內容"])
    writer.writerow(["電子信箱", profile_data.get("email", "")])
    writer.writerow(["暱稱", profile_data.get("nickname", "")])
    writer.writerow(["信用等級", f"等級 {profile_data.get('trust_level', 1)}"])
    writer.writerow(["成功還書次數", profile_data.get("successful_returns", 0)])
    writer.writerow(["逾期次數", profile_data.get("overdue_count", 0)])
    writer.writerow(["加入時間", profile_data.get("date_joined", "")[:10]])
    writer.writerow([])

    # 2. 活動統計
    activity_stats = data["activity_stats"]
    writer.writerow(["活動統計"])
    writer.writerow(["項目", "數量"])
    writer.writerow(["貢獻書籍總數", activity_stats.get("books_contributed_count", 0)])
    writer.writerow(["成功借入次數", activity_stats.get("successful_borrows", 0)])
    writer.writerow(["成功借出次數", activity_stats.get("successful_lends", 0)])
    writer.writerow(["逾期次數", activity_stats.get("overdue_count", 0)])
    writer.writerow([])

    # 3. 收到的評價統計
    ratings = data["ratings_received"]
    writer.writerow(["評價統計"])
    writer.writerow(["項目", "內容"])
    writer.writerow(["收到評價數", len(ratings)])

    if ratings:
        # 計算平均分數
        scores = [r.get("average_score", 0) for r in ratings if r.get("average_score")]
        if scores:
            avg = sum(scores) / len(scores)
            writer.writerow(["平均評分", f"{avg:.1f}"])

    writer.writerow([])

    # 4. 評價詳情（若有評價）
    if ratings:
        writer.writerow(["評價詳情"])
        writer.writerow(
            [
                "日期",
                "評分人",
                "書籍名稱",
                "友善度",
                "準時度",
                "正確度",
                "平均分數",
                "評論",
            ]
        )
        for rating in ratings:
            writer.writerow(
                [
                    rating.get("created_at", "")[:10],
                    rating.get("rater_email", ""),
                    rating.get("book_title", ""),
                    rating.get("integrity_score", ""),
                    rating.get("punctuality_score", ""),
                    rating.get("accuracy_score", ""),
                    rating.get("average_score", ""),
                    rating.get("comment", ""),
                ]
            )

    return output.getvalue()
