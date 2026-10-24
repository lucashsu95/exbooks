"""AIClient — 依賴注入的核心。config + transport 皆可注入。"""

from __future__ import annotations

from typing import Any

import requests

from .config import AIConfig
from .transport import ChatMessage, ChatResponse, RequestsTransport, Transport


class AIClient:
    def __init__(
        self,
        config: AIConfig,
        transport: Transport | None = None,
    ):
        self.config = config
        self.transport = transport or RequestsTransport()
        self.system_prompt = (config.system_prompt or "").strip() or None

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        if not self.config.api_key:
            raise ValueError("VLLM_API_KEY 未設定。請先設定環境變數或傳入 AIConfig(api_key=...)。")

        messages: list[ChatMessage] = []
        if self.system_prompt:
            messages.append(ChatMessage(role="system", content=self.system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        try:
            response = self.transport.chat(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                model=self.config.model,
                messages=messages,
                max_tokens=max_tokens or self.config.max_tokens,
                timeout=self.config.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise TimeoutError("請求超時：模型推理可能需要更長時間。") from exc

        return response.content.strip() or response.reasoning_content.strip() or "（模型回傳空內容）"

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatResponse:
        """多輪對話，支援 function calling。回傳完整 ChatResponse（含 tool_calls）。"""
        if not self.config.api_key:
            raise ValueError("VLLM_API_KEY 未設定。請先設定環境變數或傳入 AIConfig(api_key=...)。")

        return self.transport.chat(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model,
            messages=messages,
            max_tokens=max_tokens or self.config.max_tokens,
            timeout=self.config.timeout,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
