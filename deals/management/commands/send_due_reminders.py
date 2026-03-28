"""
發送即將到期的借閱提醒通知。

提前 N 天通知持有者書籍即將到期。
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from deals.models import Deal, Notification
from deals.services import notification_service


class Command(BaseCommand):
    help = "發送即將到期的借閱提醒通知"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=3,
            help="提前幾天提醒（預設 3 天）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只列出要發送的通知，不實際發送",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        # 計算目標到期日
        target_date = timezone.now().date() + timedelta(days=days)

        # 查詢即將到期的交易
        upcoming_deals = Deal.objects.filter(
            status=Deal.Status.MEETED,
            due_date=target_date,
            shared_book__status="O",  # OCCUPIED
        ).select_related("shared_book__official_book", "applicant", "responder")

        count = upcoming_deals.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"沒有 {days} 天後到期的交易"))
            return

        self.stdout.write(f"找到 {count} 筆 {days} 天後到期的交易")

        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run) 以下交易將收到提醒："))
            for deal in upcoming_deals:
                self.stdout.write(
                    f"  - {deal.shared_book.official_book.title} "
                    f"(到期: {deal.due_date}, 持有者: {deal.applicant})"
                )
            return

        # 實際發送通知
        sent = 0
        skipped = 0

        for deal in upcoming_deals:
            # 檢查是否已發送過同一天的提醒
            existing = Notification.objects.filter(
                recipient=deal.applicant,
                notification_type=Notification.NotificationType.BOOK_DUE_SOON,
                created_at__date=timezone.now().date(),
            ).exists()

            if existing:
                skipped += 1
                self.stdout.write(
                    f"  跳過: {deal.shared_book.official_book.title} (已發送提醒)"
                )
                continue

            try:
                notification_service.notify_book_due_soon(deal)
                sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ 已發送: {deal.shared_book.official_book.title} "
                        f"→ {deal.applicant}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ 發送失敗: {deal.shared_book.official_book.title} - {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n發送完成: {sent} 筆成功, {skipped} 筆跳過（已發送）")
        )
