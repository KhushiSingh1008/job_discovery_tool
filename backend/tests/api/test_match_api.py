from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routers.match import get_matcher
from app.services.matching.keyword_matcher import KeywordMatcher

RESUME = (
    "Barista at a campus cafe for a year: customer service, cash handling on the till, "
    "food hygiene certificate, strong teamwork and communication."
)
JOB = (
    "We are hiring a weekend barista. You will need customer service skills, cash "
    "handling experience and a food hygiene certificate."
)


@pytest.fixture(autouse=True)
def offline_matcher(client: TestClient) -> Iterator[None]:
    """Keep API tests deterministic whatever key the developer has configured."""
    client.app.dependency_overrides[get_matcher] = KeywordMatcher  # type: ignore[attr-defined]
    yield


def _match(client: TestClient, **body: Any) -> Any:
    return client.post("/api/match", json=body)


def test_match_against_pasted_job_description(client: TestClient) -> None:
    response = _match(client, resume_text=RESUME, job_description=JOB)

    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "keyword"
    assert body["score"] >= 70
    assert {"customer service", "cash handling", "food hygiene"} <= set(body["matched_skills"])


def test_match_against_stored_listing(client: TestClient, listing_ids: dict[str, str]) -> None:
    response = _match(client, resume_text=RESUME, listing_id=listing_ids["Weekend Barista"])

    assert response.status_code == 200
    assert response.json()["engine"] == "keyword"


def test_unknown_listing_is_404(client: TestClient) -> None:
    assert _match(client, resume_text=RESUME, listing_id="nope").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"resume_text": RESUME},  # neither job source
        {"resume_text": RESUME, "listing_id": "x", "job_description": JOB},  # both
        {"resume_text": "too short", "job_description": JOB},
        {"resume_text": RESUME, "job_description": "short"},
        {"resume_text": "x" * 20_001, "job_description": JOB},
    ],
    ids=["no-job", "both-jobs", "short-resume", "short-job", "huge-resume"],
)
def test_invalid_requests_are_422(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/api/match", json=body).status_code == 422
