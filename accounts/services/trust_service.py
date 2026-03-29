"""
信用等級計算服務。

根據用戶的交易紀錄、評價分數和逾期次數計算信用等級。
"""

from dataclasses import dataclass

from django.db.models import Avg, Q

from deals.models import Deal, Rating


# ============================================================================
# 信用等級門檻配置
# ============================================================================


@dataclass
class TrustThreshold:
    """信用等級門檻定義。"""

    min_deals: int
    min_rating: float
    max_overdue: int


# 從高到低排序，計算時依序檢查
TRUST_THRESHOLDS: dict[int, TrustThreshold] = {
    3: TrustThreshold(min_deals=30, min_rating=4.5, max_overdue=0),
    2: TrustThreshold(min_deals=10, min_rating=4.0, max_overdue=1),
    1: TrustThreshold(min_deals=3, min_rating=0.0, max_overdue=2),
    0: TrustThreshold(min_deals=0, min_rating=0.0, max_overdue=float("inf")),
}


# ============================================================================
# 借閱限制配置
# ============================================================================


@dataclass
class BorrowingLimit:
    """借閱限制定義。"""

    max_books: int | float
    max_days: int | float


BORROWING_LIMITS: dict[int, BorrowingLimit] = {
    0: BorrowingLimit(max_books=1, max_days=30),
    1: BorrowingLimit(max_books=3, max_days=60),
    2: BorrowingLimit(max_books=5, max_days=90),
    3: BorrowingLimit(max_books=float("inf"), max_days=float("inf")),
}


# ============================================================================
# 資料結構
# ============================================================================


@dataclass
class UserMetrics:
    """用戶信用計算所需的原始數據。"""

    completed_deals: int
    overdue_count: int
    avg_rating: float


# ============================================================================
# 純計算函式（可獨立測試）
# ============================================================================


def compute_trust_level(metrics: UserMetrics) -> int:
    """
    純函式：根據用戶指標計算信用等級。

    規則（依序檢查，符合即返回）：
    - Level 3 (優良): 完成交易 ≥ 30 + 評價均分 ≥ 4.5 且 逾期 = 0
    - Level 2 (可信): 完成交易 ≥ 10 + 評價均分 ≥ 4 且 逾期 ≤ 1
    - Level 1 (一般): 完成交易 ≥ 3 且 逾期 ≤ 2
    - Level 0 (新手): 其餘情況

    Args:
        metrics: 用戶指標資料

    Returns:
        int: 0-3 的信用等級
    """
    for level in [3, 2, 1]:
        threshold = TRUST_THRESHOLDS[level]
        if (
            metrics.completed_deals >= threshold.min_deals
            and metrics.avg_rating >= threshold.min_rating
            and metrics.overdue_count <= threshold.max_overdue
        ):
            return level
    return 0


def compute_borrowing_limits(trust_level: int) -> BorrowingLimit:
    """
    純函式：根據信用等級計算借閱限制。

    Args:
        trust_level: 信用等級 (0-3)

    Returns:
        BorrowingLimit: 借閱限制
    """
    return BORROWING_LIMITS.get(trust_level, BORROWING_LIMITS[0])


# ============================================================================
# 資料取得函式（需要 DB）
# ============================================================================


def get_user_metrics(user) -> UserMetrics:
    """
    取得用戶信用計算所需的原始數據。

    Args:
        user: 用戶實例

    Returns:
        UserMetrics: 包含完成交易數、逾期次數、評價均分
    """
    # 取得完成交易數
    completed_deals = Deal.objects.filter(
        Q(applicant=user) | Q(responder=user), status=Deal.Status.DONE
    ).count()

    # 取得逾期次數（防禦性存取 profile）
    overdue_count = getattr(getattr(user, "profile", None), "overdue_count", 0)

    # 取得評價均分
    avg_rating = _calculate_avg_rating(user)

    return UserMetrics(
        completed_deals=completed_deals,
        overdue_count=overdue_count,
        avg_rating=avg_rating,
    )


def _calculate_avg_rating(user) -> float:
    """
    計算用戶評價均分。

    Args:
        user: 用戶實例

    Returns:
        float: 三項評分的平均值（0-5），無評價時返回 0
    """
    ratings = Rating.objects.filter(ratee=user)
    if not ratings.exists():
        return 0.0

    avg_scores = ratings.aggregate(
        avg_integrity=Avg("integrity_score"),
        avg_punctuality=Avg("punctuality_score"),
        avg_accuracy=Avg("accuracy_score"),
    )

    total = (
        (avg_scores["avg_integrity"] or 0)
        + (avg_scores["avg_punctuality"] or 0)
        + (avg_scores["avg_accuracy"] or 0)
    )
    return total / 3


# ============================================================================
# 公開 API（向後相容）
# ============================================================================


def calculate_trust_level(user) -> int:
    """
    計算用戶信用等級（對外介面）。

    此函式保持原有簽名，內部調用重構後的函式。

    Args:
        user: 用戶實例

    Returns:
        int: 0-3 的信用等級
    """
    metrics = get_user_metrics(user)
    return compute_trust_level(metrics)


def update_trust_level(user) -> int:
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


def get_borrowing_limits(trust_level: int) -> dict:
    """
    根據信用等級取得借閱限制。

    保持原有返回格式（dict）以向後相容。

    Args:
        trust_level: 信用等級 (0-3)

    Returns:
        dict: {'max_books': 最大借閱數量, 'max_days': 最大借閱天數}
    """
    limit = compute_borrowing_limits(trust_level)
    return {
        "max_books": limit.max_books,
        "max_days": limit.max_days,
    }


def initialize_existing_user(user) -> int:
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
