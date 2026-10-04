from pathlib import Path

import pytest

from app.scraper.cli import main


def test_sources_command_succeeds() -> None:
    assert main(["sources"]) == 0


def test_unknown_source_is_rejected(db_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--source", "nope"]) == 2
    assert "Unknown source(s): nope" in capsys.readouterr().err


def test_rescore_command_runs_on_empty_database(
    db_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["rescore"]) == 0
    assert "Rescored 0 listings." in capsys.readouterr().out
    assert db_path.exists()


class _Session:
    """Stands in for PoliteSession: serves canned pages, works as a context manager."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(self, url: str) -> str:
        return self.pages[url]


def test_run_records_history_and_reports_status(
    db_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.scraper import cli, jobs
    from tests.unit.scraper.test_pipeline_lifecycle import URL, DetailAdapter

    monkeypatch.setattr(cli, "get_adapters", lambda names: [DetailAdapter(["barista"])])
    session = _Session({URL.format("barista"): "barista"})
    monkeypatch.setattr(jobs.PoliteSession, "from_settings", lambda settings: session)

    assert main(["run"]) == 0
    out = capsys.readouterr().out
    assert "detail" in out and "ok" in out
    assert "fields present:" in out

    assert main(["status"]) == 0
    assert "never run" in capsys.readouterr().out  # the real sources have not run


def test_run_exits_non_zero_when_a_source_yields_nothing(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.scraper import cli, jobs
    from tests.unit.scraper.test_pipeline_lifecycle import DetailAdapter

    monkeypatch.setattr(cli, "get_adapters", lambda names: [DetailAdapter([])])
    monkeypatch.setattr(jobs.PoliteSession, "from_settings", lambda settings: _Session({}))

    assert main(["run"]) == 1


def test_rescore_rederives_pay_from_stored_text(db_path: Path) -> None:
    from datetime import UTC, datetime

    from app.db import open_db
    from app.models import JobType, ListingIn
    from app.repositories.listings import ListingRepository, make_listing_id

    listing = ListingIn(
        title="Teaching Assistant Apprenticeship",
        employer="School",
        location="Leeds",
        pay_raw="£16,087 per month",
        pay_hourly=100.33,  # what an older parser stored
        job_type=JobType.FULL_TIME,
        posted_date=None,
        description="",
        url="https://x.test/ta",  # type: ignore[arg-type]
        source="studentjob",
    )
    with open_db(db_path) as conn:
        ListingRepository(conn).upsert(listing, datetime(2026, 10, 1, tzinfo=UTC))
        conn.commit()

    assert main(["rescore"]) == 0

    with open_db(db_path) as conn:
        stored = ListingRepository(conn).get(make_listing_id(listing.title, "School", "Leeds"))
    assert stored is not None and stored.pay_hourly == 8.25
