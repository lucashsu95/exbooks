"""
Centralized logging configuration for Exbooks.

Provides a LOGGING dictConfig builder that adapts to the environment
(dev vs production) and supports JSON structured output, SQL query logging,
and per-app logger granularity.
"""

import os
from pathlib import Path


def get_log_level() -> str:
    """Return the effective log level from environment, defaulting to INFO."""
    return os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper()


def get_sql_log_level() -> str:
    """Return SQL query log level from environment, defaulting to DEBUG."""
    return os.environ.get("SQL_LOG_LEVEL", "DEBUG").upper()


def build_dev_logging() -> dict:
    """Development logging: human-readable console output with SQL queries."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {name} {funcName}:{lineno} {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "sql": {
                "format": (
                    "\n[SQL] {asctime}\n"
                    "  Query: {message}\n"
                    "  Duration: {duration}s\n"
                    "───"
                ),
                "style": "{",
                "datefmt": "%H:%M:%S",
            },
        },
        "filters": {
            "require_debug_true": {
                "()": "django.utils.log.RequireDebugTrue",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "sql_console": {
                "class": "logging.StreamHandler",
                "formatter": "sql",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": get_log_level(),
        },
        "loggers": {
            # Django framework logs
            "django": {
                "handlers": ["console"],
                "level": get_log_level(),
                "propagate": False,
            },
            "django.server": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            # SQL query logging (only with DEBUG=True)
            "django.db.backends": {
                "handlers": ["sql_console"],
                "level": get_sql_log_level(),
                "propagate": False,
            },
            # Application loggers
            "core": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            "accounts": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            "books": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            "deals": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            "ai": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            # Celery
            "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
            # System loggers
            "system": {"handlers": ["console"], "level": get_log_level(), "propagate": False},
            "audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "business": {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
    }


def build_prod_logging(log_dir: str | Path | None = None) -> dict:
    """Production logging: JSON structured output with file rotation.

    Falls back to console-only if log_dir is None (e.g., Docker stdout).
    """
    log_level = get_log_level()

    formatters = {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(funcName)s:%(lineno)d %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "audit": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "verbose": {
            "format": "{levelname} {asctime} {name} {funcName}:{lineno} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    }

    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "json_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    }

    # Add file handler if log_dir is provided
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "exbook.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 10,
            "formatter": "json",
        }
        handlers["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "exbook_error.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
            "level": "ERROR",
        }
        # Add audit and business file handlers
        handlers["audit_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "audit.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 30,
            "formatter": "json",
            "level": "INFO",
        }
        handlers["business_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "business.log"),
            "maxBytes": 100 * 1024 * 1024,
            "backupCount": 14,
            "formatter": "json",
            "level": "INFO",
        }

    default_handlers = ["json_console"]
    if log_dir:
        default_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "handlers": default_handlers,
            "level": log_level,
        },
        "loggers": {
            "django": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "django.server": {
                "handlers": ["json_console"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": default_handlers,
                "level": "WARNING",
                "propagate": False,
            },
            "django.security": {
                "handlers": default_handlers,
                "level": "WARNING",
                "propagate": False,
            },
            "core": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "accounts": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "books": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "deals": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "ai": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "celery": {
                "handlers": default_handlers,
                "level": "INFO",
                "propagate": False,
            },
            "celery.task": {
                "handlers": default_handlers,
                "level": "WARNING",
                "propagate": False,
            },
            "system": {
                "handlers": default_handlers,
                "level": log_level,
                "propagate": False,
            },
            "audit": {
                "handlers": ["audit_file"] if log_dir else ["json_console"],
                "level": "INFO",
                "propagate": False,
            },
            "business": {
                "handlers": ["business_file", "json_console"] if log_dir else ["json_console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
