"""FastAPI dependencies."""

import sqlite3
from collections.abc import Iterator

from app.config import get_settings
from app.db import connect


def get_db() -> Iterator[sqlite3.Connection]:
    """One connection per request; the schema is created at app startup."""
    conn = connect(get_settings().resolved_database_path())
    try:
        yield conn
    finally:
        conn.close()
