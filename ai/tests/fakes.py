"""
Transport seam 的第二個 adapter：scriptable fake。

與 SDK 的 RequestsTransport（生產 adapter）同一個 Transport protocol，
讓 ChatService 可以對著腳本化的回應測試，並可斷言 request shape。
純 Python，無额外相依。
"""

from ai_client import AIClient, AIConfig, ChatResponse


class ScriptedTransport:
    """依序回傳預先腳本的 ChatResponse，並記錄每次 request。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def chat(
        self,
        *,
        base_url,
        api_key,
        model,
        messages,
        max_tokens,
        timeout,
        temperature=None,
        tools=None,
        tool_choice=None,
    ) -> ChatResponse:
        self.requests.append(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        return self.responses.pop(0)


def make_client(responses) -> tuple[AIClient, ScriptedTransport]:
    """組裝 (AIClient, ScriptedTransport) 供 ChatService(client=...) 注入。"""
    transport = ScriptedTransport(responses)
    config = AIConfig(api_key="test-key")
    return AIClient(config, transport=transport), transport
