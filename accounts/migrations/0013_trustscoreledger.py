# pyright: reportArgumentType=false

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0012_initial_trust_level_config_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrustScoreLedger",
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
                ("trust_score", models.IntegerField(verbose_name="當下積分")),
                (
                    "trust_level",
                    models.PositiveSmallIntegerField(verbose_name="當下等級（0-3）"),
                ),
                (
                    "formula_version",
                    models.CharField(max_length=40, verbose_name="公式版本"),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("recalculate", "批次／手動重算"),
                            ("rating", "收到評價"),
                            ("deal_completed", "交易結案"),
                            ("overdue_adjust", "逾期處理"),
                            ("violation", "違規處分"),
                        ],
                        db_index=True,
                        max_length=30,
                        verbose_name="來源",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(blank=True, default=dict, verbose_name="摘要指標"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trust_score_ledgers",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用戶",
                    ),
                ),
            ],
            options={
                "verbose_name": "信用積分稽核",
                "verbose_name_plural": "信用積分稽核",
                "db_table": "exbook_trust_score_ledger",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="trustscoreledger",
            index=models.Index(
                fields=["user", "-created_at"],
                name="exbook_trust_user_created_idx",
            ),
        ),
    ]
