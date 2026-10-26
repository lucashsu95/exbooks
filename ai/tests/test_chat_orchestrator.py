"""
ChatOrchestrator 測試 — 用 ScriptedTransport fake 直接打 stream()，
不經 HTTP。覆蓋：純內容、tool 即執行 + follow-up、consent_required、
tool 執行失敗、內容空 fallback、renewal ownership。
"""

from unittest.mock import patch

import pytest
from ai_client import ChatResponse

from ai.services.chat_orchestrator import ChatOrchestrator
from ai.services.chat_service import ChatService
from ai.services.tool_registry import ConsentRequirement, ToolDefinition, ToolRegistry
from ai.tests.fakes import make_client
from tests.factories import DealFactory, UserFactory

pytestmark = pytest.mark.django_db


def _run(user, responses):
    """跑完 stream()，回傳 (完整 SSE 文字, transport)。"""
    client, transport = make_client(responses)
    gen = ChatOrchestrator(service=ChatService(client=client)).stream(
        user=user, message="hi"
    )
    return "".join(gen), transport


def test_content_only():
    user = UserFactory()
    sse, transport = _run(user, [ChatResponse(content="你好")])
    assert "event: content" in sse
    assert "你好" in sse
    assert "event: done" in sse
    assert len(transport.requests) == 1


def test_tool_immediate_executes_and_follows_up():
    """content 為空 + 有 tool result → 第二次 chat 呼叫（follow-up）。"""
    user = UserFactory()
    sse, transport = _run(
        user,
        [
            ChatResponse(
                content="",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "get_user_books",
                            "arguments": '{"status": "OWNED"}',
                        },
                    }
                ],
            ),
            ChatResponse(content="你有 3 本書"),
        ],
    )
    assert "event: tool_result" in sse
    assert "get_user_books" in sse
    assert "你有 3 本書" in sse
    assert len(transport.requests) == 2  # 原本一次 + follow-up 一次


def test_consent_required_skips_execution():
    """USER_CONFIRM tool：只發 consent_required，不執行、不 follow-up。"""
    user = UserFactory()
    sse, transport = _run(
        user,
        [
            ChatResponse(
                content="我幫你延期，需要你的確認。",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "request_renewal",
                            "arguments": '{"deal_id": 1}',
                        },
                    }
                ],
            )
        ],
    )
    assert "event: consent_required" in sse
    assert "request_renewal" in sse
    assert "event: tool_result" not in sse
    assert len(transport.requests) == 1  # 沒有 follow-up


def test_consent_required_filters_args_before_storing():
    """未知 kwarg 在建立時過濾：存檔＝顯示（view 直接執行存檔值，不再二次過濾）。"""
    import re

    from ai.services.consent_store import ConsentStore

    user = UserFactory()
    sse, _ = _run(
        user,
        [
            ChatResponse(
                content="延長需要確認。",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "request_renewal",
                            "arguments": '{"deal_id": "1", "days": 7, "bogus": 1}',
                        },
                    }
                ],
            )
        ],
    )
    # 顯示面沒有 bogus
    assert "bogus" not in sse
    assert '"days": 7' in sse
    # 存檔面＝顯示面：token 存檔的 args 已過濾
    token_match = re.search(r'"token": "([^"]+)"', sse)
    assert token_match is not None
    stored = ConsentStore.consume(user.id, token_match.group(1))
    assert stored is not None
    assert stored["args"] == {"deal_id": "1", "days": 7}


def test_tool_error_yields_error_event():
    """tool 執行拋錯 → tool_result 帶 error，不中斷串流。"""
    user = UserFactory()

    def _boom(user, **kwargs):
        raise RuntimeError("downstream 壞了")

    fake_tool = ToolDefinition(
        name="get_user_books",
        description="",
        parameters={},
        func=_boom,
        consent=ConsentRequirement.NOT_REQUIRED,
    )
    client, transport = make_client(
        [
            ChatResponse(
                content="",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "get_user_books", "arguments": "{}"},
                    }
                ],
            ),
            ChatResponse(content="查不到，出錯了"),
        ]
    )
    with patch.object(ToolRegistry, "get_tool", return_value=fake_tool):
        gen = ChatOrchestrator(service=ChatService(client=client)).stream(
            user=user, message="hi"
        )
        sse = "".join(gen)
    assert '"error"' in sse
    assert "downstream 壞了" in sse
    assert "查不到，出錯了" in sse


def test_empty_content_fallback():
    """service 層空回應訊息之後，orchestrator 的 delta 兜底內容仍要輸出。"""
    user = UserFactory()
    sse, _ = _run(user, [ChatResponse(content="")])
    # service 層對空回應會回「我沒有收到回應」；orchestrator 照樣輸出為 delta
    assert "delta" in sse
    assert "event: done" in sse


class TestRequestRenewalOwnership:
    def test_non_party_rejected(self):
        """responder 與路人同吃 service 的權限錯誤（轉成 ValueError）。"""
        from ai.services.tool_registry import request_renewal
        from tests.factories import SharedBookFactory

        stranger = UserFactory()
        book = SharedBookFactory(status="O")
        deal = DealFactory(shared_book=book, status="M")

        with pytest.raises(ValueError, match="只有借閱者"):
            request_renewal(stranger, deal.pk)
        with pytest.raises(ValueError, match="只有借閱者"):
            request_renewal(deal.responder, deal.pk)

    def test_party_allowed(self):
        from ai.services.tool_registry import request_renewal
        from tests.factories import SharedBookFactory

        book = SharedBookFactory(status="O")
        deal = DealFactory(shared_book=book, status="M")

        result = request_renewal(deal.applicant, deal.pk)
        assert str(deal.pk) in result
        assert "待審核" in result
        assert "已延長" not in result

    def test_missing_deal(self):
        import uuid

        user = UserFactory()
        from ai.services.tool_registry import request_renewal

        with pytest.raises(ValueError, match="不存在"):
            request_renewal(user, uuid.uuid4())
