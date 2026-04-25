"""
信用積分計算服務。

根據用戶的交易紀錄、評價分數和逾期次數計算信用積分和星等。
配置可在 Django settings 中覆寫。
"""

import math
from dataclasses import dataclass


from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Avg, Q
from django.utils import timezone

from deals.models import Deal, Rating

from accounts.models import TrustLevelConfig


# ============================================================================
# 積分配置（從 settings 讀取，提供預設值）
# ============================================================================


@dataclass
class ScoreConfig:
    """積分配置"""

    base_score: int  # 基礎分數
    per_deal: int  # 每筆完成交易加分
    per_overdue: int  # 每次逾期扣分（負數）
    per_rating_point: int  # 每評價分加分


def _get_score_config() -> ScoreConfig:
    """從 settings 取得積分配置"""
    config = getattr(settings, "TRUST_SCORE_CONFIG", None)
    if config is None:
        # 預設值（符合 BR-4.3）
        config = {
            "base_score": 0,
            "per_deal": 10,  # 完成交易 +10
            "per_overdue": -10,  # 逾期 -10
            "per_rating_point": 5,  # 每評價分 +5
        }
    return ScoreConfig(**config)


# ============================================================================
# 借閱限制配置（從 settings 讀取，提供預設值）
# ============================================================================


@dataclass
class BorrowingLimit:
    """借閱限制定義"""

    max_books: int | float
    max_days: int | float


def _get_borrowing_limits() -> dict[int, BorrowingLimit]:
    """從 settings 取得借閱限制配置"""
    config = getattr(settings, "BORROWING_LIMITS", None)
    if config is None:
        # 預設值
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
    """用戶信用計算所需的原始數據"""

    completed_deals: int
    overdue_count: int
    avg_rating: float


# ============================================================================
# 純計算函式（可獨立測試）
# ============================================================================


def compute_trust_score(metrics: UserMetrics) -> int:
    """
    純函式：根據用戶指標計算信用積分。

    公式：base_score + (交易數 × 10) - (逾期次數 × 10) + (評價平均分 × 5)

    Args:
        metrics: 用戶指標資料

    Returns:
        int: 信用積分
    """
    config = _get_score_config()
    score = (
        config.base_score
        + (metrics.completed_deals * config.per_deal)
        + (metrics.overdue_count * config.per_overdue)
        + (metrics.avg_rating * config.per_rating_point)
    )
    return max(0, int(score))  # 最低0分


def compute_trust_stars(score: int) -> int:
    """
    純函式：根據積分計算星等（1-5星）。

    公式：floor(sqrt(score))

    Args:
        score: 信用積分

    Returns:
        int: 星等（1-5星）
    """
    if score <= 0:
        return 1  # 最低1星
    stars = int(math.floor(math.sqrt(score)))
    return min(max(stars, 1), 5)  # 限制在1-5星


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

    # 取得逾期次數
    overdue_count = user.profile.overdue_count

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
        avg_integrity=Avg("friendliness_score"),
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
# 公開 API
# ============================================================================


def calculate_trust_score(user) -> int:
    """
    計算用戶信用積分（對外介面）。

    Args:
        user: 用戶實例

    Returns:
        int: 信用積分
    """
    metrics = get_user_metrics(user)
    return compute_trust_score(metrics)


def calculate_trust_stars(user) -> int:
    """
    計算用戶信用星等。

    Args:
        user: 用戶實例

    Returns:
        int: 星等（1-5星）
    """
    score = calculate_trust_score(user)
    return compute_trust_stars(score)


def calculate_trust_level(user) -> int:
    """
    計算用戶信用等級。

    映射關係：
    - 1星: Level 0 (新手)
    - 2星: Level 1 (一般)
    - 3星: Level 2 (可信)
    - 4-5星: Level 3 (優良)

    Args:
        user: 用戶實例

    Returns:
        int: 0-3 的信用等級
    """
    stars = calculate_trust_stars(user)
    if stars <= 1:
        return 0
    elif stars == 2:
        return 1
    elif stars == 3:
        return 2
    else:  # 4-5星
        return 3


def update_trust_score(user) -> int:
    """
    更新用戶信用積分和等級。

    Args:
        user: 用戶實例

    Returns:
        int: 新的信用積分
    """
    new_score = calculate_trust_score(user)

    # 更新資料庫
    user.profile.trust_score = new_score
    user.profile.save(update_fields=["trust_score", "updated_at"])

    # 同步信用等級 Group
    sync_trust_group(user)

    return new_score


def get_borrowing_limits(trust_level: int) -> dict:
    """
    根據信用等級取得借閱限制。

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


def get_upgrade_progress(user) -> dict:
    """
    計算用戶升級進度。

    Returns:
        dict: {
            'current_score': 當前積分,
            'current_stars': 當前星等,
            'current_level': 當前等級,
            'next_level': 下一等級 (None 表示已達最高),
            'next_stars': 下一星等,
            'progress': {
                'score': {'current': X, 'required': Y, 'remaining': Z, 'percentage': W},
            },
            'summary': '整體進度百分比',
            'requirements': ['需要 X 積分', ...],
        }
    """
    # 獲取當前積分和星等
    current_score = calculate_trust_score(user)
    current_stars = compute_trust_stars(current_score)
    if current_stars <= 1:
        current_level = 0
    elif current_stars == 2:
        current_level = 1
    elif current_stars == 3:
        current_level = 2
    else:  # 4-5星
        current_level = 3

    # 獲取下一級所需積分
    next_stars = current_stars + 1 if current_stars < 5 else None
    next_level = current_level + 1 if current_level < 3 else None

    result = {
        "current_score": current_score,
        "current_stars": current_stars,
        "current_level": current_level,
        "next_level": next_level,
        "next_stars": next_stars,
        "progress": {},
        "summary": 100 if next_stars is None else 0,
        "requirements": [],
    }

    # 已達最高星等
    if next_stars is None:
        result["requirements"].append("已達最高星等")
        return result

    # 計算所需積分
    required_score = next_stars**2
    remaining_score = max(0, required_score - current_score)

    # 計算進度百分比
    # 當前星等的起始積分
    current_star_base_score = current_stars**2 if current_stars > 1 else 0
    score_range = required_score - current_star_base_score
    score_earned_in_current_star = current_score - current_star_base_score

    percentage = (
        min(100, (score_earned_in_current_star / score_range) * 100)
        if score_range > 0
        else 0
    )

    result["progress"]["score"] = {
        "current": current_score,
        "required": required_score,
        "remaining": remaining_score,
        "percentage": round(percentage, 1),
    }

    result["summary"] = round(percentage, 1)
    result["requirements"].append(f"ݦAo {remaining_score} n]F {required_score} n^")

    return result


def sync_trust_group(user) -> None:
    """
    同步用戶的信用等級 Group。
    - 根據 trust_score 對照 TrustLevelConfig 找出目標等級
    - 升級：立即加入新 Group，清除 protected_since
    - 降級：若 protected_since 為 None 則設定為現在
           若已存在且已滿 26 週則降級，否則維持
    - 不碰負向 Group（restricted, banned）
    """

    profile = user.profile
    score = profile.trust_score

    # 1. 找出目標等級（從高到低找第一個符合的）
    configs = TrustLevelConfig.objects.filter(level__gte=0).order_by("-level")
    target_config = None
    for config in configs:
        if score >= config.min_score:
            target_config = config
            break

    if target_config is None:
        # 沒有符合的等級，使用 Lv0
        target_config = TrustLevelConfig.objects.filter(level=0).first()

    target_level = target_config.level
    target_group_name = f"trust_lv{target_level}"

    # 2. 找出用戶目前的正向 Group
    current_group = None
    for level in range(3, -1, -1):
        group_name = f"trust_lv{level}"
        if user.groups.filter(name=group_name).exists():
            current_group = group_name
            break

    # 3. 判斷升級或降級
    now = timezone.now()

    if current_group is None:
        # 目前沒有任何正向 Group，直接加入目標 Group
        target_group = Group.objects.get(name=target_group_name)
        user.groups.add(target_group)
        profile.trust_level_protected_since = None
        profile.save(update_fields=["trust_level_protected_since", "updated_at"])
        return

    current_level = int(current_group[-1])  # trust_lv3 -> 3

    if target_level > current_level:
        # 升級：立即切換，清除 protected_since
        current_group_obj = Group.objects.get(name=current_group)
        target_group_obj = Group.objects.get(name=target_group_name)
        user.groups.remove(current_group_obj)
        user.groups.add(target_group_obj)
        profile.trust_level_protected_since = None
        profile.save(update_fields=["trust_level_protected_since", "updated_at"])
    elif target_level < current_level:
        # 降級邏輯：檢查 protected_since
        if profile.trust_level_protected_since is None:
            # 第一次低於門檻，設定 protected_since
            profile.trust_level_protected_since = now
            profile.save(update_fields=["trust_level_protected_since", "updated_at"])
        else:
            # 已存在 protected_since，檢查是否已滿 26 週
            weeks_elapsed = (now - profile.trust_level_protected_since).days // 7
            if weeks_elapsed >= target_config.demotion_protection_weeks:
                # 已滿保護期，執行降級
                current_group_obj = Group.objects.get(name=current_group)
                target_group_obj = Group.objects.get(name=target_group_name)
                user.groups.remove(current_group_obj)
                user.groups.add(target_group_obj)
                profile.trust_level_protected_since = None
                profile.save(
                    update_fields=["trust_level_protected_since", "updated_at"]
                )
            # 否則維持現狀
