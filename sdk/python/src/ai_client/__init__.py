"""ai_client — 可注入的 OpenAI-compatible vLLM client。"""

from .client import AIClient
from .config import AIConfig
from .factory import create_client
from .transport import ChatMessage, ChatResponse, RequestsTransport, Transport

__all__ = [
    "AIClient",
    "AIConfig",
    "create_client",
    "ChatMessage",
    "ChatResponse",
    "RequestsTransport",
    "Transport",
]
