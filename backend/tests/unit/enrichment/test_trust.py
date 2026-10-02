from datetime import date, timedelta

import pytest

from app.enrichment.trust import BASELINE, score_listing
from app.rules import load_wage_rules
from tests.factories import NOW, TODAY, make_listing

WAGES = load_wage_rules()


def _codes(**overrides: object) -> dict[str, int]:
    result = score_listing(make_listing(**overrides), TODAY, WAGES)
    return {flag.code: flag.impact for flag in result.flags}


@pytest.mark.parametrize(
    ("url", "employer", "expected"),
    [
        ("https://www.beanandleaf.co.uk/careers/1", "Bean & Leaf", "employer_own_site"),
        ("https://www.cam.ac.uk/jobs/x", "University of Cambridge", "employer_own_site"),
        ("https://job-boards.greenhouse.io/monzo/jobs/1", "Monzo", "employer_careers_board"),
        ("https://www.studentjob.co.uk/vacancies/1", "bp", "third_party_board"),
        ("https://www.studentjob.co.uk/vacancies/1", "WSP", "third_party_board"),
    ],
)
def test_employer_site_signal(url: str, employer: str, expected: str) -> None:
    assert expected in _codes(url=url, employer=employer)


def test_ats_board_of_another_company_earns_nothing() -> None:
    codes = _codes(url="https://job-boards.greenhouse.io/agency/jobs/1", employer="Monzo")
    assert not {"employer_careers_board", "employer_own_site"} & codes.keys()


def test_unnamed_employer_is_penalised() -> None:
    assert _codes(employer=" ")["employer_unnamed"] < 0


def test_pay_disclosed_vs_vague() -> None:
    assert _codes(pay_hourly=12.8)["pay_disclosed"] > 0
    assert _codes(pay_hourly=None, pay_raw="To be determined")["pay_vague"] < 0


@pytest.mark.parametrize(
    ("title", "pay", "expected"),
    [
        ("Barista", 7.00, "pay_below_legal_minimum"),
        ("Barista", 10.00, "pay_below_living_wage"),
        ("Barista", 12.71, None),  # exactly the 2026 National Living Wage
        ("Teaching Assistant Apprentice", 8.00, None),  # legal apprentice rate
        ("Teaching Assistant Apprentice", 7.50, "pay_below_legal_minimum"),
    ],
)
def test_minimum_wage_signal(title: str, pay: float, expected: str | None) -> None:
    codes = _codes(title=title, pay_hourly=pay)
    wage_codes = {"pay_below_legal_minimum", "pay_below_living_wage"} & codes.keys()
    assert wage_codes == ({expected} if expected else set())


def test_minimum_wage_uses_rates_in_force_when_posted() -> None:
    # £12.30 was above the 2025 rate (£12.21) but is below the 2026 rate (£12.71).
    assert "pay_below_living_wage" not in _codes(pay_hourly=12.30, posted_date=date(2026, 3, 1))
    assert "pay_below_living_wage" in _codes(pay_hourly=12.30, posted_date=date(2026, 9, 1))


def test_scam_phrases_are_listed_and_capped() -> None:
    flags = score_listing(
        make_listing(
            description="Pay a registration fee, buy a starter kit and message us on WhatsApp."
        ),
        TODAY,
        WAGES,
    ).flags
    scam = next(flag for flag in flags if flag.code == "scam_phrases")
    assert scam.impact == -40  # three phrases, capped at two
    assert "registration fee" in scam.message and "whatsapp" in scam.message


def test_income_claims_are_flagged() -> None:
    assert "income_claims" in _codes(title="Earn up to £1500 a month answering surveys")


@pytest.mark.parametrize(
    ("posted_days_ago", "expected"),
    [(2, "recently_posted"), (20, None), (45, "ghost_job"), (90, "ghost_job")],
)
def test_freshness_signal(posted_days_ago: int, expected: str | None) -> None:
    codes = _codes(posted_date=TODAY - timedelta(days=posted_days_ago))
    assert ({"recently_posted", "ghost_job"} & codes.keys()) == ({expected} if expected else set())


def test_listing_not_seen_recently_may_have_closed() -> None:
    assert "no_longer_listed" in _codes(last_seen=NOW - timedelta(days=10))


def test_score_is_baseline_plus_impacts_and_clamped() -> None:
    clean = score_listing(make_listing(), TODAY, WAGES)
    assert clean.score == BASELINE + sum(flag.impact for flag in clean.flags)

    worst = score_listing(
        make_listing(
            employer="",
            pay_hourly=2.0,
            description="registration fee, whatsapp, earn money",
            posted_date=TODAY - timedelta(days=100),
            last_seen=NOW - timedelta(days=30),
        ),
        TODAY,
        WAGES,
    )
    assert worst.score == 0
