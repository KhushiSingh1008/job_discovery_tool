"""Find the pages that hold listings: sitemaps where a site has one, else pagination."""

import logging
import re
from collections import deque
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scraper.extract.selectors import first_match
from app.scraper.http import FetchError
from app.scraper.types import Fetcher

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Page:
    """A page to parse.

    ``html`` is set when discovery already downloaded it. ``context`` carries facts seen on
    an index page that the detail page lacks (e.g. pay shown only on a search-result card).
    """

    url: str
    html: str | None = None
    context: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class CrawlReport:
    """What discovery could not reach.

    ``gaps`` are failures (a page that would not load); ``truncated`` records deliberate
    limits (a page cap on a source we only sample). Either way the crawl is incomplete and
    must never be used to conclude that the listings it did not see have closed.
    """

    gaps: list[str] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.gaps and not self.truncated

    def gap(self, reason: str) -> None:
        logger.warning("Incomplete crawl: %s", reason)
        self.gaps.append(reason)

    def truncate(self, reason: str) -> None:
        logger.info("Crawl limit: %s", reason)
        self.truncated.append(reason)


@dataclass(slots=True)
class SitemapContents:
    page_urls: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)


def parse_sitemap(xml: str) -> SitemapContents:
    """Split a sitemap (or sitemap index) into page URLs and child sitemap URLs."""
    soup = BeautifulSoup(xml, "xml")
    contents = SitemapContents()
    for loc in soup.select("sitemap > loc"):
        contents.sitemap_urls.append(loc.get_text(strip=True))
    for loc in soup.select("url > loc"):
        contents.page_urls.append(loc.get_text(strip=True))
    return contents


def iter_sitemap_urls(
    fetcher: Fetcher,
    sitemap_url: str,
    include: re.Pattern[str] | None = None,
    max_sitemaps: int = 25,
) -> Iterator[str]:
    """Breadth-first walk of a sitemap index, yielding page URLs that match ``include``."""
    queue: deque[str] = deque([sitemap_url])
    visited: set[str] = set()
    while queue and len(visited) < max_sitemaps:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        try:
            contents = parse_sitemap(fetcher.get(url))
        except FetchError as exc:
            logger.warning("Skipping sitemap %s: %s", url, exc)
            continue
        queue.extend(contents.sitemap_urls)
        for page_url in contents.page_urls:
            if include is None or include.search(page_url):
                yield page_url


def iter_paginated(
    fetcher: Fetcher,
    start_url: str,
    next_selectors: Sequence[str],
    max_pages: int = 10,
    report: CrawlReport | None = None,
) -> Iterator[Page]:
    """Follow "next page" links from ``start_url``, yielding each page with its HTML.

    Stopping early (a fetch error, or ``max_pages`` reached with more pages left) is
    recorded in ``report`` so callers know the crawl was not complete.
    """
    report = report if report is not None else CrawlReport()
    url: str | None = start_url
    seen: set[str] = set()
    while url and url not in seen:
        if len(seen) >= max_pages:
            report.truncate(f"stopped after {max_pages} pages of {start_url}")
            return
        seen.add(url)
        try:
            html = fetcher.get(url)
        except FetchError as exc:
            report.gap(f"pagination stopped at {url}: {exc}")
            return
        yield Page(url, html)
        href = first_match(BeautifulSoup(html, "lxml"), next_selectors, attr="href")
        url = urljoin(url, href) if href else None
