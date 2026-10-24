import json
import logging
import time
from typing import Generator

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .services.chat_orchestrator import ChatOrchestrator
from .services.conversation_cache import ConversationCache
from .services.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ChatSSEView(LoginRequiredMixin, View):
    """
    Server-Sent Events endpoint for AI Chat.
    GET: Establishes SSE connection.
    POST: Processes user message and streams AI response.
    """

    def get(self, request, *args, **kwargs):
        logger.info("chat_sse connected", extra={"user_id": request.user.pk})

        def event_stream():
            yield f"event: connection\ndata: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
            try:
                while True:
                    time.sleep(30)
                    yield f": keepalive\n\n"
            except GeneratorExit:
                logger.info("chat_sse disconnected", extra={"user_id": request.user.pk})

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user_message = data.get("message")
            if not user_message:
                return JsonResponse({"error": "Message is required"}, status=400)
        except json.JSONDecodeError:
            logger.warning("chat_sse invalid JSON", extra={"user_id": request.user.pk})
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        user_id = request.user.id
        logger.info("chat_sse message", extra={"user_id": user_id, "message_length": len(user_message)})

        # 編排（tool loop / consent / follow-up / history）在 orchestrator；
        # view 只負責 HTTP framing。
        orchestrator = ChatOrchestrator()

        def stream_response() -> Generator[str, None, None]:
            yield from orchestrator.stream(user=request.user, message=user_message)

        return StreamingHttpResponse(
            stream_response(), content_type="text/event-stream"
        )


class ConsentView(LoginRequiredMixin, View):
    """
    Handles user confirmation for sensitive tool actions.
    """

    def post(self, request, action, *args, **kwargs):
        try:
            data = json.loads(request.body)
            arguments = data.get("args", {})
            confirmed = data.get("confirmed", False)
        except json.JSONDecodeError:
            logger.warning("consent_view invalid JSON", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if not confirmed:
            logger.info("consent_view cancelled", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"status": "cancelled"})

        tool_def = ToolRegistry.get_tool(action)
        if not tool_def:
            logger.warning("consent_view action not found", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Action not found"}, status=404)

        try:
            # 帶著使用者身份執行（ownership 檢查在 tool 內）
            result = tool_def.func(user=request.user, **arguments)
            ConversationCache.add_message(
                request.user.id,
                "system",
                f"User confirmed and executed action: {action} with args {arguments}. Result: {result}",
            )
            logger.info("consent_view success", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"status": "success", "result": result})
        except Exception as e:
            logger.exception("consent_view failed", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": str(e)}, status=500)


class ClearHistoryView(LoginRequiredMixin, View):
    """
    Clears the conversation history for the current user.
    """

    def post(self, request, *args, **kwargs):
        ConversationCache.clear_history(request.user.id)
        logger.info("clear_history", extra={"user_id": request.user.pk})
        return JsonResponse({"status": "success"})
