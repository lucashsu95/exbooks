"""
處理所有已到期的借閱交易。

將到期交易根據流通性轉換狀態：
- 閱畢即還 (RETURN) → R (應返還)
- 開放傳遞 (TRANSFER) → T (可移轉)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from deals.models import Deal
from deals.services.overdue_service import batch_process_due_books


class Command(BaseCommand):
    help = "處理所有已到期的借閱交易"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只列出要處理的交易，不實際執行",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # 查詢所有已到期且書籍仍為借閱中的交易
        today = timezone.now().date()
        overdue_deals = Deal.objects.filter(
            status=Deal.Status.MEETED,
            due_date__lte=today,
            shared_book__status="O",  # OCCUPIED
        ).select_related("shared_book__official_book", "applicant", "responder")

        count = overdue_deals.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("沒有需要處理的到期交易"))
            return

        self.stdout.write(f"找到 {count} 筆到期交易")

        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run) 以下交易將被處理："))
            for deal in overdue_deals:
                transferability = deal.shared_book.get_transferability_display()
                new_status = "應返還" if transferability == "閱畢即還" else "可移轉"
                self.stdout.write(
                    f"  - {deal.shared_book.official_book.title} "
                    f"(到期: {deal.due_date}, 流通性: {transferability}) "
                    f"→ {new_status}"
                )
            return

        summary = batch_process_due_books()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n處理完成: {summary['processed']} 筆成功, {summary['errors']} 筆失敗"
            )
        )
