import json
import logging
from typing import Generator

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .services.gemini_service import GeminiService
from .services.conversation_cache import ConversationCache
from .services.tool_registry import ToolRegistry, ConsentRequirement

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
            yield f"event: connection\ndata: {json.dumps({'status': 'connected'})}\n\n"

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
        history = ConversationCache.get_history(user_id)

        ConversationCache.add_message(user_id, "user", user_message)

        service = GeminiService()
        response = service.chat(user_id, user_message, history)

        def stream_response() -> Generator[str, None, None]:
            # 1. Handle Tool Calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name")
                    if not tool_name:
                        continue
                    arguments = tool_call.get("args", {})
                    tool_def = ToolRegistry.get_tool(tool_name)

                    if tool_def and tool_def.consent == ConsentRequirement.USER_CONFIRM:
                        # Need user confirmation
                        yield f"event: consent_required\ndata: {json.dumps({'tool': tool_name, 'args': arguments})}\n\n"
                    elif tool_def:
                        # Execute immediately
                        result = tool_def.func(**arguments)
                        yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': result})}\n\n"

            # 2. Stream Content
            # Simulated streaming for T2-5
            full_content = response.content
            # To simulate streaming, we could split by words/chars but for simplicity:
            yield f"event: content\ndata: {json.dumps({'delta': full_content})}\n\n"

            # Add AI response to history
            ConversationCache.add_message(user_id, "assistant", full_content)

            yield f"event: done\ndata: {json.dumps({})}\n\n"

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
            result = tool_def.func(**arguments)
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
