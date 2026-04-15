"""處理逾期未評價交易：提醒或系統代評。"""

from django.core.management.base import BaseCommand

from deals.services.rating_service import process_pending_ratings


class Command(BaseCommand):
    help = "掃描已面交交易，提醒待評價方並於逾期 10 天後自動代評"

    def handle(self, *args, **options):
        process_pending_ratings()
        self.stdout.write("已完成待評價交易掃描")
