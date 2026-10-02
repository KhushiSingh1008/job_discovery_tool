"""Parse posted dates: ISO strings, UK-style dates and relative phrases ("3 days ago")."""

import re
from datetime import date, datetime, timedelta

from dateutil import parser as date_parser

_RELATIVE = re.compile(
    r"\b(?P<n>\d+|an?|one)\+?\s*(?P<unit>minute|min|hour|hr|day|week|month)s?\s+ago", re.I
)
_UNIT_DAYS = {"minute": 0, "min": 0, "hour": 0, "hr": 0, "day": 1, "week": 7, "month": 30}
_ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
_EARLIEST_PLAUSIBLE = date(2000, 1, 1)


def _parse_relative(text: str, today: date) -> date | None:
    lowered = text.lower()
    if re.search(r"\b(today|just posted|just now)\b", lowered):
        return today
    if "yesterday" in lowered:
        return today - timedelta(days=1)
    match = _RELATIVE.search(lowered)
    if not match:
        return None
    n = 1 if match["n"] in {"a", "an", "one"} else int(match["n"])
    return today - timedelta(days=n * _UNIT_DAYS[match["unit"]])


def _parse_absolute(text: str, today: date) -> date | None:
    if _ISO_PREFIX.match(text):
        return date.fromisoformat(text[:10])
    if not any(ch.isdigit() for ch in text):
        return None  # fuzzy parsing of "Posted recently" would invent a date
    try:
        # UK sites write 03/10/2026 for 3 October, hence dayfirst.
        parsed = date_parser.parse(
            text, dayfirst=True, fuzzy=True, default=datetime(today.year, 1, 1)
        ).date()
    except (ValueError, OverflowError):
        return None
    # "28 Dec" seen in early January refers to last year.
    if parsed > today + timedelta(days=1) and str(parsed.year) not in text:
        parsed = parsed.replace(year=parsed.year - 1)
    return parsed


def parse_posted_date(raw: str | None, today: date) -> date | None:
    """Return the posting date, or ``None`` if it cannot be determined reliably."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    try:
        parsed = _parse_relative(text, today) or _parse_absolute(text, today)
    except ValueError:
        return None
    if parsed is None or not _EARLIEST_PLAUSIBLE <= parsed <= today + timedelta(days=1):
        return None
    return parsed
