"""FastAPI dependencies (overridable in tests via ``app.dependency_overrides``)."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.db import connect


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
