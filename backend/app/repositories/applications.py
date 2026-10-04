"""Persistence for the application tracker."""

import sqlite3
from datetime import datetime
from typing import Any

from app.models import Application, ApplicationStatus

_SELECT = """
SELECT a.id, a.listing_id, a.status, a.weekly_hours, a.applied_at, a.last_contact_at,
       a.notes, a.created_at, a.updated_at,
       l.title, l.employer, l.location, l.url, l.job_type, l.pay_hourly
FROM applications a
JOIN listings l ON l.id = a.listing_id
"""

# Columns a caller may change through ``update``.
_UPDATABLE = frozenset({"status", "weekly_hours", "notes", "applied_at", "last_contact_at"})


def _to_db(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, ApplicationStatus):
        return value.value
    return value


DEFAULT_OWNER = "default"


class ApplicationRepository:
    """One owner's applications. Every query is scoped to ``owner``: another owner's rows
    are invisible here, so they can be neither read nor changed."""

    def __init__(self, conn: sqlite3.Connection, owner: str = DEFAULT_OWNER) -> None:
        self._conn = conn
        self._owner = owner

    def list(self) -> list[Application]:
        rows = self._conn.execute(
            f"{_SELECT} WHERE a.owner = ? ORDER BY a.updated_at DESC, a.id DESC", (self._owner,)
        )
        return [Application.model_validate(dict(row)) for row in rows]

    def get(self, application_id: int) -> Application | None:
        row = self._conn.execute(
            f"{_SELECT} WHERE a.id = ? AND a.owner = ?", (application_id, self._owner)
        ).fetchone()
        return Application.model_validate(dict(row)) if row else None

    def get_by_listing(self, listing_id: str) -> Application | None:
        row = self._conn.execute(
            f"{_SELECT} WHERE a.listing_id = ? AND a.owner = ?", (listing_id, self._owner)
        ).fetchone()
        return Application.model_validate(dict(row)) if row else None

    def create(
        self,
        listing_id: str,
        status: ApplicationStatus,
        weekly_hours: float,
        notes: str,
        now: datetime,
        applied_at: datetime | None = None,
    ) -> int:
        cursor = self._conn.execute(
            """INSERT INTO applications
               (owner, listing_id, status, weekly_hours, notes, applied_at, last_contact_at,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self._owner,
                listing_id,
                status.value,
                weekly_hours,
                notes,
                _to_db(applied_at),
                _to_db(applied_at),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid or 0)

    def update(self, application_id: int, changes: dict[str, Any], now: datetime) -> None:
        unknown = changes.keys() - _UPDATABLE
        if unknown:
            raise ValueError(f"Cannot update column(s): {sorted(unknown)}")
        assignments = [f"{column} = ?" for column in changes]  # names from the allow-list only
        self._conn.execute(
            f"UPDATE applications SET {', '.join([*assignments, 'updated_at = ?'])} "
            "WHERE id = ? AND owner = ?",
            [*(_to_db(v) for v in changes.values()), now.isoformat(), application_id, self._owner],
        )
        self._conn.commit()

    def delete(self, application_id: int) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM applications WHERE id = ? AND owner = ?", (application_id, self._owner)
        )
        self._conn.commit()
        return cursor.rowcount > 0
