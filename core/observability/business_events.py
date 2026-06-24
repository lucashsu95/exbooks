"""
Structured business event logging for domain events.

Provides a standardized emitter for business events (e.g., deal.created,
trust_score.changed) that automatically enriches them with trace context
and writes to the designated logger.

Usage:
    from core.observability.business_events import emit_business_event

    emit_business_event("deal.created", {
        "deal_id": str(deal.id),
        "type": deal.deal_type,
        "applicant_id": str(deal.applicant_id),
    })

    # For compliance-critical events:
    from core.observability.business_events import emit_audit_event
    emit_audit_event("keeper.transferred", {...})
"""

import logging

from core.observability.trace_context import (
    get_trace_id,
    get_span_id,
    get_request_id,
)

# Separate loggers for different tiers
_business_logger = logging.getLogger("business")
_audit_logger = logging.getLogger("audit")


def emit_business_event(event_type: str, payload: dict, level: int = logging.INFO) -> None:
    """Emit a structured business event.

    Business events represent domain-level occurrences (e.g., deal created,
    book overdue, trust score changed) for analytics and product monitoring.

    Args:
        event_type: Dot-separated event category (e.g., "deal.created").
        payload: Key-value pairs describing the event.
        level: Log level (default: INFO).
    """
    extra = {
        "event_type": event_type,
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
        "request_id": get_request_id(),
        **payload,
    }
    _business_logger.log(level, event_type, extra=extra)


def emit_audit_event(event_type: str, payload: dict) -> None:
    """Emit a compliance-critical audit event.

    Audit events are written to the immutable audit log stream. These record
    state transitions that may be needed for dispute resolution or regulatory
    compliance (e.g., keeper transfers, trust score changes, book ownership changes).

    Args:
        event_type: Dot-separated event category (e.g., "keeper.transferred").
        payload: Key-value pairs describing the audit entry.
    """
    extra = {
        "event_type": event_type,
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
        "request_id": get_request_id(),
        **payload,
    }
    _audit_logger.info(event_type, extra=extra)