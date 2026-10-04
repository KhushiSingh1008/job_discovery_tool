import pytest

from app.schemas import MatchEngine
from app.services.matching.keyword_matcher import KeywordMatcher
from app.services.matching.skills import find_skills

BARISTA_JOB = """
Weekend Barista. We need someone with customer service experience, cash handling on
the till and good food hygiene. Teamwork and communication are essential.
"""

RESUME = """
Retail assistant at a campus shop (2025-2026): served customers, handled cash and
the EPOS till, restocked shelves. Worked in a team of six. Fluent in Hindi and English.
BSc Computer Science student, Python and SQL coursework.
"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Experience with the EPOS till", {"cash handling"}),
        ("Strong customer-facing skills", {"customer service"}),
        ("MS Office and spreadsheets", {"microsoft office", "excel"}),
        ("Node.js and TypeScript", {"javascript"}),
        ("Postgres and GitHub", {"sql", "git"}),
        ("Enhanced DBS check required", {"safeguarding"}),
    ],
)
def test_aliases_map_to_canonical_skills(text: str, expected: set[str]) -> None:
    assert expected <= find_skills(text)


@pytest.mark.parametrize(
    "text",
    [
        "Crop rotation research",  # 'rota' inside a word is not scheduling
        "International relations",  # not an internship or a skill
        "She led the word game",  # ordinary verbs/nouns are not skills
    ],
)
def test_ordinary_words_are_not_mistaken_for_skills(text: str) -> None:
    assert find_skills(text) <= {"research"}


def test_match_reports_matched_and_missing_skills() -> None:
    result = KeywordMatcher().match(RESUME, "Weekend Barista", BARISTA_JOB)

    assert result.engine is MatchEngine.KEYWORD
    assert {"customer service", "cash handling", "teamwork"} <= set(result.matched_skills)
    assert "food hygiene" in result.missing_skills
    assert "barista" in result.missing_skills
    assert 30 <= result.score <= 80
    assert "of the" in result.summary


def test_score_rises_with_coverage() -> None:
    matcher = KeywordMatcher()
    weak = matcher.match("I enjoy reading novels and long walks.", "Barista", BARISTA_JOB)
    strong = matcher.match(
        RESUME + " Barista at a cafe, food hygiene certificate, great communication.",
        "Weekend Barista",
        BARISTA_JOB,
    )
    assert weak.score < strong.score
    assert strong.score >= 80


def test_job_without_known_skills_uses_keyword_overlap() -> None:
    result = KeywordMatcher().match(
        "Experienced with telescopes and astronomy outreach events.",
        "Planetarium guide",
        "Guide visitors through planetarium astronomy shows and telescopes events.",
    )
    assert result.score > 0
    assert result.matched_skills == []
    assert "few specific skills" in result.summary


def test_suggestions_are_actionable_and_deterministic() -> None:
    matcher = KeywordMatcher()
    first = matcher.match(RESUME, "Weekend Barista", BARISTA_JOB)
    second = matcher.match(RESUME, "Weekend Barista", BARISTA_JOB)

    assert first == second
    assert 1 <= len(first.suggestions) <= 3
    assert any("food hygiene" in s for s in first.suggestions)


def test_links_are_not_skill_evidence() -> None:
    resume = "linkedin.com/in/someone | github.com/someone | me@instagram-fan.com\nBarista"
    result = KeywordMatcher().match(resume, "Social media assistant", "Social media and git.")

    assert result.matched_skills == []


def test_thin_adverts_do_not_produce_confident_scores() -> None:
    # One named skill matched is not a 100% fit when the advert says almost nothing else.
    result = KeywordMatcher().match(
        "Research assistant in a biology lab, Python data pipelines.",
        "Research Software Engineer",
        "Department: Cancer Research Institute. Category: Research.",
    )

    assert result.matched_skills == ["research"]
    assert result.score < 50
    assert "rough guide" in result.summary
