from bs4 import BeautifulSoup

from app.scraper.extract.selectors import absolute_links, first_match
from tests.fakes import load_fixture


def _soup() -> BeautifulSoup:
    return BeautifulSoup(load_fixture("html/generic/no_structured_data.html"), "lxml")


def test_first_match_cleans_whitespace() -> None:
    assert first_match(_soup(), ["h1.vacancy__title"]) == "Retail Assistant (Weekends)"


def test_first_match_skips_missing_and_empty_candidates() -> None:
    # .missing does not exist and .vacancy__company is empty, so the third selector wins.
    selectors = [".missing", ".vacancy__company", ".employer-name"]
    assert first_match(_soup(), selectors) == "High Street Books"


def test_first_match_reads_attributes() -> None:
    assert first_match(_soup(), ["time"], attr="datetime") == "2026-09-20"


def test_first_match_returns_none_when_nothing_matches() -> None:
    assert first_match(_soup(), [".nope", ".also-nope"]) is None


def test_absolute_links_resolves_and_dedupes() -> None:
    html = """
      <a class="job" href="/jobs/1">One</a>
      <a class="job" href="https://example.com/jobs/1">One again</a>
      <a class="job" href="jobs/2">Two</a>
      <a class="job" href="#top">Skip</a>
      <a class="job">No href</a>
    """
    links = absolute_links(BeautifulSoup(html, "lxml"), "a.job", "https://example.com/")
    assert links == ["https://example.com/jobs/1", "https://example.com/jobs/2"]
