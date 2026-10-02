"""The contract every site adapter implements."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from app.models import JobType
from app.scraper.discovery import Page
from app.scraper.types import Fetcher, RawListing


class SourceAdapter(ABC):
    """One adapter per site: it knows where the listings are and how to read them.

    Adapters hold no network or storage logic beyond calling the injected ``Fetcher``,
    so ``parse`` can be unit-tested against saved HTML fixtures.
    """

    #: Stable identifier stored in ``listings.source`` and used on the CLI.
    name: ClassVar[str]
    #: Human-readable label for the UI.
    label: ClassVar[str]
    #: Used when a page carries no job-type signal (e.g. a chain that only hires part-time).
    default_job_type: ClassVar[JobType] = JobType.FULL_TIME
    #: Used when the page does not name the employer (e.g. a company's own career site).
    default_employer: ClassVar[str | None] = None

    @abstractmethod
    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        """Yield the pages that contain listings (detail pages or index pages)."""

    @abstractmethod
    def parse(self, page: Page, html: str) -> list[RawListing]:
        """Extract every listing found on one page. Must not perform network calls."""
