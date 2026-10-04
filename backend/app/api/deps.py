"""FastAPI dependencies (overridable in tests via ``app.dependency_overrides``)."""

import re
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.api.rate_limit import RateLimiter, enforce
from app.config import Settings, get_settings
from app.db import connect
from app.repositories.applications import DEFAULT_OWNER


def get_db() -> Iterator[sqlite3.Connection]:
    """One connection per request; the schema is created at app startup."""
    conn = connect(get_settings().resolved_database_path())
    try:
        yield conn
    finally:
        conn.close()


def get_now() -> datetime:
    """The current time, injected so tests can freeze the clock."""
    return datetime.now(UTC)


DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def resume_rate_limit(request: Request) -> None:
    """Shared hourly budget for the resume tools (match, enhance, upload)."""
    limiter: RateLimiter = request.app.state.resume_limiter
    enforce(limiter, request)


_CLIENT_ID = re.compile(r"^[A-Za-z0-9-]{16,64}$")


def get_owner(
    x_client_id: Annotated[str | None, Header(description="Anonymous per-browser id")] = None,
) -> str:
    """Whose tracker this request reads and writes.

    The frontend sends a random id it keeps in the browser, so each visitor of a public
    deployment has a private tracker without signing up. Without the header (API docs,
    scripts) the shared default tracker is used.
    """
    if x_client_id is None:
        return DEFAULT_OWNER
    if not _CLIENT_ID.match(x_client_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid X-Client-Id header")
    return x_client_id


Owner = Annotated[str, Depends(get_owner)]
