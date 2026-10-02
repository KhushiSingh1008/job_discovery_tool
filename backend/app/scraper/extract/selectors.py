"""CSS-selector helpers for sites without (usable) structured data.

Each field is given 2-3 candidate selectors and the first non-empty match wins, so a small
layout change on the site degrades one selector rather than breaking the field.
"""

from collections.abc import Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.scraper.normalize.text import clean_text


def first_match(
    root: BeautifulSoup | Tag, selectors: Sequence[str], attr: str | None = None
) -> str | None:
    """Return cleaned text (or ``attr`` value) of the first selector that matches non-empty."""
    for selector in selectors:
        element = root.select_one(selector)
        if element is None:
            continue
        value = element.get(attr) if attr else element.get_text(" ", strip=True)
        if isinstance(value, list):  # multi-valued attributes such as class
            value = " ".join(value)
        text = clean_text(value)
        if text:
            return text
    return None


def absolute_links(root: BeautifulSoup | Tag, selector: str, base_url: str) -> list[str]:
    """Absolute, de-duplicated ``href`` targets of every element matching ``selector``."""
    seen: dict[str, None] = {}
    for element in root.select(selector):
        href = element.get("href")
        if isinstance(href, str) and href.strip() and not href.startswith(("#", "javascript:")):
            seen.setdefault(urljoin(base_url, href.strip()), None)
    return list(seen)
