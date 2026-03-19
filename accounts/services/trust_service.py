"""
信用等級計算服務。

根據用戶的交易紀錄、評價分數和逾期次數計算信用等級。
"""

from django.db.models import Avg, Q
from deals.models import Deal, Rating


def calculate_trust_level(user):
    """
    計算用戶信用等級。

    規則：
    - Level 0 (新手): 完成交易 < 3 OR 逾期 ≥ 3 次
    - Level 1 (一般): 完成交易 ≥ 3 且 逾期 < 3 次
    - Level 2 (可信): 完成交易 ≥ 10 + 評價均分 ≥ 4 且 逾期 < 2 次
    - Level 3 (優良): 完成交易 ≥ 30 + 評價均分 ≥ 4.5 且 逾期 = 0

    Returns:
        int: 0-3 的信用等級
    """
    # 取得完成交易數
    completed_deals = Deal.objects.filter(
        Q(applicant=user) | Q(responder=user), status=Deal.Status.DONE
    ).count()

    # 取得逾期次數（從 UserProfile.overdue_count）
    overdue_count = user.profile.overdue_count

    # 取得評價均分
    ratings = Rating.objects.filter(ratee=user)
    if ratings.exists():
        avg_scores = ratings.aggregate(
            avg_integrity=Avg("integrity_score"),
            avg_punctuality=Avg("punctuality_score"),
            avg_accuracy=Avg("accuracy_score"),
        )
        avg_rating = (
            (avg_scores["avg_integrity"] or 0)
            + (avg_scores["avg_punctuality"] or 0)
            + (avg_scores["avg_accuracy"] or 0)
        ) / 3
    else:
        avg_rating = 0

    # 計算等級
    if completed_deals >= 30 and avg_rating >= 4.5 and overdue_count == 0:
        return 3
    elif completed_deals >= 10 and avg_rating >= 4 and overdue_count < 2:
        return 2
    elif completed_deals >= 3 and overdue_count < 3:
        return 1
    else:
        return 0


def update_trust_level(user):
    """
    更新用戶信用等級。

    Args:
        user: 用戶實例

    Returns:
        int: 新的信用等級
    """
    new_level = calculate_trust_level(user)
    user.profile.trust_level = new_level
    user.profile.save(update_fields=["trust_level"])
    return new_level


def get_borrowing_limits(trust_level):
    """
    根據信用等級取得借閱限制。

    Args:
        trust_level (int): 信用等級 (0-3)

    Returns:
        dict: {
            'max_books': 最大借閱數量,
            'max_days': 最大借閱天數
        }
    """
    limits = {
        0: {"max_books": 1, "max_days": 30},
        1: {"max_books": 3, "max_days": 60},
        2: {"max_books": 5, "max_days": 90},
        3: {"max_books": float("inf"), "max_days": float("inf")},
    }
    return limits.get(trust_level, limits[0])


def initialize_existing_user(user):
    """
    初始化現有用戶的信用等級。

    根據計劃，現有用戶上線時給 Level 1。

    Args:
        user: 用戶實例

    Returns:
        int: 初始化的信用等級 (1)
    """
    user.profile.trust_level = 1
    user.profile.save(update_fields=["trust_level"])
    return 1
