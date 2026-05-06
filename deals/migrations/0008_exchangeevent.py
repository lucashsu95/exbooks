# pyright: reportArgumentType=false

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("deals", "0007_alter_notification_notification_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExchangeEvent",
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
                    "event_type",
                    models.CharField(
                        choices=[
                            ("deal_requested", "交易申請"),
                            ("deal_accepted", "交易接受"),
                            ("deal_declined", "交易婉拒"),
                            ("deal_cancelled_request", "申請者取消"),
                            ("deal_superseded", "競價替代取消（BR-15）"),
                            ("deal_meeting_completed", "面交完成"),
                            ("keeper_changed", "持有者變更"),
                            ("book_overdue_processed", "到期排程處理"),
                            ("deal_confirm_return", "確認歸還／上架"),
                            ("deal_completed", "交易結案（DONE）"),
                            ("extension_requested", "延長申請"),
                            ("extension_approved", "延長核准"),
                            ("extension_rejected", "延長拒絕"),
                            ("extension_cancelled", "延長取消"),
                            ("rating_submitted", "評價送出"),
                        ],
                        db_index=True,
                        max_length=40,
                        verbose_name="事件類型",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(blank=True, default=dict, verbose_name="附加資料"),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exchange_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="操作者",
                    ),
                ),
                (
                    "deal",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exchange_events",
                        to="deals.deal",
                        verbose_name="交易",
                    ),
                ),
                (
                    "shared_book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exchange_events",
                        to="books.sharedbook",
                        verbose_name="分享書籍",
                    ),
                ),
            ],
            options={
                "verbose_name": "交換事件",
                "verbose_name_plural": "交換事件",
                "db_table": "exbook_exchange_event",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="exchangeevent",
            index=models.Index(
                fields=["shared_book", "-created_at"],
                name="exbook_exc_shared__idx",
            ),
        ),
        migrations.AddIndex(
            model_name="exchangeevent",
            index=models.Index(
                fields=["deal", "created_at"],
                name="exbook_exc_deal_created_idx",
            ),
        ),
    ]
