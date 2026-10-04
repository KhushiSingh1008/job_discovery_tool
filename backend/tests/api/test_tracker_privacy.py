"""Each browser has its own tracker: visitors never see or change each other's jobs."""

import pytest
from fastapi.testclient import TestClient

ALICE = {"X-Client-Id": "a1b2c3d4-0000-4000-8000-00000000aaaa"}
BOB = {"X-Client-Id": "b1b2c3d4-0000-4000-8000-00000000bbbb"}


@pytest.fixture
def alice_app_id(client: TestClient, listing_ids: dict[str, str]) -> int:
    body = {"listing_id": listing_ids["Weekend Barista"], "weekly_hours": 12, "status": "applied"}
    response = client.post("/api/applications", json=body, headers=ALICE)
    assert response.status_code == 201
    return int(response.json()["id"])


def test_trackers_are_private_per_browser(client: TestClient, alice_app_id: int) -> None:
    assert [a["id"] for a in client.get("/api/applications", headers=ALICE).json()] == [
        alice_app_id
    ]
    assert client.get("/api/applications", headers=BOB).json() == []
    assert client.get("/api/applications").json() == []  # the shared default tracker


def test_others_cannot_read_change_or_delete_an_application(
    client: TestClient, alice_app_id: int
) -> None:
    url = f"/api/applications/{alice_app_id}"

    assert client.get(url, headers=BOB).status_code == 404
    assert client.patch(url, json={"weekly_hours": 40}, headers=BOB).status_code == 404
    assert client.delete(url, headers=BOB).status_code == 404
    assert client.get(url, headers=ALICE).json()["weekly_hours"] == 12


def test_hours_guard_counts_only_your_own_jobs(client: TestClient, alice_app_id: int) -> None:
    # The guard counts jobs at interview stage or beyond.
    patch = {"status": "interviewing"}
    client.patch(f"/api/applications/{alice_app_id}", json=patch, headers=ALICE)

    def committed(headers: dict[str, str]) -> float:
        return float(
            client.get("/api/applications/hours-summary", headers=headers).json()["potential_hours"]
        )

    assert committed(ALICE) == 12
    assert committed(BOB) == 0


def test_two_browsers_can_track_the_same_job(
    client: TestClient, listing_ids: dict[str, str], alice_app_id: int
) -> None:
    body = {"listing_id": listing_ids["Weekend Barista"]}
    assert client.post("/api/applications", json=body, headers=BOB).status_code == 201
    assert client.post("/api/applications", json=body, headers=BOB).status_code == 409


@pytest.mark.parametrize(
    "bad", ["short", "has spaces in it 1234", "x" * 65, "semi;colon-1234567890"]
)
def test_malformed_client_ids_are_rejected(client: TestClient, bad: str) -> None:
    assert client.get("/api/applications", headers={"X-Client-Id": bad}).status_code == 400
