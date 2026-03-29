from django.apps import AppConfig


class DealsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "deals"
    verbose_name = "交易管理"

    def ready(self):
        """註冊 Signal 處理器。"""
        import deals.signals  # noqa: F401
