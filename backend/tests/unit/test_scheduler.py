from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app import scheduler as scheduler_module
from app.config import Settings
from app.db import open_db
from app.repositories.scrape_runs import ScrapeRunRepository
from app.scheduler import ScrapeScheduler
from app.schemas import ScrapeRun, ScrapeRunStatus
from app.scraper.jobs import ScrapeAlreadyRunningError

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _scheduler(tmp_path: Path) -> ScrapeScheduler:
    settings = Settings(database_path=tmp_path / "jobs.db", scrape_interval_hours=24)
    return ScrapeScheduler(settings, clock=lambda: NOW)


def _last_run_at(tmp_path: Path, finished: datetime) -> None:
    with open_db(tmp_path / "jobs.db") as conn:
        ScrapeRunRepository(conn).record(
            ScrapeRun(
                source="cambridge",
                started_at=finished - timedelta(minutes=5),
                finished_at=finished,
                status=ScrapeRunStatus.OK,
            )
        )
        conn.commit()


def test_due_when_never_scraped(tmp_path: Path) -> None:
    assert _scheduler(tmp_path).is_due()


def test_not_due_within_the_interval(tmp_path: Path) -> None:
    _last_run_at(tmp_path, NOW - timedelta(hours=23))
    assert not _scheduler(tmp_path).is_due()


def test_due_again_after_the_interval(tmp_path: Path) -> None:
    _last_run_at(tmp_path, NOW - timedelta(hours=24))
    assert _scheduler(tmp_path).is_due()


def test_runs_every_source_when_due(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        scheduler_module,
        "run_scrape_job",
        lambda conn, settings, adapters: calls.append([a.name for a in adapters]),
    )

    assert _scheduler(tmp_path).run_if_due() is True
    assert calls == [["cambridge", "studentjob", "greenhouse"]]


def test_skips_when_not_due(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _last_run_at(tmp_path, NOW - timedelta(hours=1))
    monkeypatch.setattr(scheduler_module, "run_scrape_job", pytest.fail)

    assert _scheduler(tmp_path).run_if_due() is False


@pytest.mark.parametrize("error", [ScrapeAlreadyRunningError("busy"), RuntimeError("network down")])
def test_survives_scrape_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def explode(*_: object) -> None:
        raise error

    monkeypatch.setattr(scheduler_module, "run_scrape_job", explode)

    _scheduler(tmp_path).run_if_due()  # must not raise


def test_start_and_stop_without_scraping(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "jobs.db",
        scrape_interval_hours=24,
        scrape_start_delay_seconds=3600,
    )
    scheduler = ScrapeScheduler(settings)
    scheduler.start()
    scheduler.stop(timeout=2)  # the start delay is interrupted immediately
