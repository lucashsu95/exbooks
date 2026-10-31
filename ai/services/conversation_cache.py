import logging
from typing import List, Dict, Any
from django.core.cache import cache

from .fencing import is_fenced_record

logger = logging.getLogger(__name__)


def _is_turn_start(msg: Dict[str, str]) -> bool:
    return msg.get("role") == "user" and not is_fenced_record(msg.get("content", ""))


class ConversationCache:
    """
    Manages user conversation history in Redis (or fallback cache).

    Format in cache: List of dicts [{"role": "user", "content": "..."}, ...]
    TTL: 1 hour (3600 seconds)
    Max messages: 20
    """

    CACHE_PREFIX = "ai_conv:"
    TTL = 3600
    MAX_MESSAGES = 20

    @classmethod
    def _get_key(cls, user_id: Any) -> str:
        return f"{cls.CACHE_PREFIX}{user_id}"

    @classmethod
    def get_history(cls, user_id: Any) -> List[Dict[str, str]]:
        """Retrieve conversation history for a user."""
        key = cls._get_key(user_id)
        history = cache.get(key)
        if history is None:
            logger.debug("conversation cache miss", extra={"user_id": str(user_id)})
        else:
            logger.debug(
                "conversation cache hit",
                extra={"user_id": str(user_id), "msg_count": len(history)},
            )
        return history if history is not None else []

    @classmethod
    def add_messages(cls, user_id: Any, messages: List[Dict[str, str]]) -> None:
        """Append a batch of messages, then trim and refresh TTL (single source)."""
        if not messages:
            return
        key = cls._get_key(user_id)
        history = cls.get_history(user_id)

        history.extend(messages)

        cache.set(key, cls._trim(history), cls.TTL)

    @classmethod
    def _trim(cls, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """只留最後 MAX_MESSAGES 則，且以 turn 為界。

        單純取尾巴會切在 turn 中間：歷史可能以孤兒 tool marker、fenced
        結果、consent 紀錄或 assistant 回覆開頭，model 看到的是沒有提問的
        答案。往後跳到第一則「使用者親自輸入」的訊息；進行中的 turn
        （其 user 訊息必定在窗內）永遠完整保留。
        """
        if len(history) <= cls.MAX_MESSAGES:
            return history  # 沒有裁切就沒有切到 turn 中間的問題
        window = history[-cls.MAX_MESSAGES :]
        for i, msg in enumerate(window):
            if _is_turn_start(msg):
                return window[i:]
        return []

    @classmethod
    def add_message(cls, user_id: Any, role: str, content: str) -> None:
        """Add a new message to the history and enforce length limits."""
        cls.add_messages(user_id, [{"role": role, "content": content}])

    @classmethod
    def clear_history(cls, user_id: Any) -> None:
        """Clear conversation history for a user."""
        key = cls._get_key(user_id)
        cache.delete(key)
        logger.info("conversation history cleared", extra={"user_id": str(user_id)})
