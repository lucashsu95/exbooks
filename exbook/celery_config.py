"""
Celery 設定
"""

import os

from celery.schedules import crontab


def _default_celery_redis_url() -> str:
    """Broker／結果後端預設使用 Redis DB 1，與快取 DB 0 分離。"""
    base = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0").rstrip("/")
    if base.endswith("/0"):
        return f"{base[:-2]}/1"
    return f"{base}/1"


broker_url = os.environ.get("CELERY_BROKER_URL") or _default_celery_redis_url()
result_backend = os.environ.get("CELERY_RESULT_BACKEND") or broker_url
timezone = "Asia/Taipei"

# 允許透過環境變數強制 eager mode（測試用），避免測試需要真實 Redis
task_always_eager = (
    os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
)  # noqa: F401
task_eager_propagates = task_always_eager  # noqa: F401

beat_schedule = {
    "process-due-books-daily": {
        "task": "deals.process_due_books",
        "schedule": crontab(hour=0, minute=0),
    },
    "send-due-reminders-daily": {
        "task": "deals.send_due_reminders",
        "schedule": crontab(hour=9, minute=0),
        "kwargs": {"days": 3},
    },
    "process-pending-ratings-daily": {
        "task": "deals.process_pending_ratings",
        "schedule": crontab(hour=8, minute=30),
    },
    "recalculate-trust-scores-weekly": {
        "task": "accounts.recalculate_trust_scores",
        "schedule": crontab(day_of_week="mon", hour=2, minute=0),
    },
    # --- Anomaly Detection ---
    "run-anomaly-detection-hourly": {
        "task": "core.run_anomaly_detection",
        "schedule": crontab(minute=0),  # Every hour at minute 0
    },
}
