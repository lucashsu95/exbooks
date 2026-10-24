"""依賴注入示範：注入 config、自訂 transport、mock transport。"""

from ai_client import AIClient, AIConfig, ChatResponse, RequestsTransport

# 1) 注入 config（不走 env）
config = AIConfig(
    api_key="sk-...",
    base_url="https://chatapi.ntubimdbirc.tw/v1",
    model="Gemma4-31B",
    system_prompt="你是食安助理，只根據資料回答。",
)

# 2) 注入自訂 transport（例如加 logging / retry）
class LoggingTransport(RequestsTransport):
    def chat(self, **kwargs):
        print(f"→ model={kwargs['model']}")
        response = super().chat(**kwargs)
        print(f"← {len(response.content)} 字元")
        return response

client = AIClient(config=config, transport=LoggingTransport())
print(client.complete("說明什麼是食品業者登錄"))

# 3) 注入 mock transport（測試用，不打真實 API）
class MockTransport:
    def chat(self, **kwargs):
        return ChatResponse(content="這是假的回應，用於測試。")

mock_client = AIClient(config=config, transport=MockTransport())
print(mock_client.complete("任何問題"))
