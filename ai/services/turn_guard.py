"""
每位使用者的對話輪次保護：同時只能有一輪進行中，且每分鐘有次數上限。

- in-flight 鎖用 ``cache.add``（SET NX 語義，Redis／LocMem 皆原子）；TTL 是
  worker 意外死掉時的保底，正常路徑由 ``guard_stream`` 在串流結束／關閉時釋放。
- 限流是固定視窗計數（每分鐘一個 key）。
"""

import time
from enum import Enum
from typing import Iterable, Iterator, Optional

from django.core.cache import cache

RATE_LIMIT_PER_MINUTE = 20
# 鎖的保底 TTL：需大於一輪最長時間（turn deadline 90s + 單次 LLM 呼叫上限 120s）
IN_FLIGHT_TTL_SECONDS = 240

_LOCK_PREFIX = "ai_turn_lock:"
_RATE_PREFIX = "ai_turn_rate:"


class TurnRejection(Enum):
    IN_FLIGHT = "上一則訊息還在回覆中，請等它完成後再送出。"
    RATE_LIMITED = "訊息送得太頻繁了，請稍候一分鐘再試。"

    @property
    def message(self) -> str:
        return self.value


def _lock_key(user_id) -> str:
    return f"{_LOCK_PREFIX}{user_id}"


def _hit_rate_limit(user_id) -> bool:
    key = f"{_RATE_PREFIX}{user_id}:{int(time.time() // 60)}"
    cache.add(key, 0, 60)
    try:
        count = cache.incr(key)
    except ValueError:  # key 剛好過期：視為本視窗第一次
        cache.set(key, 1, 60)
        count = 1
    return count > RATE_LIMIT_PER_MINUTE


def begin_turn(user_id) -> Optional[TurnRejection]:
    """嘗試開始一輪；成功回 None（呼叫方須在結束時 end_turn），否則回拒絕原因。"""
    if not cache.add(_lock_key(user_id), True, IN_FLIGHT_TTL_SECONDS):
        return TurnRejection.IN_FLIGHT
    if _hit_rate_limit(user_id):
        end_turn(user_id)
        return TurnRejection.RATE_LIMITED
    return None


def end_turn(user_id) -> None:
    cache.delete(_lock_key(user_id))


class _GuardedStream:
    """包住串流；迭代結束、例外或 close() 時釋放鎖（冪等）。

    用 class 而非 generator：client 在串流開始前就斷線時 Django 只呼叫
    close()，未啟動的 generator 不會執行 finally。
    """

    def __init__(self, user_id, stream: Iterable[str]):
        self._user_id = user_id
        self._stream = stream
        self._released = False

    def __iter__(self) -> Iterator[str]:
        try:
            yield from self._stream
        finally:
            self.close()

    def close(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            close = getattr(self._stream, "close", None)
            if close is not None:
                close()
        finally:
            end_turn(self._user_id)


def guard_stream(user_id, stream: Iterable[str]) -> _GuardedStream:
    return _GuardedStream(user_id, stream)
