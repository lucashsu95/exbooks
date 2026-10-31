import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View

from .services.chat_orchestrator import ChatOrchestrator
from .services.consent_service import ConsentStatus, resolve_consent
from .services.conversation_cache import ConversationCache
from .services.turn_guard import begin_turn, guard_stream

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1000

_ERR_BAD_REQUEST = "請求格式錯誤，請重新整理頁面後再試。"
_ERR_EMPTY_MESSAGE = "請輸入訊息內容。"
_ERR_TOO_LONG = f"訊息太長了，請精簡到 {MAX_MESSAGE_LENGTH} 字以內。"
_ERR_CONSENT_NOT_FOUND = "這個確認請求已失效，請重新詢問米豆。"
_ERR_CONSENT_FAILED = "執行失敗，請稍後再試。"


def _parse_json_object(request):
    """回傳 dict；body 不是 JSON 物件時回 None。"""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


class ChatSSEView(LoginRequiredMixin, View):
    """POST：處理使用者訊息，以 SSE 串流回覆。"""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        data = _parse_json_object(request)
        if data is None:
            logger.warning("chat invalid body", extra={"user_id": request.user.pk})
            return JsonResponse({"error": _ERR_BAD_REQUEST}, status=400)

        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return JsonResponse({"error": _ERR_EMPTY_MESSAGE}, status=400)
        message = message.strip()
        if len(message) > MAX_MESSAGE_LENGTH:
            return JsonResponse({"error": _ERR_TOO_LONG}, status=400)

        user_id = request.user.pk
        rejection = begin_turn(user_id)
        if rejection is not None:
            logger.info("chat turn rejected", extra={"user_id": user_id, "reason": rejection.name})
            return JsonResponse({"error": rejection.message}, status=429)

        logger.info("chat message", extra={"user_id": user_id, "message_length": len(message)})
        # 編排（tool loop / consent / follow-up / history）在 orchestrator；
        # view 只負責 HTTP framing。
        stream = ChatOrchestrator().stream(user=request.user, message=message)
        response = StreamingHttpResponse(
            guard_stream(user_id, stream), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ConsentView(LoginRequiredMixin, View):
    """使用者對敏感 tool 操作的確認／取消；規則在 consent_service。"""

    http_method_names = ["post"]

    def post(self, request, action, *args, **kwargs):
        data = _parse_json_object(request)
        if data is None:
            logger.warning("consent invalid body", extra={"user_id": request.user.pk, "action": action})
            return JsonResponse({"error": _ERR_BAD_REQUEST}, status=400)

        outcome = resolve_consent(
            request.user, action, data.get("token"), data.get("confirmed") is True
        )
        if outcome.status is ConsentStatus.SUCCESS:
            return JsonResponse({"status": "success", "result": outcome.result})
        if outcome.status is ConsentStatus.CANCELLED:
            return JsonResponse({"status": "cancelled"})
        if outcome.status is ConsentStatus.NOT_FOUND:
            return JsonResponse({"error": _ERR_CONSENT_NOT_FOUND}, status=404)
        return JsonResponse({"error": _ERR_CONSENT_FAILED}, status=500)


class ClearHistoryView(LoginRequiredMixin, View):
    """清除目前使用者的對話紀錄。"""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ConversationCache.clear_history(request.user.id)
        logger.info("clear_history", extra={"user_id": request.user.pk})
        return JsonResponse({"status": "success"})
