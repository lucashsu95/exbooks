"""
核心異常類別 - 統一專案的異常處理策略

遵循「好的程式碼不需要註解」原則，透過清晰的命名使異常自解釋。
"""

from typing import Optional, Any
from django.core.exceptions import ValidationError as DjangoValidationError


class ServiceError(Exception):
    """所有服務層異常的基礎類別"""

    def __init__(
        self, message: str, code: Optional[str] = None, details: Optional[Any] = None
    ):
        """
        初始化服務異常

        Args:
            message: 人類可讀的錯誤訊息
            code: 錯誤代碼（用於程式化處理）
            details: 詳細錯誤資訊（字典、列表等）
        """
        self.message = message
        self.code = code
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        """字串表示形式"""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ValidationError(ServiceError):
    """輸入驗證失敗"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """
        初始化驗證異常

        Args:
            message: 驗證失敗訊息
            field: 相關欄位名稱（可選）
        """
        code = "validation_error"
        details = {"field": field} if field else None
        super().__init__(message, code=code, details=details, **kwargs)


class PermissionError(ServiceError):
    """權限檢查失敗"""

    def __init__(
        self, message: str, required_permission: Optional[str] = None, **kwargs
    ):
        """
        初始化權限異常

        Args:
            message: 權限錯誤訊息
            required_permission: 需要的權限（可選）
        """
        code = "permission_error"
        details = (
            {"required_permission": required_permission}
            if required_permission
            else None
        )
        super().__init__(message, code=code, details=details, **kwargs)


class NotFoundError(ServiceError):
    """資源未找到"""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化未找到異常

        Args:
            message: 未找到訊息
            resource_type: 資源類型（如 'user', 'book'）
            resource_id: 資源 ID
        """
        code = "not_found"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, code=code, details=details, **kwargs)


class ConflictError(ServiceError):
    """資源衝突（如唯一約束違反）"""

    def __init__(self, message: str, conflicting_field: Optional[str] = None, **kwargs):
        """
        初始化衝突異常

        Args:
            message: 衝突訊息
            conflicting_field: 衝突的欄位名稱（可選）
        """
        code = "conflict_error"
        details = (
            {"conflicting_field": conflicting_field} if conflicting_field else None
        )
        super().__init__(message, code=code, details=details, **kwargs)


class StateTransitionError(ServiceError):
    """狀態轉換失敗（FSM 相關）"""

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化狀態轉換異常

        Args:
            message: 狀態轉換失敗訊息
            current_state: 當前狀態
            target_state: 目標狀態
        """
        code = "state_transition_error"
        details = {"current_state": current_state, "target_state": target_state}
        super().__init__(message, code=code, details=details, **kwargs)


class ExternalServiceError(ServiceError):
    """外部服務呼叫失敗"""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        """
        初始化外部服務異常

        Args:
            message: 外部服務錯誤訊息
            service_name: 服務名稱（如 'email', 'push'）
            status_code: HTTP 狀態碼（如果適用）
        """
        code = "external_service_error"
        details = {"service_name": service_name, "status_code": status_code}
        super().__init__(message, code=code, details=details, **kwargs)


class BusinessRuleError(ServiceError):
    """業務規則違反"""

    def __init__(self, message: str, rule_name: Optional[str] = None, **kwargs):
        """
        初始化業務規則異常

        Args:
            message: 業務規則違反訊息
            rule_name: 規則名稱（可選）
        """
        code = "business_rule_error"
        details = {"rule_name": rule_name} if rule_name else None
        super().__init__(message, code=code, details=details, **kwargs)


class IntegrityError(ServiceError):
    """資料完整性錯誤"""

    def __init__(self, message: str, related_models: Optional[list] = None, **kwargs):
        """
        初始化完整性異常

        Args:
            message: 完整性錯誤訊息
            related_models: 相關的模型列表（可選）
        """
        code = "integrity_error"
        details = {"related_models": related_models} if related_models else None
        super().__init__(message, code=code, details=details, **kwargs)


# ============================================================================
# 輔助函數
# ============================================================================


def raise_if_invalid(condition: bool, exception_class: type, message: str, **kwargs):
    """
    如果條件不滿足則拋出異常

    Args:
        condition: 檢查條件
        exception_class: 異常類別
        message: 異常訊息
        **kwargs: 傳遞給異常的額外參數

    Raises:
        指定的異常類別
    """
    if not condition:
        raise exception_class(message, **kwargs)


def convert_validation_error(
    validation_error: DjangoValidationError,
) -> ValidationError:
    """
    將 Django ValidationError 轉換為自定義 ValidationError

    Args:
        validation_error: Django ValidationError 實例

    Returns:
        ValidationError: 自定義驗證異常
    """
    # 提取錯誤訊息
    if hasattr(validation_error, "message_dict"):
        # 表單驗證錯誤
        messages = []
        for field, errors in validation_error.message_dict.items():
            for error in errors:
                messages.append(f"{field}: {error}")
        message = "; ".join(messages)
    elif hasattr(validation_error, "messages"):
        # 單一錯誤訊息列表
        message = "; ".join(validation_error.messages)
    else:
        # 單一錯誤訊息
        message = str(validation_error)

    return ValidationError(message=message)


def create_not_found(resource_type: str, resource_id: Any) -> NotFoundError:
    """
    建立標準的「未找到」異常

    Args:
        resource_type: 資源類型（如 'user', 'book'）
        resource_id: 資源 ID

    Returns:
        NotFoundError: 未找到異常
    """
    message = f"{resource_type} 未找到（ID: {resource_id}）"
    return NotFoundError(
        message=message,
        resource_type=resource_type,
        resource_id=str(resource_id),
    )


def create_permission_denied(action: str, resource: str = None) -> PermissionError:
    """
    建立標準的「權限不足」異常

    Args:
        action: 嘗試執行的動作
        resource: 資源名稱（可選）

    Returns:
        PermissionError: 權限異常
    """
    if resource:
        message = f"沒有權限對 {resource} 執行 {action}"
    else:
        message = f"沒有權限執行 {action}"

    return PermissionError(message=message)
