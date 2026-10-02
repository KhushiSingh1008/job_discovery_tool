import pytest
import requests
import responses

from app.scraper.http import FetchError, PoliteSession, RobotsDisallowedError
from tests.fakes import FakeClock

SITE = "https://jobs.example"
DELAY = 1.5  # distinct from the 2s/4s back-off steps so assertions can tell them apart


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def session(clock: FakeClock) -> PoliteSession:
    return PoliteSession(
        user_agent="TestAgent/1.0",
        min_delay=DELAY,
        max_delay=DELAY,
        max_retries=2,
        sleep=clock.sleep,
        clock=clock,
    )


def _robots(body: str = "", status: int = 404) -> None:
    responses.get(f"{SITE}/robots.txt", body=body, status=status)


@responses.activate
def test_returns_body_with_browser_like_headers(session: PoliteSession) -> None:
    _robots()
    responses.get(f"{SITE}/jobs", body="<html>ok</html>")

    assert session.get(f"{SITE}/jobs") == "<html>ok</html>"
    headers = responses.calls[-1].request.headers
    assert headers["User-Agent"] == "TestAgent/1.0"
    assert headers["Accept-Language"].startswith("en-GB")


@responses.activate
def test_detects_encoding_when_charset_missing(session: PoliteSession) -> None:
    _robots()
    responses.get(f"{SITE}/pay", body="Pay: £12.21 per hour".encode(), content_type="text/html")

    assert "£12.21" in session.get(f"{SITE}/pay")


@responses.activate
def test_waits_between_requests_to_same_host(session: PoliteSession, clock: FakeClock) -> None:
    _robots()
    responses.get(f"{SITE}/a", body="a")
    responses.get(f"{SITE}/b", body="b")

    session.get(f"{SITE}/a")
    session.get(f"{SITE}/b")

    # robots.txt -> /a -> /b: each follow-up request waits the full delay.
    assert clock.sleeps == [DELAY, DELAY]


@responses.activate
def test_honours_robots_crawl_delay(session: PoliteSession, clock: FakeClock) -> None:
    _robots("User-agent: *\nCrawl-delay: 10\n", status=200)
    responses.get(f"{SITE}/a", body="a")

    session.get(f"{SITE}/a")

    assert clock.sleeps == [10.0]


@responses.activate
def test_refuses_urls_disallowed_by_robots(session: PoliteSession) -> None:
    _robots("User-agent: *\nDisallow: /private\n", status=200)

    with pytest.raises(RobotsDisallowedError):
        session.get(f"{SITE}/private/page")
    assert [c.request.url for c in responses.calls] == [f"{SITE}/robots.txt"]


@responses.activate
def test_backs_off_on_429_using_retry_after(session: PoliteSession, clock: FakeClock) -> None:
    _robots()
    responses.get(f"{SITE}/jobs", status=429, headers={"Retry-After": "7"})
    responses.get(f"{SITE}/jobs", body="finally")

    assert session.get(f"{SITE}/jobs") == "finally"
    assert 7.0 in clock.sleeps


@responses.activate
def test_exponential_backoff_then_gives_up_on_503(session: PoliteSession, clock: FakeClock) -> None:
    _robots()
    responses.get(f"{SITE}/jobs", status=503)

    with pytest.raises(FetchError) as exc_info:
        session.get(f"{SITE}/jobs")

    assert exc_info.value.status == 503
    page_calls = [c for c in responses.calls if c.request.url == f"{SITE}/jobs"]
    assert len(page_calls) == 3  # first try + max_retries
    assert [s for s in clock.sleeps if s != DELAY] == [2.0, 4.0]


@responses.activate
def test_client_errors_are_not_retried(session: PoliteSession) -> None:
    _robots()
    responses.get(f"{SITE}/gone", status=404)

    with pytest.raises(FetchError) as exc_info:
        session.get(f"{SITE}/gone")

    assert exc_info.value.status == 404
    assert len([c for c in responses.calls if c.request.url == f"{SITE}/gone"]) == 1


@responses.activate
def test_retries_network_errors(session: PoliteSession) -> None:
    _robots()
    responses.get(f"{SITE}/flaky", body=requests.ConnectionError("reset"))
    responses.get(f"{SITE}/flaky", body="recovered")

    assert session.get(f"{SITE}/flaky") == "recovered"
