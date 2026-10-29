import logging
from typing import List, Dict, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


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

        # Keep only the last MAX_MESSAGES
        cache.set(key, history[-cls.MAX_MESSAGES :], cls.TTL)

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
