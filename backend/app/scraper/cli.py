"""Command line entry point.

python -m app.scraper.cli sources
python -m app.scraper.cli run [--source NAME ...] [--limit N] [-v]
python -m app.scraper.cli rescore
"""

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from app.config import Settings, get_settings
from app.db import open_db
from app.enrichment.service import enrich_all
from app.rules import load_wage_rules
from app.scraper.http import PoliteSession
from app.scraper.pipeline import SourceRunStats, run_all
from app.scraper.sources import ALL_SOURCES, get_adapters


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.scraper.cli", description="GradGuide job scraper")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("sources", help="list available sources")

    run = commands.add_parser("run", help="scrape sources into the database, then rescore")
    run.add_argument("--source", action="append", dest="sources", help="source name (repeatable)")
    run.add_argument("--limit", type=int, default=None, help="max listings stored per source")

    commands.add_parser("rescore", help="recompute trust scores and eligibility tags")
    return parser


def _print_summary(results: list[SourceRunStats]) -> None:
    header = f"{'source':<22}{'pages':>7}{'new':>7}{'updated':>9}{'skipped':>9}{'failed':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.source:<22}{r.pages:>7}{r.inserted:>7}{r.updated:>9}"
            f"{r.skipped:>9}{r.failed_pages:>8}"
        )
        for error in r.errors:
            print(f"    ! {error}")


def _rescore(conn: sqlite3.Connection, settings: Settings) -> None:
    count = enrich_all(
        conn, datetime.now(UTC).date(), load_wage_rules(), ghost_days=settings.ghost_job_days
    )
    print(f"Rescored {count} listings.")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    settings = get_settings()

    if args.command == "sources":
        for source in ALL_SOURCES:
            print(f"{source.name:<22}{source.label}")
        return 0

    if args.command == "rescore":
        with open_db(settings.resolved_database_path()) as conn:
            _rescore(conn, settings)
        return 0

    try:
        adapters = get_adapters(args.sources)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2
    if not adapters:
        print("No sources registered.", file=sys.stderr)
        return 2

    with (
        open_db(settings.resolved_database_path()) as conn,
        PoliteSession.from_settings(settings) as session,
    ):
        results = run_all(adapters, session, conn, limit=args.limit)
        _print_summary(results)
        _rescore(conn, settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
