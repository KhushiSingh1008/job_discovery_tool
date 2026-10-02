import pytest
import requests

from app.scraper.robots import RobotsPolicy

ROBOTS = """
User-agent: *
Disallow: /private
Crawl-delay: 5
"""


class RobotsStub:
    def __init__(self, status: int = 200, body: str = ROBOTS, error: bool = False) -> None:
        self.status, self.body, self.error = status, body, error
        self.calls: list[str] = []

    def __call__(self, url: str) -> tuple[int, str]:
        self.calls.append(url)
        if self.error:
            raise requests.ConnectionError("down")
        return self.status, self.body


def test_respects_disallow_rules_and_crawl_delay() -> None:
    policy = RobotsPolicy("TestBot", RobotsStub())

    assert policy.allowed("https://example.com/jobs/1")
    assert not policy.allowed("https://example.com/private/admin")
    assert policy.crawl_delay("https://example.com/jobs") == 5.0


def test_robots_is_fetched_once_per_origin() -> None:
    stub = RobotsStub()
    policy = RobotsPolicy("TestBot", stub)

    policy.allowed("https://example.com/a")
    policy.allowed("https://example.com/b")
    policy.allowed("https://other.example/a")

    assert stub.calls == ["https://example.com/robots.txt", "https://other.example/robots.txt"]


@pytest.mark.parametrize(
    ("stub", "allowed"),
    [
        (RobotsStub(status=404, body=""), True),  # no robots.txt: everything allowed
        (RobotsStub(status=503, body=""), False),  # server error: stay away
        (RobotsStub(error=True), False),  # unreachable: stay away
    ],
)
def test_missing_or_failing_robots(stub: RobotsStub, allowed: bool) -> None:
    assert RobotsPolicy("TestBot", stub).allowed("https://example.com/jobs") is allowed
