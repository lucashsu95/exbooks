"""
建立信用等級與限制狀態所需的 Django Groups。
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "建立信用等級與限制狀態所需的 Django Groups"

    def handle(self, *args, **options):
        # 6 個 Group 名稱：trust_lv0~3, restricted, banned
        group_names = [
            "trust_lv0",
            "trust_lv1",
            "trust_lv2",
            "trust_lv3",
            "restricted",
            "banned",
        ]

        for name in group_names:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully created group: {name}")
                )
            else:
                self.stdout.write(self.style.WARNING(f"Group already exists: {name}"))
