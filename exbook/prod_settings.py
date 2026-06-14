"""
Production settings — Docker / Linux deployment.

Usage:
    DJANGO_SETTINGS_MODULE=exbook.prod_settings gunicorn exbook.wsgi
"""

import os

from .settings import *  # noqa: F401, F403

# ── Security ────────────────────────────────────────────────────
DEBUG = False
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/m/ip,5/5m/key",
}

# ── Logging / Monitoring ────────────────────────────────────────
from core.logging_config import build_prod_logging  # noqa: E402

LOGGING = build_prod_logging(log_dir="/var/log/exbook")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
            send_default_pii=False,
        )
    except ImportError:
        pass

# ── Database (Docker Compose 內部網路) ──────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "exbook"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "db"),  # docker-compose service name
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
    }
}

# ── Static / Media ──────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

# ── CSRF / Session ─────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    x.strip()
    for x in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if x.strip()
]
