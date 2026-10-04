"""Keeps listings fresh by scraping on a timer inside the web process.

Render cron jobs run as separate services and cannot reach the web service's disk, where
the SQLite database lives, so the schedule runs here instead. Whether a scrape is due is
read from the run history in the database, so restarts and deploys never trigger extra
scrapes. Only one scrape runs at a time (see ``app.scraper.jobs``).
"""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.db import open_db
from app.repositories.scrape_runs import ScrapeRunRepository
from app.scraper.jobs import ScrapeAlreadyRunningError, run_scrape_job
from app.scraper.sources import get_adapters

logger = logging.getLogger(__name__)

CHECK_EVERY = timedelta(minutes=15)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ScrapeScheduler:
    def __init__(
        self,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = _utc_now,
        check_every: timedelta = CHECK_EVERY,
    ) -> None:
        self._settings = settings
        self._interval = timedelta(hours=settings.scrape_interval_hours)
        self._first_delay = timedelta(seconds=settings.scrape_start_delay_seconds)
        self._clock = clock
        self._check_every = check_every
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="scrape-scheduler", daemon=True)
        self._thread.start()
        logger.info("Scrape scheduler started: every %s", self._interval)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def is_due(self) -> bool:
        with open_db(self._settings.resolved_database_path()) as conn:
            runs = ScrapeRunRepository(conn).latest_by_source().values()
        last = max((run.finished_at for run in runs), default=None)
        return last is None or self._clock() - last >= self._interval

    def run_if_due(self) -> bool:
        """Scrape every source if the last scrape is older than the interval."""
        if not self.is_due():
            return False
        try:
            with open_db(self._settings.resolved_database_path()) as conn:
                run_scrape_job(conn, self._settings, get_adapters(None))
        except ScrapeAlreadyRunningError:
            logger.info("Skipping scheduled scrape: one is already running")
            return False
        except Exception:  # the scheduler must survive any scrape failure
            logger.exception("Scheduled scrape failed")
        return True

    def _loop(self) -> None:
        if self._stop.wait(self._first_delay.total_seconds()):
            return  # give the web server time to start answering first
        while True:
            self.run_if_due()
            if self._stop.wait(self._check_every.total_seconds()):
                return
