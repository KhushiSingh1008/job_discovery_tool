import re

from app.scraper.discovery import Page, iter_paginated, iter_sitemap_urls, parse_sitemap
from tests.fakes import FakeFetcher

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://ex.com/sitemap-jobs.xml</loc></sitemap>
  <sitemap><loc>https://ex.com/sitemap-missing.xml</loc></sitemap>
</sitemapindex>"""

SITEMAP_JOBS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://ex.com/jobs/barista-1</loc><lastmod>2026-09-30</lastmod></url>
  <url><loc>https://ex.com/about</loc></url>
  <url><loc> https://ex.com/jobs/rider-2 </loc></url>
</urlset>"""


def _page(n: int, next_href: str | None) -> str:
    link = f'<a rel="next" class="next" href="{next_href}">Next</a>' if next_href else ""
    return f"<html><body><h1>Page {n}</h1>{link}</body></html>"


def test_parse_sitemap_splits_pages_and_children() -> None:
    assert parse_sitemap(SITEMAP_INDEX).sitemap_urls == [
        "https://ex.com/sitemap-jobs.xml",
        "https://ex.com/sitemap-missing.xml",
    ]
    assert parse_sitemap(SITEMAP_JOBS).page_urls == [
        "https://ex.com/jobs/barista-1",
        "https://ex.com/about",
        "https://ex.com/jobs/rider-2",
    ]


def test_iter_sitemap_urls_follows_index_filters_and_survives_missing_child() -> None:
    fetcher = FakeFetcher(
        {
            "https://ex.com/sitemap.xml": SITEMAP_INDEX,
            "https://ex.com/sitemap-jobs.xml": SITEMAP_JOBS,
        }
    )

    urls = list(iter_sitemap_urls(fetcher, "https://ex.com/sitemap.xml", re.compile(r"/jobs/")))

    assert urls == ["https://ex.com/jobs/barista-1", "https://ex.com/jobs/rider-2"]


def test_iter_paginated_follows_next_links_and_stops_on_cycle() -> None:
    fetcher = FakeFetcher(
        {
            "https://ex.com/jobs": _page(1, "/jobs?page=2"),
            "https://ex.com/jobs?page=2": _page(2, "?page=3"),
            "https://ex.com/jobs?page=3": _page(3, "/jobs"),  # links back to page 1
        }
    )

    pages = list(iter_paginated(fetcher, "https://ex.com/jobs", ["a[rel=next]", "a.next"]))

    assert [p.url for p in pages] == [
        "https://ex.com/jobs",
        "https://ex.com/jobs?page=2",
        "https://ex.com/jobs?page=3",
    ]
    assert all(isinstance(p, Page) and p.html for p in pages)


def test_iter_paginated_respects_max_pages_and_stops_on_fetch_error() -> None:
    fetcher = FakeFetcher({"https://ex.com/p1": _page(1, "/p2")})  # /p2 is a 404

    assert [p.url for p in iter_paginated(fetcher, "https://ex.com/p1", ["a.next"])] == [
        "https://ex.com/p1"
    ]
    assert len(list(iter_paginated(fetcher, "https://ex.com/p1", ["a.next"], max_pages=0))) == 0
