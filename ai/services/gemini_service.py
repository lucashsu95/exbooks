import os
from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass
from .tool_registry import ToolRegistry, ConsentRequirement

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

    def chat(self, user_id: Any, message: str, history: List[Dict[str, str]]) -> GeminiResponse:
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
        
        # Placeholder for implementation logic
        return GeminiResponse(
            content=f"已收到您的訊息：'{message}'。 (這是 GeminiService 的模擬回應)",
            tool_calls=[],
            raw_response=None
        )

    def _handle_function_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call requested by Gemini."""
        tool_def = ToolRegistry.get_tool(tool_name)
        if not tool_def:
            return f"Error: Tool '{tool_name}' not found."
            
        # In a real implementation, we might check consent here or in the view
        return tool_def.func(**arguments)
