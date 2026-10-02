"""StudentJob UK: a student job board (part-time, casual, summer, placements, graduate).

Two-stage scrape:
1. City and category result pages (paginated) list job cards. Cards carry the pay and
   weekly hours, which the detail page does not show, so they travel in ``Page.context``.
2. Detail pages carry JSON-LD ``JobPosting``. It is used for employer, location, type,
   date and description, but **not** the title: the site's JSON-LD title is sometimes
   just the category ("Retail "), so the visible ``<h1>`` wins.

Cards pointing at ``/vacatures/.../redirect_to_external`` are skipped: they leave the
site and that path is disallowed by robots.txt.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models import JobType
from app.scraper.discovery import Page, iter_paginated
from app.scraper.extract.jsonld import extract_from_jsonld
from app.scraper.extract.selectors import first_match
from app.scraper.normalize.text import clean_text, html_to_text
from app.scraper.sources.base import SourceAdapter
from app.scraper.types import Fetcher, RawListing

BASE_URL = "https://www.studentjob.co.uk"
START_PATHS = (
    "/jobs/london",
    "/jobs/manchester",
    "/jobs/birmingham",
    "/jobs/leeds",
    "/jobs/edinburgh",
    "/job-type/retail-jobs",
    "/job-type/bar-staff-jobs",
    "/job-type/customer-service-jobs",
)
MAX_PAGES_PER_START = 2
INTERNAL_PREFIX = "/vacancies/"

_CARDS = ("a.job-opening__item", "a[data-job-opening-id]")
_CARD_TITLE = ("h3", "h2")
_CARD_LOCATION = (".nyc-icon-location + span",)
_CARD_PAY = (".nyc-icon-euro-circle + span", ".nyc-icon-pound-circle + span")
_CARD_HOURS = (".nyc-icon-time + span",)
_NEXT_PAGE = (
    "li.pagination__item.-active + li a.pagination__link",
    "a.pagination__link:has(.nyc-icon-arrow-right)",
    "a[rel=next]",
)
_DETAIL_TITLE = ("h1[itemprop=title]", "h1")
_DETAIL_DESCRIPTION = ("[itemprop=description]", ".job-opening__description", "main")
_DETAIL_POSTED = ("[itemprop=datePosted]", "time[datetime]")


@dataclass(frozen=True, slots=True)
class Card:
    url: str
    title: str
    location: str
    pay: str
    hours: str
    employment: str
    promoted: bool = False

    def as_context(self) -> dict[str, str]:
        return {
            "title": self.title,
            "location": self.location,
            "pay": self.pay,
            "hours": self.hours,
            "employment": self.employment,
        }


def _card_from(element: Tag, base_url: str) -> Card | None:
    href = element.get("href")
    if not isinstance(href, str) or not href.startswith(INTERNAL_PREFIX):
        return None
    title_attr = element.get("data-job-opening-title")
    employment = element.get("data-job-opening-employment")
    return Card(
        url=urljoin(base_url, href),
        title=clean_text(title_attr if isinstance(title_attr, str) else "")
        or first_match(element, _CARD_TITLE)
        or "",
        location=first_match(element, _CARD_LOCATION) or "",
        pay=first_match(element, _CARD_PAY) or "",
        hours=first_match(element, _CARD_HOURS) or "",
        employment=employment if isinstance(employment, str) else "",
        promoted=element.get("data-job-opening-topjob") == "true",
    )


def parse_cards(html: str, base_url: str) -> list[Card]:
    """Job cards on a result page that link to on-site detail pages."""
    soup = BeautifulSoup(html, "lxml")
    elements: list[Tag] = []
    for selector in _CARDS:
        elements = soup.select(selector)
        if elements:
            break
    cards = [card for element in elements if (card := _card_from(element, base_url))]
    # Promoted "top job" cards (mostly survey panels) are pinned to every result page;
    # list regular cards first so a --limit run is not filled with the same promotions.
    return sorted(cards, key=lambda card: card.promoted)


class StudentJobAdapter(SourceAdapter):
    name = "studentjob"
    label = "StudentJob UK"
    default_job_type = JobType.PART_TIME

    def discover(self, fetcher: Fetcher) -> Iterator[Page]:
        # Index pages are few and cheap; walk them all first so that regular jobs from every
        # city/category are scraped before the promoted cards pinned to each page.
        cards: dict[str, Card] = {}
        for path in START_PATHS:
            for index in iter_paginated(
                fetcher, BASE_URL + path, _NEXT_PAGE, max_pages=MAX_PAGES_PER_START
            ):
                for card in parse_cards(index.html or "", index.url):
                    cards.setdefault(card.url, card)
        for card in sorted(cards.values(), key=lambda card: card.promoted):
            yield Page(card.url, context=card.as_context())

    def parse(self, page: Page, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        structured = extract_from_jsonld(soup, page.url)
        card = page.context

        title = (
            first_match(soup, _DETAIL_TITLE)
            or card.get("title")
            or (structured.title if structured else "")
        )
        if not title:
            return []

        description = structured.description if structured else ""
        if not description:
            element = next(
                (el for sel in _DETAIL_DESCRIPTION if (el := soup.select_one(sel))), None
            )
            description = html_to_text(str(element)) if element else ""
        if card.get("hours"):
            description = f"Hours: {card['hours']}\n\n{description}".strip()

        return [
            RawListing(
                title=title,
                employer=structured.employer if structured else "",
                url=page.url,
                location=(structured.location if structured else "") or card.get("location", ""),
                pay_raw=(structured.pay_raw if structured else None) or card.get("pay") or None,
                job_type_raw=(structured.job_type_raw if structured else None)
                or card.get("employment")
                or None,
                posted_raw=(structured.posted_raw if structured else None)
                or first_match(soup, _DETAIL_POSTED, attr="datetime"),
                description=description,
            )
        ]
