import secrets
from typing import Any, Dict, Optional

from django.core.cache import cache


class ConsentStore:
    """
    待確認 tool 執行的 server-side 綁定。

    Orchestrator 在發 consent_required 前把 args 存進 cache（token 為
    one-shot），ConsentView 執行時只信任 store 裡的 args，client 送的
    args 一律忽略。TTL 過期等同未確認。
    """

    CACHE_PREFIX = "ai_consent:"
    TTL = 600

    @classmethod
    def create(cls, user_id: Any, tool: str, args: Dict[str, Any]) -> str:
        token = secrets.token_urlsafe(32)
        cache.set(
            f"{cls.CACHE_PREFIX}{token}",
            {"user_id": user_id, "tool": tool, "args": args},
            cls.TTL,
        )
        return token

    @classmethod
    def consume(cls, user_id: Any, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """取回並銷毀（one-shot）；token 缺失或 user 不符都回 None。"""
        if not token:
            return None
        key = f"{cls.CACHE_PREFIX}{token}"
        # 先宣告再取回：add() 具 SET NX 語義（Redis/LocMem 皆原子），
        # 並發雙 POST 只有一筆能宣告成功（Django 5.2 尚無 get_delete）
        if not cache.add(f"{key}:claimed", True, cls.TTL):
            return None
        payload = cache.get(key)
        cache.delete(key)
        if payload is None or payload["user_id"] != user_id:
            return None
        return payload
