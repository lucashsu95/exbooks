import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="accounts.recalculate_trust_scores")
def recalculate_trust_scores():
    from accounts.services.trust_service import recalculate_all_trust_scores

    logger.info("Task started", extra={"task": "accounts.recalculate_trust_scores"})
    try:
        recalculate_all_trust_scores()
        logger.info("Task completed", extra={"task": "accounts.recalculate_trust_scores"})
    except Exception:
        logger.exception("Task failed", extra={"task": "accounts.recalculate_trust_scores"})
        raise
