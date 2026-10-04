"""SQLite connection handling and schema initialisation.

The ``listings`` table is the single source of truth: the listing view, filters,
trust score and application tracker all read from it.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id              TEXT PRIMARY KEY,          -- sha1(title|employer|location)
    title           TEXT NOT NULL,
    employer        TEXT NOT NULL,
    location        TEXT NOT NULL DEFAULT '',
    pay_raw         TEXT,                      -- pay exactly as the page shows it
    pay_hourly      REAL,                      -- normalised GBP/hour, NULL if vague
    job_type        TEXT NOT NULL CHECK (job_type IN ('part-time', 'full-time', 'internship')),
    posted_date     TEXT NOT NULL,             -- ISO date; page date, else first_seen
    description     TEXT NOT NULL DEFAULT '',
    url             TEXT NOT NULL,
    source          TEXT NOT NULL,             -- which scraper adapter produced it
    first_seen      TEXT NOT NULL,             -- ISO datetime (UTC)
    last_seen       TEXT NOT NULL,             -- ISO datetime (UTC)
    trust_score     INTEGER,                   -- 0..100
    trust_flags     TEXT NOT NULL DEFAULT '[]',-- JSON list of reasons
    eligibility_tag TEXT NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_listings_job_type    ON listings(job_type);
CREATE INDEX IF NOT EXISTS idx_listings_posted_date ON listings(posted_date);
CREATE INDEX IF NOT EXISTS idx_listings_trust_score ON listings(trust_score);
CREATE INDEX IF NOT EXISTS idx_listings_source      ON listings(source);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'saved'
                    CHECK (status IN ('saved', 'applied', 'interviewing', 'offered', 'rejected')),
    weekly_hours    REAL NOT NULL DEFAULT 0 CHECK (weekly_hours >= 0),
    applied_at      TEXT,
    last_contact_at TEXT,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE (listing_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
"""

# Each migration upgrades the schema by one version. ``SCHEMA`` above is version 1; never
# edit a released migration, append a new one instead.
MIGRATIONS: tuple[str, ...] = (
    # 2: listing lifecycle (closed listings, incremental re-fetching) and scrape run history
    """
    ALTER TABLE listings ADD COLUMN closed_at TEXT;      -- set when the job is gone
    ALTER TABLE listings ADD COLUMN last_fetched TEXT;   -- when the detail page was read
    UPDATE listings SET last_fetched = last_seen;
    CREATE INDEX IF NOT EXISTS idx_listings_url ON listings(url);
    CREATE INDEX IF NOT EXISTS idx_listings_closed_at ON listings(closed_at);

    CREATE TABLE IF NOT EXISTS scrape_runs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        source       TEXT NOT NULL,
        started_at   TEXT NOT NULL,
        finished_at  TEXT NOT NULL,
        status       TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'empty', 'failed')),
        pages        INTEGER NOT NULL DEFAULT 0,
        inserted     INTEGER NOT NULL DEFAULT 0,
        updated      INTEGER NOT NULL DEFAULT 0,
        unchanged    INTEGER NOT NULL DEFAULT 0,  -- seen again, detail page still fresh
        skipped      INTEGER NOT NULL DEFAULT 0,  -- failed validation
        failed_pages INTEGER NOT NULL DEFAULT 0,
        closed       INTEGER NOT NULL DEFAULT 0,
        errors       TEXT NOT NULL DEFAULT '[]',  -- JSON list
        quality      TEXT NOT NULL DEFAULT '{}'   -- JSON: share of listings with each field
    );
    CREATE INDEX IF NOT EXISTS idx_scrape_runs_source ON scrape_runs(source, started_at);
    """,
    # 3: each tracker belongs to one browser (anonymous id), so visitors of a public
    # deployment never see each other's applications. SQLite cannot change a UNIQUE
    # constraint in place, so the table is rebuilt.
    """
    CREATE TABLE applications_v3 (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        owner           TEXT NOT NULL DEFAULT 'default',
        listing_id      TEXT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
        status          TEXT NOT NULL DEFAULT 'saved'
                        CHECK (status IN ('saved', 'applied', 'interviewing', 'offered',
                                          'rejected')),
        weekly_hours    REAL NOT NULL DEFAULT 0 CHECK (weekly_hours >= 0),
        applied_at      TEXT,
        last_contact_at TEXT,
        notes           TEXT NOT NULL DEFAULT '',
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL,
        UNIQUE (owner, listing_id)
    );
    INSERT INTO applications_v3
        (id, listing_id, status, weekly_hours, applied_at, last_contact_at, notes,
         created_at, updated_at)
    SELECT id, listing_id, status, weekly_hours, applied_at, last_contact_at, notes,
           created_at, updated_at
    FROM applications;
    DROP TABLE applications;
    ALTER TABLE applications_v3 RENAME TO applications;
    CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
    CREATE INDEX IF NOT EXISTS idx_applications_owner ON applications(owner);
    """,
)

SCHEMA_VERSION = 1 + len(MIGRATIONS)


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open a connection with row access by name and foreign keys enforced."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(db_path) != ":memory:":
        # WAL lets the API keep reading while a scheduled scrape writes.
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the schema and apply any pending migrations (idempotent)."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        conn.executescript(SCHEMA)
        version = 1
    for target, migration in enumerate(MIGRATIONS[version - 1 :], start=version + 1):
        conn.executescript(migration)
        conn.execute(f"PRAGMA user_version = {target}")
    conn.commit()


@contextmanager
def open_db(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """Connection that is initialised on open and always closed afterwards."""
    conn = connect(db_path)
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()
