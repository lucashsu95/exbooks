"""Transport — HTTP 層抽象。可注入自訂實作（mock、logging、retry、其他 HTTP client）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests


@dataclass
class ChatMessage:
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.tool_calls:
            payload["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass
class ChatResponse:
    content: str
    reasoning_content: str = ""
    tool_calls: list[dict[str, Any]] | None = None


class Transport(Protocol):
    def chat(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
        timeout: float,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatResponse: ...


class RequestsTransport:
    """預設 transport — 用 requests 打 OpenAI-compatible /chat/completions。"""

    def chat(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
        timeout: float,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": max_tokens,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        res = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        res.raise_for_status()
        message = res.json()["choices"][0]["message"]
        return ChatResponse(
            content=message.get("content") or "",
            reasoning_content=message.get("reasoning_content") or "",
            tool_calls=message.get("tool_calls") or None,
        )
