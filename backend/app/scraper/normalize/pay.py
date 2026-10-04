"""Turn free-text UK pay strings into a comparable hourly GBP figure.

We store the *lower bound* of a range: it is what the student is guaranteed, and it is
the right value to compare against the National Minimum Wage. Vague pay
("Competitive", "DOE") returns ``None`` instead of a guess.
"""

import re
from enum import StrEnum

HOURS_PER_DAY = 7.5
HOURS_PER_WEEK = 37.5
WEEKS_PER_YEAR = 52

# Results outside this band are almost certainly parse errors (e.g. a year or a phone number).
_MIN_PLAUSIBLE_HOURLY = 3.0
_MAX_PLAUSIBLE_HOURLY = 300.0
# Annual pay that works out below this per full-time hour is a pro-rata salary (e.g.
# "£7,221" for a term-time, part-time post), which cannot be turned into an hourly rate.
_MIN_FULL_TIME_ANNUAL_HOURLY = 7.0

_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_DASHES = "-" + chr(0x2013) + chr(0x2014)  # hyphen, en dash, em dash
_RANGE_TAIL = rf"(?:\s*(?:[{_DASHES}]|to)\s*£?\s*(?P<high>{_NUMBER})\s*(?P<hk>k\b)?)?"
_POUND_AMOUNT = re.compile(rf"£\s*(?P<low>{_NUMBER})\s*(?P<lk>k\b)?{_RANGE_TAIL}", re.I)
_BARE_AMOUNT = re.compile(rf"(?<![\w.])(?P<low>{_NUMBER})\s*(?P<lk>k\b)?{_RANGE_TAIL}", re.I)


class PayPeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


_PERIOD_PATTERNS: dict[PayPeriod, re.Pattern[str]] = {
    PayPeriod.HOUR: re.compile(r"hour|\bhr\b|\bph\b|p/h|/h\b", re.I),
    PayPeriod.DAY: re.compile(r"\bday\b|daily|/d\b|p/d", re.I),
    PayPeriod.WEEK: re.compile(r"week|\bpw\b|p/w|/wk\b", re.I),
    PayPeriod.MONTH: re.compile(r"month|\bpcm\b|/mo\b", re.I),
    PayPeriod.YEAR: re.compile(r"annum|annual|year|\bpa\b|p\.a\.|/yr\b|\byr\b", re.I),
}

#: Weekly or monthly amounts at or above these are annual salaries mislabelled by the page.
_ANNUAL_ABOVE: dict[PayPeriod, float] = {PayPeriod.WEEK: 3_000, PayPeriod.MONTH: 6_000}

_HOURS_IN_PERIOD: dict[PayPeriod, float] = {
    PayPeriod.HOUR: 1.0,
    PayPeriod.DAY: HOURS_PER_DAY,
    PayPeriod.WEEK: HOURS_PER_WEEK,
    PayPeriod.MONTH: HOURS_PER_WEEK * WEEKS_PER_YEAR / 12,
    PayPeriod.YEAR: HOURS_PER_WEEK * WEEKS_PER_YEAR,
}


def _to_number(digits: str, thousands: str | None) -> float:
    value = float(digits.replace(",", ""))
    return value * 1000 if thousands else value


def _earliest_period(text: str) -> PayPeriod | None:
    best: tuple[int, PayPeriod] | None = None
    for period, pattern in _PERIOD_PATTERNS.items():
        match = pattern.search(text)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), period)
    return best[1] if best else None


def _infer_period_from_magnitude(amount: float) -> PayPeriod | None:
    if amount <= 100:
        return PayPeriod.HOUR
    if amount >= 5000:
        return PayPeriod.YEAR
    return None  # e.g. "£400": weekly or monthly? Too ambiguous to guess.


def detect_period(raw: str, amount_end: int) -> PayPeriod | None:
    """Prefer the unit written right after the amount ("£11 per hour, 20 hours a week")."""
    return _earliest_period(raw[amount_end : amount_end + 40]) or _earliest_period(raw)


_WEEKLY_HOURS = re.compile(
    rf"(?P<low>\d+(?:\.\d+)?)(?:\s*(?:[{_DASHES}]|to)\s*(?P<high>\d+(?:\.\d+)?))?\s*"
    r"(?:hours|hrs)\s*(?:per|a|each|/)\s*week",
    re.I,
)
_MAX_WEEKLY_HOURS = 60.0


def parse_weekly_hours(text: str | None) -> tuple[float, float] | None:
    """'4 - 20 hours per week' -> (4, 20); '16 hours a week' -> (16, 16)."""
    match = _WEEKLY_HOURS.search(text or "")
    if not match:
        return None
    low = float(match["low"])
    high = float(match["high"] or low)
    if not 0 < low <= high <= _MAX_WEEKLY_HOURS:
        return None
    return low, high


def to_hourly(
    raw: str | None,
    *,
    weekly_hours: tuple[float, float] | None = None,
    full_time: bool = True,
) -> float | None:
    """Parse a pay string into GBP per hour (lower bound), or ``None`` if vague/unparseable.

    Weekly and monthly pay are divided by the job's own hours when the advert gives them.
    Without them a 37.5-hour week is assumed only for full-time roles: "£200 a week" for
    a part-time job is not £5.33 an hour, and guessing so would wrongly flag it as below
    the minimum wage.
    """
    if not raw:
        return None

    match = _POUND_AMOUNT.search(raw) or _BARE_AMOUNT.search(raw)
    if not match:
        return None

    low = _to_number(match["low"], match["lk"])
    if low <= 0:
        return None

    period = detect_period(raw, match.end()) or _infer_period_from_magnitude(low)
    if period is None:
        return None
    # "£16,087 per month" for an apprenticeship, or "£27,700, plus a monthly commission":
    # amounts this large are annual salaries, whatever unit the text puts next to them.
    if period in _ANNUAL_ABOVE and low >= _ANNUAL_ABOVE[period]:
        period = PayPeriod.YEAR

    if period in (PayPeriod.WEEK, PayPeriod.MONTH):
        high = _to_number(match["high"], match["hk"] or match["lk"]) if match["high"] else low
        to_weekly = 1.0 if period is PayPeriod.WEEK else 12 / WEEKS_PER_YEAR
        if weekly_hours is not None:
            # Pair the ends of both ranges: the lower rate of the two is the safe figure.
            hours_low, hours_high = weekly_hours
            hourly = min(low * to_weekly / hours_low, high * to_weekly / hours_high)
        elif full_time:
            hourly = low * to_weekly / HOURS_PER_WEEK
        else:
            return None
    else:
        hourly = low / _HOURS_IN_PERIOD[period]

    if period is PayPeriod.YEAR and hourly < _MIN_FULL_TIME_ANNUAL_HOURLY:
        return None  # a pro-rata salary for part-time or term-time hours: not comparable
    if not _MIN_PLAUSIBLE_HOURLY <= hourly <= _MAX_PLAUSIBLE_HOURLY:
        return None
    return round(hourly, 2)


# Words near an amount that suggest it is the salary, or a perk that merely costs money.
_SALARY_CONTEXT = re.compile(
    r"salary|base pay|per annum|per year|a year|per hour|an hour|hourly|compensation|"
    r"\bpay\b|wage|rate|range|package",
    re.I,
)
_PERK_AFTER = re.compile(
    r"^\s*(?:\w+\s+)?(?:budget|allowance|learning|pension|equity|voucher|discount|"
    r"referral|relocation|towards|contribution)",
    re.I,
)
_SNIPPET_TAIL = re.compile(r"[^\n.;]{0,30}")


def find_pay_in_text(text: str | None) -> str | None:
    """Pick the salary mention out of a free-text job description.

    Descriptions mention many amounts ("£1,000 learning budget"); a range, or an amount
    near salary words, is the likely pay. Returns the snippet, which ``to_hourly`` can parse.
    """
    if not text:
        return None
    best: tuple[int, str] | None = None
    for match in _POUND_AMOUNT.finditer(text):
        before = text[max(0, match.start() - 60) : match.start()]
        tail = _SNIPPET_TAIL.match(text, match.end())
        after = tail.group(0) if tail else ""
        score = 0
        score += 2 if match["high"] else 0
        score += 2 if _SALARY_CONTEXT.search(before + after) else 0
        score -= 3 if _PERK_AFTER.search(after) else 0
        if score > 0 and (best is None or score > best[0]):
            best = (score, (match.group(0) + after).strip())
    return best[1] if best else None
