import inspect
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from deals.models import LoanExtension

logger = logging.getLogger(__name__)


class ToolError(ValueError):
    """tool 刻意 raise 的錯誤：訊息是寫給模型看的（繁中、可自我修正），
    orchestrator 會原樣回灌與持久化。其他例外一律視為非預期，
    訊息只進 log、不外流（可能含內部細節）。"""


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
# 回傳一律 str；可預期的錯誤 raise ToolError（訊息會直接餵給 AI），
# 其他例外被 orchestrator 視為非預期：只記 log，模型只看到通用錯誤訊息。

MAX_TOOL_LINES = 20


def _book_line(book) -> str:
    return f"#{book.pk}《{book.official_book.title}》｜{book.get_status_display()}｜持有者：{book.keeper.username}"


def _deal_line(deal, viewer, pending) -> str:
    from django.utils import timezone

    from deals.services.extension_service import is_extension_eligible

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
    if pending is not None:
        # pending 的申請永遠是借閱者建的，出借者視角不能說「你已申請」
        if viewer == deal.applicant:
            line += f"｜你已申請延長 {pending.extra_days} 天（待審核）"
        else:
            line += f"｜借閱者已申請延長 {pending.extra_days} 天（待你審核）"
    # 資格判定與 service 同一來源；pending 必須傳入（prefetch 已取回），
    # 省略會每筆 deal 多一筆 DB 查詢，打破讀 tool 的查詢量上界
    if is_extension_eligible(viewer, deal, pending=pending):
        line += "（可申請延長）"
    return line


def _lines_or_total(lines: list[str], total: int, omitted_note: str) -> str:
    """total 是全集筆數；lines 應由呼叫方 slice 到 MAX_TOOL_LINES，這裡再切一次兜底。"""
    if total > MAX_TOOL_LINES:
        lines = lines[:MAX_TOOL_LINES]
        lines.append(omitted_note.format(omitted=total - MAX_TOOL_LINES))
    return "\n".join(lines)


def filter_args_by_signature(func: Callable, args: Dict[str, Any]) -> Dict[str, Any]:
    """只留 tool signature 內的參數（user 由呼叫方注入），未知 kwarg 靜默丟掉。

    在同意建立的來源端（orchestrator）過濾一次，存檔＝顯示＝執行。
    """
    accepted = set(inspect.signature(func).parameters) - {"user"}
    return {k: v for k, v in args.items() if k in accepted}


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
        raise ToolError("status 只能為 OWNED、HELD 或 ALL。")
    # _book_line 要 official_book.title 與 keeper.username，一併 join 掉避免 N+1
    books = books.select_related("official_book", "keeper").order_by("-created_at")

    empty_messages = {
        "OWNED": "你沒有擁有的書籍。",
        "HELD": "你沒有持有的書籍。",
        "ALL": "你沒有符合的書籍。",
    }
    total = books.count()
    if total == 0:
        return empty_messages[status]

    # 截斷在物化前：大帳號只取回 MAX_TOOL_LINES 行，tail note 用全集 count
    lines = [_book_line(book) for book in books[:MAX_TOOL_LINES]]
    return _lines_or_total(
        lines, total, "（另有 {omitted} 本未列出，可改用 OWNED 或 HELD 縮小範圍）"
    )


@ToolRegistry.register(
    name="get_borrowing_status",
    description="列出你目前進行中的借閱交易（含狀態、到期日、待審核的延長申請），並標記哪些可申請延長。",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_borrowing_status(user) -> str:
    from django.db.models import Prefetch, Q
    from deals.models import Deal, LoanExtension

    deals = (
        Deal.objects.filter(
            deal_type=Deal.DealType.LOAN,
            status__in=[Deal.Status.REQUESTED, Deal.Status.RESPONDED, Deal.Status.MEETED],
        )
        .filter(Q(applicant=user) | Q(responder=user))
        # _deal_line 要 official_book.title 與 applicant.username，一併 join 掉避免 N+1
        .select_related("shared_book__official_book", "applicant")
        # 每筆 deal 的 pending extension 一次 batch 取回，不再逐筆 filter
        .prefetch_related(
            Prefetch(
                "extensions",
                queryset=LoanExtension.objects.filter(status=LoanExtension.Status.PENDING),
            )
        )
        .order_by("-created_at")
    )
    total = deals.count()
    if total == 0:
        return "你目前沒有進行中的借閱交易。"

    lines = []
    for deal in deals[:MAX_TOOL_LINES]:  # 截斷在物化前
        # 已 prefetch（只有 PENDING），pending 物件直接傳給 _deal_line 的資格判定
        pending = deal.extensions.first()
        lines.append(_deal_line(deal, user, pending))
    return _lines_or_total(lines, total, "（另有 {omitted} 項未列出）")


@ToolRegistry.register(
    name="request_renewal",
    description=(
        f"為借閱中的書申請延長到期日。僅該筆交易的借閱者本人可申請，且書必須已面交、"
        f"狀態為借閱中；天數需為 {LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 之間。"
        f"提交後為「待審核」，需書的擁有者核准。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "deal_id": {
                "type": "string",
                "description": "要延長借閱的交易 ID（UUID，可從 get_borrowing_status 取得）",
            },
            "days": {
                "type": "integer",
                "description": f"延長天數（{LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 之間）",
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
        raise ToolError(not_found)

    deal = Deal.objects.filter(pk=deal_id).first()
    if deal is None:
        raise ToolError(not_found)

    try:
        extra_days = int(days)
    except (TypeError, ValueError):
        raise ToolError(
            f"days 需要是整數天數，{LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 之間。"
        )
    if not (
        LoanExtension.MIN_EXTRA_DAYS <= extra_days <= LoanExtension.MAX_EXTRA_DAYS
    ):
        raise ToolError(
            f"延長天數需為 {LoanExtension.MIN_EXTRA_DAYS}~{LoanExtension.MAX_EXTRA_DAYS} 天之間"
            f"（收到 {extra_days} 天）。請改用範圍內的數值重試。"
        )

    # 權限與書狀態由 service 判定（responder 與路人同吃 service 的權限錯誤）
    # service 的 ValidationError 經 str() 會帶出 "['…']" 括號，轉成 ToolError
    try:
        request_extension(deal, user, extra_days)
    except ValidationError as e:
        raise ToolError(service_error_message(e)) from None
    return (
        f"已為交易 #{deal.pk}《{deal.shared_book.official_book.title}》"
        f"提交延長 {extra_days} 天的申請，目前為「待審核」，"
        # 面交後 keeper 就是借書人本人、service 又禁止自審自批，有效審核者只有 owner
        "需書的擁有者核准後才會實際延長到期日。"
    )
