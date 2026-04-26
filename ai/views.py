import json
from typing import Generator
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .services.gemini_service import GeminiService
from .services.conversation_cache import ConversationCache
from .services.tool_registry import ToolRegistry, ConsentRequirement


class ChatSSEView(LoginRequiredMixin, View):
    """
    Server-Sent Events endpoint for AI Chat.
    GET: Establishes SSE connection.
    POST: Processes user message and streams AI response.
    """

    def get(self, request, *args, **kwargs):
        def event_stream():
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    @method_decorator(
        csrf_exempt
    )  # For simplicity in T2-5, usually handled via header in production
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user_message = data.get("message")
            if not user_message:
                return JsonResponse({"error": "Message is required"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        user_id = request.user.id
        history = ConversationCache.get_history(user_id)

        # Add user message to history
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
                        yield f"data: {json.dumps({'type': 'consent_required', 'tool': tool_name, 'args': arguments})}\n\n"
                    elif tool_def:
                        # Execute immediately
                        result = tool_def.func(**arguments)
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': result})}\n\n"

            # 2. Stream Content
            # Simulated streaming for T2-5
            full_content = response.content
            # To simulate streaming, we could split by words/chars but for simplicity:
            yield f"data: {json.dumps({'type': 'content', 'delta': full_content})}\n\n"

            # Add AI response to history
            ConversationCache.add_message(user_id, "assistant", full_content)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingHttpResponse(
            stream_response(), content_type="text/event-stream"
        )


class ConsentView(LoginRequiredMixin, View):
    """
    Handles user confirmation for sensitive tool actions.
    """

    @method_decorator(csrf_exempt)
    def post(self, request, action, *args, **kwargs):
        try:
            data = json.loads(request.body)
            arguments = data.get("args", {})
            confirmed = data.get("confirmed", False)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if not confirmed:
            return JsonResponse({"status": "cancelled"})

        tool_def = ToolRegistry.get_tool(action)
        if not tool_def:
            return JsonResponse({"error": "Action not found"}, status=404)

        try:
            result = tool_def.func(**arguments)
            # Optionally add to history that action was confirmed and executed
            ConversationCache.add_message(
                request.user.id,
                "system",
                f"User confirmed and executed action: {action} with args {arguments}. Result: {result}",
            )
            return JsonResponse({"status": "success", "result": result})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
