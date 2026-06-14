"""Dev settings with SQLite for local testing."""
from .settings import *  # noqa: F403, F401

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "dev.db",  # noqa: F405
    }
}

MIGRATION_MODULES = {}
