"""settings 的 cache 選擇：Redis 連不上時退回 LocMemCache，且必須大聲警告。

LocMemCache 是 per-process：gunicorn 多 worker 下 AI 對話的 in-flight 鎖與
限流會各算各的，等於失效——靜默退回會讓正式環境的 Redis 設定錯誤被埋掉。
"""

import importlib.util
import logging
from pathlib import Path
from unittest.mock import patch

import redis

_SETTINGS_PATH = Path(__file__).resolve().parents[2] / "exbook" / "settings.py"


def _load_settings_fresh():
    spec = importlib.util.spec_from_file_location("exbook._settings_probe", _SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Conn:
    def __init__(self, ok):
        self._ok = ok

    def ping(self):
        if not self._ok:
            raise redis.ConnectionError("refused")
        return True


def test_redis_unreachable_falls_back_to_locmem_with_warning(caplog):
    with patch("redis.from_url", return_value=_Conn(ok=False)):
        with caplog.at_level(logging.WARNING, logger="exbook.settings"):
            settings = _load_settings_fresh()

    # 退回行為不變
    assert settings.CACHES["default"]["BACKEND"].endswith("LocMemCache")
    warnings = [r for r in caplog.records if r.name == "exbook.settings"]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    assert "LocMemCache" in text
    assert "in-flight" in text and "限流" in text
    assert "per-process" in text


def test_redis_reachable_no_warning(caplog):
    with patch("redis.from_url", return_value=_Conn(ok=True)):
        with caplog.at_level(logging.WARNING, logger="exbook.settings"):
            settings = _load_settings_fresh()

    assert settings.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"
    assert not [r for r in caplog.records if r.name == "exbook.settings"]
