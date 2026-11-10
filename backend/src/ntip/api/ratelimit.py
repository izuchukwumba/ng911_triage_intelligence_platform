"""Per-client request rate limiting (design v1.2, sections 5.3 and 13.2).

A sliding one-minute window per client, keyed by a digest of the bearer
token (so different users behind one address are counted separately) or, for
unauthenticated requests, by the client address. Over the limit the API
answers 429 with Retry-After. Health checks are exempt so orchestration
probes never get throttled.

In-process only: each API process counts on its own. A multi-process
deployment would need a shared counter (e.g. Redis), which the design defers
until it is needed (section 3.3).
"""

import hashlib
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_minute = per_minute
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.per_minute > 0

    def check(self, key: str) -> float | None:
        """None if the request may proceed, else seconds until it may retry."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return max(0.0, 60 - (now - hits[0]))
            hits.append(now)
            return None


def client_key(authorization: str | None, client_host: str | None) -> str:
    if authorization:
        return "token:" + hashlib.sha256(authorization.encode()).hexdigest()[:16]
    return f"addr:{client_host or 'unknown'}"
