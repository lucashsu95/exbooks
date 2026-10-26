import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from deals.models import LoanExtension

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

MAX_TOOL_LINES = 20


def _book_line(book) -> str:
    return f"#{book.pk}《{book.official_book.title}》｜{book.get_status_display()}｜持有者：{book.keeper.username}"


def _deal_line(deal, viewer, pending_extra_days) -> str:
    from django.utils import timezone

    # 出借者視角需要答得出「誰借了我的書」，故行內帶借閱者身分
    line = (
        f"#{deal.pk}《{deal.shared_book.official_book.title}》｜{deal.get_status_display()}"
        f"｜借閱者：{deal.applicant.username}"
    )
    if deal.due_date is not None:
        days_left = (deal.due_date - timezone.localdate()).days
        if days_left < 0:
            line += f"｜到期日：{deal.due_date:%Y-%m-%d}（已逾期 {-days_left} 天）"
        else:
            line += f"｜到期日：{deal.due_date:%Y-%m-%d}（剩 {days_left} 天）"
    if pending_extra_days is not None:
        # pending 的申請永遠是借閱者建的，出借者視角不能說「你已申請」
        if viewer == deal.applicant:
            line += f"｜你已申請延長 {pending_extra_days} 天（待審核）"
        else:
            line += f"｜借閱者已申請延長 {pending_extra_days} 天（待你審核）"
    return line


def _lines_or_total(lines: list[str], total: int, omitted_note: str) -> str:
    if total > MAX_TOOL_LINES:
        lines = lines[:MAX_TOOL_LINES]
        lines.append(omitted_note.format(omitted=total - MAX_TOOL_LINES))
    return "\n".join(lines)


@ToolRegistry.register(
    name="get_user_books",
    description="查詢目前使用者的書籍。OWNED＝使用者擁有（貢獻）的書；HELD＝使用者手上正持有的書；ALL＝兩者並集（預設）。",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["OWNED", "HELD", "ALL"],
                "description": "OWNED＝使用者擁有（貢獻）的書；HELD＝使用者手上正持有的書；ALL＝兩者並集（預設）。",
            }
        },
        "required": [],
    },
)
def get_user_books(user, status: str = "ALL") -> str:
    from django.db.models import Q
    from books.models import SharedBook

    status = str(status).upper()
    if status == "OWNED":
        books = SharedBook.objects.filter(owner=user)
    elif status == "HELD":
        books = SharedBook.objects.filter(keeper=user)
    elif status == "ALL":
        books = SharedBook.objects.filter(Q(owner=user) | Q(keeper=user))
    else:
        raise ValueError("status 只能為 OWNED、HELD 或 ALL。")
    books = books.select_related("official_book").order_by("-created_at")

    empty_messages = {
        "OWNED": "你沒有擁有的書籍。",
        "HELD": "你沒有持有的書籍。",
        "ALL": "你沒有符合的書籍。",
    }
    if not books.exists():
        return empty_messages[status]

    lines = [_book_line(book) for book in books]
    return _lines_or_total(
        lines, len(lines), "（另有 {omitted} 本未列出，可改用 OWNED 或 HELD 縮小範圍）"
    )


@ToolRegistry.register(
    name="get_borrowing_status",
    description="Get the status of current borrowing requests or active deals for the user.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_borrowing_status(user) -> str:
    from django.db.models import Q
    from deals.models import Deal, LoanExtension

    deals = (
        Deal.objects.filter(
            deal_type=Deal.DealType.LOAN,
            status__in=[Deal.Status.REQUESTED, Deal.Status.RESPONDED, Deal.Status.MEETED],
        )
        .filter(Q(applicant=user) | Q(responder=user))
        .select_related("shared_book__official_book")
        .order_by("-created_at")
    )
    if not deals.exists():
        return "你目前沒有進行中的借閱交易。"

    lines = []
    for deal in deals:
        pending = deal.extensions.filter(status=LoanExtension.Status.PENDING).first()
        lines.append(_deal_line(deal, user, pending.extra_days if pending else None))
    return _lines_or_total(lines, len(lines), "（另有 {omitted} 項未列出）")


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
                "minimum": LoanExtension.MIN_EXTRA_DAYS,
                "maximum": LoanExtension.MAX_EXTRA_DAYS,
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
        raise ValueError(
            f"days 需要是整數天數，{LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 之間。"
        )
    if not (
        LoanExtension.MIN_EXTRA_DAYS <= extra_days <= LoanExtension.MAX_EXTRA_DAYS
    ):
        raise ValueError(
            f"延長天數需為 {LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 天之間"
            f"（收到 {extra_days} 天）。請改用範圍內的數值重試。"
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
