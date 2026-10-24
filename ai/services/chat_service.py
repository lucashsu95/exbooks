import json
import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ai_client import ChatMessage, ChatResponse as SDKChatResponse

from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Standardized response from AI backend."""

    content: str
    tool_calls: List[Dict[str, Any]]
    raw_response: Any


class GeminiService:
    """
    Exbook AI 助手服務 — 底層統一走 ai-client SDK（OpenAI 相容 vLLM 端點）。

    端點／模型／金鑰由 VLLM_* 環境變數決定（AI-Forge SDK 預設即 BIRC H200 端點）。
    當 ``VLLM_API_KEY`` 未設定時回傳 mock 回應，方便本地開發。
    """

    SYSTEM_PROMPT = (
        "你是一位專門協助 Exbook 共享書籍平臺用戶的 AI 助手。你的任務是回答用戶關於借書、"
        "還書、信用等級、書籍搜尋等問題。你可以使用提供的工具來獲取用戶的實時資訊或執行操作。"
        "請使用繁體中文（台灣習慣）回答，口氣親切專業。如果需要用戶確認敏感操作，請明確說明。"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VLLM_API_KEY")
        self._client = None
        if self.api_key:
            from ai_client import create_client

            self._client = create_client()
        else:
            logger.warning("VLLM_API_KEY not set, GeminiService will use mock responses")

    def _build_tools(self) -> List[Dict[str, Any]]:
        """Convert ToolRegistry tools to OpenAI function format."""
        tools = []
        for tool_def in ToolRegistry.get_all_tools():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_def.name,
                        "description": tool_def.description,
                        "parameters": tool_def.parameters,
                    },
                }
            )
        return tools

    def _to_messages(
        self, history: List[Dict[str, str]], current_message: str
    ) -> List[ChatMessage]:
        """Map conversation history to SDK ChatMessage objects."""
        messages: List[ChatMessage] = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT)
        ]
        for msg in history:
            role = msg["role"]
            text = msg["content"]
            sdk_role = "assistant" if role == "assistant" else "user"
            messages.append(ChatMessage(role=sdk_role, content=text))
        messages.append(ChatMessage(role="user", content=current_message))
        return messages

    def chat(
        self, user_id: Any, message: str, history: List[Dict[str, str]]
    ) -> GeminiResponse:
        """
        Processes a user message and returns a response from the AI backend.

        When ``VLLM_API_KEY`` is available the real BIRC vLLM endpoint is called;
        otherwise a mock response is returned for local development.
        """
        logger.info(
            "AI chat called",
            extra={
                "user_id": str(user_id),
                "message_length": len(message),
                "history_length": len(history),
            },
        )

        msg_lower = message.strip().lower()
        if msg_lower in ("喵", "cat", "meow", "🐱"):
            return GeminiResponse(
                content=(
                    "喵～你發現了隱藏彩蛋！\n\n"
                    "    /|_╱|\n"
                    "   ( •̀ㅅ •́ )\n"
                    "  ＿ノ ヽ ノ＼＿\n"
                    " /　`/ ⌒Ｙ⌒ Ｙ　 \\n"
                    "( 　(三ヽ人　 /　 　|\n"
                    "|　ﾉ⌒＼ ￣￣ヽ　 ノ\n"
                    "ヽ＿＿＿＞､＿＿／\n\n"
                    "這隻貓咪是 Exbooks 的守護靈，謝謝你來分享書籍 🐾"
                ),
                tool_calls=[],
                raw_response=None,
            )

        if not self._client:
            logger.debug("GeminiService returning mock response (no API key)")
            return GeminiResponse(
                content=f"已收到您的訊息：'{message}'。 (這是 GeminiService 的模擬回應)",
                tool_calls=[],
                raw_response=None,
            )

        messages = self._to_messages(history, message)
        tools = self._build_tools()

        try:
            response = self._client.chat(
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            logger.exception("AI API call failed", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content=f"抱歉，AI 服務暫時無法回應，請稍後再試。 ({e})",
                tool_calls=[],
                raw_response=None,
            )

        content_text = (response.content or "").strip()
        if not content_text and not response.tool_calls:
            logger.warning("AI returned empty response", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content="抱歉，我沒有收到回應，請再試一次。",
                tool_calls=[],
                raw_response=response,
            )

        tool_calls: List[Dict[str, Any]] = []
        for tc in response.tool_calls or []:
            function = tc.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": function.get("name"), "args": args})

        logger.info(
            "AI response parsed",
            extra={
                "user_id": str(user_id),
                "text_length": len(content_text),
                "tool_calls_count": len(tool_calls),
            },
        )

        return GeminiResponse(
            content=content_text,
            tool_calls=tool_calls,
            raw_response=response,
        )

    def _handle_function_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call requested by the AI."""
        tool_def = ToolRegistry.get_tool(tool_name)
        if tool_def is None:
            return f"Error: Tool '{tool_name}' not found."

        logger.debug(
            "handling function call",
            extra={
                "tool_name": tool_name,
            },
        )
        return tool_def.func(**arguments)
