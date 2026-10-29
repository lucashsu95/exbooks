import json
import logging
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .services.chat_orchestrator import ChatOrchestrator, _wrap_persisted
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

        # 取消與確認同紀律：token 一律吃掉（one-shot），但 transcript 只在
        # 全部校驗通過後才寫——token 過期/不存在、action 不符或未註冊都
        # 404 且不寫（舊 cancel 路徑對過期 token 會寫下「declined (unknown)」
        # 的虛假紀錄，action 也完全未校驗）。
        payload = ConsentStore.consume(request.user.id, token)
        if payload is None:
            logger.warning("consent_view token invalid", extra={"user_id": request.user.pk, "action": action, "confirmed": confirmed})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)
        if payload["tool"] != action:
            logger.warning("consent_view token/action mismatch", extra={"user_id": request.user.pk, "action": action, "confirmed": confirmed})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)

        tool_def = ToolRegistry.get_tool(action)
        if tool_def is None or tool_def.consent != ConsentRequirement.USER_CONFIRM:
            logger.warning("consent_view action not found", extra={"user_id": request.user.pk, "action": action, "confirmed": confirmed})
            return JsonResponse({"error": "Consent request not found or expired"}, status=404)

        if not confirmed:
            logger.info("consent_view cancelled", extra={"user_id": request.user.pk, "action": action})
            # 拒絕也記進對話紀錄：下一 turn model 知道被拒，不會再重複提出。
            # 整則紀錄視為一筆 untrusted payload 統一 fence＋escaped——
            # action 來自 URL、args 可能含使用者可控字串（任一 tool 加 string
            # 參數時不得在 fence 外裸奔）。
            ConversationCache.add_message(
                request.user.id,
                "system",
                _wrap_persisted(
                    f"User declined to execute action: {action} with args {payload['args']}."
                ),
            )
            return JsonResponse({"status": "cancelled"})

        # 存檔 args 在建立時（orchestrator）已依 signature 過濾，直接執行
        arguments = payload["args"]

        try:
            # 帶著使用者身份執行（ownership 檢查在 tool 內）
            result = tool_def.func(user=request.user, **arguments)
            # 整則紀錄（action/args/result）視為一筆 untrusted payload
            # 統一 fence＋escaped：今天 args 恰好都是 UUID/int 才安全，
            # 任一 USER_CONFIRM tool 加 string 參數（備註、書名引用）
            # 就不應在 fence 外（#13 與 orchestrator 回灌路徑同紀律）。
            ConversationCache.add_message(
                request.user.id,
                "system",
                _wrap_persisted(
                    f"User confirmed and executed action: {action} with args {arguments}. "
                    f"Result: {result}"
                ),
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
