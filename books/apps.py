from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "books"
    verbose_name = "書籍管理"

    def ready(self) -> None:
        """註冊 Signal 處理器（SharedBook 自訂封面檔案清理）。"""
        import books.signals  # noqa: F401
