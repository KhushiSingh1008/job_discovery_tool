from datetime import date

import pytest

from app.scraper.normalize.dates import parse_posted_date

TODAY = date(2026, 10, 2)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-09-30", date(2026, 9, 30)),
        ("2026-09-30T10:00:00+01:00", date(2026, 9, 30)),
        ("Posted today", TODAY),
        ("Just posted", TODAY),
        ("yesterday", date(2026, 10, 1)),
        ("Posted 3 days ago", date(2026, 9, 29)),
        ("a day ago", date(2026, 10, 1)),
        ("5 hours ago", TODAY),
        ("2 weeks ago", date(2026, 9, 18)),
        ("30+ days ago", date(2026, 9, 2)),
        ("12 Sep 2026", date(2026, 9, 12)),
        ("Posted on 12 September 2026", date(2026, 9, 12)),
        ("03/09/2026", date(2026, 9, 3)),  # UK day-first
        ("12 Sep", date(2026, 9, 12)),  # year inferred
    ],
)
def test_parses_posted_dates(raw: str, expected: date) -> None:
    assert parse_posted_date(raw, TODAY) == expected


def test_date_without_year_in_the_future_means_last_year() -> None:
    assert parse_posted_date("28 Dec", date(2027, 1, 5)) == date(2026, 12, 28)


@pytest.mark.parametrize(
    "raw",
    [None, "", "   ", "Posted recently", "2030-01-01", "1999-01-01", "31/02/2026"],
)
def test_unparseable_or_implausible_dates_are_none(raw: str | None) -> None:
    assert parse_posted_date(raw, TODAY) is None
