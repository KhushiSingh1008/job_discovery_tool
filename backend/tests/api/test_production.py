"""Production behaviour: rate limits, security headers and serving the built frontend."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.rate_limit import RateLimiter
from app.config import get_settings

RESUME = "Sam Lee\n- Responsible for handling cash on the till at a campus shop every week"
JOB = "We are hiring a weekend barista with customer service and cash handling skills."


def test_rate_limiter_counts_a_sliding_window() -> None:
    now = [0.0]
    limiter = RateLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.hit("a") is None
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 60  # third request waits for the first to expire
    assert limiter.hit("b") is None  # other clients are unaffected
    now[0] = 61
    assert limiter.hit("a") is None


def test_resume_tools_share_an_hourly_limit(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GG_RESUME_REQUESTS_PER_HOUR", "2")
    get_settings.cache_clear()
    from app.api.main import create_app

    with TestClient(create_app()) as client:
        body = {"resume_text": RESUME, "job_description": JOB}
        assert client.post("/api/match", json=body).status_code == 200
        assert client.post("/api/resume/enhance", json=body).status_code == 200
        limited = client.post("/api/match", json=body)

    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    assert "try again later" in limited.json()["detail"]


def test_security_headers_are_set(client: TestClient) -> None:
    headers = client.get("/api/health").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "strict-origin" in headers["Referrer-Policy"]


@pytest.fixture
def frontend(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    (dist / "assets" / "app-123.js").write_text("console.log('app')")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("outside the build")
    monkeypatch.setenv("GG_STATIC_DIR", str(dist))
    get_settings.cache_clear()
    from app.api.main import create_app

    with TestClient(create_app()) as client:
        yield client


def test_client_routes_get_the_app_shell(frontend: TestClient) -> None:
    for path in ["/", "/tracker", "/jobs/abc123"]:
        response = frontend.get(path)
        assert response.status_code == 200
        assert "id=root" in response.text
        assert response.headers["Cache-Control"] == "no-cache"


def test_uptime_monitors_can_use_head(frontend: TestClient) -> None:
    assert frontend.head("/").status_code == 200


def test_hashed_assets_are_cached_for_a_year(frontend: TestClient) -> None:
    response = frontend.get("/assets/app-123.js")

    assert response.status_code == 200
    assert "immutable" in response.headers["Cache-Control"]
    assert frontend.get("/favicon.svg").text == "<svg/>"


def test_api_routes_are_not_swallowed_by_the_frontend(frontend: TestClient) -> None:
    assert frontend.get("/api/health").json()["status"] == "ok"
    assert frontend.get("/api/nope").status_code == 404


def test_files_outside_the_build_are_never_served(frontend: TestClient) -> None:
    response = frontend.get("/../secret.txt")
    assert "outside the build" not in response.text
    response = frontend.get("/%2e%2e/secret.txt")
    assert "outside the build" not in response.text
