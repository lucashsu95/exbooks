"""
使用者對敏感 tool 操作的確認／取消（consent 決策的業務規則）。

規則：
- token 一律先吃掉（one-shot）：任何失敗都不可重試，使用者需重新詢問。
- transcript 只在全部校驗通過後才寫——token 過期／不存在、action 與 token
  不符、或 action 不是已註冊的 USER_CONFIRM tool 一律 NOT_FOUND 且不寫。
- 確認與取消都記進對話紀錄（下一 turn model 知道結果，不會重複提出），
  整則紀錄視為一筆 untrusted payload 統一 fence＋escaped。
- 只執行 server-side 存檔的 args；client 送的 args 一律不採用。
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .consent_store import ConsentStore
from .conversation_cache import ConversationCache
from .fencing import wrap_persisted
from .tool_registry import ConsentRequirement, ToolRegistry

logger = logging.getLogger(__name__)


class ConsentStatus(str, Enum):
    SUCCESS = "success"
    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"
    FAILED = "failed"


@dataclass(frozen=True)
class ConsentResult:
    status: ConsentStatus
    result: Optional[Any] = None


def resolve_consent(user, action: str, token: Optional[str], confirmed: bool) -> ConsentResult:
    log_extra = {"user_id": user.pk, "action": action, "confirmed": confirmed}

    payload = ConsentStore.consume(user.id, token)
    if payload is None:
        logger.warning("consent token invalid", extra=log_extra)
        return ConsentResult(ConsentStatus.NOT_FOUND)
    if payload["tool"] != action:
        logger.warning("consent token/action mismatch", extra=log_extra)
        return ConsentResult(ConsentStatus.NOT_FOUND)

    tool_def = ToolRegistry.get_tool(action)
    if tool_def is None or tool_def.consent != ConsentRequirement.USER_CONFIRM:
        logger.warning("consent action not found", extra=log_extra)
        return ConsentResult(ConsentStatus.NOT_FOUND)

    # 存檔 args 在建立時（orchestrator）已依 signature 過濾
    arguments = payload["args"]

    if not confirmed:
        ConversationCache.add_message(
            user.id,
            "system",
            wrap_persisted(f"User declined to execute action: {action} with args {arguments}."),
        )
        logger.info("consent cancelled", extra=log_extra)
        return ConsentResult(ConsentStatus.CANCELLED)

    try:
        # 帶著使用者身份執行（ownership 檢查在 tool 內）
        result = tool_def.func(user=user, **arguments)
    except Exception:
        # tool 例外訊息不回 client（可能含 signature／內部細節），只進 log
        logger.exception("consent execution failed", extra=log_extra)
        return ConsentResult(ConsentStatus.FAILED)

    ConversationCache.add_message(
        user.id,
        "system",
        wrap_persisted(
            f"User confirmed and executed action: {action} with args {arguments}. "
            f"Result: {result}"
        ),
    )
    logger.info("consent executed", extra=log_extra)
    return ConsentResult(ConsentStatus.SUCCESS, result=result)
