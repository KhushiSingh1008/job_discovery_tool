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


def test_version_1_database_is_migrated_in_place() -> None:
    from app.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA user_version = 1")
    _insert_listing(conn)

    init_db(conn)

    row = conn.execute("SELECT closed_at, last_fetched FROM listings WHERE id = 'abc'").fetchone()
    assert row["closed_at"] is None
    assert row["last_fetched"] == NOW  # backfilled from last_seen
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "scrape_runs" in tables
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_version_2_trackers_move_to_the_default_owner() -> None:
    from app.db import MIGRATIONS, SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.executescript(MIGRATIONS[0])
    conn.execute("PRAGMA user_version = 2")
    _insert_listing(conn)
    conn.execute(
        "INSERT INTO applications (listing_id, weekly_hours, created_at, updated_at) "
        "VALUES ('abc', 12, ?, ?)",
        (NOW, NOW),
    )

    init_db(conn)

    row = conn.execute("SELECT owner, weekly_hours FROM applications").fetchone()
    assert (row["owner"], row["weekly_hours"]) == ("default", 12)
    conn.execute(  # a second browser may now track the same listing
        "INSERT INTO applications (owner, listing_id, created_at, updated_at) "
        "VALUES ('someone-else', 'abc', ?, ?)",
        (NOW, NOW),
    )
