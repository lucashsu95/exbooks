"""Test-specific settings — SQLite file-based for concurrency safety.

Uses a shared cache file-based SQLite database instead of pure in-memory.
This allows multiple connections to share the same database, fixing
concurrency issues during E2E tests.
"""

import os
import tempfile
import uuid

from .settings import *  # noqa: F401, F403

# Create a unique temporary database for each test run
# This ensures test isolation while still allowing concurrent connections
_temp_dir = tempfile.gettempdir()
_unique_id = str(uuid.uuid4())[:8]
_test_db_path = os.path.join(_temp_dir, f"exbook_test_{_unique_id}.db")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _test_db_path,
        # Critical: these options enable safe concurrent access
        "OPTIONS": {
            "timeout": 30,  # Wait up to 30 seconds for locks
            "check_same_thread": False,  # Allow multi-threaded access
        },
        # Ensure test database is properly managed
        "TEST": {
            "NAME": _test_db_path,
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
