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


def to_hourly(raw: str | None) -> float | None:
    """Parse a pay string into GBP per hour (lower bound), or ``None`` if vague/unparseable."""
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

    hourly = low / _HOURS_IN_PERIOD[period]
    if not _MIN_PLAUSIBLE_HOURLY <= hourly <= _MAX_PLAUSIBLE_HOURLY:
        return None
    return round(hourly, 2)
