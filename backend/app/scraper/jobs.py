"""One complete scrape job: every source, run history, stale listings, rescoring.

Shared by the CLI (``python -m app.scraper.cli run``) and the in-process scheduler, so a
manual run and a scheduled run behave identically.
"""

import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.enrichment.service import enrich_all
from app.repositories.listings import ListingRepository
from app.repositories.scrape_runs import ScrapeRunRepository
from app.rules import load_wage_rules
from app.scraper.http import PoliteSession
from app.scraper.pipeline import SourceRunStats, hourly_pay, run_all
from app.scraper.sources.base import SourceAdapter

logger = logging.getLogger(__name__)

# Only one scrape at a time per process, whether started by the CLI or the scheduler.
_SCRAPE_LOCK = threading.Lock()


class ScrapeAlreadyRunningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ScrapeJobResult:
    sources: list[SourceRunStats]
    stale_closed: int
    rescored: int

    @property
    def healthy(self) -> bool:
        """Every source confirmed at least one listing (an empty source needs attention)."""
        return all(stats.seen > 0 for stats in self.sources)


def renormalize_pay(conn: sqlite3.Connection) -> int:
    """Re-derive hourly pay from the stored advert text, so parser fixes reach old rows."""
    repo = ListingRepository(conn)
    changed = 0
    for listing in list(repo.iter_all()):  # read all first: updates follow
        pay = hourly_pay(listing.pay_raw, listing.description, listing.job_type)
        if pay != listing.pay_hourly:
            repo.set_pay_hourly(listing.id, pay)
            changed += 1
    conn.commit()
    return changed


def rescore(conn: sqlite3.Connection, settings: Settings) -> int:
    """Refresh everything derived from stored text: hourly pay, trust and eligibility."""
    renormalize_pay(conn)
    return enrich_all(
        conn, datetime.now(UTC).date(), load_wage_rules(), ghost_days=settings.ghost_job_days
    )


def run_scrape_job(
    conn: sqlite3.Connection,
    settings: Settings,
    adapters: list[SourceAdapter],
    *,
    limit: int | None = None,
) -> ScrapeJobResult:
    if not _SCRAPE_LOCK.acquire(blocking=False):
        raise ScrapeAlreadyRunningError("A scrape is already running")
    try:
        with PoliteSession.from_settings(settings) as session:
            results = run_all(
                adapters,
                session,
                conn,
                limit=limit,
                refresh_after=timedelta(days=settings.scraper_refresh_days),
            )
        finished = datetime.now(UTC)
        runs = ScrapeRunRepository(conn)
        for stats in results:
            runs.record(stats.to_run(finished))
        stale = ListingRepository(conn).close_stale(
            seen_before=finished - timedelta(days=settings.listing_stale_days), now=finished
        )
        conn.commit()
        result = ScrapeJobResult(results, stale, rescore(conn, settings))
        logger.info(
            "Scrape finished: %s",
            ", ".join(f"{s.source}={s.status.value}/{s.seen}" for s in results),
        )
        return result
    finally:
        _SCRAPE_LOCK.release()
