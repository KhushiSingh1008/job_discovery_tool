from datetime import date

from app.models import JobType
from app.scraper.discovery import Page
from app.scraper.pipeline import normalize
from app.scraper.sources.cambridge import SEARCH_URL, CambridgeAdapter
from app.scraper.types import RawListing
from tests.fakes import FakeFetcher, load_fixture

TODAY = date(2026, 10, 2)


def _parse() -> list[RawListing]:
    return CambridgeAdapter().parse(Page(SEARCH_URL), load_fixture("html/cambridge/search.html"))


def test_parses_table_rows_with_all_required_fields() -> None:
    listings = _parse()

    assert len(listings) == 6
    accounts = next(item for item in listings if item.title == "Accounts Assistant")
    assert accounts.employer == "University of Cambridge"
    assert accounts.location == "Cambridge"
    assert accounts.pay_raw == "£27,319-£31,236"
    assert accounts.posted_raw == "2026-09-24T01:00:00+01:00"
    assert accounts.url == "https://www.cam.ac.uk/jobs/accounts-assistant-nq51192"
    assert "Reference: NQ51192" in accounts.description


def test_skips_phd_studentships() -> None:
    assert all("Category: Studentships" not in item.description for item in _parse())


def test_normalised_rows_cover_full_and_part_time() -> None:
    adapter = CambridgeAdapter()
    by_title = {item.title: normalize(item, adapter, TODAY) for item in _parse()}

    part_time = by_title["Academic Support Coordinator (Part Time, Fixed Term)"]
    assert part_time.job_type is JobType.PART_TIME
    assert part_time.pay_hourly == 16.02
    assert by_title["Accounts Assistant"].job_type is JobType.FULL_TIME
    assert by_title["Accounts Assistant"].posted_date == date(2026, 9, 24)


def test_row_without_salary_keeps_pay_empty() -> None:
    director = next(item for item in _parse() if item.title.startswith("Director"))
    assert director.pay_raw is None


def test_discover_yields_prefetched_search_page() -> None:
    html = load_fixture("html/cambridge/search.html")

    pages = list(CambridgeAdapter().discover(FakeFetcher({SEARCH_URL: html})))

    assert [page.url for page in pages] == [SEARCH_URL]
    assert pages[0].html == html
