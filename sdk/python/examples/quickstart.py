"""快速開始：直接吃環境變數。"""

from ai_client import create_client

client = create_client()
print(client.complete("用一句話說明什麼是產銷履歷"))
