import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client
from unittest.mock import patch
from ai.services.gemini_service import GeminiResponse


@pytest.mark.django_db
class TestAIViews:
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.url_chat = reverse("ai:chat_sse")
        self.url_consent = reverse(
            "ai:chat_consent", kwargs={"action": "request_renewal"}
        )
        self.url_clear = reverse("ai:chat_clear")

    def test_chat_view_requires_login(self):
        """Should redirect to login if not authenticated."""
        response = self.client.get(self.url_chat)
        assert response.status_code == 302
        assert "login" in response.url

    def test_chat_view_get_sse_connection(self):
        """GET request should establish SSE connection."""
        self.client.login(username="testuser", password="password")
        response = self.client.get(self.url_chat)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"

        # Check initial data
        content = b"".join(response.streaming_content).decode()
        assert "connected" in content

    @patch("ai.views.GeminiService.chat")
    def test_chat_view_post_simple_message(self, mock_chat):
        """POST request should process message and return streamed response."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = GeminiResponse(
            content="Hello from AI", tool_calls=[], raw_response=None
        )

        data = {"message": "Hi"}
        response = self.client.post(
            self.url_chat, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"

        content = b"".join(response.streaming_content).decode()
        assert "Hello from AI" in content
        assert '"type": "done"' in content

    @patch("ai.views.GeminiService.chat")
    def test_chat_view_post_tool_call_immediate(self, mock_chat):
        """Should execute tool immediately if no consent required."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = GeminiResponse(
            content="Checking your books...",
            tool_calls=[{"name": "get_user_books", "args": {"status": "OWNED"}}],
            raw_response=None,
        )

        response = self.client.post(
            self.url_chat,
            data=json.dumps({"message": "My books"}),
            content_type="application/json",
        )

        content = b"".join(response.streaming_content).decode()
        assert '"type": "tool_result"' in content
        assert "get_user_books" in content

    @patch("ai.views.GeminiService.chat")
    def test_chat_view_post_tool_call_consent_required(self, mock_chat):
        """Should request consent if tool requires it."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = GeminiResponse(
            content="I need your permission to renew.",
            tool_calls=[{"name": "request_renewal", "args": {"deal_id": 1}}],
            raw_response=None,
        )

        response = self.client.post(
            self.url_chat,
            data=json.dumps({"message": "Renew book"}),
            content_type="application/json",
        )

        content = b"".join(response.streaming_content).decode()
        assert '"type": "consent_required"' in content
        assert "request_renewal" in content

    def test_consent_view_confirm(self):
        """Should execute tool if user confirms."""
        self.client.login(username="testuser", password="password")

        data = {"args": {"deal_id": 1, "days": 7}, "confirmed": True}
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "success"
        assert "request_renewal" in res_data["result"]

    def test_consent_view_cancel(self):
        """Should return cancelled if user does not confirm."""
        self.client.login(username="testuser", password="password")

        data = {"args": {"deal_id": 1}, "confirmed": False}
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_chat_view_invalid_json(self):
        """Should return 400 for invalid JSON."""
        self.client.login(username="testuser", password="password")
        response = self.client.post(
            self.url_chat, data="not a json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_clear_history_view(self):
        """Should clear history through the view."""
        self.client.login(username="testuser", password="password")
        from ai.services.conversation_cache import ConversationCache

        ConversationCache.add_message(self.user.id, "user", "Hello")

        response = self.client.post(self.url_clear)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert ConversationCache.get_history(self.user.id) == []
