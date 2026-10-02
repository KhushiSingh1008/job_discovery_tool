"""Apply trust scoring and eligibility tagging to stored listings.

Runs over stored rows (not inside the scrape loop) because the ghost-job and
"no longer listed" signals depend on ``first_seen``/``last_seen`` history, and because
scores must age even on days nothing new is scraped (``cli rescore``).
"""

import sqlite3
from datetime import date

from app.enrichment.eligibility import tag_eligibility
from app.enrichment.trust import score_listing
from app.repositories.listings import ListingRepository
from app.rules import WageRules


def enrich_all(
    conn: sqlite3.Connection, today: date, wages: WageRules, ghost_days: int = 45
) -> int:
    """Rescore every listing; returns how many were updated."""
    repo = ListingRepository(conn)
    listings = list(repo.iter_all())  # materialise before writing to the same table
    for listing in listings:
        trust = score_listing(listing, today, wages, ghost_days)
        tag = tag_eligibility(listing.title, listing.description)
        repo.update_enrichment(listing.id, trust.score, trust.flags, tag)
    conn.commit()
    return len(listings)
