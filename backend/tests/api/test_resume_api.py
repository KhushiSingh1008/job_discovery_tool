from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routers.resume import get_enhancer
from app.services.enhancement.rules import RuleBasedEnhancer

RESUME = """Sam Lee
- Responsible for handling cash on the till at a campus shop
- Served customers during busy lunchtime shifts
"""
JOB = (
    "We are hiring a weekend barista. You will need customer service skills, cash "
    "handling experience and a food hygiene certificate."
)


@pytest.fixture(autouse=True)
def offline_enhancer(client: TestClient) -> Iterator[None]:
    """Keep API tests deterministic whatever key the developer has configured."""
    client.app.dependency_overrides[get_enhancer] = RuleBasedEnhancer  # type: ignore[attr-defined]
    yield


def _enhance(client: TestClient, **body: Any) -> Any:
    return client.post("/api/resume/enhance", json=body)


def test_enhance_against_pasted_job_description(client: TestClient) -> None:
    response = _enhance(client, resume_text=RESUME, job_description=JOB)

    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "rules"
    assert body["notice"] is None
    first = body["suggestions"][0]
    assert set(first) == {"id", "kind", "section", "original", "replacement", "reason"}
    assert "this role" in first["replacement"]  # profile aimed at the pasted job


def test_enhance_against_stored_listing(client: TestClient, listing_ids: dict[str, str]) -> None:
    response = _enhance(client, resume_text=RESUME, listing_id=listing_ids["Weekend Barista"])

    assert response.status_code == 200
    profile = response.json()["suggestions"][0]
    assert "the Weekend Barista role" in profile["replacement"]


def test_unknown_listing_is_404(client: TestClient) -> None:
    assert _enhance(client, resume_text=RESUME, listing_id="nope").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"resume_text": RESUME},
        {"resume_text": "too short", "job_description": JOB},
        {"resume_text": RESUME, "listing_id": "x", "job_description": JOB},
    ],
    ids=["no-job", "short-resume", "both-jobs"],
)
def test_invalid_requests_are_422(client: TestClient, body: dict[str, Any]) -> None:
    assert _enhance(client, **body).status_code == 422
