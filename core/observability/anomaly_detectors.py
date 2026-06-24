"""
Domain-aware anomaly detectors for the Exbooks book-sharing platform.

Detects business-level anomalies such as trust score cliff drops and overdue
cascades, and logs them to the system alert logger for monitoring.

All detectors are safe to call from Celery beat tasks.
"""

import logging
from datetime import timedelta

from django.db.models import Avg, Count, F, Max, Min, Q
from django.utils import timezone

from core.observability.trace_context import new_trace

logger = logging.getLogger("system.alerts")


def check_trust_score_cliff_drop() -> None:
    """Alert if any user's trust score drops more than 20% in 1 hour.

    Queries TrustScoreLedger for users with multiple entries in the last
    hour and flags those with a >20% drop from their peak.
    """
    from accounts.models import TrustScoreLedger

    since = timezone.now() - timedelta(hours=1)
    drops = (
        TrustScoreLedger.objects
        .filter(created_at__gte=since)
        .values("user_id")
        .annotate(
            min_score=Min("trust_score"),
            max_score=Max("trust_score"),
        )
        .filter(max_score__gt=0, min_score__lt=F("max_score") * 0.8)
    )

    for d in drops:
        drop_pct = round(100 - (d["min_score"] / d["max_score"]) * 100, 1)
        logger.warning(
            "trust_score_cliff_drop user=%s max=%d min=%d drop=%.1f%%",
            d["user_id"], d["max_score"], d["min_score"], drop_pct,
            extra={
                "anomaly_type": "trust_score_cliff_drop",
                "user_id": d["user_id"],
                "max_score": d["max_score"],
                "min_score": d["min_score"],
                "drop_pct": drop_pct,
            },
        )


def check_overdue_cascade() -> None:
    """Alert if overdue rate among active deals exceeds 30%.

    Monitors deals in MEETED status past their due_date. If overdue ratio
    exceeds the threshold among a significant sample, logs a warning.
    """
    from deals.models.deal import Deal

    now = timezone.now().date()
    active_deals = Deal.objects.filter(
        status=Deal.Status.MEETED,
        due_date__isnull=False,
    )
    total_active = active_deals.count()

    if total_active < 10:
        return  # Not enough data to draw a conclusion

    overdue_count = active_deals.filter(due_date__lt=now).count()
    overdue_rate = overdue_count / total_active

    if overdue_rate > 0.30:
        logger.warning(
            "overdue_cascade rate=%.1f%% total=%d overdue=%d",
            overdue_rate * 100, total_active, overdue_count,
            extra={
                "anomaly_type": "overdue_cascade",
                "overdue_rate": round(overdue_rate, 3),
                "total_active": total_active,
                "overdue_count": overdue_count,
            },
        )


def run_all() -> None:
    """Run all anomaly detectors with a fresh trace context."""
    new_trace()
    check_trust_score_cliff_drop()
    check_overdue_cascade()