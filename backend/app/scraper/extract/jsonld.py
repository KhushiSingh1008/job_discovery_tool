"""Extract schema.org ``JobPosting`` data from ``<script type="application/ld+json">`` blocks.

Structured data is the most resilient extraction layer: it survives redesigns that would
break CSS selectors. Malformed or missing JSON-LD returns ``None`` so callers can fall
back to selectors.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup

from app.scraper.normalize.text import clean_text, html_to_text
from app.scraper.types import RawListing

logger = logging.getLogger(__name__)

_UNIT_LABELS = {
    "HOUR": "per hour",
    "DAY": "per day",
    "WEEK": "per week",
    "MONTH": "per month",
    "YEAR": "per year",
}
_CURRENCY_SYMBOLS = {"GBP": "£", "EUR": "€", "USD": "$"}


def _walk(node: Any) -> Iterator[dict[str, Any]]:
    """Yield every object in a JSON-LD document, flattening lists and ``@graph``."""
    if isinstance(node, list):
        for item in node:
            yield from _walk(item)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _walk(node["@graph"])


def _is_job_posting(obj: dict[str, Any]) -> bool:
    kind = obj.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return "JobPosting" in kinds


def find_job_postings(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """All ``JobPosting`` objects on the page; unparseable blocks are skipped."""
    postings: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        payload = tag.string or tag.get_text()
        try:
            data = json.loads(payload, strict=False)  # strict=False tolerates raw newlines
        except json.JSONDecodeError:
            logger.debug("Skipping malformed JSON-LD block")
            continue
        postings.extend(obj for obj in _walk(data) if _is_job_posting(obj))
    return postings


def _name_of(value: Any) -> str:
    if isinstance(value, dict):
        return clean_text(str(value.get("name") or ""))
    if isinstance(value, list) and value:
        return _name_of(value[0])
    return clean_text(str(value)) if value else ""


def _location_of(posting: dict[str, Any]) -> str:
    locations = posting.get("jobLocation")
    first = locations[0] if isinstance(locations, list) and locations else locations
    address = first.get("address") if isinstance(first, dict) else None
    if isinstance(address, str):
        return clean_text(address)
    if isinstance(address, dict):
        parts = (address.get(key) for key in ("addressLocality", "addressRegion", "postalCode"))
        text = ", ".join(clean_text(str(p)) for p in parts if p)
        if text:
            return text
    if str(posting.get("jobLocationType", "")).upper() == "TELECOMMUTE":
        return "Remote"
    return ""


def _format_amount(value: Any) -> str:
    number = float(value)
    return f"{number:,.0f}" if number >= 1000 else f"{number:,.2f}"


def _salary_text(posting: dict[str, Any]) -> str | None:
    """Render ``baseSalary`` back into the human form the pay normaliser understands."""
    salary = posting.get("baseSalary") or posting.get("estimatedSalary")
    if isinstance(salary, list):
        salary = salary[0] if salary else None
    if isinstance(salary, (str, int, float)):
        return clean_text(str(salary))
    if not isinstance(salary, dict):
        return None

    symbol = _CURRENCY_SYMBOLS.get(str(salary.get("currency", "GBP")).upper(), "")
    value = salary.get("value")
    unit = ""
    try:
        if isinstance(value, dict):
            unit = _UNIT_LABELS.get(str(value.get("unitText", "")).upper(), "")
            low = value.get("minValue", value.get("value"))
            high = value.get("maxValue")
            if low is None:
                return None
            amount = f"{symbol}{_format_amount(low)}"
            if high is not None and float(high) != float(low):
                amount += f" - {symbol}{_format_amount(high)}"
        elif value is not None:
            amount = f"{symbol}{_format_amount(value)}"
        else:
            return None
    except (TypeError, ValueError):
        return None
    return f"{amount} {unit}".strip()


def _employment_type_of(posting: dict[str, Any]) -> str | None:
    value = posting.get("employmentType")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or None
    return str(value) if value else None


def parse_job_posting(posting: dict[str, Any], url: str) -> RawListing | None:
    """Map one ``JobPosting`` object to a ``RawListing``; ``None`` if the title is missing."""
    title = clean_text(str(posting.get("title") or posting.get("name") or ""))
    if not title:
        return None
    return RawListing(
        title=title,
        employer=_name_of(posting.get("hiringOrganization")),
        url=str(posting.get("url") or url),
        location=_location_of(posting),
        pay_raw=_salary_text(posting),
        job_type_raw=_employment_type_of(posting),
        posted_raw=str(posting["datePosted"]) if posting.get("datePosted") else None,
        description=html_to_text(str(posting.get("description") or "")),
    )


def extract_from_jsonld(soup: BeautifulSoup, url: str) -> RawListing | None:
    """The first usable ``JobPosting`` on the page, or ``None`` to signal "use selectors"."""
    for posting in find_job_postings(soup):
        listing = parse_job_posting(posting, url)
        if listing is not None:
            return listing
    return None
