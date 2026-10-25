"""
交易清單（Deal feed）查詢服務。

「什麼交易算待回應 / 待我申請 / 待面交 / 待評價 / 歷史」的 tab 定義
在此為唯一來源；view 與未來其他入口都走 get_feed。
"""

from collections import OrderedDict

from django.db.models import Count, Q

from deals.models import Deal

TABS = ("pending", "pending_applicant", "meeting", "rating", "history")


def _base_deals(user):
    return (
        Deal.objects.filter(Q(applicant=user) | Q(responder=user))
        .select_related(
            "shared_book__official_book",
            "applicant__profile",
            "responder__profile",
        )
        .prefetch_related("shared_book__photos")
    )


def tab_filter(tab, user):
    """各 tab 的交易分類規則（BR-3.6 分組前的原始集合）。"""
    meted_rated_filter = Q(status=Deal.Status.MEETED) & (
        Q(applicant=user, applicant_rated=True)
        | Q(responder=user, responder_rated=True)
    )
    filters = {
        "pending": Q(responder=user, status=Deal.Status.REQUESTED),
        "pending_applicant": Q(applicant=user, status=Deal.Status.REQUESTED),
        "meeting": Q(status=Deal.Status.RESPONDED),
        "rating": Q(status=Deal.Status.MEETED)
        & (
            Q(applicant=user, applicant_rated=False)
            | Q(responder=user, responder_rated=False)
        ),
        "history": Q(status__in=[Deal.Status.DONE, Deal.Status.CANCELLED])
        | meted_rated_filter,
    }
    return filters[tab]


class DealFeed:
    """提供 template 相容介面（iter/bool/count）的交易清單。"""

    def __init__(self, items=None, total=0):
        self._items = items or []
        self._total = total

    def __iter__(self):
        return iter(self._items)

    def __bool__(self):
        return bool(self._items)

    def count(self):
        return self._total


def _grouped_pending(deals):
    """BR-3.6：將待回應申請依書籍分組（保留既有資料結構）。"""
    grouped = OrderedDict()
    for deal in deals:
        book = deal.shared_book
        if book not in grouped:
            grouped[book] = []
        grouped[book].append(deal)
    return grouped


def get_feed(user, tab):
    """取得某 tab 的完整清單 context（view 直接 render）。"""
    if tab not in TABS:
        tab = "pending"

    deals_base = _base_deals(user)
    count_keys = {
        "pending": "pending_responder_count",
        "pending_applicant": "pending_applicant_count",
        "meeting": "pending_meeting_count",
        "rating": "pending_rating_count",
        "history": "history_count",
    }
    counts = deals_base.aggregate(
        **{
            count_keys[tab_name]: Count("pk", filter=tab_filter(tab_name, user))
            for tab_name in TABS
        }
    )

    deals = list(deals_base.filter(tab_filter(tab, user)).distinct())

    feeds = {
        name: DealFeed(deals, counts[count_keys[name]]) for name in TABS
    }

    def feed_for(name):
        return feeds[name] if name == tab else DealFeed(total=feeds[name]._total)

    return {
        "current_tab": tab,
        "deals": deals,
        "pending_responder": feed_for("pending"),
        "grouped_pending": _grouped_pending(feed_for("pending")),
        "pending_applicant": feed_for("pending_applicant"),
        "pending_meeting": feed_for("meeting"),
        "pending_rating": feed_for("rating"),
        "history": feed_for("history"),
    }
