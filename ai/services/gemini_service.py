import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Standardized response from GeminiService."""

    content: str
    tool_calls: List[Dict[str, Any]]
    raw_response: Any


class GeminiService:
    """
    Wrapper for Google Gemini API handling chat and function calling.

    Uses the ``google-genai`` SDK (``google.genai``). Falls back to mock
    responses when ``GEMINI_API_KEY`` is not configured.
    """

    SYSTEM_PROMPT = (
        "你是一位專門協助 Exbook 共享書籍平臺用戶的 AI 助手。你的任務是回答用戶關於借書、"
        "還書、信用等級、書籍搜尋等問題。你可以使用提供的工具來獲取用戶的實時資訊或執行操作。"
        "請使用繁體中文（台灣習慣）回答，口氣親切專業。如果需要用戶確認敏感操作，請明確說明。"
    )

    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None
        if self.api_key:
            import google.genai

            self._client = google.genai.Client(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY not set, GeminiService will use mock responses")

    def _build_gemini_tools(self) -> List[Any]:
        """Convert ToolRegistry tools to Gemini function declaration format."""
        from google.genai import types

        function_declarations = []
        for tool_def in ToolRegistry.get_all_tools():
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=types.Schema(**tool_def.parameters),
                )
            )
        if function_declarations:
            return [types.Tool(function_declarations=function_declarations)]
        return []

    def _to_gemini_contents(
        self, history: List[Dict[str, str]], current_message: str
    ) -> List[Any]:
        """Map conversation history to Gemini ``Content`` objects."""
        from google.genai import types

        contents: List[types.Content] = []
        for msg in history:
            role = msg["role"]
            text = msg["content"]
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                types.Content(role=gemini_role, parts=[types.Part(text=text)])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part(text=current_message)])
        )
        return contents

    def chat(
        self, user_id: Any, message: str, history: List[Dict[str, str]]
    ) -> GeminiResponse:
        """
        Processes a user message and returns a response from Gemini.

        When ``GEMINI_API_KEY`` is available the real Gemini API is called;
        otherwise a mock response is returned for local development.
        """
        logger.info(
            "Gemini chat called",
            extra={
                "user_id": str(user_id),
                "message_length": len(message),
                "history_length": len(history),
            },
        )

        # 🐱 Easter egg: cat meow keyword
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

        from google.genai import types

        contents = self._to_gemini_contents(history, message)
        tools = self._build_gemini_tools()

        config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_PROMPT,
        )
        if tools:
            config.tools = tools

        try:
            response = self._client.models.generate_content(
                model=self.MODEL,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.exception("Gemini API call failed", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content=f"抱歉，AI 服務暫時無法回應，請稍後再試。 ({e})",
                tool_calls=[],
                raw_response=None,
            )

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            logger.warning("Gemini returned empty response", extra={"user_id": str(user_id)})
            return GeminiResponse(
                content="抱歉，我沒有收到回應，請再試一次。",
                tool_calls=[],
                raw_response=response,
            )

        content_text = ""
        tool_calls: List[Dict[str, Any]] = []
        for part in candidate.content.parts:
            if part.text:
                content_text += part.text
            elif part.function_call:
                fc = part.function_call
                tool_calls.append({"name": fc.name, "args": dict(fc.args) if fc.args else {}})

        logger.info(
            "Gemini response parsed",
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
        """Execute a function call requested by Gemini."""
        tool_def = ToolRegistry.get_tool(tool_name)
        if not tool_def:
            return f"Error: Tool '{tool_name}' not found."

        logger.debug(
            "handling function call",
            extra={"tool_name": tool_name},
        )
        return tool_def.func(**arguments)
