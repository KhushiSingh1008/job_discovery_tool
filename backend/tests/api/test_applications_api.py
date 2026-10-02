from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_now
from tests.factories import NOW


def _track(client: TestClient, listing_id: str, **fields: Any) -> dict[str, Any]:
    response = client.post("/api/applications", json={"listing_id": listing_id, **fields})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _patch(client: TestClient, application_id: int, **fields: Any) -> Any:
    return client.patch(f"/api/applications/{application_id}", json=fields)


class TestCrud:
    def test_create_saved_application_with_listing_details(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        app = _track(client, listing_ids["Weekend Barista"], weekly_hours=12)

        assert app["status"] == "saved"
        assert app["applied_at"] is None
        assert (app["title"], app["employer"], app["weekly_hours"]) == (
            "Weekend Barista",
            "Bean & Leaf",
            12,
        )
        assert client.get("/api/applications").json()[0]["id"] == app["id"]

    def test_creating_as_applied_records_applied_at(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        app = _track(client, listing_ids["Delivery Rider"], status="applied")
        assert app["applied_at"] is not None

    def test_unknown_listing_and_duplicates_are_rejected(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        missing = client.post("/api/applications", json={"listing_id": "nope"})
        assert missing.status_code == 404

        _track(client, listing_ids["Weekend Barista"])
        duplicate = client.post(
            "/api/applications", json={"listing_id": listing_ids["Weekend Barista"]}
        )
        assert duplicate.status_code == 409

    @pytest.mark.parametrize("hours", [-1, 169])
    def test_weekly_hours_are_validated(
        self, client: TestClient, listing_ids: dict[str, str], hours: int
    ) -> None:
        response = client.post(
            "/api/applications",
            json={"listing_id": listing_ids["Weekend Barista"], "weekly_hours": hours},
        )
        assert response.status_code == 422

    def test_update_notes_and_hours_only(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        app = _track(client, listing_ids["Weekend Barista"])

        updated = _patch(client, app["id"], notes="Ask about Sunday shifts", weekly_hours=8)

        assert updated.status_code == 200
        assert updated.json()["notes"] == "Ask about Sunday shifts"
        assert updated.json()["status"] == "saved"

    def test_delete(self, client: TestClient, listing_ids: dict[str, str]) -> None:
        app = _track(client, listing_ids["Weekend Barista"])

        assert client.delete(f"/api/applications/{app['id']}").status_code == 204
        assert client.get(f"/api/applications/{app['id']}").status_code == 404
        assert client.delete(f"/api/applications/{app['id']}").status_code == 404


class TestStatusPipeline:
    def test_moving_to_applied_stamps_dates(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        app = _track(client, listing_ids["Weekend Barista"])

        applied = _patch(client, app["id"], status="applied").json()

        assert applied["status"] == "applied"
        assert applied["applied_at"] is not None
        assert applied["last_contact_at"] is not None

    def test_full_happy_path(self, client: TestClient, listing_ids: dict[str, str]) -> None:
        app = _track(client, listing_ids["Delivery Rider"])
        for status in ("applied", "interviewing", "offered"):
            response = _patch(client, app["id"], status=status)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == status

    @pytest.mark.parametrize(
        ("path", "invalid_next"),
        [
            (["applied"], "saved"),
            ([], "offered"),  # cannot skip from saved straight to an offer
            (["rejected"], "applied"),  # rejected is final
        ],
    )
    def test_invalid_transitions_are_409(
        self,
        client: TestClient,
        listing_ids: dict[str, str],
        path: list[str],
        invalid_next: str,
    ) -> None:
        app = _track(client, listing_ids["Delivery Rider"])
        for status in path:
            assert _patch(client, app["id"], status=status).status_code == 200

        response = _patch(client, app["id"], status=invalid_next)

        assert response.status_code == 409
        assert "Cannot move" in response.json()["detail"]


class TestHoursSummary:
    def _offer(self, client: TestClient, listing_id: str, hours: float, final: str) -> None:
        app = _track(client, listing_id, status="applied", weekly_hours=hours)
        if final in ("interviewing", "offered"):
            _patch(client, app["id"], status="interviewing")
        if final == "offered":
            _patch(client, app["id"], status="offered")

    def test_over_the_uk_student_cap(self, client: TestClient, listing_ids: dict[str, str]) -> None:
        self._offer(client, listing_ids["Weekend Barista"], 12, "offered")
        self._offer(client, listing_ids["Delivery Rider"], 10, "offered")

        body = client.get("/api/applications/hours-summary").json()

        assert body["cap_hours"] == 20
        assert body["cap_source"] == "visa_rule"
        assert body["committed_hours"] == 22
        assert body["status"] == "over_limit"
        assert body["source_url"].startswith("https://www.gov.uk/")

    def test_interviews_that_would_push_over_the_cap_warn_early(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        self._offer(client, listing_ids["Weekend Barista"], 12, "offered")
        self._offer(client, listing_ids["Delivery Rider"], 10, "interviewing")

        body = client.get("/api/applications/hours-summary").json()

        assert (body["committed_hours"], body["potential_hours"]) == (12, 22)
        assert body["status"] == "near_limit"

    def test_override_and_other_visas(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        self._offer(client, listing_ids["Weekend Barista"], 22, "offered")
        url = "/api/applications/hours-summary"

        override = client.get(url, params={"cap_override": 30}).json()
        graduate = client.get(url, params={"visa_type": "graduate"}).json()
        australia = client.get(url, params={"country": "AU"}).json()
        unknown = client.get(url, params={"country": "ZZ", "visa_type": "x"}).json()

        assert (override["cap_source"], override["status"]) == ("user_override", "ok")
        assert (graduate["status"], graduate["cap_hours"]) == ("no_limit", None)
        assert (australia["cap_hours"], australia["status"]) == (24, "near_limit")
        assert (unknown["cap_source"], unknown["cap_hours"]) == ("fallback", 20)


class TestReminders:
    def test_reminder_after_seven_quiet_days(
        self, client: TestClient, listing_ids: dict[str, str]
    ) -> None:
        applied = _track(client, listing_ids["Weekend Barista"], status="applied")
        _track(client, listing_ids["Delivery Rider"])  # only saved: no reminder

        assert client.get("/api/applications/reminders").json() == []

        later = NOW + timedelta(days=8)
        client.app.dependency_overrides[get_now] = lambda: later
        reminders = client.get("/api/applications/reminders").json()

        assert [r["application_id"] for r in reminders] == [applied["id"]]
        assert reminders[0]["days_silent"] == 8
        assert "Weekend Barista" in reminders[0]["draft_message"]
        assert "Bean & Leaf" in reminders[0]["draft_message"]
