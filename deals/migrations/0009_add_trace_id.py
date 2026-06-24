from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("deals", "0008_exchangeevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="exchangeevent",
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
