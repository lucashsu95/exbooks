"""
每週重新計算信用積分管理指令。
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.services.trust_service import (
    calculate_trust_score,
    sync_trust_group,
    update_trust_score,
)

User = get_user_model()


class Command(BaseCommand):
    help = "重新計算所有用戶的信用積分"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只顯示將會變更的結果，不實際更新",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        users = User.objects.filter(is_active=True)

        increased = 0
        decreased = 0
        unchanged = 0

        for user in users:
            old_score = user.profile.trust_score

            if dry_run:
                new_score = calculate_trust_score(user)
            else:
                new_score = update_trust_score(user)
                sync_trust_group(user)

            if new_score > old_score:
                increased += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(
                        f"用戶 {user.email} 積分上升: {old_score} → {new_score}"
                    )
            elif new_score < old_score:
                decreased += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(
                        f"用戶 {user.email} 積分下降: {old_score} → {new_score}"
                    )
            else:
                unchanged += 1

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] 將重新計算 {users.count()} 位用戶: "
                f"{increased} 位上升, {decreased} 位下降, {unchanged} 位不變"
            )
        else:
            self.stdout.write(
                f"已重新計算 {users.count()} 位用戶: "
                f"{increased} 位上升, {decreased} 位下降, {unchanged} 位不變"
            )
