import random

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserProfile
from books.models import BookSet, OfficialBook, SharedBook
from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating


# 固定帳密的示範帳號，讓任何人 clone 後執行 seed 都能直接登入（僅供本地開發）
DEMO_ACCOUNTS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin12345",
        "is_staff": True,
        "is_superuser": True,
        "role": "管理員（可進 /admin/）",
    },
    {
        "username": "reader",
        "email": "reader@example.com",
        "password": "reader12345",
        "is_staff": False,
        "is_superuser": False,
        "role": "一般會員",
    },
]
_ADMIN = next(a for a in DEMO_ACCOUNTS if a["is_superuser"])


class Command(BaseCommand):
    help = "Generate fake data for Exbooks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--amount",
            type=str,
            choices=["small", "medium", "large"],
            default="small",
            help="Amount of data to generate (default: small)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=True,
            help="Clear existing data before seeding (default: True)",
        )
        parser.add_argument(
            "--no-clear",
            action="store_false",
            dest="clear",
            help="Do not clear existing data before seeding",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Allow running when DEBUG is False (creates fixed demo admin credentials!)",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "拒絕執行：DEBUG=False（疑似正式環境）。seed 會清除資料並建立固定帳密的"
                f"示範管理員帳號（{_ADMIN['email']} / {_ADMIN['password']}）。"
                "若確定要在此環境執行，請加上 --force。"
            )

        amount = options["amount"]
        clear = options["clear"]

        if clear:
            self._clear_data()

        self._generate_data(amount)

    def _clear_data(self):
        self.stdout.write("Clearing existing data...")

        with transaction.atomic():
            Rating.objects.all().delete()
            DealMessage.objects.all().delete()
            LoanExtension.objects.all().delete()
            Notification.objects.all().delete()
            Deal.objects.all().delete()
            SharedBook.objects.all().delete()
            BookSet.objects.all().delete()
            OfficialBook.objects.all().delete()
            UserProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write(
            self.style.SUCCESS("Existing data cleared (Superusers preserved).")
        )

    def _ensure_demo_accounts(self):
        """建立/更新固定帳密的示範帳號，並把 email 標記為已驗證。"""
        from allauth.account.models import EmailAddress

        self.stdout.write("Ensuring demo accounts...")
        for acct in DEMO_ACCOUNTS:
            user, created = User.objects.get_or_create(username=acct["username"])
            if not created and (
                user.email != acct["email"]
                or user.is_staff != acct["is_staff"]
                or user.is_superuser != acct["is_superuser"]
                or not user.check_password(acct["password"])
            ):
                self.stdout.write(
                    self.style.WARNING(
                        f"  {acct['username']} 已存在且與示範帳號定義不符，"
                        f"將覆寫其 email/權限/密碼。"
                    )
                )
            user.email = acct["email"]
            user.is_staff = acct["is_staff"]
            user.is_superuser = acct["is_superuser"]
            user.set_password(acct["password"])
            user.save()

            email, _ = EmailAddress.objects.get_or_create(
                user=user,
                email=acct["email"],
                defaults={"verified": True, "primary": True},
            )
            email.verified = True
            email.primary = True
            email.save()
            # 同一用戶可能有舊的 EmailAddress 殘留，primary 必須唯一
            EmailAddress.objects.filter(user=user).exclude(pk=email.pk).update(
                primary=False
            )

            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {acct['email']} / {acct['password']} ({acct['role']}, {action})"
                )
            )

    def _assign_demo_books(self):
        """把現有的可移轉書各綁一本給 admin / reader，方便立即測試借用功能。"""
        demo_users = User.objects.filter(
            username__in=[acct["username"] for acct in DEMO_ACCOUNTS]
        )
        candidates = (
            SharedBook.objects.filter(status=SharedBook.Status.TRANSFERABLE)
            .exclude(owner__in=demo_users)
            .select_related("official_book", "owner")
        )
        assigned = 0
        for user in demo_users:
            book = candidates.exclude(owner_id=user.id).first()
            if book is None:
                break
            book.owner = user
            book.keeper = user
            book.save(update_fields=["owner", "keeper", "updated_at"])
            assigned += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {user.username} 綁定：{book.official_book.title} ({book.pk})"
                )
            )
        if assigned < demo_users.count():
            self.stdout.write(
                self.style.WARNING("  可移轉書不足，示範帳號綁定未完成。")
            )

    def _generate_data(self, amount):
        self.stdout.write(f"Generating {amount} data...")

        try:
            from tests import factories
        except ImportError:
            raise CommandError(
                "Missing dependencies. Please run 'pip install -e \".[dev,test]\"' to use this command."
            )

        config = {
            "small": {"users": 10, "official_books": 20, "shared_books": 30},
            "medium": {"users": 30, "official_books": 50, "shared_books": 100},
            "large": {"users": 100, "official_books": 200, "shared_books": 500},
        }
        counts = config.get(amount, config["small"])

        with transaction.atomic():
            # 0. Fixed demo accounts (see DEMO_ACCOUNTS)
            self._ensure_demo_accounts()

            # 1. Users
            profiles = factories.UserProfileFactory.create_batch(counts["users"])
            users = [p.user for p in profiles]
            self.stdout.write(f"Created {len(users)} users with profiles.")

            # 2. OfficialBooks
            official_books = factories.OfficialBookFactory.create_batch(
                counts["official_books"]
            )
            self.stdout.write(f"Created {len(official_books)} official books.")

            # 3. SharedBooks
            shared_books_count = 0
            for _ in range(counts["shared_books"]):
                owner = random.choice(users)
                official_book = random.choice(official_books)
                status = random.choice(
                    [SharedBook.Status.TRANSFERABLE, SharedBook.Status.OCCUPIED]
                )
                factories.SharedBookFactory.create(
                    owner=owner,
                    keeper=owner,
                    official_book=official_book,
                    status=status,
                )
                shared_books_count += 1

            self.stdout.write(f"Created {shared_books_count} shared books.")

            # 4. 示範帳號各綁一本現有的可移轉書，方便立即測試借用功能
            self._assign_demo_books()

            # 5. Deals for occupied books
            occupied_books = SharedBook.objects.filter(
                status=SharedBook.Status.OCCUPIED
            )
            deals_count = 0
            for sb in occupied_books:
                other_users = [u for u in users if u != sb.owner]
                if not other_users:
                    continue

                applicant = random.choice(other_users)
                factories.DealFactory.create(
                    shared_book=sb,
                    applicant=applicant,
                    responder=sb.owner,
                    status=Deal.Status.MEETED,
                    deal_type=Deal.DealType.LOAN,
                    previous_book_status=SharedBook.Status.TRANSFERABLE,
                )
                sb.keeper = applicant
                sb.save()
                deals_count += 1

            self.stdout.write(f"Created {deals_count} deals for occupied books.")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully generated {amount} data for Exbooks.")
        )
