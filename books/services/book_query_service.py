import logging

from django.core.cache import cache
from django.db.models import Count

from books.models import SharedBook

logger = logging.getLogger(__name__)

HOT_BOOKS_TTL = 60 * 5


def get_hot_books(user) -> list:
    """取得熱門書籍（排除使用者自己的書）。結果快取 5 分鐘。"""
    cache_key = f"hot_books:{user.id}"
    result = cache.get(cache_key)
    if result is None:
        logger.debug("hot books cache miss", extra={"user_id": user.id})
        result = list(
            SharedBook.objects.select_related("official_book", "keeper__profile")
            .prefetch_related("photos")
            .filter(status=SharedBook.Status.TRANSFERABLE)
            .exclude(keeper=user)
            .annotate(deal_count=Count("deals"))
            .order_by("-deal_count", "-updated_at")[:3]
        )
        cache.set(cache_key, result, HOT_BOOKS_TTL)
    else:
        logger.debug("hot books cache hit", extra={"user_id": user.id})
    logger.debug(
        "hot books fetched",
        extra={"user_id": user.id, "count": len(result)},
    )
    return result
