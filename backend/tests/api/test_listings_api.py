from typing import Any

import pytest
from fastapi.testclient import TestClient


def _titles(client: TestClient, **params: Any) -> list[str]:
    response = client.get("/api/listings", params=params)
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


@pytest.mark.usefixtures("listing_ids")
class TestSearch:
    def test_default_lists_everything_newest_first_without_descriptions(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/listings").json()

        assert body["total"] == 5
        assert [item["title"] for item in body["items"]][:2] == [
            "Delivery Rider",
            "Weekend Barista",
        ]
        assert "description" not in body["items"][0]
        assert {"title", "employer", "location", "pay_raw", "job_type", "posted_date"} <= set(
            body["items"][0]
        )

    def test_every_word_must_match(self, client: TestClient) -> None:
        assert _titles(client, q="summer intern") == ["Summer Software Intern"]
        assert _titles(client, q="summer barista") == []

    def test_search_covers_description_and_escapes_wildcards(self, client: TestClient) -> None:
        assert _titles(client, q="sponsor") == ["Graduate Analyst"]
        assert _titles(client, q="100%") == ["Weekend Barista"]  # literal %, not a wildcard
        assert _titles(client, q="_") == []

    def test_filters_combine(self, client: TestClient) -> None:
        assert set(_titles(client, job_type=["internship", "full-time"])) == {
            "Summer Software Intern",
            "Graduate Analyst",
        }
        assert _titles(client, location="LEEDS") == ["Delivery Rider"]
        assert set(_titles(client, min_pay=13)) == {"Summer Software Intern", "Delivery Rider"}
        assert _titles(client, job_type="part-time", min_pay=13) == ["Delivery Rider"]
        assert _titles(client, source="greenhouse", q="rider") == ["Delivery Rider"]

    def test_trust_and_eligibility_filters(self, client: TestClient) -> None:
        assert "Earn money with surveys" not in _titles(client, min_trust=50)
        assert _titles(client, eligibility="student-friendly") == ["Weekend Barista"]
        assert _titles(client, eligibility="right-to-work-required") == ["Graduate Analyst"]

    def test_posted_within_days_is_relative_to_now(self, client: TestClient) -> None:
        assert "Graduate Analyst" not in _titles(client, posted_within_days=7)
        assert len(_titles(client, posted_within_days=7)) == 4

    def test_sort_by_pay_puts_unknown_pay_last(self, client: TestClient) -> None:
        assert _titles(client, sort="pay") == [
            "Summer Software Intern",
            "Delivery Rider",
            "Weekend Barista",
            "Earn money with surveys",
            "Graduate Analyst",
        ]

    def test_sort_by_trust_is_descending(self, client: TestClient) -> None:
        items = client.get("/api/listings", params={"sort": "trust"}).json()["items"]
        scores = [item["trust_score"] for item in items]
        assert scores == sorted(scores, reverse=True)

    def test_pagination(self, client: TestClient) -> None:
        body = client.get("/api/listings", params={"page": 3, "page_size": 2}).json()
        assert (body["total"], body["page"], len(body["items"])) == (5, 3, 1)

    @pytest.mark.parametrize(
        "params",
        [
            {"page_size": 101},
            {"page": 0},
            {"job_type": "gig"},
            {"min_trust": 101},
            {"sort": "random"},
            {"eligibility": "maybe"},
        ],
    )
    def test_invalid_parameters_are_rejected(
        self, client: TestClient, params: dict[str, Any]
    ) -> None:
        assert client.get("/api/listings", params=params).status_code == 422


def test_listing_detail_includes_description_and_trust_reasons(
    client: TestClient, listing_ids: dict[str, str]
) -> None:
    response = client.get(f"/api/listings/{listing_ids['Earn money with surveys']}")

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Get paid to share your opinion."
    codes = {flag["code"] for flag in body["trust_flags"]}
    assert {"pay_below_legal_minimum", "income_claims"} <= codes


def test_unknown_listing_is_404(client: TestClient) -> None:
    assert client.get("/api/listings/nope").status_code == 404


@pytest.mark.usefixtures("listing_ids")
def test_filter_facets(client: TestClient) -> None:
    body = client.get("/api/meta/filters").json()

    assert {"value": "part-time", "count": 3} in body["job_types"]
    assert body["locations"][0] == {"value": "London", "count": 2}
    assert body["max_pay_hourly"] == 25.0
    assert {f["value"] for f in body["sources"]} == {"studentjob", "greenhouse"}


def test_visa_rules_endpoint(client: TestClient) -> None:
    body = client.get("/api/visa-rules").json()
    assert body["fallback_hours_per_week"] == 20
    assert any(r["country"] == "UK" and r["visa_type"] == "student" for r in body["rules"])
