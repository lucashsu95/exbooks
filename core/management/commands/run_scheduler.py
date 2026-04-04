"""獨立啟動 APScheduler 的管理指令。"""

from django.core.management.base import BaseCommand

from exbook.scheduler import run_blocking_scheduler


class Command(BaseCommand):
    help = "以獨立程序啟動 APScheduler（適用生產環境）"

    def handle(self, *args, **options):
        self.stdout.write("啟動 APScheduler（BlockingScheduler）...")
        try:
            run_blocking_scheduler()
        except KeyboardInterrupt:
            self.stdout.write("收到中斷訊號，scheduler 已停止。")
            return
