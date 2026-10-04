from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import open_db
from app.repositories.listings import ListingRepository
from app.repositories.scrape_runs import ScrapeRunRepository
from app.schemas import ScrapeRun, ScrapeRunStatus

FINISHED = datetime(2026, 10, 2, 13, 0, tzinfo=UTC)


def _record_run(db_path: Path, source: str, status: ScrapeRunStatus, inserted: int) -> None:
    with open_db(db_path) as conn:
        ScrapeRunRepository(conn).record(
            ScrapeRun(
                source=source,
                started_at=FINISHED.replace(hour=12),
                finished_at=FINISHED,
                status=status,
                pages=5,
                inserted=inserted,
                quality={"pay_hourly": 0.6},
            )
        )
        conn.commit()


def test_sources_report_open_listings_and_last_run(
    client: TestClient, db_path: Path, listing_ids: dict[str, str]
) -> None:
    _record_run(db_path, "studentjob", ScrapeRunStatus.OK, inserted=3)

    response = client.get("/api/meta/sources")

    assert response.status_code == 200
    by_name = {source["name"]: source for source in response.json()}
    assert set(by_name) == {"cambridge", "studentjob", "greenhouse"}
    assert by_name["studentjob"]["open_listings"] == 3
    assert by_name["studentjob"]["last_run"]["status"] == "ok"
    assert by_name["studentjob"]["last_run"]["quality"] == {"pay_hourly": 0.6}
    assert by_name["cambridge"]["last_run"] is None


def test_health_reports_when_listings_were_last_scraped(client: TestClient, db_path: Path) -> None:
    _record_run(db_path, "greenhouse", ScrapeRunStatus.PARTIAL, inserted=1)

    assert client.get("/api/health").json()["last_scraped_at"] == FINISHED.isoformat()


def test_closed_listings_leave_search_but_keep_their_page(
    client: TestClient, db_path: Path, listing_ids: dict[str, str]
) -> None:
    barista = listing_ids["Weekend Barista"]
    with open_db(db_path) as conn:
        url = ListingRepository(conn).get(barista).url  # type: ignore[union-attr]
        ListingRepository(conn).close_urls([url], FINISHED)
        conn.commit()

    titles = [item["title"] for item in client.get("/api/listings").json()["items"]]
    detail = client.get(f"/api/listings/{barista}").json()

    assert "Weekend Barista" not in titles
    assert detail["closed_at"] == FINISHED.isoformat().replace("+00:00", "Z")
