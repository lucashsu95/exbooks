"""
consent 氣泡的人類可讀描述（繁體中文）。

取代把 ``request_renewal(deal_id=<uuid>, days=7)`` 原樣丟給使用者。
能便宜查到書名時帶上書名；查不到（或交易不屬於此使用者）就用通用描述，
絕不拋錯——描述只是顯示用，不能擋住 consent 流程。
"""

import logging
import uuid
from typing import Any, Callable, Dict

from django.db.models import Q

logger = logging.getLogger(__name__)

_GENERIC = "執行這項操作"


def _renewal(user, args: Dict[str, Any]) -> str:
    try:
        days = int(args.get("days", 7))
    except (TypeError, ValueError):
        days = 7
    title = _deal_book_title(user, args.get("deal_id"))
    if title:
        return f"申請延長《{title}》的借期 {days} 天"
    return f"申請延長借期 {days} 天"


def _deal_book_title(user, deal_id) -> str | None:
    try:
        uuid.UUID(str(deal_id))
    except (TypeError, ValueError):
        return None
    from deals.models import Deal

    try:
        deal = (
            Deal.objects.select_related("shared_book__official_book")
            .filter(Q(applicant=user) | Q(responder=user), pk=deal_id)
            .first()
        )
    except Exception:
        logger.warning("consent label lookup failed", exc_info=True)
        return None
    if deal is None:
        return None
    return deal.shared_book.official_book.title


_DESCRIBERS: Dict[str, Callable[[Any, Dict[str, Any]], str]] = {
    "request_renewal": _renewal,
}


def describe_consent(user, tool: str, args: Dict[str, Any]) -> str:
    """回傳「確認要＿＿嗎？」中間那段的描述。"""
    describer = _DESCRIBERS.get(tool)
    if describer is None:
        return _GENERIC
    try:
        return describer(user, args)
    except Exception:
        logger.warning("consent label failed", extra={"tool": tool}, exc_info=True)
        return _GENERIC
