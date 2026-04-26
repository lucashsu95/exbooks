from typing import List, Dict, Any, Optional
from django.core.cache import cache

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
        return history if history is not None else []

    @classmethod
    def add_message(cls, user_id: Any, role: str, content: str) -> None:
        """Add a new message to the history and enforce length limits."""
        key = cls._get_key(user_id)
        history = cls.get_history(user_id)
        
        history.append({"role": role, "content": content})
        
        # Keep only the last MAX_MESSAGES
        if len(history) > cls.MAX_MESSAGES:
            history = history[-cls.MAX_MESSAGES:]
            
        cache.set(key, history, cls.TTL)

    @classmethod
    def clear_history(cls, user_id: Any) -> None:
        """Clear conversation history for a user."""
        key = cls._get_key(user_id)
        cache.delete(key)
