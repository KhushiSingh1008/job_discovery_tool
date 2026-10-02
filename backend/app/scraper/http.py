"""Polite HTTP fetching: the only module in the scraper that touches the network.

- Browser-like headers on a persistent ``requests.Session`` (connection reuse, cookies).
- Randomised 1.5-3.5 s delay between requests to the same host (or robots.txt Crawl-delay).
- robots.txt checked before every crawl.
- Exponential back-off on 429/5xx, honouring ``Retry-After``.

No proxy rotation and no CAPTCHA solving: if a site blocks a polite client, we swap the source.
"""

import logging
import random
import time
from collections.abc import Callable
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit

import requests

from app.config import Settings
from app.scraper.robots import RobotsPolicy

logger = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_SECONDS = 60.0
BACKOFF_BASE_SECONDS = 2.0


class FetchError(Exception):
    def __init__(self, url: str, reason: str, status: int | None = None) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.status = status


class RobotsDisallowedError(FetchError):
    def __init__(self, url: str) -> None:
        super().__init__(url, "disallowed by robots.txt")


class PoliteSession:
    def __init__(
        self,
        *,
        user_agent: str,
        min_delay: float = 1.5,
        max_delay: float = 3.5,
        timeout: float = 20.0,
        max_retries: int = 3,
        respect_robots: bool = True,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._timeout = timeout
        self._max_retries = max_retries
        self._respect_robots = respect_robots
        self._sleep = sleep
        self._clock = clock
        self._rng = rng or random.Random()
        self._last_request_at: dict[str, float] = {}

        self._http = session or requests.Session()
        self._http.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-GB,en;q=0.9",
            }
        )
        self.robots = RobotsPolicy(user_agent, self._fetch_robots)

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            user_agent=settings.scraper_user_agent,
            min_delay=settings.scraper_min_delay,
            max_delay=settings.scraper_max_delay,
            timeout=settings.scraper_timeout,
            max_retries=settings.scraper_max_retries,
        )

    def get(self, url: str) -> str:
        """Fetch ``url`` and return its decoded body, or raise ``FetchError``."""
        if self._respect_robots and not self.robots.allowed(url):
            raise RobotsDisallowedError(url)
        response = self._get_with_retries(url)
        if "charset" not in response.headers.get("Content-Type", "").lower():
            response.encoding = response.apparent_encoding
        return response.text

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- internals -------------------------------------------------------------------------

    def _delay_for(self, url: str) -> float:
        delay = self._rng.uniform(self._min_delay, self._max_delay)
        if self._respect_robots:
            crawl_delay = self.robots.crawl_delay(url)
            if crawl_delay is not None:
                delay = max(delay, crawl_delay)
        return delay

    def _throttle(self, url: str, delay: float) -> None:
        host = urlsplit(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            wait = last + delay - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._last_request_at[host] = self._clock()

    def _send(self, url: str, delay: float) -> requests.Response:
        self._throttle(url, delay)
        return self._http.get(url, timeout=self._timeout)

    def _backoff_seconds(self, attempt: int, response: requests.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdigit():
                return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
        return BACKOFF_BASE_SECONDS * 2.0**attempt

    def _get_with_retries(self, url: str) -> requests.Response:
        delay = self._delay_for(url)
        for attempt in range(self._max_retries + 1):
            is_last_attempt = attempt == self._max_retries
            try:
                response = self._send(url, delay)
            except (requests.ConnectionError, requests.Timeout) as exc:
                if is_last_attempt:
                    raise FetchError(url, f"network error: {exc}") from exc
                logger.info("Network error on %s, retrying (%d)", url, attempt + 1)
                self._sleep(self._backoff_seconds(attempt, None))
                continue

            if response.status_code in RETRY_STATUSES and not is_last_attempt:
                wait = self._backoff_seconds(attempt, response)
                logger.info("HTTP %d on %s, backing off %.1fs", response.status_code, url, wait)
                self._sleep(wait)
                continue
            if response.status_code >= 400:
                raise FetchError(url, f"HTTP {response.status_code}", response.status_code)
            return response
        raise AssertionError("unreachable")  # pragma: no cover

    def _fetch_robots(self, robots_url: str) -> tuple[int, str]:
        response = self._send(robots_url, self._rng.uniform(self._min_delay, self._max_delay))
        return response.status_code, response.text
