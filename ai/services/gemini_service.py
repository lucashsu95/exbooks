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

    Note: Actual API calls are not performed without a valid API key.
    This class handles the logic for building requests and parsing responses.
    """

    SYSTEM_PROMPT = (
        "你是一位專門協助 Exbook 共享書籍平臺用戶的 AI 助手。你的任務是回答用戶關於借書、"
        "還書、信用等級、書籍搜尋等問題。你可以使用提供的工具來獲取用戶的實時資訊或執行操作。"
        "請使用繁體中文（台灣習慣）回答，口氣親切專業。如果需要用戶確認敏感操作，請明確說明。"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set, GeminiService will use mock responses")

    def _build_gemini_tools(self) -> List[Dict[str, Any]]:
        """Convert ToolRegistry tools to Gemini function declaration format."""
        tools = []
        for tool_def in ToolRegistry.get_all_tools():
            function_declaration = {
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": tool_def.parameters,
            }
            tools.append({"function_declaration": function_declaration})
        return tools

    def chat(
        self, user_id: Any, message: str, history: List[Dict[str, str]]
    ) -> GeminiResponse:
        """
        Processes a user message and returns a response from Gemini.
        In a real scenario, this would call the google-generativeai SDK.
        """
        # In this task, we don't actually call the API.
        # We simulate the logic structure.

        # 1. Prepare messages (system + history + current)
        # 2. Prepare tools (from _build_gemini_tools)
        # 3. Send to API
        # 4. Handle response (text or tool_use)

        logger.info(
            "Gemini chat called",
            extra={
                "user_id": str(user_id),
                "message_length": len(message),
                "history_length": len(history),
            },
        )

        # Placeholder for implementation logic
        logger.debug("GeminiService returning mock response")

        # 🐱 Easter egg: cat meow keyword
        msg_lower = message.strip().lower()
        if msg_lower in ("喵", "cat", "meow", "🐱"):
            return GeminiResponse(
                content=(
                    "喵～你發現了隱藏彩蛋！\n\n"
                    "    /|_╱|\n"
                    "   ( •̀ㅅ •́ )\n"
                    "  ＿ノ ヽ ノ＼＿\n"
                    " /　`/ ⌒Ｙ⌒ Ｙ　 \\\n"
                    "( 　(三ヽ人　 /　 　|\n"
                    "|　ﾉ⌒＼ ￣￣ヽ　 ノ\n"
                    "ヽ＿＿＿＞､＿＿／\n\n"
                    "這隻貓咪是 Exbooks 的守護靈，謝謝你來分享書籍 🐾"
                ),
                tool_calls=[],
                raw_response=None,
            )

        return GeminiResponse(
            content=f"已收到您的訊息：'{message}'。 (這是 GeminiService 的模擬回應)",
            tool_calls=[],
            raw_response=None,
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
        # In a real implementation, we might check consent here or in the view
        return tool_def.func(**arguments)
