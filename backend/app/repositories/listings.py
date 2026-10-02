"""Persistence for job listings."""

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import StrEnum

from app.models import Listing, ListingIn
from app.scraper.normalize.text import clean_text


def make_listing_id(title: str, employer: str, location: str) -> str:
    """Stable id so the same job seen on every re-scrape maps to one row.

    The URL is deliberately excluded: sites often add tracking parameters or move postings.
    """
    key = "|".join(clean_text(part).casefold() for part in (title, employer, location))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


class UpsertOutcome(StrEnum):
    INSERTED = "inserted"
    UPDATED = "updated"


_UPSERT_SQL = """
INSERT INTO listings (
    id, title, employer, location, pay_raw, pay_hourly, job_type, posted_date,
    description, url, source, first_seen, last_seen
) VALUES (
    :id, :title, :employer, :location, :pay_raw, :pay_hourly, :job_type,
    COALESCE(:page_posted_date, :today), :description, :url, :source, :now, :now
)
ON CONFLICT(id) DO UPDATE SET
    pay_raw     = excluded.pay_raw,
    pay_hourly  = excluded.pay_hourly,
    job_type    = excluded.job_type,
    posted_date = COALESCE(:page_posted_date, listings.posted_date),
    description = excluded.description,
    url         = excluded.url,
    source      = excluded.source,
    last_seen   = excluded.last_seen
"""


class ListingRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, listing: ListingIn, now: datetime) -> UpsertOutcome:
        """Insert a new listing, or refresh an existing one keeping its ``first_seen``.

        Re-scrapes never wipe the table: ``last_seen`` moving forward is what lets us
        detect ghost jobs (live for weeks) and stale ones (no longer on the site).
        """
        listing_id = make_listing_id(listing.title, listing.employer, listing.location)
        existed = (
            self._conn.execute("SELECT 1 FROM listings WHERE id = ?", (listing_id,)).fetchone()
            is not None
        )
        self._conn.execute(
            _UPSERT_SQL,
            {
                "id": listing_id,
                "title": listing.title,
                "employer": listing.employer,
                "location": listing.location,
                "pay_raw": listing.pay_raw,
                "pay_hourly": listing.pay_hourly,
                "job_type": listing.job_type.value,
                "page_posted_date": (
                    listing.posted_date.isoformat() if listing.posted_date else None
                ),
                "today": now.date().isoformat(),
                "description": listing.description,
                "url": str(listing.url),
                "source": listing.source,
                "now": now.isoformat(),
            },
        )
        return UpsertOutcome.UPDATED if existed else UpsertOutcome.INSERTED

    def get(self, listing_id: str) -> Listing | None:
        row = self._conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return row_to_listing(row) if row else None

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0])


def row_to_listing(row: sqlite3.Row) -> Listing:
    data = dict(row)
    data["trust_flags"] = json.loads(data["trust_flags"] or "[]")
    return Listing.model_validate(data)
