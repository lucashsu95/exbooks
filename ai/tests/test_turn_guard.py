"""turn_guard：每位使用者同時只能有一輪對話進行中，且有每分鐘次數上限。"""

import pytest
from django.core.cache import cache

from ai.services import turn_guard
from ai.services.turn_guard import TurnRejection, begin_turn, guard_stream


@pytest.fixture(autouse=True)
def _isolate_cache():
    cache.clear()
    yield
    cache.clear()


def test_second_concurrent_turn_rejected_until_released():
    assert begin_turn(1) is None
    assert begin_turn(1) is TurnRejection.IN_FLIGHT
    turn_guard.end_turn(1)
    assert begin_turn(1) is None


def test_in_flight_lock_is_per_user():
    assert begin_turn(1) is None
    assert begin_turn(2) is None


def test_rate_limit_per_minute(monkeypatch):
    monkeypatch.setattr(turn_guard, "RATE_LIMIT_PER_MINUTE", 3)
    for _ in range(3):
        assert begin_turn(1) is None
        turn_guard.end_turn(1)
    assert begin_turn(1) is TurnRejection.RATE_LIMITED
    # 被限流時不得留下 in-flight 鎖
    monkeypatch.setattr(turn_guard, "RATE_LIMIT_PER_MINUTE", 100)
    assert begin_turn(1) is None


def test_rejection_messages_are_traditional_chinese():
    for rejection in TurnRejection:
        assert rejection.message
        assert any("一" <= ch <= "鿿" for ch in rejection.message)


def test_guard_stream_releases_lock_after_full_iteration():
    assert begin_turn(1) is None
    stream = guard_stream(1, iter(["a", "b"]))
    assert list(stream) == ["a", "b"]
    assert begin_turn(1) is None


def test_guard_stream_releases_lock_on_close_without_iteration():
    """client 在串流開始前就斷線：Django 只呼叫 close()，未啟動的 generator
    不會跑 finally——wrapper 的 close() 仍須釋放鎖。"""

    def _gen():
        yield "never"

    assert begin_turn(1) is None
    stream = guard_stream(1, _gen())
    stream.close()
    assert begin_turn(1) is None


def test_guard_stream_releases_lock_on_mid_stream_close():
    def _gen():
        yield "a"
        yield "b"

    assert begin_turn(1) is None
    stream = guard_stream(1, _gen())
    assert next(iter(stream)) == "a"
    stream.close()
    assert begin_turn(1) is None
