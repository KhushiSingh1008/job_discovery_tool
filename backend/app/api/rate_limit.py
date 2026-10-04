"""Per-client rate limiting for endpoints that cost money or CPU (AI calls, file parsing).

An in-memory sliding window is enough for a single-instance deployment; behind a proxy the
client address comes from ``X-Forwarded-For`` (uvicorn ``--proxy-headers``).
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Record a request; returns seconds to wait if over the limit, else ``None``."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.window - (now - hits[0])
            hits.append(now)
            self._forget_idle(now)
            return None

    def _forget_idle(self, now: float) -> None:
        if len(self._hits) < 1000:
            return
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
            del self._hits[key]


def enforce(limiter: RateLimiter, request: Request) -> None:
    """Answer 429 with ``Retry-After`` when this client is over the limit."""
    client = request.client.host if request.client else "unknown"
    wait = limiter.hit(client)
    if wait is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You've used the resume tools a lot in the last hour. Please try again later.",
            headers={"Retry-After": str(math.ceil(wait))},
        )
