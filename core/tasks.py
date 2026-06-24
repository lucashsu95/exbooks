import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.run_anomaly_detection")
def run_anomaly_detection():
    from core.observability.anomaly_detectors import run_all

    logger.info("Task started", extra={"task": "core.run_anomaly_detection"})
    try:
        run_all()
        logger.info("Task completed", extra={"task": "core.run_anomaly_detection"})
    except Exception:
        logger.exception("Task failed", extra={"task": "core.run_anomaly_detection"})
        raise
