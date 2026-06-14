"""交換事件（稽核）寫入 — 僅新增，不修改。"""

from __future__ import annotations

import logging
from typing import Any

from books.models import SharedBook
from django.contrib.auth.models import AbstractBaseUser

from deals.models import Deal, ExchangeEvent

logger = logging.getLogger(__name__)


def record_exchange_event(
    *,
    shared_book: SharedBook,
    event_type: str,
    deal: Deal | None = None,
    actor: AbstractBaseUser | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExchangeEvent:
    event = ExchangeEvent.objects.create(
        shared_book=shared_book,
        deal=deal,
        event_type=event_type,
        actor=actor,
        metadata=metadata or {},
    )
    logger.debug(
        "exchange event recorded",
        extra={
            "event_id": event.id,
            "event_type": event_type,
            "book_id": shared_book.id,
            "deal_id": deal.id if deal else None,
        },
    )
    return event
