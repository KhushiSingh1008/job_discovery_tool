import sqlite3

import pytest

from app.db import SCHEMA_VERSION, init_db

NOW = "2026-10-02T09:00:00+00:00"


def _insert_listing(db: sqlite3.Connection, job_type: str = "part-time") -> None:
    db.execute(
        """INSERT INTO listings
           (id, title, employer, job_type, posted_date, url, source, first_seen, last_seen)
           VALUES ('abc', 'Barista', 'Cafe Ltd', ?, '2026-10-01',
                   'https://x.test/1', 'test', ?, ?)""",
        (job_type, NOW, NOW),
    )


def test_schema_creates_tables(db: sqlite3.Connection) -> None:
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"listings", "applications"} <= tables


def test_init_db_is_idempotent(db: sqlite3.Connection) -> None:
    init_db(db)
    init_db(db)
    assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_listing_defaults(db: sqlite3.Connection) -> None:
    _insert_listing(db)
    row = db.execute("SELECT * FROM listings WHERE id = 'abc'").fetchone()
    assert row["trust_flags"] == "[]"
    assert row["eligibility_tag"] == "unknown"
    assert row["location"] == ""


def test_job_type_is_constrained(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert_listing(db, job_type="gig")


def test_application_requires_existing_listing(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO applications (listing_id, created_at, updated_at) VALUES ('nope', ?, ?)",
            (NOW, NOW),
        )


def test_deleting_listing_cascades_to_application(db: sqlite3.Connection) -> None:
    _insert_listing(db)
    db.execute(
        "INSERT INTO applications (listing_id, created_at, updated_at) VALUES ('abc', ?, ?)",
        (NOW, NOW),
    )
    db.execute("DELETE FROM listings WHERE id = 'abc'")
    assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0
