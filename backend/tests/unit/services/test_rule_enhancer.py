import pytest

from app.schemas import EnhanceEngine, ResumeSuggestion, SuggestionKind
from app.services.enhancement.rules import (
    METRIC_PLACEHOLDER,
    RuleBasedEnhancer,
    past_tense,
    strengthen_opening,
)

RESUME = """Priya Sharma
priya@example.com | Manchester

EXPERIENCE
Retail Assistant, Boots (2025-2026)
- Responsible for handling cash on the till
- Served customers at busy times and kept the shop floor tidy
- Worked on the weekly stock count with the team

EDUCATION
- MSc Data Science, University of Manchester, studying machine learning

Skills: Excel, teamwork, English and Hindi
"""
JOB_TITLE = "Weekend Barista"
JOB = "Weekend barista. You need customer service, cash handling and food hygiene."


def _enhance(
    resume: str = RESUME, title: str = JOB_TITLE, job: str = JOB
) -> list[ResumeSuggestion]:
    result = RuleBasedEnhancer().enhance(resume, title, job)
    assert result.engine is EnhanceEngine.RULES
    return result.suggestions


def _by_section(suggestions: list[ResumeSuggestion], section: str) -> list[ResumeSuggestion]:
    return [s for s in suggestions if s.section == section]


@pytest.mark.parametrize(
    ("gerund", "past"),
    [
        ("managing", "managed"),
        ("serving", "served"),
        ("planning", "planned"),
        ("carrying", "carried"),
        ("playing", "played"),
        ("teaching", "taught"),
        ("running", "ran"),
        ("Organising", "organised"),
    ],
)
def test_past_tense(gerund: str, past: str) -> None:
    assert past_tense(gerund) == past


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Responsible for training new staff", "Trained new staff"),
        ("I was responsible for the rota", "Managed the rota"),
        ("Responsible for everything at the front desk", "Managed everything at the front desk"),
        ("In charge of opening the cafe", "Opened the cafe"),
        ("Duties included serving customers", "Served customers"),
        ("Helped with organising events", "Contributed to organising events"),
        ("Worked on a group project", "Delivered a group project"),
        ("Did the weekly banking", "Completed the weekly banking"),
        ("I managed a team of 4", "Managed a team of 4"),
    ],
)
def test_weak_openings_become_action_verbs(text: str, expected: str) -> None:
    result = strengthen_opening(text)
    assert result is not None
    assert result[0] == expected


@pytest.mark.parametrize(
    "text", ["Led a team of 4", "Helped customers find products", "Responsible"]
)
def test_strong_or_ambiguous_openings_are_left_alone(text: str) -> None:
    assert strengthen_opening(text) is None


def test_every_suggestion_can_be_applied_to_the_resume() -> None:
    suggestions = _enhance()

    assert [s.id for s in suggestions] == [f"s{i}" for i in range(1, len(suggestions) + 1)]
    for suggestion in suggestions:
        assert suggestion.original in RESUME
        assert suggestion.reason


def test_profile_is_added_below_the_name() -> None:
    [profile] = _by_section(_enhance(), "Profile")

    assert profile.kind is SuggestionKind.ADD
    assert profile.original == "Priya Sharma"
    assert "the Weekend Barista role" in profile.replacement
    assert "[Your course]" in profile.replacement  # facts only the student knows


def test_existing_profile_is_respected() -> None:
    resume = RESUME.replace("EXPERIENCE", "Profile: Friendly MSc student.\n\nEXPERIENCE")
    assert not _by_section(_enhance(resume), "Profile")


def test_bullets_get_action_verbs_and_at_most_two_metric_prompts() -> None:
    experience = _by_section(_enhance(), "Experience")
    rewrites = {s.original: s for s in experience if s.kind is SuggestionKind.REWRITE}

    cash = rewrites["Responsible for handling cash on the till"]
    assert cash.replacement == f"Handled cash on the till, {METRIC_PLACEHOLDER}"
    assert "Responsible for" in cash.reason
    assert rewrites["Worked on the weekly stock count with the team"].replacement.startswith(
        "Delivered the weekly stock count"
    )
    assert sum(METRIC_PLACEHOLDER in s.replacement for s in experience) == 2


def test_education_bullets_are_not_asked_for_numbers() -> None:
    assert not _by_section(_enhance(), "Education")


def test_evidenced_skills_are_named_in_the_adverts_words() -> None:
    [skills] = _by_section(_enhance(), "Skills")

    assert skills.kind is SuggestionKind.REWRITE
    assert skills.original == "Skills: Excel, teamwork, English and Hindi"
    # "Served customers" and "handling cash" are evidence; the advert's terms are added.
    assert skills.replacement.endswith(", customer service, cash handling")


def test_skills_are_added_under_a_skills_heading() -> None:
    resume = RESUME.replace("Skills: Excel, teamwork, English and Hindi", "SKILLS\n- Excel")
    [skills] = _by_section(_enhance(resume), "Skills")

    assert skills.kind is SuggestionKind.ADD
    assert skills.original == "SKILLS"
    assert skills.replacement == "Customer service, cash handling"


def test_skills_line_is_added_when_resume_has_no_skills_section() -> None:
    resume = RESUME.replace("\nSkills: Excel, teamwork, English and Hindi\n", "")
    [skills] = _by_section(_enhance(resume), "Skills")

    assert skills.kind is SuggestionKind.ADD
    assert skills.replacement == "Skills: customer service, cash handling"


def test_missing_skill_prompt_prefers_requirements_over_the_job_name() -> None:
    adds = [s for s in _enhance() if s.kind is SuggestionKind.ADD and s.section == "Experience"]

    [missing] = adds
    assert (
        missing.replacement
        == "- [Your experience of food hygiene: where, what you did, the result]"
    )
    assert missing.original == "Worked on the weekly stock count with the team"
    assert "Only add this if you have real experience" in missing.reason


def test_a_tailored_resume_gets_few_suggestions() -> None:
    resume = """Profile: MSc student and experienced barista.

EXPERIENCE
- Led 3 baristas on weekend shifts serving 200 customers a day
- Trained 5 new starters in food hygiene and cash handling

Skills: customer service, cash handling, food hygiene, barista
"""
    assert _enhance(resume) == []
