"""Scrape run history: what each run of each source did, for monitoring and the UI."""

import json
import sqlite3

from app.schemas import ScrapeRun

_COLUMNS = (
    "source, started_at, finished_at, status, pages, inserted, updated, unchanged, skipped, "
    "failed_pages, closed, errors, quality"
)


def _row_to_run(row: sqlite3.Row) -> ScrapeRun:
    data = dict(row)
    data["errors"] = json.loads(data["errors"])
    data["quality"] = json.loads(data["quality"])
    return ScrapeRun.model_validate(data)


class ScrapeRunRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, run: ScrapeRun) -> None:
        self._conn.execute(
            f"INSERT INTO scrape_runs ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.source,
                run.started_at.isoformat(),
                run.finished_at.isoformat(),
                run.status.value,
                run.pages,
                run.inserted,
                run.updated,
                run.unchanged,
                run.skipped,
                run.failed_pages,
                run.closed,
                json.dumps(run.errors),
                json.dumps(run.quality),
            ),
        )

    def latest_by_source(self) -> dict[str, ScrapeRun]:
        """The most recent run of every source that has ever run."""
        rows = self._conn.execute(
            f"""SELECT {_COLUMNS} FROM scrape_runs AS r
                WHERE started_at = (
                    SELECT MAX(started_at) FROM scrape_runs WHERE source = r.source
                )"""
        )
        return {row["source"]: _row_to_run(row) for row in rows}

    def history(self, source: str, limit: int = 10) -> list[ScrapeRun]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM scrape_runs WHERE source = ? ORDER BY started_at DESC LIMIT ?",
            (source, limit),
        )
        return [_row_to_run(row) for row in rows]
