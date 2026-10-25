"""
Service 層錯誤轉譯（錯誤契約見 GLOSSARY「慣例」）。

Service 層失敗一律 raise ValidationError / PermissionDenied（訊息為
使用者可讀中文）；View 層負責轉譯成 messages / HTTP 回應。
"""

from django.core.exceptions import ValidationError


def service_error_message(exc: Exception) -> str:
    """將 service 層例外轉成可顯示給使用者的訊息。

    注意：Django 的 ``ValidationError.__str__`` 走 ``repr(list(self))``，
    會產出 ``"['…']"`` 這種帶方括號與引號的串——絕不能直接進
    messages / HTTP 回應；使用者可讀的訊息在 ``.messages``。
    """
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return str(exc)
