"""
每日信用等級更新管理指令。
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.services.trust_service import update_trust_level

User = get_user_model()


class Command(BaseCommand):
    help = "更新所有用戶的信用等級"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只顯示將會變更的結果，不實際更新",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        users = User.objects.filter(is_active=True)

        upgraded = 0
        downgraded = 0
        unchanged = 0

        for user in users:
            old_level = user.profile.trust_level

            if dry_run:
                from accounts.services.trust_service import calculate_trust_level

                new_level = calculate_trust_level(user)
            else:
                new_level = update_trust_level(user)

            if new_level > old_level:
                upgraded += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(
                        f"用戶 {user.email} 升級: {old_level} → {new_level}"
                    )
            elif new_level < old_level:
                downgraded += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(
                        f"用戶 {user.email} 降級: {old_level} → {new_level}"
                    )
            else:
                unchanged += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] 將更新 {users.count()} 位用戶: "
                    f"{upgraded} 位升級, {downgraded} 位降級, {unchanged} 位不變"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"已更新 {users.count()} 位用戶: "
                    f"{upgraded} 位升級, {downgraded} 位降級, {unchanged} 位不變"
                )
            )
