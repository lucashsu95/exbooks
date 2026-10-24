import pytest

from ai_client import AIClient, AIConfig, ChatMessage, ChatResponse


class FakeTransport:
    """注入用假 transport — 不碰真實 API。"""

    def __init__(self, content="OK", reasoning_content=""):
        self.content = content
        self.reasoning_content = reasoning_content
        self.call_kwargs: dict = {}

    def chat(self, **kwargs):
        self.call_kwargs = kwargs
        return ChatResponse(content=self.content, reasoning_content=self.reasoning_content)


def _client(transport=None, content="OK", reasoning_content="", **cfg):
    transport = transport or FakeTransport(content=content, reasoning_content=reasoning_content)
    return AIClient(config=AIConfig(api_key="sk-test", **cfg), transport=transport)


def test_missing_api_key_raises():
    client = AIClient(AIConfig(api_key=""))
    with pytest.raises(ValueError, match="VLLM_API_KEY"):
        client.complete("hi")


def test_returns_content():
    assert _client(content="👋").complete("hi") == "👋"


def test_falls_back_to_reasoning_content_when_content_empty():
    assert _client(content="", reasoning_content="思考中").complete("hi") == "思考中"


def test_sends_system_prompt_when_configured():
    transport = FakeTransport()
    _client(transport, system_prompt="你是助手").complete("hi")
    assert transport.call_kwargs["messages"][0] == ChatMessage("system", "你是助手")
    assert transport.call_kwargs["messages"][1] == ChatMessage("user", "hi")


def test_transport_http_error_raises():
    class BoomTransport(FakeTransport):
        def chat(self, **kwargs):
            raise Exception("boom")

    with pytest.raises(Exception, match="boom"):
        _client(BoomTransport()).complete("hi")


def test_transport_timeout_raises():
    import requests

    class SlowTransport(FakeTransport):
        def chat(self, **kwargs):
            raise requests.exceptions.Timeout()

    with pytest.raises(TimeoutError, match="請求超時"):
        _client(SlowTransport()).complete("hi")
