from datetime import date

import pytest

from app.models import JobType
from app.scraper.discovery import Page
from app.scraper.pipeline import normalize
from app.scraper.sources import studentjob
from app.scraper.sources.studentjob import StudentJobAdapter, parse_cards
from tests.fakes import FakeFetcher, load_fixture

LISTING_URL = "https://www.studentjob.co.uk/jobs/manchester"
DETAIL_URL = "https://www.studentjob.co.uk/vacancies/8798133-uk-acquisition-support-manager"
TODAY = date(2026, 10, 2)


def test_cards_carry_pay_hours_and_location() -> None:
    cards = parse_cards(load_fixture("html/studentjob/listing.html"), LISTING_URL)
    survey = next(card for card in cards if "524050" in card.url)

    assert survey.title == "Earn up to £1500 a month answering surveys"
    assert survey.location == "Nationwide"
    assert survey.pay == "Between £300 and £1,500 Per Month"
    assert survey.hours == "4 - 10 hours per week"
    assert "Casual / Part Time Jobs" in survey.employment


def test_external_redirect_cards_are_skipped() -> None:
    html = load_fixture("html/studentjob/listing.html")
    assert "redirect_to_external" in html  # the fixture really contains them

    cards = parse_cards(html, LISTING_URL)

    assert cards
    assert all(card.url.startswith("https://www.studentjob.co.uk/vacancies/") for card in cards)


def test_detail_prefers_visible_title_over_wrong_jsonld_title() -> None:
    page = Page(
        DETAIL_URL,
        context={"pay": "To be determined", "hours": "37 - 40 hours per week"},
    )

    [listing] = StudentJobAdapter().parse(page, load_fixture("html/studentjob/detail.html"))

    assert listing.title == "UK Acquisition Support Manager"  # JSON-LD says "Retail "
    assert listing.employer == "bp"
    assert listing.location == "Milton Keynes, MK9"
    assert listing.pay_raw == "To be determined"  # JSON-LD has no salary: card value used
    assert listing.posted_raw == "2026-10-01T11:34:43+02:00"
    assert listing.description.startswith("Hours: 37 - 40 hours per week")
    assert "UK Network Strategy" in listing.description


def test_detail_normalises_to_full_time_listing() -> None:
    adapter = StudentJobAdapter()
    [raw] = adapter.parse(Page(DETAIL_URL), load_fixture("html/studentjob/detail.html"))

    listing = normalize(raw, adapter, TODAY)

    assert listing.job_type is JobType.FULL_TIME
    assert listing.pay_hourly is None
    assert listing.posted_date == date(2026, 10, 1)


def test_detail_without_any_title_yields_nothing() -> None:
    assert StudentJobAdapter().parse(Page(DETAIL_URL), "<html><body></body></html>") == []


def test_discover_dedupes_cards_across_start_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(studentjob, "START_PATHS", ("/jobs/manchester", "/jobs/leeds"))
    monkeypatch.setattr(studentjob, "MAX_PAGES_PER_START", 1)
    html = load_fixture("html/studentjob/listing.html")
    fetcher = FakeFetcher(
        {LISTING_URL: html, "https://www.studentjob.co.uk/jobs/leeds": html}  # same cards
    )

    pages = list(StudentJobAdapter().discover(fetcher))

    urls = [page.url for page in pages]
    assert len(urls) == len(set(urls)) == len(parse_cards(html, LISTING_URL))
    assert all(page.html is None and page.context["title"] for page in pages)


def test_regular_cards_come_before_promoted_ones() -> None:
    cards = parse_cards(load_fixture("html/studentjob/listing.html"), LISTING_URL)

    flags = [card.promoted for card in cards]
    assert any(flags) and not all(flags)
    assert flags == sorted(flags)  # all False (regular) before True (promoted)


def test_discover_yields_regular_cards_before_promoted_across_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(studentjob, "START_PATHS", ("/jobs/manchester",))
    monkeypatch.setattr(studentjob, "MAX_PAGES_PER_START", 1)
    html = load_fixture("html/studentjob/listing.html")

    pages = list(StudentJobAdapter().discover(FakeFetcher({LISTING_URL: html})))

    promoted = {card.url for card in parse_cards(html, LISTING_URL) if card.promoted}
    flags = [page.url in promoted for page in pages]
    assert flags == sorted(flags)
