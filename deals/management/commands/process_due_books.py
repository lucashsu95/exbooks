"""
處理所有已到期的借閱交易。

將到期交易根據流通性轉換狀態：
- 閱畢即還 (RETURN) → R (應返還)
- 開放傳遞 (TRANSFER) → T (可移轉)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from deals.models import Deal
from deals.services import deal_service


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

        # 實際處理
        processed = 0
        errors = 0

        for deal in overdue_deals:
            try:
                deal_service.process_book_due(deal)
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ 已處理: {deal.shared_book.official_book.title}"
                    )
                )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ 處理失敗: {deal.shared_book.official_book.title} - {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n處理完成: {processed} 筆成功, {errors} 筆失敗")
        )
