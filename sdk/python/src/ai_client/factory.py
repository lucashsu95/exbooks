"""create_client — 從環境變數組裝 AIClient。"""

from __future__ import annotations

from .client import AIClient
from .config import AIConfig


def create_client(config: AIConfig | None = None) -> AIClient:
    """建立 AIClient。未傳 config 時從 VLLM_* 環境變數讀取。"""
    return AIClient(config or AIConfig.from_env())
