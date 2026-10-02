import sqlite3
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest

from app.models import JobType
from app.repositories.listings import ListingRepository
from app.scraper.discovery import Page
from app.scraper.pipeline import normalize, run_source
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing
from tests.fakes import FakeFetcher

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def _raw(title: str, **overrides: str) -> RawListing:
    fields = {
        "title": title,
        "employer": "Bean & Leaf",
        "url": f"https://beanandleaf.example/jobs/{title.lower().replace(' ', '-')}",
        "location": "Manchester",
        "pay_raw": "£12.21 per hour",
    }
    fields.update(overrides)
    return RawListing(**fields)


class FakeAdapter(SourceAdapter):
    """Pages are keyed by URL; the HTML body names which canned listings it contains."""

    name = "fake"
    label = "Fake source"
    default_job_type = JobType.PART_TIME
    default_employer = "Default Employer"

    def __init__(self, pages: list[Page], content: dict[str, list[RawListing]]) -> None:
        self.pages = pages
        self.content = content

    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        yield from self.pages

    def parse(self, page: Page, html: str) -> list[RawListing]:
        if html == "boom":
            raise ValueError("layout changed")
        return self.content[html]


class ExplodingDiscoveryAdapter(FakeAdapter):
    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        yield from self.pages
        raise RuntimeError("site redesigned")


def test_normalize_applies_all_normalisers_and_defaults() -> None:
    adapter = FakeAdapter([], {})
    raw = _raw("  Barista ", employer="", pay_raw="£24,000 per annum", posted_raw="3 days ago")

    listing = normalize(raw, adapter, date(2026, 10, 2))

    assert listing.title == "Barista"
    assert listing.employer == "Default Employer"
    assert listing.pay_hourly == 12.31
    assert listing.job_type is JobType.PART_TIME
    assert listing.posted_date == date(2026, 9, 29)
    assert listing.source == "fake"


def test_run_source_stores_listings_and_isolates_failures(db: sqlite3.Connection) -> None:
    adapter = FakeAdapter(
        pages=[
            Page("https://ex.com/p1", html="p1"),  # pre-fetched by discovery
            Page("https://ex.com/p2"),  # fetched by the pipeline
            Page("https://ex.com/broken", html="boom"),  # parser raises
            Page("https://ex.com/404"),  # fetch fails
        ],
        content={
            "p1": [_raw("Barista"), _raw("Kitchen Porter"), _raw("", url="not a url")],
            "p2": [_raw("Summer Internship", job_type_raw="INTERN")],
        },
    )
    fetcher = FakeFetcher({"https://ex.com/p2": "p2"})

    stats = run_source(adapter, fetcher, db, now=NOW)

    assert fetcher.requested == ["https://ex.com/p2", "https://ex.com/404"]
    assert (stats.pages, stats.inserted, stats.updated) == (4, 3, 0)
    assert stats.skipped == 1
    assert stats.failed_pages == 2
    assert len(stats.errors) == 2
    assert ListingRepository(db).count() == 3


def test_second_run_updates_instead_of_duplicating(db: sqlite3.Connection) -> None:
    adapter = FakeAdapter([Page("https://ex.com/p1", html="p1")], {"p1": [_raw("Barista")]})

    run_source(adapter, FakeFetcher({}), db, now=NOW)
    stats = run_source(adapter, FakeFetcher({}), db, now=NOW)

    assert (stats.inserted, stats.updated) == (0, 1)
    assert ListingRepository(db).count() == 1


@pytest.mark.parametrize("limit", [0, 1, 2])
def test_limit_caps_listings_stored(db: sqlite3.Connection, limit: int) -> None:
    adapter = FakeAdapter(
        [Page("https://ex.com/p1", html="p1"), Page("https://ex.com/p2", html="p2")],
        {"p1": [_raw("A"), _raw("B")], "p2": [_raw("C")]},
    )

    stats = run_source(adapter, FakeFetcher({}), db, limit=limit, now=NOW)

    assert stats.stored == limit
    assert ListingRepository(db).count() == limit


def test_discovery_crash_keeps_already_stored_listings(db: sqlite3.Connection) -> None:
    adapter = ExplodingDiscoveryAdapter(
        [Page("https://ex.com/p1", html="p1")], {"p1": [_raw("Barista")]}
    )

    stats = run_source(adapter, FakeFetcher({}), db, now=NOW)

    assert stats.inserted == 1
    assert stats.errors == ["discovery aborted: site redesigned"]
    assert ListingRepository(db).count() == 1
