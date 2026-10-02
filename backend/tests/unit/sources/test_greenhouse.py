from datetime import date

from app.scraper.discovery import Page
from app.scraper.pipeline import normalize
from app.scraper.sources.greenhouse import Company, GreenhouseAdapter, parse_board
from tests.fakes import FakeFetcher, load_fixture

BOARD = "https://job-boards.greenhouse.io/deliveroo"
DETAIL_URL = "https://job-boards.greenhouse.io/monzo/jobs/8132044"


def test_board_rows_have_title_location_and_uk_flag() -> None:
    rows = parse_board(load_fixture("html/greenhouse/board.html"), BOARD)

    assert len(rows) == 10
    rome = rows[0]
    assert rome.title == "Head of Communications & PR, Italy"  # "New" badge stripped
    assert rome.location == "Rome, Italy"
    assert not rome.is_uk
    assert sum(row.is_uk for row in rows) == 8


def test_discover_follows_only_uk_rows_and_stops_when_pages_repeat() -> None:
    board_html = load_fixture("html/greenhouse/board.html")
    # Page 2 returns the same rows (no new jobs), so pagination stops there.
    fetcher = FakeFetcher({BOARD: board_html, f"{BOARD}?page=2": board_html})
    adapter = GreenhouseAdapter(companies=(Company("deliveroo", "Deliveroo"),))

    pages = list(adapter.discover(fetcher))

    assert len(pages) == 8
    assert fetcher.requested == [BOARD, f"{BOARD}?page=2"]
    assert pages[0].context["employer"] == "Deliveroo"
    assert "United Kingdom" in pages[0].context["location"]


def test_discover_skips_company_whose_board_fails() -> None:
    adapter = GreenhouseAdapter(companies=(Company("gone", "Gone Ltd"),))
    assert list(adapter.discover(FakeFetcher({}))) == []


def test_detail_extracts_salary_from_description_and_publish_date() -> None:
    adapter = GreenhouseAdapter()
    page = Page(DETAIL_URL, context={"employer": "Monzo", "location": "London"})

    [raw] = adapter.parse(page, load_fixture("html/greenhouse/detail.html"))
    listing = normalize(raw, adapter, date(2026, 10, 2))

    assert listing.title == "Senior Finance Business Partner"
    assert listing.employer == "Monzo"
    assert listing.location == "London"
    assert raw.pay_raw is not None and raw.pay_raw.startswith("£84,200 - £99,000")
    assert listing.pay_hourly == 43.18
    assert listing.posted_date == date(2026, 8, 17)
    assert "make money work for everyone" in listing.description
