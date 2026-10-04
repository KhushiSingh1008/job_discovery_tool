import pytest

from app.scraper.normalize.pay import find_pay_in_text, parse_weekly_hours, to_hourly


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


def test_find_pay_in_text_prefers_salary_over_perks() -> None:
    text = (
        "Benefits include a £1,000 learning budget each year.\n"
        "The salary range for this role is £84,200 - £99,000 + incentive awards."
    )
    assert find_pay_in_text(text) == "£84,200 - £99,000 + incentive awards"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("We pay £12.50 per hour plus tips", "£12.50 per hour plus tips"),
        ("£500 towards your gym membership", None),
        ("No pay information here", None),
        (None, None),
    ],
)
def test_find_pay_in_text(text: str | None, expected: str | None) -> None:
    assert find_pay_in_text(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4 - 20 hours per week", (4.0, 20.0)),
        ("16 hours a week", (16.0, 16.0)),
        ("Hours: 10 to 15 hrs per week", (10.0, 15.0)),
        ("20 hours", None),
        ("0 hours per week", None),
        ("40 - 90 hours per week", None),
        (None, None),
    ],
)
def test_parse_weekly_hours(text: str | None, expected: tuple[float, float] | None) -> None:
    assert parse_weekly_hours(text) == expected


@pytest.mark.parametrize(
    ("raw", "hours", "full_time", "expected"),
    [
        # StudentJob style: weekly pay range for a part-time job with stated hours
        ("£100.00 - £400.00 per week", (4.0, 20.0), False, 20.0),  # min(25, 20)
        ("£200.00 - £800.00 per month", (4.0, 20.0), False, 9.23),
        ("£240 per week", (20.0, 20.0), False, 12.0),
        # survey "jobs" with absurd ranges stay unparsed
        ("£1.00 - £250.00 per week", (4.0, 20.0), False, None),
        # without hours: full-time assumes 37.5h, part-time refuses to guess
        ("£400 per week", None, True, 10.67),
        ("£200 per week", None, False, None),
        # hourly pay ignores the hours
        ("£12.50 per hour", (4.0, 20.0), False, 12.5),
    ],
)
def test_weekly_and_monthly_pay_uses_real_hours(
    raw: str, hours: tuple[float, float] | None, full_time: bool, expected: float | None
) -> None:
    assert to_hourly(raw, weekly_hours=hours, full_time=full_time) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Annual salaries mislabelled by the page
        ("£16,087 per month", 8.25),
        ("£27,700 , plus a monthly commission for achieving targets", 14.21),
        # A pro-rata salary for a term-time, part-time post cannot become an hourly rate
        ("£7,221 - £7,833 per month", None),
        ("£9,500 per annum pro rata", None),
        # A real monthly salary stays monthly
        ("£2,500 per month", 15.38),
    ],
)
def test_annual_salaries_are_recognised_whatever_the_label(
    raw: str, expected: float | None
) -> None:
    assert to_hourly(raw) == expected
