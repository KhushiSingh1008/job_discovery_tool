from pathlib import Path

from fastapi.testclient import TestClient


def test_health_reports_ok_and_creates_db(client: TestClient, db_path: Path) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "listings": 0}
    assert db_path.exists()
