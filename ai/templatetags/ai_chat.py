"""聊天 widget 用的 template tag：把伺服器端時間預算注入前端，避免兩邊各自寫死。"""

from django import template

from ai.services.chat_orchestrator import CLIENT_TIMEOUT_SECONDS

register = template.Library()


@register.simple_tag
def chat_client_timeout_ms() -> int:
    """用戶端等待一輪回覆的上限（毫秒）。"""
    return int(CLIENT_TIMEOUT_SECONDS * 1000)
