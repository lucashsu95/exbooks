"""獨立啟動 APScheduler 的管理指令。"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "以獨立程序啟動 APScheduler（適用生產環境）"

    def _run_command(self, command_name, **kwargs):
        call_command(command_name, **kwargs)

    def handle(self, *args, **options):
        self.stdout.write("啟動 APScheduler（BlockingScheduler）...")

        scheduler = BlockingScheduler(
            timezone=getattr(settings, "APSCHEDULER_TIMEZONE", settings.TIME_ZONE),
            job_defaults=getattr(settings, "APSCHEDULER_JOB_DEFAULTS", {}),
        )

        scheduler.add_job(
            self._run_command,
            CronTrigger(hour=0, minute=0),
            id="process_due_books",
            replace_existing=True,
            kwargs={"command_name": "process_due_books"},
        )
        scheduler.add_job(
            self._run_command,
            CronTrigger(hour=9, minute=0),
            id="send_due_reminders",
            replace_existing=True,
            kwargs={"command_name": "send_due_reminders", "days": 3},
        )
        scheduler.add_job(
            self._run_command,
            CronTrigger(day_of_week="mon", hour=2, minute=0),
            id="recalculate_trust_scores",
            replace_existing=True,
            kwargs={"command_name": "recalculate_trust_scores"},
        )
        scheduler.add_job(
            self._run_command,
            CronTrigger(hour=8, minute=30),
            id="process_pending_ratings",
            replace_existing=True,
            kwargs={"command_name": "process_pending_ratings"},
        )

        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write("收到中斷訊號，scheduler 已停止。")
            return
