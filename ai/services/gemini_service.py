import json
import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

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
    Wrapper for NVIDIA API (OpenAI-compatible) handling chat and function calling.

    Falls back to mock responses when ``NVIDIA_API_KEY`` is not configured.
    """

    SYSTEM_PROMPT = (
        "你是一位專門協助 Exbook 共享書籍平臺用戶的 AI 助手。你的任務是回答用戶關於借書、"
        "還書、信用等級、書籍搜尋等問題。你可以使用提供的工具來獲取用戶的實時資訊或執行操作。"
        "請使用繁體中文（台灣習慣）回答，口氣親切專業。如果需要用戶確認敏感操作，請明確說明。"
    )

    BASE_URL = "https://api.groq.com/openai/v1"
    MODEL = "llama-3.1-70b-versatile"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        self._client = None
        if self.api_key:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key,
            )
        else:
            logger.warning("NVIDIA_API_KEY not set, GeminiService will use mock responses")

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
    ) -> List[Dict[str, Any]]:
        """Map conversation history to OpenAI message objects."""
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        for msg in history:
            role = msg["role"]
            text = msg["content"]
            openai_role = "assistant" if role == "assistant" else "user"
            messages.append({"role": openai_role, "content": text})
        messages.append({"role": "user", "content": current_message})
        return messages

    def chat(
        self, user_id: Any, message: str, history: List[Dict[str, str]]
    ) -> GeminiResponse:
        """
        Processes a user message and returns a response from the AI backend.

        When ``NVIDIA_API_KEY`` is available the real NVIDIA API is called;
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
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            logger.exception("NVIDIA API call failed", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content=f"抱歉，AI 服務暫時無法回應，請稍後再試。 ({e})",
                tool_calls=[],
                raw_response=None,
            )

        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message:
            logger.warning("NVIDIA returned empty response", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content="抱歉，我沒有收到回應，請再試一次。",
                tool_calls=[],
                raw_response=response,
            )

        content_text = choice.message.content or ""
        tool_calls: List[Dict[str, Any]] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({"name": tc.function.name, "args": args})

        logger.info(
            "NVIDIA response parsed",
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
        if not tool_def:
            return f"Error: Tool '{tool_name}' not found."

        logger.debug(
            "handling function call",
            extra={"tool_name": tool_name},
        )
        return tool_def.func(**arguments)
