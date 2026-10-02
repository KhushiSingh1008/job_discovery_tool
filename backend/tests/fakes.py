"""Test doubles shared across test modules."""

from pathlib import Path

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
