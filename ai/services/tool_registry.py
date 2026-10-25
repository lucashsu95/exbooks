import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConsentRequirement(Enum):
    """Defines if a tool requires explicit user consent before execution."""

    NOT_REQUIRED = auto()
    USER_CONFIRM = auto()


@dataclass
class ToolDefinition:
    """Represents a tool available for AI function calling."""

    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable
    consent: ConsentRequirement = ConsentRequirement.NOT_REQUIRED


class ToolRegistry:
    """
    Registry for tools available to the AI chatbot.
    """

    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        consent: ConsentRequirement = ConsentRequirement.NOT_REQUIRED,
    ) -> Callable:
        """Decorator to register a function as a tool."""

        def decorator(func: Callable) -> Callable:
            cls._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                func=func,
                consent=consent,
            )
            logger.debug("tool registered", extra={"tool_name": name})
            return func

        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolDefinition]:
        """Retrieve a tool definition by name."""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> List[ToolDefinition]:
        """Retrieve all registered tool definitions."""
        return list(cls._tools.values())


# --- Pre-defined Tools (Placeholders for T2-2) ---
#
# 約定：所有 tool 函式的第一個參數是 `user`（由呼叫方注入的當前使用者），
# 其餘參數才來自 AI 的 function calling arguments。


@ToolRegistry.register(
    name="get_user_books",
    description="Retrieve a list of books owned or currently held by the authenticated user.",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["OWNED", "HELD", "ALL"],
                "description": "Filter by ownership or current possession status.",
            }
        },
        "required": [],
    },
)
def get_user_books(user, status: str = "ALL") -> str:
    """Placeholder for retrieving user books."""
    return "Tool 'get_user_books' executed (Placeholder)"


@ToolRegistry.register(
    name="get_borrowing_status",
    description="Get the status of current borrowing requests or active deals for the user.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_borrowing_status(user) -> str:
    """Placeholder for retrieving borrowing status."""
    return "Tool 'get_borrowing_status' executed (Placeholder)"


@ToolRegistry.register(
    name="request_renewal",
    description="Request a renewal for a book currently being borrowed.",
    parameters={
        "type": "object",
        "properties": {
            "deal_id": {
                "type": "integer",
                "description": "The ID of the transaction/deal to renew.",
            },
            "days": {
                "type": "integer",
                "description": "Number of days to extend the borrowing period.",
            },
        },
        "required": ["deal_id"],
    },
    consent=ConsentRequirement.USER_CONFIRM,
)
def request_renewal(user, deal_id: int, days: int = 7) -> str:
    """Placeholder for requesting a book renewal."""
    from django.core.exceptions import PermissionDenied, ValidationError
    from deals.models import Deal

    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None:
        raise ValidationError(f"交易 {deal_id} 不存在。")
    if user not in (deal.applicant, deal.responder):
        raise PermissionDenied("您不是此交易的當事人，無法申請延期。")
    # 佔位實作：只做身份驗證、沒有真正建立延期——回傳文案不可稱「已執行」，
    # 否則 AI 會把 no-op 當成成功告知使用者
    return (
        f"Tool 'request_renewal' verified ownership for deal {deal_id} "
        f"(no-op placeholder: renewal was NOT actually requested)"
    )
