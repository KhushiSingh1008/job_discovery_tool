"""Test doubles shared across test modules."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import anthropic

from app.scraper.http import FetchError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> str:
    return (FIXTURES_DIR / relative_path).read_text(encoding="utf-8")


class FakeFetcher:
    """Serves canned bodies by URL; unknown URLs raise ``FetchError`` like a 404."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise FetchError(url, "HTTP 404", 404)
        return self.pages[url]


class FakeClock:
    """Deterministic monotonic clock whose ``sleep`` advances time instead of blocking."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def claude_response(text: str | None = None, stop_reason: str = "end_turn") -> SimpleNamespace:
    """The parts of a Messages API response the app reads."""
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class FakeClaude:
    """Mimics ``anthropic.Anthropic().beta.messages.create`` and records each call."""

    def __init__(self, result: SimpleNamespace | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def as_client(self) -> anthropic.Anthropic:
        return cast(anthropic.Anthropic, self)
