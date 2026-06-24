from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_notification_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="trustscoreledger",
            name="trace_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=32,
                verbose_name="追蹤ID",
            ),
        ),
    ]
