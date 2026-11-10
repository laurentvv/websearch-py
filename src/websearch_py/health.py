"""Engine health memory: an engine that answered with a captcha / rate limit rests before being asked again.

Without it every query pays the failed request of the blocked engines again (and keeps hammering them, which makes the
block last longer). The state is process-wide by default so it survives the throw-away `WebSearcher` instances created by
the top-level `search()` helper.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from websearch_py.exceptions import RateLimitError


@dataclass
class _State:
    consecutive_blocks: int = 0
    resting_until: float = 0.0
    last_error: str = ""


class EngineHealth:
    def __init__(
        self,
        cooldown_s: float = 300.0,
        max_cooldown_s: float = 1800.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cooldown_s, self.max_cooldown_s, self._clock = cooldown_s, max_cooldown_s, clock
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()

    def record_success(self, name: str) -> None:
        with self._lock:
            self._states[name] = _State()

    def record_failure(self, name: str, error: BaseException) -> None:
        """Only blocks (RateLimitError, ChallengeError) make an engine rest: the rest doubles up to `max_cooldown_s`."""
        if not isinstance(error, RateLimitError):
            return
        with self._lock:
            st = self._states.setdefault(name, _State())
            st.consecutive_blocks += 1
            rest = min(self.cooldown_s * 2 ** (st.consecutive_blocks - 1), self.max_cooldown_s)
            st.resting_until = self._clock() + rest
            st.last_error = str(error)[:120]

    def is_resting(self, name: str) -> bool:
        with self._lock:
            st = self._states.get(name)
            return bool(st and st.resting_until > self._clock())

    def status(self) -> dict[str, dict[str, object]]:
        now = self._clock()
        with self._lock:
            return {
                n: {
                    "resting": s.resting_until > now,
                    "rest_left_s": max(0.0, round(s.resting_until - now, 1)),
                    "consecutive_blocks": s.consecutive_blocks,
                    "last_error": s.last_error,
                }
                for n, s in self._states.items()
            }

    def reset(self) -> None:
        with self._lock:
            self._states.clear()


SHARED_HEALTH = EngineHealth()
