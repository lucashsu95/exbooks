"""
統一的 API Response 格式。

所有 JSON API 端點應使用此模組以確保回應格式一致。

格式規範：
- 成功：{"success": true, "data": {...}, "message": "..."}
- 失敗：{"success": false, "error": {"code": "...", "message": "..."}}
"""

from django.http import JsonResponse
from typing import Optional


def api_success(
    data: Optional[dict] = None,
    message: Optional[str] = None,
    status: int = 200,
) -> JsonResponse:
    """
    回傳統一的成功回應。

    Args:
        data: 回應資料（可選）
        message: 成功訊息（可選）
        status: HTTP 狀態碼（預設 200）

    Returns:
        JsonResponse: 標準化的成功回應
    """
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
    return JsonResponse(response, status=status)


def api_error(
    message: str,
    code: Optional[str] = None,
    status: int = 400,
    details: Optional[dict] = None,
) -> JsonResponse:
    """
    回傳統一的錯誤回應。

    Args:
        message: 錯誤訊息
        code: 錯誤代碼（可選，如 "VALIDATION_ERROR", "NOT_FOUND"）
        status: HTTP 狀態碼（預設 400）
        details: 額外錯誤詳情（可選）

    Returns:
        JsonResponse: 標準化的錯誤回應
    """
    error = {"message": message}
    if code is not None:
        error["code"] = code
    if details is not None:
        error["details"] = details

    return JsonResponse(
        {"success": False, "error": error},
        status=status,
    )


# 預定義的錯誤代碼
class ErrorCode:
    """標準錯誤代碼常數。"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_JSON = "INVALID_JSON"
    MISSING_FIELD = "MISSING_FIELD"
