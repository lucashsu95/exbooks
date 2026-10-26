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


# --- Pre-defined Tools ---
#
# 約定：所有 tool 函式的第一個參數是 `user`（由呼叫方注入的當前使用者），
# 其餘參數才來自 AI 的 function calling arguments（已 json.loads，值可能是字串）。
# 回傳一律 str；錯誤一律 raise，str(e) 會直接餵給 AI。


def _extension_day_bounds() -> tuple[int, int]:
    """延長天數範圍，以 LoanExtension.model validator 為唯一來源。"""
    from django.core.validators import MaxValueValidator, MinValueValidator
    from deals.models import LoanExtension

    min_days = max_days = None
    for validator in LoanExtension._meta.get_field("extra_days").validators:
        if isinstance(validator, MinValueValidator):
            min_days = validator.limit_value
        elif isinstance(validator, MaxValueValidator):
            max_days = validator.limit_value
    if min_days is None or max_days is None:
        raise RuntimeError("LoanExtension.extra_days 缺少 Min/MaxValueValidator")
    return min_days, max_days


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


_MIN_EXTRA_DAYS, _MAX_EXTRA_DAYS = _extension_day_bounds()


@ToolRegistry.register(
    name="request_renewal",
    description="Request a renewal for a book currently being borrowed.",
    parameters={
        "type": "object",
        "properties": {
            "deal_id": {
                "type": "string",
                "description": "UUID of the transaction/deal to renew.",
            },
            "days": {
                "type": "integer",
                "description": "Number of days to extend the borrowing period.",
                "minimum": _MIN_EXTRA_DAYS,
                "maximum": _MAX_EXTRA_DAYS,
            },
        },
        "required": ["deal_id"],
    },
    consent=ConsentRequirement.USER_CONFIRM,
)
def request_renewal(user, deal_id, days=7) -> str:
    import uuid

    from django.core.exceptions import ValidationError

    from core.error_messages import service_error_message
    from deals.models import Deal
    from deals.services.extension_service import request_extension

    not_found = f"交易 {deal_id} 不存在，請先用 get_borrowing_status 確認。"
    # malformed 值傳進 UUIDField 的 filter 會先炸 raw ValidationError，
    # 查不到（含格式不對）都回同一條友善訊息
    try:
        uuid.UUID(str(deal_id))
    except (TypeError, ValueError):
        raise ValueError(not_found)

    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None:
        raise ValueError(not_found)

    try:
        extra_days = int(days)
    except (TypeError, ValueError):
        raise ValueError(f"days 需要是整數天數，{_MIN_EXTRA_DAYS}~{_MAX_EXTRA_DAYS} 之間。")
    if not (_MIN_EXTRA_DAYS <= extra_days <= _MAX_EXTRA_DAYS):
        raise ValueError(
            f"延長天數需為 {_MIN_EXTRA_DAYS}~{_MAX_EXTRA_DAYS} 天之間（收到 {extra_days} 天）。"
            "請改用範圍內的數值重試。"
        )

    # 權限與書狀態由 service 判定（responder 與路人同吃 service 的權限錯誤）
    # service 的 ValidationError 經 str() 會帶出 "['…']" 括號，轉成一般 ValueError
    try:
        request_extension(deal, user, extra_days)
    except ValidationError as e:
        raise ValueError(service_error_message(e)) from None
    return (
        f"已為交易 #{deal.pk}《{deal.shared_book.official_book.title}》"
        f"提交延長 {extra_days} 天的申請，目前為「待審核」，"
        "需 book 所有者或持有者核准後才會實際延長到期日。"
    )
