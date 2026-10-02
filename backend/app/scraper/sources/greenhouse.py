"""Employer career boards hosted on Greenhouse (the employers' own job pages).

Board pages are server-rendered HTML tables (``tr.job-post``). We follow only UK rows to
the detail page, read the title, location and description from the HTML, pull the salary
out of the description text, and take the publish date from the page source.

Greenhouse also offers a JSON job-board API; we deliberately do not use it.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models import JobType
from app.scraper.discovery import Page
from app.scraper.extract.selectors import first_match
from app.scraper.http import FetchError
from app.scraper.normalize.pay import find_pay_in_text
from app.scraper.normalize.text import clean_text, html_to_text
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing

BOARD_URL = "https://job-boards.greenhouse.io/{slug}"
MAX_BOARD_PAGES = 3


@dataclass(frozen=True, slots=True)
class Company:
    slug: str
    name: str


COMPANIES = (
    Company("deliveroo", "Deliveroo"),
    Company("monzo", "Monzo"),
    Company("gocardless", "GoCardless"),
    Company("imc", "IMC Trading"),
)

UK_LOCATION = re.compile(
    r"united kingdom|\buk\b|england|scotland|wales|london|manchester|edinburgh|cardiff|"
    r"birmingham|bristol|leeds|glasgow|cambridge|belfast",
    re.I,
)
_PUBLISHED = re.compile(r'"(?:first_published|published_at)"\s*:\s*"([^"]+)"')

_ROWS = ("tr.job-post", ".job-post")
_ROW_TITLE = ("p.body--medium", "a")
_ROW_LOCATION = ("p.body--metadata", ".location")
_DETAIL_TITLE = (".job__title h1", "h1")
_DETAIL_LOCATION = (".job__location", ".location")
_DETAIL_DESCRIPTION = (".job__description", "#content", "main")


@dataclass(frozen=True, slots=True)
class BoardRow:
    url: str
    title: str
    location: str

    @property
    def is_uk(self) -> bool:
        return bool(UK_LOCATION.search(self.location))


def parse_board(html: str, base_url: str) -> list[BoardRow]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select(".tag-container"):  # "New" badges inside the title
        tag.decompose()
    rows: list[Tag] = next((found for sel in _ROWS if (found := soup.select(sel))), [])
    board: list[BoardRow] = []
    for row in rows:
        href = first_match(row, ("a[href]",), attr="href")
        title = first_match(row, _ROW_TITLE)
        if href and title:
            location = first_match(row, _ROW_LOCATION) or ""
            board.append(BoardRow(urljoin(base_url, href), title, location))
    return board


class GreenhouseAdapter(SourceAdapter):
    name = "greenhouse"
    label = "Employer career boards (Greenhouse)"
    default_job_type = JobType.FULL_TIME

    def __init__(self, companies: tuple[Company, ...] = COMPANIES) -> None:
        self.companies = companies

    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        for company in self.companies:
            yield from self._discover_company(fetcher, company)

    def _discover_company(self, fetcher: Fetcher, company: Company) -> Iterator[Page]:
        base = BOARD_URL.format(slug=company.slug)
        seen: set[str] = set()
        for page_number in range(1, MAX_BOARD_PAGES + 1):
            url = base if page_number == 1 else f"{base}?page={page_number}"
            try:
                rows = parse_board(fetcher.get(url), url)
            except FetchError:
                return
            new_rows = [row for row in rows if row.url not in seen]
            if not new_rows:  # past the last page (or the page parameter was ignored)
                return
            for row in new_rows:
                seen.add(row.url)
                if row.is_uk:
                    context = {"employer": company.name, "title": row.title}
                    yield Page(row.url, context=context | {"location": row.location})

    def parse(self, page: Page, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        title = first_match(soup, _DETAIL_TITLE) or page.context.get("title", "")
        if not title:
            return []

        element = next((el for sel in _DETAIL_DESCRIPTION if (el := soup.select_one(sel))), None)
        description = html_to_text(str(element)) if element else ""
        published = _PUBLISHED.search(html)

        return [
            RawListing(
                title=title,
                employer=page.context.get("employer", ""),
                url=page.url,
                location=clean_text(first_match(soup, _DETAIL_LOCATION))
                or page.context.get("location", ""),
                pay_raw=find_pay_in_text(description),
                posted_raw=published.group(1) if published else None,
                description=description,
            )
        ]
