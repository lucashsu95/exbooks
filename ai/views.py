import json
import logging
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .services.chat_orchestrator import ChatOrchestrator
from .services.consent_store import ConsentStore
from .services.conversation_cache import ConversationCache
from .services.tool_registry import ConsentRequirement, ToolRegistry

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
                    yield ": keepalive\n\n"
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
        return StreamingHttpResponse(
            orchestrator.stream(user=request.user, message=user_message),
            content_type="text/event-stream",
        )


class ConsentView(LoginRequiredMixin, View):
    """
    Handles user confirmation for sensitive tool actions.
    """

    def post(self, request, action, *args, **kwargs):
        try:
            data = json.loads(request.body)
            token = data.get("token")
            confirmed = data.get("confirmed", False)
        except json.JSONDecodeError:
            logger.warning("consent_view invalid JSON", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # 取消也把 token 吃掉：one-shot 對任何有效 POST 成立
        payload = ConsentStore.consume(request.user.id, token)
        if not confirmed:
            logger.info("consent_view cancelled", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"status": "cancelled"})

        if payload is None:
            logger.warning("consent_view token invalid", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)
        if payload["tool"] != action:
            logger.warning("consent_view token/action mismatch", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)

        tool_def = ToolRegistry.get_tool(action)
        if tool_def is None or tool_def.consent != ConsentRequirement.USER_CONFIRM:
            logger.warning("consent_view action not found", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)

        # 存檔 args 在建立時（orchestrator）已依 signature 過濾，直接執行
        arguments = payload["args"]

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
        except Exception:
            logger.exception("consent_view failed", extra={"user_id": request.user.pk, "action": action})
            # tool 例外訊息不回 client（可能含 signature/內部細節），只進 log
            return JsonResponse({"error": "執行失敗，請稍後再試。"}, status=500)


class ClearHistoryView(LoginRequiredMixin, View):
    """
    Clears the conversation history for the current user.
    """

    def post(self, request, *args, **kwargs):
        ConversationCache.clear_history(request.user.id)
        logger.info("clear_history", extra={"user_id": request.user.pk})
        return JsonResponse({"status": "success"})
