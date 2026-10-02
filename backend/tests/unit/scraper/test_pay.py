import pytest

from app.scraper.normalize.pay import to_hourly


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # hourly
        ("£11.44 per hour", 11.44),
        ("£11.44/hr", 11.44),
        ("£11.44 - £12 ph", 11.44),
        ("£12.21 - £13.00 per hour", 12.21),
        ("Up to £12.50 an hour", 12.5),
        ("12.00 GBP hourly", 12.0),
        ("£12 per hour, 20 hours per week", 12.0),
        # annual (52 weeks x 37.5 hours)
        ("£22,000 - £25,000 per annum", 11.28),
        (f"£22,000 {chr(0x2013)} £25,000 per annum", 11.28),  # en dash range
        ("£24,000 per year pro rata", 12.31),
        ("£24,000 per annum, 37.5 hours per week", 12.31),
        ("£25k - £30k", 12.82),  # no unit: magnitude says annual
        # weekly / monthly / daily
        ("£400 a week", 10.67),
        ("£2,000 per month", 12.31),
        ("£95 per day", 12.67),
    ],
)
def test_parses_pay_to_hourly_lower_bound(raw: str, expected: float) -> None:
    assert to_hourly(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "Competitive",
        "Negotiable / DOE",
        "£0",
        "£400",  # weekly or monthly? too ambiguous to guess
        "Annual salary £1",  # implausible after conversion
    ],
)
def test_vague_or_implausible_pay_is_none(raw: str | None) -> None:
    assert to_hourly(raw) is None
