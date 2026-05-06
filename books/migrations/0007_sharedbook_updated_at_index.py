# pyright: reportArgumentType=false

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0006_sharedbook_min_trust_level"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="sharedbook",
            index=models.Index(
                fields=["-updated_at"],
                name="idx_shared_book_updated_at",
            ),
        ),
    ]
