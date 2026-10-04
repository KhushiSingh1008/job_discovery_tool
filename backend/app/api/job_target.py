"""Resolve the job a resume request targets: a stored listing or pasted text."""

import sqlite3

from fastapi import HTTPException, status

from app.repositories.listings import ListingRepository
from app.schemas import ResumeJobRequest


def resolve_job(db: sqlite3.Connection, data: ResumeJobRequest) -> tuple[str, str]:
    """Return ``(title, job_text)``; 404 when the listing does not exist."""
    if data.listing_id is None:
        return "this role", data.job_description or ""
    listing = ListingRepository(db).get(data.listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing.title, f"{listing.employer}\n{listing.description}"
