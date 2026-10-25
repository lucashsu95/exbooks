"""
Service 層錯誤轉譯（core.error_messages）。

背景：Django 的 ``ValidationError.__str__`` 走 ``repr(list(self))``，
會產出 ``"['…']"`` 這種帶方括號與引號的輸出——view 若直接
``str(e)`` 進 messages / HTTP 回應，會把方括號秀給使用者。
"""

from django.core.exceptions import PermissionDenied, ValidationError

from core.error_messages import service_error_message


def test_validation_error_str_has_brackets():
    """紀錄被規避的行為：str(ValidationError) 帶方括號。"""
    exc = ValidationError("此交易已結束，無法再發送留言。")
    assert "[" in str(exc)
    assert service_error_message(exc) == "此交易已結束，無法再發送留言。"


def test_validation_error_multiple_messages_joined():
    exc = ValidationError(["第一條", "第二條"])
    assert service_error_message(exc) == "第一條; 第二條"


def test_permission_denied_passthrough():
    exc = PermissionDenied("只有持有者可以申請例外處理")
    assert service_error_message(exc) == "只有持有者可以申請例外處理"


def test_unexpected_exception_passthrough():
    assert service_error_message(ValueError("boom")) == "boom"
