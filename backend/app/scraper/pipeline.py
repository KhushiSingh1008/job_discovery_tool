"""Orchestrates one scrape: discover -> fetch -> parse -> normalise -> store.

Failures are isolated: a bad page is logged and skipped, and a broken source does not
stop the other sources.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from pydantic import ValidationError

from app.models import ListingIn
from app.repositories.listings import ListingRepository, UpsertOutcome
from app.scraper.normalize.dates import parse_posted_date
from app.scraper.normalize.job_type import normalize_job_type
from app.scraper.normalize.pay import to_hourly
from app.scraper.normalize.text import clean_text
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing

logger = logging.getLogger(__name__)

MAX_ERRORS_KEPT = 20


@dataclass(slots=True)
class SourceRunStats:
    source: str
    pages: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed_pages: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def stored(self) -> int:
        return self.inserted + self.updated

    def record_error(self, message: str) -> None:
        if len(self.errors) < MAX_ERRORS_KEPT:
            self.errors.append(message)


def normalize(raw: RawListing, adapter: SourceAdapter, today: date) -> ListingIn:
    """Turn a raw listing into a validated ``ListingIn`` (raises ``ValidationError``)."""
    title = clean_text(raw.title)
    return ListingIn(
        title=title,
        employer=clean_text(raw.employer) or adapter.default_employer or "",
        location=clean_text(raw.location),
        pay_raw=clean_text(raw.pay_raw) or None,
        pay_hourly=to_hourly(raw.pay_raw),
        job_type=normalize_job_type(
            raw.job_type_raw, title, raw.description, default=adapter.default_job_type
        ),
        posted_date=parse_posted_date(raw.posted_raw, today),
        description=raw.description.strip(),
        url=raw.url,  # type: ignore[arg-type]  # pydantic validates str -> HttpUrl
        source=adapter.name,
    )


def run_source(
    adapter: SourceAdapter,
    fetcher: Fetcher,
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    now: datetime | None = None,
) -> SourceRunStats:
    """Scrape one source into the database, committing after every page."""
    now = now or datetime.now(UTC)
    repo = ListingRepository(conn)
    stats = SourceRunStats(source=adapter.name)

    try:
        for page in adapter.discover(fetcher):
            if limit is not None and stats.stored >= limit:
                break
            stats.pages += 1
            try:
                html = page.html if page.html is not None else fetcher.get(page.url)
                raw_listings = adapter.parse(page.url, html)
            except Exception as exc:  # noqa: BLE001 - one bad page must not abort the run
                stats.failed_pages += 1
                stats.record_error(f"{page.url}: {exc}")
                logger.warning("[%s] failed page %s: %s", adapter.name, page.url, exc)
                continue

            for raw in raw_listings:
                if limit is not None and stats.stored >= limit:
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
    except Exception as exc:  # a broken source must not stop the others
        stats.record_error(f"discovery aborted: {exc}")
        logger.exception("[%s] source aborted", adapter.name)
        conn.commit()

    return stats


def run_all(
    adapters: list[SourceAdapter],
    fetcher: Fetcher,
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
) -> list[SourceRunStats]:
    return [run_source(adapter, fetcher, conn, limit=limit) for adapter in adapters]
