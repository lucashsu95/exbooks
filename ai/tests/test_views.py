import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client
from unittest.mock import patch
from ai.services.chat_service import AIResponse


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

        # SSE 串流是無限的（keepalive loop），只能讀第一個 event 就斷言
        first_event = next(iter(response.streaming_content))
        assert "connected" in first_event.decode()

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_chat_view_post_simple_message(self, mock_chat):
        """POST request should process message and return streamed response."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = AIResponse(
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

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_chat_view_post_tool_call_immediate(self, mock_chat):
        """Should execute tool immediately if no consent required."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = AIResponse(
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

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_chat_view_post_tool_call_consent_required(self, mock_chat):
        """Should request consent if tool requires it."""
        self.client.login(username="testuser", password="password")

        mock_chat.return_value = AIResponse(
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

    def _make_active_deal(self):
        # tool 帶使用者身份執行：書籍要「借閱中」且使用者是借入者（applicant）
        from tests.factories import DealFactory, SharedBookFactory

        owner = User.objects.create_user(username="owner", password="password")
        book = SharedBookFactory(owner=owner, keeper=self.user, status="O")
        return DealFactory(
            shared_book=book,
            applicant=self.user,
            responder=owner,
            status="M",
        )

    def test_consent_view_confirm(self):
        """Should execute tool if user confirms."""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        data = {"token": token, "confirmed": True}
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "success"
        assert "提交" in res_data["result"]
        assert "待審核" in res_data["result"]
        assert "已延長" not in res_data["result"]

    def test_consent_view_cancel(self):
        """Should return cancelled if user does not confirm."""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        token = ConsentStore.create(self.user.id, "request_renewal", {"deal_id": "1"})
        data = {"token": token, "confirmed": False}
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_consent_view_cancel_consumes_token(self):
        """A cancelled consent token must not be confirmable afterwards."""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        cancelled = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": False}),
            content_type="application/json",
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        replay = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )
        assert replay.status_code == 404

    def test_consent_view_confirm_without_token_404(self):
        """Confirm without a stored consent token should 404."""
        self.client.login(username="testuser", password="password")
        data = {"confirmed": True}
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 404

    def test_consent_view_ignores_client_args(self):
        """Args in the request body must be ignored; the stored args run."""
        from ai.services.consent_store import ConsentStore
        from deals.models import LoanExtension

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        data = {
            "token": token,
            "confirmed": True,
            "args": {"deal_id": str(deal.pk), "days": 14},
        }
        response = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "延長 7 天" in response.json()["result"]
        assert (
            LoanExtension.objects.get(deal=deal).extra_days
            == 7
        )

    def test_consent_view_token_is_one_shot(self):
        """A consumed consent token must not work a second time."""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        data = {"token": token, "confirmed": True}

        first = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )
        assert first.status_code == 200

        second = self.client.post(
            self.url_consent, data=json.dumps(data), content_type="application/json"
        )
        assert second.status_code == 404

    def test_consent_view_non_user_confirm_tool_404(self):
        """Non-USER_CONFIRM tools must not be executable via the consent path."""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        token = ConsentStore.create(self.user.id, "get_user_books", {})
        url = reverse("ai:chat_consent", kwargs={"action": "get_user_books"})
        response = self.client.post(
            url, data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_consent_view_tool_error_returns_generic_message(self):
        """tool 執行錯誤 → 500 通用訊息，不回 str(e)（防洩 signature/內部細節）。"""
        import uuid

        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        token = ConsentStore.create(
            self.user.id,
            "request_renewal",
            {"deal_id": str(uuid.uuid4()), "days": 7},  # 不存在的 deal
        )
        response = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )

        assert response.status_code == 500
        assert response.json()["error"] == "執行失敗，請稍後再試。"
        # 內部細節（tool 的例外訊息）不得外洩
        assert "不存在" not in response.content.decode()

    def test_consent_view_cross_user_token_404(self):
        """token 綁定建立時的使用者；別的使用者拿不到也不能用。"""
        from ai.services.consent_store import ConsentStore
        from tests.factories import UserFactory

        other = UserFactory(username="otheruser")
        token = ConsentStore.create(self.user.id, "request_renewal", {"deal_id": "1"})
        self.client.force_login(other)
        response = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_consent_view_action_mismatch_consumes_token(self):
        """打錯 action 的 POST 也吃掉 token（one-shot），改打正確 action 亦 404。"""
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        mismatched = self.client.post(
            reverse("ai:chat_consent", kwargs={"action": "get_user_books"}),
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )
        assert mismatched.status_code == 404

        replay = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )
        assert replay.status_code == 404

    def test_consent_cancel_persists_declined_note(self):
        """使用者取消也記進對話紀錄：model 下一 turn 知道被拒，不再重複提出同一操作。"""
        from ai.services.conversation_cache import ConversationCache
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        token = ConsentStore.create(self.user.id, "request_renewal", {"deal_id": "1"})
        response = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": False}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        history = ConversationCache.get_history(self.user.id)
        declines = [
            m for m in history if m["role"] == "system" and "declined" in m["content"]
        ]
        assert len(declines) == 1
        assert "request_renewal" in declines[0]["content"]

    def test_consent_view_persists_fenced_record(self):
        """#13 一致性：confirm 後持久化的 tool result 必須 fenced
        （result 內含使用者可控書名，與 orchestrator 的 fence 同一個 wrapper）。"""
        from ai.services.conversation_cache import ConversationCache
        from ai.services.consent_store import ConsentStore

        self.client.login(username="testuser", password="password")
        deal = self._make_active_deal()
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        response = self.client.post(
            self.url_consent,
            data=json.dumps({"token": token, "confirmed": True}),
            content_type="application/json",
        )
        assert response.status_code == 200
        history = ConversationCache.get_history(self.user.id)
        records = [
            m for m in history if m["role"] == "system" and "User confirmed" in m["content"]
        ]
        assert len(records) == 1
        content = records[0]["content"]
        assert "Tool results" in content
        assert "<<<" in content
        assert "untrusted" in content.lower()

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
