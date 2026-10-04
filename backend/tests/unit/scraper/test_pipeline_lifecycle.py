"""Incremental re-fetching, closing listings that have gone, and run health."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from app.models import JobType
from app.repositories.listings import ListingRepository, ListingSearch
from app.schemas import ScrapeRunStatus
from app.scraper.discovery import Page
from app.scraper.http import FetchError
from app.scraper.pipeline import normalize, run_source
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing
from tests.fakes import FakeFetcher

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
URL = "https://jobs.example/{}"


def _raw(slug: str, pay_raw: str | None = None, **overrides: str) -> RawListing:
    fields = {"title": slug.title(), "employer": "Cafe Co", "url": URL.format(slug)}
    fields.update(overrides)
    return RawListing(**fields, pay_raw=pay_raw)


class DetailAdapter(SourceAdapter):
    """Discovers detail pages by slug; each page's HTML is the slug it holds."""

    name = "detail"
    label = "Detail pages"
    default_job_type = JobType.PART_TIME

    def __init__(
        self,
        slugs: list[str],
        *,
        complete_listing: bool = False,
        closed: set[str] | None = None,
        gap: str | None = None,
    ) -> None:
        super().__init__()
        self.slugs = slugs
        self.closed = closed or set()
        self.gap = gap
        if complete_listing:
            self.exhaustive = True  # type: ignore[misc]  # per-instance override for tests

    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        if self.gap:
            self.report.gap(self.gap)
        for slug in self.slugs:
            yield Page(URL.format(slug))

    def closed_urls(self, fetcher: Fetcher, open_urls: set[str]) -> set[str]:
        return {URL.format(slug) for slug in self.closed} & open_urls

    def parse(self, page: Page, html: str) -> list[RawListing]:
        return [_raw(html)]


def _pages(*slugs: str) -> FakeFetcher:
    return FakeFetcher({URL.format(slug): slug for slug in slugs})


def _open_titles(db: sqlite3.Connection) -> list[str]:
    items, _ = ListingRepository(db).search(ListingSearch(page_size=50))
    return sorted(item.title for item in items)


def test_recent_detail_pages_are_not_fetched_again(db: sqlite3.Connection) -> None:
    run_source(DetailAdapter(["barista", "porter"]), _pages("barista", "porter"), db, now=NOW)

    fetcher = _pages("barista", "porter")
    later = NOW + timedelta(days=1)
    stats = run_source(DetailAdapter(["barista", "porter"]), fetcher, db, now=later)

    assert fetcher.requested == []
    assert (stats.unchanged, stats.stored) == (2, 0)
    assert stats.status is ScrapeRunStatus.OK


def test_detail_pages_are_refreshed_after_the_window(db: sqlite3.Connection) -> None:
    run_source(DetailAdapter(["barista"]), _pages("barista"), db, now=NOW)

    fetcher = _pages("barista")
    stats = run_source(DetailAdapter(["barista"]), fetcher, db, now=NOW + timedelta(days=4))

    assert fetcher.requested == [URL.format("barista")]
    assert stats.updated == 1


def test_a_404_detail_page_closes_the_listing(db: sqlite3.Connection) -> None:
    slugs = ["barista", "porter"]
    run_source(DetailAdapter(slugs), _pages(*slugs), db, now=NOW)

    stats = run_source(DetailAdapter(slugs), _pages("porter"), db, now=NOW + timedelta(days=5))

    assert stats.closed == 1
    assert stats.failed_pages == 0
    assert _open_titles(db) == ["Porter"]
    everything, _ = ListingRepository(db).search(ListingSearch(include_closed=True))
    assert len(everything) == 2  # kept for the tracker, just hidden from search


def test_a_closed_listing_reopens_when_it_is_seen_again(db: sqlite3.Connection) -> None:
    run_source(DetailAdapter(["barista"]), _pages("barista"), db, now=NOW)
    run_source(DetailAdapter(["barista"]), _pages(), db, now=NOW + timedelta(days=5))
    assert _open_titles(db) == []

    run_source(DetailAdapter(["barista"]), _pages("barista"), db, now=NOW + timedelta(days=6))

    assert _open_titles(db) == ["Barista"]


def test_jobs_the_site_reports_closed_are_closed(db: sqlite3.Connection) -> None:
    slugs = ["barista", "porter"]
    run_source(DetailAdapter(slugs), _pages(*slugs), db, now=NOW)

    adapter = DetailAdapter([], closed={"porter", "never-stored"})
    stats = run_source(adapter, _pages(), db, now=NOW)

    assert stats.closed == 1
    assert _open_titles(db) == ["Barista"]


def test_complete_crawl_of_an_exhaustive_source_closes_what_it_no_longer_lists(
    db: sqlite3.Connection,
) -> None:
    slugs = ["barista", "porter", "chef"]
    run_source(DetailAdapter(slugs, complete_listing=True), _pages(*slugs), db, now=NOW)

    adapter = DetailAdapter(["barista", "chef"], complete_listing=True)
    stats = run_source(adapter, _pages(*slugs), db, now=NOW + timedelta(days=1))

    assert stats.closed == 1
    assert _open_titles(db) == ["Barista", "Chef"]


def test_sampled_sources_never_close_unseen_listings(db: sqlite3.Connection) -> None:
    slugs = ["barista", "porter", "chef"]
    run_source(DetailAdapter(slugs), _pages(*slugs), db, now=NOW)

    stats = run_source(
        DetailAdapter(["barista", "chef"]), _pages(*slugs), db, now=NOW + timedelta(days=1)
    )

    assert stats.closed == 0


def test_a_crawl_with_gaps_never_closes_unseen_listings(db: sqlite3.Connection) -> None:
    slugs = ["barista", "porter", "chef"]
    run_source(DetailAdapter(slugs, complete_listing=True), _pages(*slugs), db, now=NOW)

    adapter = DetailAdapter(["barista", "chef"], complete_listing=True, gap="page 2 timed out")
    stats = run_source(adapter, _pages(*slugs), db, now=NOW + timedelta(days=1))

    assert stats.closed == 0
    assert stats.status is ScrapeRunStatus.PARTIAL
    assert "gap: page 2 timed out" in stats.to_run(NOW).errors


def test_mass_closure_is_refused_as_a_likely_scraper_fault(db: sqlite3.Connection) -> None:
    slugs = ["barista", "porter", "chef"]
    run_source(DetailAdapter(slugs, complete_listing=True), _pages(*slugs), db, now=NOW)

    adapter = DetailAdapter(["barista"], complete_listing=True)
    stats = run_source(adapter, _pages(*slugs), db, now=NOW + timedelta(days=1))

    assert stats.closed == 0
    assert any("refused to close 2 of 3" in error for error in stats.errors)


def test_pages_without_listings_mark_the_run_empty(db: sqlite3.Connection) -> None:
    class Blank(DetailAdapter):
        def parse(self, page: Page, html: str) -> list[RawListing]:
            return []  # e.g. the site changed its layout and every selector misses

    stats = run_source(Blank(["barista"]), _pages("barista"), db, now=NOW)

    assert stats.status is ScrapeRunStatus.EMPTY


def test_unreachable_source_is_failed(db: sqlite3.Connection) -> None:
    class Broken(DetailAdapter):
        def discover(self, fetcher: Fetcher) -> Iterator[Page]:
            raise FetchError("https://jobs.example", "HTTP 503", 503)

    stats = run_source(Broken([]), _pages(), db, now=NOW)

    assert stats.status is ScrapeRunStatus.FAILED
    assert stats.errors == ["discovery aborted: https://jobs.example: HTTP 503"]


def test_quality_report_counts_fields_present(db: sqlite3.Connection) -> None:
    class Mixed(DetailAdapter):
        def parse(self, page: Page, html: str) -> list[RawListing]:
            pay = "£12.50 per hour" if html == "barista" else None
            return [_raw(html, pay_raw=pay, location="Leeds")]

    stats = run_source(Mixed(["barista", "porter"]), _pages("barista", "porter"), db, now=NOW)

    assert stats.quality["pay_hourly"] == 0.5
    assert stats.quality["location"] == 1.0


def test_weekly_pay_uses_the_hours_stated_in_the_advert() -> None:
    raw = _raw(
        "barista",
        pay_raw="£100.00 - £400.00 per week",
        description="Hours: 4 - 20 hours per week\n\nServe coffee.",
    )

    listing = normalize(raw, DetailAdapter([]), NOW.date())

    assert listing.pay_hourly == 20.0
