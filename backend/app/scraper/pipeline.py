"""Orchestrates one scrape: discover -> fetch -> parse -> normalise -> store -> retire.

- Failures are isolated: a bad page is logged and skipped, and a broken source does not
  stop the other sources.
- Re-runs are incremental: a detail page read within ``refresh_after`` is not downloaded
  again, the listing is just marked as still listed.
- Listings that have gone are closed, never deleted (the tracker may still point at them):
  a detail page answering 404/410, the site's own list of closed jobs, or a *complete*
  crawl of an exhaustive source that no longer shows them.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from pydantic import ValidationError

from app.models import JobType, ListingIn
from app.repositories.listings import ListingRepository, UpsertOutcome
from app.schemas import ScrapeRun, ScrapeRunStatus
from app.scraper.http import FetchError
from app.scraper.normalize.dates import parse_posted_date
from app.scraper.normalize.job_type import normalize_job_type
from app.scraper.normalize.pay import parse_weekly_hours, to_hourly
from app.scraper.normalize.text import clean_text
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing

logger = logging.getLogger(__name__)

MAX_ERRORS_KEPT = 20
DEFAULT_REFRESH_AFTER = timedelta(days=3)
GONE_STATUSES = frozenset({404, 410})
#: A "complete" crawl that would close more than this share of a source's open listings
#: is far more likely a scraper fault than a mass closure, so nothing is closed.
MAX_CLOSE_SHARE = 0.5


@dataclass(slots=True)
class SourceRunStats:
    source: str
    started_at: datetime
    pages: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed_pages: int = 0
    closed: int = 0
    aborted: bool = False
    limited: bool = False
    errors: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    #: Share of the source's open listings with each field, measured after the run.
    quality: dict[str, float] = field(default_factory=dict)

    @property
    def stored(self) -> int:
        return self.inserted + self.updated

    @property
    def seen(self) -> int:
        """Listings confirmed as still listed, whether re-read or not."""
        return self.stored + self.unchanged

    @property
    def status(self) -> ScrapeRunStatus:
        if self.aborted and self.seen == 0:
            return ScrapeRunStatus.FAILED
        if self.pages > 0 and self.seen == 0:
            return ScrapeRunStatus.EMPTY
        if self.aborted or self.failed_pages or self.gaps:
            return ScrapeRunStatus.PARTIAL
        return ScrapeRunStatus.OK

    def record_error(self, message: str) -> None:
        if len(self.errors) < MAX_ERRORS_KEPT:
            self.errors.append(message)

    def to_run(self, finished_at: datetime) -> ScrapeRun:
        return ScrapeRun(
            source=self.source,
            started_at=self.started_at,
            finished_at=finished_at,
            status=self.status,
            pages=self.pages,
            inserted=self.inserted,
            updated=self.updated,
            unchanged=self.unchanged,
            skipped=self.skipped,
            failed_pages=self.failed_pages,
            closed=self.closed,
            errors=[*self.errors, *(f"gap: {gap}" for gap in self.gaps)][:MAX_ERRORS_KEPT],
            quality=self.quality,
        )


def hourly_pay(pay_raw: str | None, description: str, job_type: JobType) -> float | None:
    """Hourly pay from the advert's own words, using the hours it states when it does."""
    return to_hourly(
        pay_raw,
        weekly_hours=parse_weekly_hours(f"{pay_raw or ''}\n{description}"),
        full_time=job_type is JobType.FULL_TIME,
    )


def normalize(raw: RawListing, adapter: SourceAdapter, today: date) -> ListingIn:
    """Turn a raw listing into a validated ``ListingIn`` (raises ``ValidationError``)."""
    title = clean_text(raw.title)
    job_type = normalize_job_type(
        raw.job_type_raw, title, raw.description, default=adapter.default_job_type
    )
    return ListingIn(
        title=title,
        employer=clean_text(raw.employer) or adapter.default_employer or "",
        location=clean_text(raw.location),
        pay_raw=clean_text(raw.pay_raw) or None,
        pay_hourly=hourly_pay(raw.pay_raw, raw.description, job_type),
        job_type=job_type,
        posted_date=parse_posted_date(raw.posted_raw, today),
        description=raw.description.strip(),
        url=raw.url,  # type: ignore[arg-type]  # pydantic validates str -> HttpUrl
        source=adapter.name,
    )


def _crawl(
    adapter: SourceAdapter,
    fetcher: Fetcher,
    repo: ListingRepository,
    conn: sqlite3.Connection,
    stats: SourceRunStats,
    *,
    limit: int | None,
    now: datetime,
    fetched_since: datetime,
) -> None:
    for page in adapter.discover(fetcher):
        if limit is not None and stats.stored >= limit:
            stats.limited = True
            break
        stats.pages += 1

        # Detail pages already read recently are not downloaded again.
        if page.html is None and repo.mark_seen_if_fresh(page.url, now, fetched_since):
            stats.unchanged += 1
            continue

        try:
            html = page.html if page.html is not None else fetcher.get(page.url)
            raw_listings = adapter.parse(page, html)
        except FetchError as exc:
            if exc.status in GONE_STATUSES:
                stats.closed += repo.close_urls([page.url], now)
                continue
            stats.failed_pages += 1
            stats.record_error(str(exc))
            continue
        except Exception as exc:  # noqa: BLE001 - one bad page must not abort the run
            stats.failed_pages += 1
            stats.record_error(f"{page.url}: {exc}")
            logger.warning("[%s] failed page %s: %s", adapter.name, page.url, exc)
            continue

        for raw in raw_listings:
            if limit is not None and stats.stored >= limit:
                stats.limited = True
                break
            try:
                listing = normalize(raw, adapter, now.date())
            except ValidationError as exc:
                stats.skipped += 1
                logger.debug("[%s] skipped %s: %s", adapter.name, raw.url, exc)
                continue
            outcome = repo.upsert(listing, now)
            if outcome is UpsertOutcome.INSERTED:
                stats.inserted += 1
            else:
                stats.updated += 1
        conn.commit()


def _close_unseen_if_complete(
    adapter: SourceAdapter, repo: ListingRepository, stats: SourceRunStats, now: datetime
) -> None:
    """Close listings a complete crawl of an exhaustive source no longer shows."""
    complete = adapter.report.complete and not (
        stats.aborted or stats.limited or stats.failed_pages
    )
    if not adapter.exhaustive or not complete or stats.seen == 0:
        return
    open_count = len(repo.open_urls(adapter.name))
    unseen = open_count - stats.seen
    if open_count and unseen / open_count > MAX_CLOSE_SHARE:
        stats.record_error(
            f"refused to close {unseen} of {open_count} listings: likely a scraper fault"
        )
        return
    stats.closed += repo.close_unseen(adapter.name, seen_before=now, now=now)


def run_source(
    adapter: SourceAdapter,
    fetcher: Fetcher,
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    now: datetime | None = None,
    refresh_after: timedelta = DEFAULT_REFRESH_AFTER,
) -> SourceRunStats:
    """Scrape one source into the database, committing after every page."""
    now = now or datetime.now(UTC)
    repo = ListingRepository(conn)
    stats = SourceRunStats(source=adapter.name, started_at=now)

    try:
        reported = adapter.closed_urls(fetcher, repo.open_urls(adapter.name))
        stats.closed += repo.close_urls(reported, now)
    except Exception as exc:  # noqa: BLE001 - the closed list is a bonus, not essential
        stats.record_error(f"closed-jobs list unavailable: {exc}")

    try:
        _crawl(
            adapter,
            fetcher,
            repo,
            conn,
            stats,
            limit=limit,
            now=now,
            fetched_since=now - refresh_after,
        )
    except Exception as exc:  # a broken source must not stop the others
        stats.aborted = True
        stats.record_error(f"discovery aborted: {exc}")
        logger.exception("[%s] source aborted", adapter.name)

    stats.gaps = list(adapter.report.gaps)
    _close_unseen_if_complete(adapter, repo, stats, now)
    conn.commit()
    stats.quality = repo.field_completeness(adapter.name)
    return stats


def run_all(
    adapters: list[SourceAdapter],
    fetcher: Fetcher,
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    refresh_after: timedelta = DEFAULT_REFRESH_AFTER,
) -> list[SourceRunStats]:
    return [
        run_source(adapter, fetcher, conn, limit=limit, refresh_after=refresh_after)
        for adapter in adapters
    ]
