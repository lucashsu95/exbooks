# pyright: reportArgumentType=false

import re
import uuid

import django.db.models.deletion
from django.db import migrations, models


def split_author_names(value: str) -> list[str]:
    if not value or not str(value).strip():
        return []
    parts = re.split(r"[,，、;；]", str(value).strip())
    return [p.strip() for p in parts if p.strip()]


def populate_author_links(apps, schema_editor):
    Author = apps.get_model("books", "Author")
    OfficialBook = apps.get_model("books", "OfficialBook")
    OfficialBookAuthor = apps.get_model("books", "OfficialBookAuthor")
    for ob in OfficialBook.objects.all().iterator():
        names = split_author_names(ob.author or "")
        if not names:
            continue
        for order, display_name in enumerate(names):
            author, _ = Author.objects.get_or_create(
                display_name=display_name,
                defaults={"sort_key": display_name.lower()},
            )
            OfficialBookAuthor.objects.get_or_create(
                official_book=ob,
                author=author,
                defaults={
                    "sort_order": order,
                    "role": "author",
                },
            )


def noop_reverse(apps, schema_editor):
    OfficialBookAuthor = apps.get_model("books", "OfficialBookAuthor")
    OfficialBookAuthor.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0008_publisher_and_officialbook_publisher_ref"),
    ]

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "display_name",
                    models.CharField(max_length=200, unique=True, verbose_name="顯示名稱"),
                ),
                (
                    "sort_key",
                    models.CharField(
                        blank=True,
                        help_text="空白時以顯示名稱小寫排序",
                        max_length=200,
                        verbose_name="排序鍵",
                    ),
                ),
            ],
            options={
                "verbose_name": "作者",
                "verbose_name_plural": "作者",
                "db_table": "exbook_author",
                "ordering": ["sort_key", "display_name"],
            },
        ),
        migrations.CreateModel(
            name="OfficialBookAuthor",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("author", "作者"),
                            ("translator", "譯者"),
                        ],
                        default="author",
                        max_length=20,
                        verbose_name="角色",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="排序"),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="book_links",
                        to="books.author",
                        verbose_name="作者",
                    ),
                ),
                (
                    "official_book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="author_links",
                        to="books.officialbook",
                        verbose_name="官方書目",
                    ),
                ),
            ],
            options={
                "verbose_name": "書目作者關聯",
                "verbose_name_plural": "書目作者關聯",
                "db_table": "exbook_official_book_author",
                "ordering": ["sort_order", "created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="officialbookauthor",
            constraint=models.UniqueConstraint(
                fields=("official_book", "author"),
                name="uniq_official_book_author",
            ),
        ),
        migrations.AddField(
            model_name="officialbook",
            name="authors",
            field=models.ManyToManyField(
                related_name="official_books",
                through="OfficialBookAuthor",
                to="books.author",
                verbose_name="作者（正規化）",
            ),
        ),
        migrations.RunPython(populate_author_links, noop_reverse),
    ]
