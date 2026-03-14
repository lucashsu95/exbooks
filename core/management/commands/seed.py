import os
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserProfile
from books.models import BookPhoto, BookSet, OfficialBook, SharedBook
from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating


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

    def handle(self, *args, **options):
        amount = options["amount"]
        clear = options["clear"]

        if clear:
            self._clear_data()

        self._setup_media()
        self._generate_data(amount)

    def _clear_data(self):
        self.stdout.write("Clearing existing data...")

        with transaction.atomic():
            Rating.objects.all().delete()
            DealMessage.objects.all().delete()
            LoanExtension.objects.all().delete()
            Notification.objects.all().delete()
            Deal.objects.all().delete()
            BookPhoto.objects.all().delete()
            SharedBook.objects.all().delete()
            BookSet.objects.all().delete()
            OfficialBook.objects.all().delete()
            UserProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write(
            self.style.SUCCESS("Existing data cleared (Superusers preserved).")
        )

    def _setup_media(self):
        self.stdout.write("Setting up media directories and dummy files...")

        # Ensure directories exist
        subdirs = ["book_covers", "book_photos", "avatars"]
        for subdir in subdirs:
            path = os.path.join(settings.MEDIA_ROOT, subdir)
            os.makedirs(path, exist_ok=True)

        # Create a minimal 1x1 pixel JPG file
        # This is a valid 1x1 black pixel JPG in bytes
        dummy_jpg_content = (
            b"\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07"
            b"\t\x08\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
            b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
            b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01"
            b"\x00\x00\x3f\x00\x10\xbf\x06\xaf\xff\xd9"
        )

        dummy_path = os.path.join(settings.MEDIA_ROOT, "dummy.jpg")
        with open(dummy_path, "wb") as f:
            f.write(dummy_jpg_content)

        self.stdout.write(self.style.SUCCESS(f"Media setup complete: {dummy_path}"))

    def _generate_data(self, amount):
        self.stdout.write(f"Generating {amount} data...")

        try:
            import factory
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
        dummy_path = os.path.join(settings.MEDIA_ROOT, "dummy.jpg")

        with transaction.atomic():
            # 1. Users (via UserProfileFactory to ensure profiles exist)
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

                sb = factories.SharedBookFactory.create(
                    owner=owner,
                    keeper=owner,
                    official_book=official_book,
                    status=status,
                )
                shared_books_count += 1

                # Add photo using dummy.jpg
                factories.BookPhotoFactory.create(
                    shared_book=sb,
                    uploader=owner,
                    photo=factory.django.FileField(from_path=dummy_path),
                )

            self.stdout.write(f"Created {shared_books_count} shared books with photos.")

            # 4. Deals for occupied books
            occupied_books = SharedBook.objects.filter(
                status=SharedBook.Status.OCCUPIED
            )
            deals_count = 0
            for sb in occupied_books:
                # Pick an applicant who is not the owner
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
                # Update keeper to applicant as it's already met
                sb.keeper = applicant
                sb.save()
                deals_count += 1

            self.stdout.write(f"Created {deals_count} deals for occupied books.")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully generated {amount} data for Exbooks.")
        )
