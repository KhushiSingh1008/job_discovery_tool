from app.schemas import SuggestionDraft, SuggestionKind
from app.services.enhancement.base import finalize_suggestions

RESUME = "Sam Lee\n- Responsible for the till\n- Served customers\nSkills: Excel"


def _draft(kind: SuggestionKind, original: str, replacement: str) -> SuggestionDraft:
    return SuggestionDraft(
        kind=kind, section="Experience", original=original, replacement=replacement, reason="r"
    )


def _rewrite(original: str, replacement: str) -> SuggestionDraft:
    return _draft(SuggestionKind.REWRITE, original, replacement)


def _add(anchor: str, replacement: str) -> SuggestionDraft:
    return _draft(SuggestionKind.ADD, anchor, replacement)


def test_valid_edits_are_numbered_in_order() -> None:
    result = finalize_suggestions(
        RESUME, [_rewrite("Responsible for the till", "Ran the till"), _add("", "Profile: x")]
    )

    assert [(s.id, s.replacement) for s in result] == [("s1", "Ran the till"), ("s2", "Profile: x")]


def test_rewrites_must_quote_the_resume() -> None:
    result = finalize_suggestions(RESUME, [_rewrite("Managed a team of 10", "Led a team of 10")])
    assert result == []


def test_no_op_and_empty_edits_are_dropped() -> None:
    drafts = [_rewrite("Served customers", "Served customers"), _add("", "   ")]
    assert finalize_suggestions(RESUME, drafts) == []


def test_overlapping_rewrites_keep_only_the_first() -> None:
    drafts = [
        _rewrite("Served customers", "Served 40 customers"),
        _rewrite("customers", "guests"),
        _rewrite("Skills: Excel", "Skills: Excel, customer service"),
    ]

    assert [s.original for s in finalize_suggestions(RESUME, drafts)] == [
        "Served customers",
        "Skills: Excel",
    ]


def test_duplicate_replacements_are_dropped() -> None:
    drafts = [_add("Sam Lee", "Profile: x"), _add("", "Profile: x")]
    assert len(finalize_suggestions(RESUME, drafts)) == 1


def test_unknown_add_anchor_moves_to_the_end() -> None:
    [suggestion] = finalize_suggestions(RESUME, [_add("No such line", "- Volunteered")])
    assert suggestion.original == "Skills: Excel"


def test_text_is_trimmed_and_limit_applies() -> None:
    drafts = [_add("", f"  line {i}  ") for i in range(5)]

    result = finalize_suggestions(RESUME, drafts, limit=3)

    assert [s.replacement for s in result] == ["line 0", "line 1", "line 2"]
