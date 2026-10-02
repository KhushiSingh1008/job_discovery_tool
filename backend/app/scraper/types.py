"""Types shared across the scraper."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RawListing:
    """A listing as extracted from a page, before normalisation.

    Values are kept as close to the page text as possible; ``normalize`` turns them
    into typed fields (hourly pay, job type, ISO date).
    """

    title: str
    employer: str
    url: str
    location: str = ""
    pay_raw: str | None = None
    job_type_raw: str | None = None
    posted_raw: str | None = None
    description: str = ""


class Fetcher(Protocol):
    """Anything that can return the HTML/XML body of a URL (``PoliteSession`` in production)."""

    def get(self, url: str) -> str: ...
