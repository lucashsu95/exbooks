# pyright: reportArgumentType=false

import uuid

import django.db.models.deletion
from django.db import migrations, models


def populate_publisher_ref(apps, schema_editor):
    Publisher = apps.get_model("books", "Publisher")
    OfficialBook = apps.get_model("books", "OfficialBook")
    cache: dict[str, object] = {}
    for ob in OfficialBook.objects.all().iterator():
        raw = (ob.publisher or "").strip()
        if not raw:
            continue
        if raw not in cache:
            cache[raw], _ = Publisher.objects.get_or_create(
                name=raw,
                defaults={},
            )
        ob.publisher_ref = cache[raw]
        ob.save(update_fields=["publisher_ref_id"])


def noop_reverse(apps, schema_editor):
    OfficialBook = apps.get_model("books", "OfficialBook")
    OfficialBook.objects.all().update(publisher_ref_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0007_sharedbook_updated_at_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="Publisher",
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
                ("name", models.CharField(max_length=200, unique=True, verbose_name="名稱")),
            ],
            options={
                "verbose_name": "出版社",
                "verbose_name_plural": "出版社",
                "db_table": "exbook_publisher",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="officialbook",
            name="publisher_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="official_books",
                to="books.publisher",
                verbose_name="出版社（正規化）",
            ),
        ),
        migrations.RunPython(populate_publisher_ref, noop_reverse),
    ]
