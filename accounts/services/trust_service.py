"""
信用等級計算服務。

根據用戶的交易紀錄、評價分數和逾期次數計算信用等級。
配置可在 Django settings 中覆寫。
"""

from dataclasses import dataclass

from django.conf import settings
from django.db.models import Avg, Q

from deals.models import Deal, Rating


# ============================================================================
# 信用等級門檻配置（從 settings 讀取，提供預設值）
# ============================================================================


@dataclass
class TrustThreshold:
    """信用等級門檻定義。"""

    min_deals: int
    min_rating: float
    max_overdue: int | float


def _get_trust_thresholds() -> dict[int, TrustThreshold]:
    """從 settings 取得信用等級門檻配置。"""
    config = getattr(settings, "TRUST_THRESHOLDS", None)
    if config is None:
        # 預設值（向後相容）
        config = {
            3: {"min_deals": 30, "min_rating": 4.5, "max_overdue": 0},
            2: {"min_deals": 10, "min_rating": 4.0, "max_overdue": 1},
            1: {"min_deals": 3, "min_rating": 0.0, "max_overdue": 2},
            0: {"min_deals": 0, "min_rating": 0.0, "max_overdue": float("inf")},
        }
    return {k: TrustThreshold(**v) for k, v in config.items()}


# ============================================================================
# 借閱限制配置（從 settings 讀取，提供預設值）
# ============================================================================


@dataclass
class BorrowingLimit:
    """借閱限制定義。"""

    max_books: int | float
    max_days: int | float


def _get_borrowing_limits() -> dict[int, BorrowingLimit]:
    """從 settings 取得借閱限制配置。"""
    config = getattr(settings, "BORROWING_LIMITS", None)
    if config is None:
        # 預設值（向後相容）
        config = {
            0: {"max_books": 1, "max_days": 30},
            1: {"max_books": 3, "max_days": 60},
            2: {"max_books": 5, "max_days": 90},
            3: {"max_books": float("inf"), "max_days": float("inf")},
        }
    return {k: BorrowingLimit(**v) for k, v in config.items()}


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
    thresholds = _get_trust_thresholds()
    for level in [3, 2, 1]:
        threshold = thresholds[level]
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
    limits = _get_borrowing_limits()
    return limits.get(trust_level, limits[0])


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


def get_upgrade_progress(user) -> dict:
    """
    計算用戶升級進度。

    Returns:
        dict: {
            'current_level': 當前等級,
            'next_level': 下一等級 (None 表示已達最高),
            'progress': {
                'deals': {'current': X, 'required': Y, 'percentage': Z},
                'rating': {'current': X, 'required': Y, 'percentage': Z},
                'overdue': {'current': X, 'max_allowed': Y, 'ok': True/False},
            },
            'summary': '整體進度百分比',
            'requirements': ['需要完成 X 筆交易', '評價均分需達 Y', ...],
        }
    """
    metrics = get_user_metrics(user)
    current_level = compute_trust_level(metrics)
    thresholds = _get_trust_thresholds()

    # 找出下一個等級
    next_level = current_level + 1 if current_level < 3 else None

    result = {
        "current_level": current_level,
        "next_level": next_level,
        "progress": {},
        "summary": 100 if next_level is None else 0,
        "requirements": [],
    }

    # 已達最高等級
    if next_level is None:
        result["requirements"].append("已達最高等級")
        return result

    # 取得下一等級門檻
    threshold = thresholds[next_level]

    # 計算交易進度
    deals_progress = min(100, (metrics.completed_deals / threshold.min_deals) * 100)
    result["progress"]["deals"] = {
        "current": metrics.completed_deals,
        "required": threshold.min_deals,
        "percentage": round(deals_progress, 1),
    }

    # 計算評價進度（假設最高 5 分）
    rating_progress = 0
    if threshold.min_rating > 0:
        rating_progress = min(100, (metrics.avg_rating / threshold.min_rating) * 100)
    result["progress"]["rating"] = {
        "current": round(metrics.avg_rating, 2),
        "required": threshold.min_rating,
        "percentage": round(rating_progress, 1),
    }

    # 計算逾期狀態
    overdue_ok = metrics.overdue_count <= threshold.max_overdue
    result["progress"]["overdue"] = {
        "current": metrics.overdue_count,
        "max_allowed": int(threshold.max_overdue),
        "ok": overdue_ok,
    }

    # 計算整體進度（取三項最小值）
    progress_values = [deals_progress, rating_progress]
    if not overdue_ok:
        progress_values.append(0)  # 逾期超標則進度為 0
    result["summary"] = round(min(progress_values), 1)

    # 生成升級條件說明
    remaining_deals = max(0, threshold.min_deals - metrics.completed_deals)
    if remaining_deals > 0:
        result["requirements"].append(
            f"需再完成 {remaining_deals} 筆交易（達 {threshold.min_deals} 筆）"
        )
    else:
        result["requirements"].append(f"✓ 已完成 {threshold.min_deals} 筆交易")

    if metrics.avg_rating < threshold.min_rating:
        gap = round(threshold.min_rating - metrics.avg_rating, 1)
        result["requirements"].append(
            f"評價均分需提升 {gap} 分（達 {threshold.min_rating} 分）"
        )
    else:
        result["requirements"].append(f"✓ 評價均分已達 {threshold.min_rating} 分")

    if overdue_ok:
        result["requirements"].append(
            f"✓ 逾期次數未超過 {int(threshold.max_overdue)} 次"
        )
    else:
        excess = metrics.overdue_count - int(threshold.max_overdue)
        result["requirements"].append(
            f"逾期次數超標 {excess} 次（需 ≤ {int(threshold.max_overdue)} 次）"
        )

    return result
