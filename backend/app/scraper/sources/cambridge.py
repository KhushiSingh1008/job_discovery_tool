"""University of Cambridge job search (campus job board).

The search page is a server-rendered Drupal table with every field we need in one row,
and no JSON-LD, so this adapter is pure CSS-selector parsing of raw HTML. Each field has
two candidate selectors: the semantic Drupal class, then the column position.
"""

from collections.abc import Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models import JobType
from app.scraper.discovery import Page, iter_paginated
from app.scraper.extract.selectors import first_match
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing

SEARCH_URL = "https://www.cam.ac.uk/jobs/search"
MAX_PAGES = 20
LOCATION = "Cambridge"

_ROWS = ("table.views-table tbody tr", "table tbody tr")
_TITLE = ("td.views-field-title a", "td:nth-of-type(1) a")
_DEPARTMENT = ("td.views-field-field-department-location", "td:nth-of-type(2)")
_SALARY = ("td.views-field-field-salary", "td:nth-of-type(3)")
_CATEGORY = ("td.views-field-field-category", "td:nth-of-type(4)")
_POSTED_ATTR = ("td.views-field-created time", "td:nth-of-type(5) time")
_POSTED_TEXT = ("td.views-field-created", "td:nth-of-type(5)")
_CLOSES = ("td.views-field-field-closing-date", "td:nth-of-type(6)")
_REFERENCE = ("td.views-field-field-reference", "td:nth-of-type(7)")
_NEXT_PAGE = ("li.pager__item--next a", "a[rel=next]")

# PhD studentships are funded study places, not jobs.
_SKIPPED_CATEGORIES = frozenset({"studentships"})


def _rows(soup: BeautifulSoup) -> list[Tag]:
    for selector in _ROWS:
        rows = soup.select(selector)
        if rows:
            return rows
    return []


class CambridgeAdapter(SourceAdapter):
    name = "cambridge"
    label = "University of Cambridge jobs"
    default_job_type = JobType.FULL_TIME
    default_employer = "University of Cambridge"
    exhaustive = True  # the search lists every open vacancy across its pages

    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        yield from iter_paginated(
            fetcher, SEARCH_URL, _NEXT_PAGE, max_pages=MAX_PAGES, report=self.report
        )

    def parse(self, page: Page, html: str) -> list[RawListing]:
        listings: list[RawListing] = []
        for row in _rows(BeautifulSoup(html, "lxml")):
            listing = self._parse_row(row, page.url)
            if listing is not None:
                listings.append(listing)
        return listings

    def _parse_row(self, row: Tag, base_url: str) -> RawListing | None:
        title = first_match(row, _TITLE)
        href = first_match(row, _TITLE, attr="href")
        if not title or not href:
            return None

        category = first_match(row, _CATEGORY) or ""
        if category.casefold() in _SKIPPED_CATEGORIES:
            return None

        department = first_match(row, _DEPARTMENT)
        closes = first_match(row, _CLOSES)
        reference = first_match(row, _REFERENCE)
        details = [
            f"Department: {department}" if department else "",
            f"Category: {category}" if category else "",
            f"Closing date: {closes}" if closes else "",
            f"Reference: {reference}" if reference else "",
        ]
        return RawListing(
            title=title,
            employer=self.default_employer or "",
            url=urljoin(base_url, href),
            location=LOCATION,
            pay_raw=first_match(row, _SALARY),
            posted_raw=first_match(row, _POSTED_ATTR, attr="datetime")
            or first_match(row, _POSTED_TEXT),
            description="\n".join(line for line in details if line),
        )
