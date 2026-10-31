"""
ChatService 測試 — 透過 Transport seam 注入 ScriptedTransport fake，
不再 mock 私有屬性。
"""

from ai_client import ChatResponse

from ai.services.chat_service import AIResponse, ChatService
from ai.tests.fakes import make_client


class TestChatService:
    def test_build_tools_openai_format(self):
        """ToolRegistry tools 轉為 OpenAI function format。"""
        service = ChatService()
        tools = service._build_tools()

        assert len(tools) >= 3
        tool_names = [t["function"]["name"] for t in tools]
        assert "get_user_books" in tool_names
        assert "get_borrowing_status" in tool_names
        assert "request_renewal" in tool_names

        get_books = next(
            t["function"] for t in tools if t["function"]["name"] == "get_user_books"
        )
        assert "description" in get_books
        assert "parameters" in get_books

    def test_mock_response_when_no_api_key(self, monkeypatch):
        """無注入 client 且無 VLLM_API_KEY → mock 回應。"""
        monkeypatch.delenv("VLLM_API_KEY", raising=False)
        service = ChatService()
        response = service.chat(user_id=1, message="Hello", history=[])

        assert isinstance(response, AIResponse)
        assert "Hello" in response.content
        assert response.tool_calls == []

    def test_chat_routes_through_injected_transport(self):
        """注入 client 後，request 經由 ScriptedTransport，可斷言 request shape。"""
        client, transport = make_client(
            [ChatResponse(content="Hi there", tool_calls=None)]
        )
        service = ChatService(client=client)

        response = service.chat(user_id=1, message="Hi", history=[])

        assert response.content == "Hi there"
        assert response.tool_calls == []
        assert len(transport.requests) == 1
        req = transport.requests[0]
        assert req["temperature"] == 0.7
        assert req["tools"]  # ToolRegistry tools 有轉發
        assert req["messages"][0].role == "system"

    def test_chat_parses_tool_calls(self):
        """SDK 回應的 tool_calls 解析為 name/args dicts。"""
        client, _ = make_client(
            [
                ChatResponse(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_user_books",
                                "arguments": '{"status": "OWNED"}',
                            },
                        }
                    ],
                )
            ]
        )
        service = ChatService(client=client)

        response = service.chat(user_id=1, message="My books", history=[])

        assert response.tool_calls == [
            {"name": "get_user_books", "args": {"status": "OWNED"}}
        ]

    def test_easter_egg_bypasses_transport(self):
        """彩蛋訊息直接回傳，不打 provider。"""
        client, transport = make_client([])
        service = ChatService(client=client)

        response = service.chat(user_id=1, message="喵", history=[])

        assert "彩蛋" in response.content
        assert transport.requests == []

    def test_chat_use_tools_false_omits_tools(self):
        """use_tools=False（loop 強制收尾用）：request 不帶 tools/tool_choice，
        結構上模型不可能回 tool_calls。"""
        client, transport = make_client([ChatResponse(content="OK", tool_calls=None)])
        service = ChatService(client=client)

        service.chat(user_id=1, message="Hi", history=[], use_tools=False)

        req = transport.requests[0]
        assert req["tools"] is None
        assert req["tool_choice"] is None
        assert req["messages"][0].role == "system"

    def test_api_failure_does_not_leak_exception_text(self):
        """provider 例外只進 log；使用者看到（並寫進歷史）的是通用訊息。"""
        from ai_client import AIClient, AIConfig

        class _BoomTransport:
            def chat(self, **kwargs):
                raise RuntimeError("secret-host:8000 connection refused token=abc")

        client = AIClient(AIConfig(api_key="k"), transport=_BoomTransport())
        response = ChatService(client=client).chat(user_id=1, message="Hi", history=[])

        assert "暫時無法回應" in response.content
        assert "secret-host" not in response.content
        assert "connection refused" not in response.content
        assert "(" not in response.content
