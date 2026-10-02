"""Persistence for job listings."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from app.models import EligibilityTag, JobType, Listing, ListingIn, TrustFlag
from app.schemas import FacetCount, FilterFacets, ListingSummary, SortOrder
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


@dataclass(slots=True)
class ListingSearch:
    """Search criteria; empty/None fields do not filter."""

    q: str | None = None
    job_types: list[JobType] = field(default_factory=list)
    location: str | None = None
    min_pay: float | None = None
    min_trust: int | None = None
    eligibility: list[EligibilityTag] = field(default_factory=list)
    posted_since: date | None = None
    source: str | None = None
    sort: SortOrder = SortOrder.NEWEST
    page: int = 1
    page_size: int = 20


_SUMMARY_COLUMNS = (
    "id, title, employer, location, pay_raw, pay_hourly, job_type, posted_date, url, "
    "source, trust_score, eligibility_tag"
)
_ORDER_BY = {
    SortOrder.NEWEST: "posted_date DESC, trust_score DESC, id",
    # NULL pay/trust sort last regardless of direction.
    SortOrder.PAY: "pay_hourly IS NULL, pay_hourly DESC, posted_date DESC, id",
    SortOrder.TRUST: "trust_score IS NULL, trust_score DESC, posted_date DESC, id",
}


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where_clause(search: ListingSearch) -> tuple[str, list[object]]:
    """Build a parameterised WHERE clause; user input never enters the SQL text."""
    conditions: list[str] = []
    params: list[object] = []

    # Every word must appear somewhere (title, employer, location or description).
    for term in (search.q or "").split():
        conditions.append(
            "(title LIKE ? ESCAPE '\\' OR employer LIKE ? ESCAPE '\\' "
            "OR location LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
        )
        params.extend([_like_pattern(term)] * 4)
    if search.job_types:
        conditions.append(f"job_type IN ({', '.join('?' * len(search.job_types))})")
        params.extend(job_type.value for job_type in search.job_types)
    if search.eligibility:
        conditions.append(f"eligibility_tag IN ({', '.join('?' * len(search.eligibility))})")
        params.extend(tag.value for tag in search.eligibility)
    if search.location:
        conditions.append("location LIKE ? ESCAPE '\\'")
        params.append(_like_pattern(search.location.strip()))
    if search.min_pay is not None:
        conditions.append("pay_hourly >= ?")
        params.append(search.min_pay)
    if search.min_trust is not None:
        conditions.append("trust_score >= ?")
        params.append(search.min_trust)
    if search.posted_since is not None:
        conditions.append("posted_date >= ?")
        params.append(search.posted_since.isoformat())
    if search.source:
        conditions.append("source = ?")
        params.append(search.source)

    return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), params


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

    def search(self, search: ListingSearch) -> tuple[list[ListingSummary], int]:
        """One page of matching listings plus the total number of matches."""
        where, params = _where_clause(search)
        total = int(
            self._conn.execute(f"SELECT COUNT(*) FROM listings {where}", params).fetchone()[0]
        )
        rows = self._conn.execute(
            f"SELECT {_SUMMARY_COLUMNS} FROM listings {where} "
            f"ORDER BY {_ORDER_BY[search.sort]} LIMIT ? OFFSET ?",
            [*params, search.page_size, (search.page - 1) * search.page_size],
        ).fetchall()
        return [ListingSummary.model_validate(dict(row)) for row in rows], total

    def facets(self, top_locations: int = 15) -> FilterFacets:
        """Values (with counts) the UI can offer as filters."""

        def counts(column: str, limit: int | None = None) -> list[FacetCount]:
            sql = (
                f"SELECT {column} AS value, COUNT(*) AS count FROM listings "
                f"WHERE {column} != '' GROUP BY {column} ORDER BY count DESC, value"
            )
            if limit is not None:
                sql += f" LIMIT {int(limit)}"
            return [FacetCount(value=r["value"], count=r["count"]) for r in self._conn.execute(sql)]

        max_pay = self._conn.execute("SELECT MAX(pay_hourly) FROM listings").fetchone()[0]
        return FilterFacets(
            job_types=counts("job_type"),
            sources=counts("source"),
            locations=counts("location", top_locations),
            eligibility=counts("eligibility_tag"),
            max_pay_hourly=max_pay,
        )

    def iter_all(self) -> Iterator[Listing]:
        for row in self._conn.execute("SELECT * FROM listings ORDER BY id"):
            yield row_to_listing(row)

    def update_enrichment(
        self,
        listing_id: str,
        trust_score: int,
        trust_flags: list[TrustFlag],
        eligibility_tag: EligibilityTag,
    ) -> None:
        self._conn.execute(
            """UPDATE listings
               SET trust_score = ?, trust_flags = ?, eligibility_tag = ?
               WHERE id = ?""",
            (
                trust_score,
                json.dumps([flag.model_dump() for flag in trust_flags]),
                eligibility_tag.value,
                listing_id,
            ),
        )


def row_to_listing(row: sqlite3.Row) -> Listing:
    data = dict(row)
    data["trust_flags"] = json.loads(data["trust_flags"] or "[]")
    return Listing.model_validate(data)
