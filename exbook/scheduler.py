"""APScheduler 整合：集中管理排程任務。"""

from __future__ import annotations

import atexit
import importlib
import logging
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

_background_scheduler: Any | None = None


def _run_management_command(command_name: str, **kwargs: Any) -> None:
    """執行管理命令並記錄結果。"""
    logger.info("開始執行排程命令：%s", command_name)
    try:
        call_command(command_name, **kwargs)
        logger.info("排程命令執行完成：%s", command_name)
    except Exception:  # pragma: no cover
        logger.exception("排程命令執行失敗：%s", command_name)


def _job_settings() -> Mapping[str, Any]:
    """讀取 APScheduler 任務設定。"""
    jobs = getattr(settings, "APSCHEDULER_JOBS", {})
    if isinstance(jobs, Mapping):
        return jobs
    return {}


def configure_scheduler_jobs(
    scheduler: Any,
) -> None:
    """註冊所有排程任務。"""
    jobs = _job_settings()
    reminder_days = int(getattr(settings, "APSCHEDULER_DUE_REMINDER_DAYS", 3))

    process_due_books = jobs.get("process_due_books", {"hour": 0, "minute": 0})
    send_due_reminders = jobs.get("send_due_reminders", {"hour": 9, "minute": 0})
    recalculate_trust_scores = jobs.get(
        "recalculate_trust_scores", {"day_of_week": "mon", "hour": 2, "minute": 0}
    )
    process_pending_ratings = jobs.get(
        "process_pending_ratings", {"hour": 8, "minute": 30}
    )

    scheduler.add_job(
        _run_management_command,
        trigger="cron",
        id="process_due_books",
        replace_existing=True,
        kwargs={"command_name": "process_due_books"},
        **process_due_books,
    )
    scheduler.add_job(
        _run_management_command,
        trigger="cron",
        id="send_due_reminders",
        replace_existing=True,
        kwargs={"command_name": "send_due_reminders", "days": reminder_days},
        **send_due_reminders,
    )
    scheduler.add_job(
        _run_management_command,
        trigger="cron",
        id="recalculate_trust_scores",
        replace_existing=True,
        kwargs={"command_name": "recalculate_trust_scores"},
        **recalculate_trust_scores,
    )
    scheduler.add_job(
        _run_management_command,
        trigger="cron",
        id="process_pending_ratings",
        replace_existing=True,
        kwargs={"command_name": "process_pending_ratings"},
        **process_pending_ratings,
    )


def _create_background_scheduler() -> Any:
    background_module = importlib.import_module("apscheduler.schedulers.background")
    background_scheduler_cls = getattr(background_module, "BackgroundScheduler")
    job_defaults = getattr(settings, "APSCHEDULER_JOB_DEFAULTS", {})
    scheduler = background_scheduler_cls(
        timezone=getattr(settings, "APSCHEDULER_TIMEZONE", settings.TIME_ZONE),
        job_defaults=job_defaults,
    )
    configure_scheduler_jobs(scheduler)
    return scheduler


def start_background_scheduler() -> bool:
    """啟動背景排程器（runserver 開發模式）。"""
    global _background_scheduler

    if not getattr(settings, "APSCHEDULER_ENABLED", True):
        logger.info("APScheduler 已停用（APSCHEDULER_ENABLED=False）")
        return False

    if _background_scheduler and _background_scheduler.running:
        logger.debug("APScheduler 已在執行中，略過重複啟動")
        return False

    scheduler = _create_background_scheduler()
    scheduler.start()
    _background_scheduler = scheduler
    atexit.register(stop_background_scheduler)
    logger.info("APScheduler 已啟動（BackgroundScheduler）")
    return True


def stop_background_scheduler() -> bool:
    """停止背景排程器。"""
    global _background_scheduler

    if not _background_scheduler:
        return False
    if _background_scheduler.running:
        _background_scheduler.shutdown(wait=False)
    _background_scheduler = None
    logger.info("APScheduler 已停止（BackgroundScheduler）")
    return True


def run_blocking_scheduler() -> None:
    """啟動阻塞式排程器（生產模式獨立程序）。"""
    if not getattr(settings, "APSCHEDULER_ENABLED", True):
        logger.warning("APScheduler 已停用（APSCHEDULER_ENABLED=False）")
        return

    blocking_module = importlib.import_module("apscheduler.schedulers.blocking")
    blocking_scheduler_cls = getattr(blocking_module, "BlockingScheduler")
    job_defaults = getattr(settings, "APSCHEDULER_JOB_DEFAULTS", {})
    scheduler = blocking_scheduler_cls(
        timezone=getattr(settings, "APSCHEDULER_TIMEZONE", settings.TIME_ZONE),
        job_defaults=job_defaults,
    )
    configure_scheduler_jobs(scheduler)
    logger.info("APScheduler 已啟動（BlockingScheduler）")
    scheduler.start()
