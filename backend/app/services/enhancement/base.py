"""The resume-enhancer interface and the checks every engine's output goes through.

Suggestions are applied by the student one at a time, so each must be applicable on its
own: a rewrite must quote text that really is in the resume, and no two rewrites may touch
the same text.
"""

from collections.abc import Iterable
from typing import Protocol

from app.schemas import EnhanceResult, ResumeSuggestion, SuggestionDraft, SuggestionKind

MAX_SUGGESTIONS = 8


class Enhancer(Protocol):
    def enhance(self, resume_text: str, job_title: str, job_text: str) -> EnhanceResult: ...


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def finalize_suggestions(
    resume_text: str, drafts: Iterable[SuggestionDraft], limit: int = MAX_SUGGESTIONS
) -> list[ResumeSuggestion]:
    """Drop edits that cannot be applied cleanly and number the rest ``s1``, ``s2``..."""
    accepted: list[SuggestionDraft] = []
    rewritten: list[str] = []
    seen_replacements: set[str] = set()

    for draft in drafts:
        original, replacement = draft.original.strip(), draft.replacement.strip()
        if not replacement or replacement in seen_replacements:
            continue

        if draft.kind is SuggestionKind.REWRITE:
            if not original or original == replacement or original not in resume_text:
                continue  # invented or no-op text cannot be applied
            if any(original in other or other in original for other in rewritten):
                continue  # overlapping edits would conflict when both are accepted
            rewritten.append(original)
        elif original and original not in resume_text:
            original = _last_line(resume_text)  # unknown anchor: add at the end instead

        seen_replacements.add(replacement)
        accepted.append(draft.model_copy(update={"original": original, "replacement": replacement}))
        if len(accepted) == limit:
            break

    return [
        ResumeSuggestion(**draft.model_dump(), id=f"s{index}")
        for index, draft in enumerate(accepted, start=1)
    ]
