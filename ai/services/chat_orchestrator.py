"""
AI chat orchestration — tool loop、consent 決策、follow-up、history 寫入。

介面：``ChatOrchestrator(stream)`` 直接 yield SSE 幀字串
（``event: xxx\\ndata: {...}\\n\\n``）。AI client 可注入（任意
AIClient adapter，見 ai/tests/fakes.py）。

View 層只負責：HTTP framing（StreamingHttpResponse）與授權
（LoginRequiredMixin）。
"""

import json
import logging
from typing import Any, Dict, Generator

from .chat_service import ChatService
from .consent_store import ConsentStore
from .conversation_cache import ConversationCache
from .tool_registry import ConsentRequirement, ToolRegistry, filter_args_by_signature

logger = logging.getLogger(__name__)


def _sse(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps({'type': event, **payload}, ensure_ascii=False)}\n\n"


class ChatOrchestrator:
    """一輪 AI 對話的完整編排（tool loop / consent / follow-up / history）。"""

    def __init__(self, service: ChatService | None = None):
        self._service = service

    def stream(self, user, message: str) -> Generator[str, None, None]:
        service = self._service or ChatService()

        history = ConversationCache.get_history(user.id)
        ConversationCache.add_message(user.id, "user", message)

        response = service.chat(user.id, message, history)

        # 1. Tool calls：執行或請求 consent（決策在此，執行帶著使用者身份）
        tool_results = []
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name")
            if not tool_name:
                continue
            arguments = tool_call.get("args") or {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_def = ToolRegistry.get_tool(tool_name)

            if tool_def and tool_def.consent == ConsentRequirement.USER_CONFIRM:
                # 需要使用者確認：此輪不執行，ConsentView 稍後帶著 user 執行；
                # args 先依 signature 過濾再存 server-side（one-shot token），
                # 存檔＝顯示＝執行，client 回傳的 args 不可信
                arguments = filter_args_by_signature(tool_def.func, arguments)
                token = ConsentStore.create(user.id, tool_name, arguments)
                yield _sse("consent_required", {"tool": tool_name, "args": arguments, "token": token})
            elif tool_def:
                try:
                    result = tool_def.func(user=user, **arguments)
                    if not isinstance(result, (str, int, float, bool, list, dict, type(None))):
                        result = str(result)
                    tool_results.append({"tool": tool_name, "result": result})
                    yield _sse("tool_result", {"tool": tool_name, "result": result})
                except Exception as e:
                    logger.exception("tool execution failed", extra={"tool_name": tool_name})
                    tool_results.append({"tool": tool_name, "error": str(e)})
                    yield _sse("tool_result", {"tool": tool_name, "error": str(e)})

        # 2. 內容；若 AI 只回了 tool_calls，帶 tool 結果再問一次
        full_content = response.content
        if not full_content and tool_results:
            tool_summary = "\n".join(
                f"{r['tool']}: {r.get('result', r.get('error', 'Unknown'))}"
                for r in tool_results
            )
            followup_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"[Called tools: {', '.join(r['tool'] for r in tool_results)}]"},
                {"role": "user", "content": f"Tool results:\n{tool_summary}\n\nPlease provide a helpful response based on these results."},
            ]
            followup_response = service.chat(user.id, "", followup_history)
            full_content = followup_response.content

        # 3. 兜底，確保內容永不為空
        if not full_content:
            full_content = "（AI 正在思考中，請稍後再試）"

        yield _sse("content", {"delta": full_content})

        ConversationCache.add_message(user.id, "assistant", full_content)
        yield _sse("done", {})
