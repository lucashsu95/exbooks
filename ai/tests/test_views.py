"""
AI view 測試——只驗 HTTP 層：登入、輸入驗證、限流、result → status 映射。
業務規則（consent token、transcript 紀錄）見 test_consent_service.py。
"""

import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from ai.services.chat_service import AIResponse
from ai.services.consent_service import ConsentResult, ConsentStatus


@pytest.fixture(autouse=True)
def _isolate_conversation_cache():
    # SQLite 測試庫回滾每個測試，user pk 會重用 1，而 locmem cache 不跨測試
    # 清除——consent/對話紀錄／限流計數會累積成前面測試的殘留。
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


@pytest.mark.django_db
class TestChatView:
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.url_chat = reverse("ai:chat_sse")

    def _post(self, body, raw=False):
        return self.client.post(
            self.url_chat,
            data=body if raw else json.dumps(body),
            content_type="application/json",
        )

    def test_requires_login(self):
        response = self._post({"message": "hi"})
        assert response.status_code == 302
        assert "login" in response.url

    def test_get_not_allowed(self):
        """GET 長連線已移除：輸入可用性不再依賴它。"""
        self.client.force_login(self.user)
        assert self.client.get(self.url_chat).status_code == 405

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_post_simple_message(self, mock_chat):
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(
            content="Hello from AI", tool_calls=[], raw_response=None
        )
        response = self._post({"message": "Hi"})

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        content = b"".join(response.streaming_content).decode()
        assert "Hello from AI" in content
        assert '"type": "done"' in content

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_post_message_is_stripped(self, mock_chat):
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(content="ok", tool_calls=[], raw_response=None)
        response = self._post({"message": "  你好  "})
        b"".join(response.streaming_content)
        assert mock_chat.call_args.args[1] == "你好"

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_post_tool_call_immediate(self, mock_chat):
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(
            content="Checking your books...",
            tool_calls=[{"name": "get_user_books", "args": {"status": "OWNED"}}],
            raw_response=None,
        )
        content = b"".join(self._post({"message": "My books"}).streaming_content).decode()
        assert '"type": "tool_result"' in content
        assert "get_user_books" in content

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_post_tool_call_consent_required(self, mock_chat):
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(
            content="I need your permission to renew.",
            tool_calls=[{"name": "request_renewal", "args": {"deal_id": 1}}],
            raw_response=None,
        )
        content = b"".join(self._post({"message": "Renew book"}).streaming_content).decode()
        assert '"type": "consent_required"' in content
        assert "request_renewal" in content

    @pytest.mark.parametrize(
        "body",
        [
            "not a json",
            "[]",
            '"hi"',
            "5",
            "null",
            json.dumps({}),
            json.dumps({"message": 5}),
            json.dumps({"message": None}),
            json.dumps({"message": ["hi"]}),
            json.dumps({"message": ""}),
            json.dumps({"message": "   \n\t "}),
            json.dumps({"message": "字" * 1001}),
        ],
    )
    def test_invalid_input_returns_400_with_chinese_error(self, body):
        self.client.force_login(self.user)
        response = self._post(body, raw=True)
        assert response.status_code == 400
        assert _has_cjk(response.json()["error"])

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_max_length_message_accepted(self, mock_chat):
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(content="ok", tool_calls=[], raw_response=None)
        response = self._post({"message": "字" * 1000})
        assert response.status_code == 200
        b"".join(response.streaming_content)

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_concurrent_turn_rejected_429(self, mock_chat):
        """同一使用者前一輪還在串流中 → 第二輪 429（中文訊息）。"""
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(content="ok", tool_calls=[], raw_response=None)
        first = self._post({"message": "一"})
        assert first.status_code == 200  # 尚未讀完串流：鎖仍持有

        second = self._post({"message": "二"})
        assert second.status_code == 429
        assert _has_cjk(second.json()["error"])

        b"".join(first.streaming_content)  # 串流結束釋放鎖
        third = self._post({"message": "三"})
        assert third.status_code == 200
        b"".join(third.streaming_content)

    @patch("ai.services.chat_orchestrator.ChatService.chat")
    def test_rate_limited_429(self, mock_chat, monkeypatch):
        from ai.services import turn_guard

        monkeypatch.setattr(turn_guard, "RATE_LIMIT_PER_MINUTE", 2)
        self.client.force_login(self.user)
        mock_chat.return_value = AIResponse(content="ok", tool_calls=[], raw_response=None)
        for _ in range(2):
            b"".join(self._post({"message": "hi"}).streaming_content)
        response = self._post({"message": "hi"})
        assert response.status_code == 429
        assert _has_cjk(response.json()["error"])


@pytest.mark.django_db
class TestConsentView:
    """View 只解析 JSON、把 ConsentResult 映射成 HTTP 狀態。"""

    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.url = reverse("ai:chat_consent", kwargs={"action": "request_renewal"})

    def _post(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_requires_login(self):
        assert self._post({"token": "x", "confirmed": True}).status_code == 302

    def test_invalid_json_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data="nope", content_type="application/json")
        assert response.status_code == 400
        assert _has_cjk(response.json()["error"])

    def test_non_object_body_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data="[]", content_type="application/json")
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "result,status,key",
        [
            (ConsentResult(ConsentStatus.SUCCESS, result="已提交"), 200, "result"),
            (ConsentResult(ConsentStatus.CANCELLED), 200, "status"),
            (ConsentResult(ConsentStatus.NOT_FOUND), 404, "error"),
            (ConsentResult(ConsentStatus.FAILED), 500, "error"),
        ],
    )
    def test_result_mapping(self, result, status, key):
        self.client.force_login(self.user)
        with patch("ai.views.resolve_consent", return_value=result) as resolve:
            response = self._post({"token": "t", "confirmed": True, "args": {"days": 14}})
        assert response.status_code == status
        assert key in response.json()
        if status >= 400:
            assert _has_cjk(response.json()["error"])
        # client 送來的 args 一律不傳給 service
        resolve.assert_called_once_with(self.user, "request_renewal", "t", True)

    def test_success_payload(self):
        self.client.force_login(self.user)
        with patch(
            "ai.views.resolve_consent",
            return_value=ConsentResult(ConsentStatus.SUCCESS, result="已提交申請"),
        ):
            data = self._post({"token": "t", "confirmed": True}).json()
        assert data == {"status": "success", "result": "已提交申請"}

    def test_end_to_end_confirm(self):
        """一條不 mock 的整合路徑：token → 執行 → 200。"""
        from ai.services.consent_store import ConsentStore
        from tests.factories import DealFactory, SharedBookFactory

        owner = User.objects.create_user(username="owner", password="password")
        book = SharedBookFactory(owner=owner, keeper=self.user, status="O")
        deal = DealFactory(shared_book=book, applicant=self.user, responder=owner, status="M")
        token = ConsentStore.create(
            self.user.id, "request_renewal", {"deal_id": str(deal.pk), "days": 7}
        )
        self.client.force_login(self.user)
        response = self._post({"token": token, "confirmed": True})
        assert response.status_code == 200
        assert "待審核" in response.json()["result"]


@pytest.mark.django_db
def test_clear_history_view():
    from ai.services.conversation_cache import ConversationCache

    user = User.objects.create_user(username="testuser", password="password")
    client = Client()
    client.force_login(user)
    ConversationCache.add_message(user.id, "user", "Hello")

    response = client.post(reverse("ai:chat_clear"))
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert ConversationCache.get_history(user.id) == []
