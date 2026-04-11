"""Test-specific settings — SQLite file-based for concurrency safety.

Uses a shared cache file-based SQLite database instead of pure in-memory.
This allows multiple connections to share the same database, fixing
concurrency issues during E2E tests.
"""

import os
import tempfile

from .settings import *  # noqa: F401, F403

# Create a temporary directory for test database
# Using shared cache mode allows concurrent connections to share data
_temp_dir = tempfile.gettempdir()
_test_db_path = os.path.join(_temp_dir, "exbook_test.db")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _test_db_path,
        # Critical: these options enable safe concurrent access
        "OPTIONS": {
            "timeout": 30,  # Wait up to 30 seconds for locks
            "check_same_thread": False,  # Allow multi-threaded access
        },
    }
}

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Disable migrations for speed — create tables directly from models
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Silence logging during tests
LOGGING = {}

DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"

# Disable Web Push in tests (no VAPID keys configured)
WEBPUSH_ENABLED = False
