import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, status


class AttemptLimiter:
    """Sliding-window counter. In-memory, so it is per-process: fine for one server, not for many."""

    def __init__(self, max_attempts: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        hits = self._hits[key]
        cutoff = self.clock() - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if not hits:
            self._hits.pop(key, None)
        return hits

    def check(self, key: str) -> None:
        hits = self._prune(key)
        if len(hits) >= self.max_attempts:
            retry = max(1, int(hits[0] + self.window - self.clock()))
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many attempts. Try again later.",
                headers={"Retry-After": str(retry)},
            )

    def record(self, key: str) -> None:
        self._prune(key)
        self._hits[key].append(self.clock())

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()


# Failed logins: tight per account+IP, looser per IP so rotating emails does not bypass it.
login_by_account = AttemptLimiter(max_attempts=5, window_seconds=15 * 60)
login_by_ip = AttemptLimiter(max_attempts=20, window_seconds=15 * 60)
# Every registration attempt counts, successful or not.
register_by_ip = AttemptLimiter(max_attempts=10, window_seconds=60 * 60)

ALL_LIMITERS = (login_by_account, login_by_ip, register_by_ip)
