"""
他人顯示名稱（L-2）的單一規則。

對其他使用者顯示的名稱只能是暱稱；暱稱空白時一律為「會員#<user pk>」，
絕不回退到 email、帳號名稱（username 由 email 前綴產生）或 User.__str__。
模板 filter（user_tags.display_name）、DRF serializer、通知文字、匯出等
所有對外呈現他人名稱的地方都直接呼叫本模組。
"""

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist


def member_display_name(user_id: int | None, nickname: str | None = "") -> str:
    """暱稱優先，否則「會員#<user pk>」。"""
    nickname = (nickname or "").strip()
    if nickname:
        return nickname
    return f"會員#{user_id}"


def display_name_for(user: AbstractBaseUser | None) -> str:
    """User 的對外顯示名稱；profile 不存在時同樣回退「會員#<pk>」，None 回傳空字串。"""
    if user is None:
        return ""
    try:
        nickname = user.profile.nickname  # pyright: ignore[reportAttributeAccessIssue]
    except ObjectDoesNotExist:
        nickname = ""
    return member_display_name(user.pk, nickname)
