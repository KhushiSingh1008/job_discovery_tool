"""Command line entry point.

python -m app.scraper.cli sources
python -m app.scraper.cli run [--source NAME ...] [--limit N] [-v]
python -m app.scraper.cli status
python -m app.scraper.cli rescore
"""

import argparse
import logging
import sqlite3
import sys
from collections.abc import Sequence

from app.config import Settings, get_settings
from app.db import open_db
from app.repositories.listings import ListingRepository
from app.repositories.scrape_runs import ScrapeRunRepository
from app.scraper.jobs import rescore, run_scrape_job
from app.scraper.pipeline import SourceRunStats
from app.scraper.sources import ALL_SOURCES, get_adapters
from app.scraper.sources.base import SourceAdapter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.scraper.cli", description="GradGuide job scraper")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("sources", help="list available sources")

    run = commands.add_parser("run", help="scrape sources into the database, then rescore")
    run.add_argument("--source", action="append", dest="sources", help="source name (repeatable)")
    run.add_argument("--limit", type=int, default=None, help="max listings stored per source")

    commands.add_parser("status", help="show the last run and open listings of every source")
    commands.add_parser("rescore", help="recompute trust scores and eligibility tags")
    return parser


def _print_summary(results: list[SourceRunStats]) -> None:
    header = (
        f"{'source':<14}{'status':>9}{'pages':>7}{'new':>6}{'updated':>9}{'unchanged':>11}"
        f"{'closed':>8}{'skipped':>9}{'failed':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.source:<14}{r.status.value:>9}{r.pages:>7}{r.inserted:>6}{r.updated:>9}"
            f"{r.unchanged:>11}{r.closed:>8}{r.skipped:>9}{r.failed_pages:>8}"
        )
        if r.quality:
            fields = ", ".join(f"{name} {share:.0%}" for name, share in r.quality.items())
            print(f"    fields present: {fields}")
        for error in r.errors:
            print(f"    ! {error}")
        for gap in r.gaps:
            print(f"    ~ {gap}")


def _print_status(conn: sqlite3.Connection) -> None:
    open_counts = ListingRepository(conn).open_counts_by_source()
    latest = ScrapeRunRepository(conn).latest_by_source()
    for source in ALL_SOURCES:
        run = latest.get(source.name)
        last = (
            f"{run.status.value} at {run.finished_at:%Y-%m-%d %H:%M} UTC "
            f"(+{run.inserted} new, {run.closed} closed)"
            if run
            else "never run"
        )
        print(f"{source.name:<14}{open_counts.get(source.name, 0):>5} open   last run: {last}")


def _run(
    conn: sqlite3.Connection,
    settings: Settings,
    adapters: list[SourceAdapter],
    limit: int | None,
) -> int:
    result = run_scrape_job(conn, settings, adapters, limit=limit)
    _print_summary(result.sources)
    if result.stale_closed:
        print(
            f"Closed {result.stale_closed} listings not seen for "
            f"{settings.listing_stale_days} days."
        )
    print(f"Rescored {result.rescored} listings.")
    # Non-zero exit when a source produced nothing, so a scheduler can alert on it.
    return 0 if result.healthy else 1


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

    adapters: list[SourceAdapter] = []
    if args.command == "run":  # validate before touching the database
        try:
            adapters = get_adapters(args.sources)
        except KeyError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2

    with open_db(settings.resolved_database_path()) as conn:
        if args.command == "status":
            _print_status(conn)
            return 0
        if args.command == "rescore":
            print(f"Rescored {rescore(conn, settings)} listings.")
            return 0
        return _run(conn, settings, adapters, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
