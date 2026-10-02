from bs4 import BeautifulSoup

from app.scraper.extract.jsonld import extract_from_jsonld, find_job_postings, parse_job_posting
from tests.fakes import load_fixture

PAGE_URL = "https://beanandleaf.example/jobs/barista-123"


def _soup(name: str) -> BeautifulSoup:
    return BeautifulSoup(load_fixture(f"html/generic/{name}"), "lxml")


def test_extracts_every_field_from_jobposting() -> None:
    listing = extract_from_jsonld(_soup("jobposting_basic.html"), PAGE_URL)

    assert listing is not None
    assert listing.title == "Barista - Part Time"
    assert listing.employer == "Bean & Leaf Coffee"
    assert listing.location == "Manchester, Greater Manchester, M1 1AA"
    assert listing.pay_raw == "£12.21 - £12.75 per hour"
    assert listing.job_type_raw == "PART_TIME"
    assert listing.posted_raw == "2026-09-28"
    assert listing.url == PAGE_URL  # no url in JSON-LD, falls back to the page
    assert listing.description.splitlines()[0] == "Join our friendly team in central Manchester."
    assert "Free coffee" in listing.description


def test_handles_graph_string_org_remote_and_skips_malformed_block() -> None:
    listing = extract_from_jsonld(_soup("jobposting_graph.html"), "https://acme.example/x")

    assert listing is not None
    assert listing.title == "Graduate Analyst"
    assert listing.employer == "Acme Ltd"
    assert listing.location == "Remote"
    assert listing.pay_raw == "£28,000 per year"
    assert listing.url == "https://acme.example/careers/graduate-analyst"
    assert listing.posted_raw == "2026-09-15T09:00:00Z"


def test_returns_none_when_no_usable_jobposting() -> None:
    assert extract_from_jsonld(_soup("no_structured_data.html"), PAGE_URL) is None


def test_only_jobposting_objects_are_returned() -> None:
    postings = find_job_postings(_soup("jobposting_basic.html"))
    assert [p["title"] for p in postings] == ["Barista - Part Time"]


def test_posting_without_title_is_rejected() -> None:
    assert parse_job_posting({"@type": "JobPosting", "title": "  "}, PAGE_URL) is None


def test_salary_with_single_value_and_bad_value() -> None:
    single = parse_job_posting(
        {"title": "Rider", "baseSalary": {"currency": "GBP", "value": 12.5}}, PAGE_URL
    )
    bad = parse_job_posting(
        {"title": "Rider", "baseSalary": {"value": {"minValue": "n/a"}}}, PAGE_URL
    )
    assert single is not None and single.pay_raw == "£12.50"
    assert bad is not None and bad.pay_raw is None
