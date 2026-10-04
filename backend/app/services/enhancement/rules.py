"""Offline resume enhancer: deterministic rules, no network, no invented facts.

It proposes four kinds of edit, each standard resume advice:

1. Start bullets with an action verb instead of "Responsible for", "Helped with"...
2. Ask for a number where an experience bullet has none.
3. Name skills the resume already evidences using the advert's own wording.
4. Add a profile line aimed at the role, and a prompt for the top missing skill.

Wherever only the student knows the facts, the edit holds a ``[placeholder]`` instead.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

from app.schemas import EnhanceEngine, EnhanceResult, SuggestionDraft, SuggestionKind
from app.services.enhancement.base import finalize_suggestions
from app.services.matching.skills import find_skills, skills_in_order

MAX_BULLET_EDITS = 5
MAX_METRIC_HINTS = 2
MAX_SKILLS_TO_NAME = 4
METRIC_PLACEHOLDER = "[add a number or result]"

_BULLET = re.compile(r"^\s*(?P<marker>[-•*\u2013·▪]|\d+[.)])\s+(?P<text>\S.*?)\s*$")
_SECTION_NAMES = re.compile(
    r"^(profile|summary|personal statement|about me|(career )?objective|"
    r"(work |relevant |professional )?experience|employment( history)?|education|"
    r"(key |technical |core )?skills|projects|achievements|volunteering|interests|"
    r"languages|certifications|awards)$",
    re.I,
)
_PROFILE = re.compile(r"^(profile|summary|personal statement|about me|(career )?objective)\b", re.I)
_SKILLS_LINE = re.compile(r"^(key |technical |core )?skills\s*[:\-\u2013]\s*\S", re.I)
_SKILLS_HEADING = re.compile(r"^(key |technical |core )?skills$", re.I)
_NO_METRIC_SECTIONS = re.compile(r"education|skills|interests|languages|certifications", re.I)

# Weak openers and the action verb that replaces them. "{gerund}" openers become the past
# tense of the verb that follows when there is one: "Responsible for training" -> "Trained".
_WEAK_OPENERS: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(r"^(?:i\s+was\s+|was\s+)?responsible\s+for\s+", re.I), "Managed", True),
    (re.compile(r"^(?:i\s+was\s+|was\s+)?in\s+charge\s+of\s+", re.I), "Led", True),
    (
        re.compile(
            r"^(?:my\s+)?(?:duties|tasks|responsibilities)\s+(?:included|were)\s*:?\s*", re.I
        ),
        "Handled",
        True,
    ),
    (re.compile(r"^(?:i\s+)?helped\s+(?:out\s+)?with\s+", re.I), "Contributed to", False),
    (re.compile(r"^(?:i\s+)?worked\s+on\s+", re.I), "Delivered", False),
    (re.compile(r"^(?:i\s+)?did\s+", re.I), "Completed", False),
    (re.compile(r"^i\s+(?=[a-z]+ed\b)", re.I), "", False),  # "I managed" -> "Managed"
]
_GERUND = re.compile(r"^(?P<word>[a-z]{3,}ing)\b(?P<rest>.*)$", re.I | re.S)
_NOT_GERUNDS = frozenset(
    {"everything", "anything", "something", "nothing", "morning", "evening", "clothing",
     "ceiling", "string", "spring", "wedding", "bedding", "sibling"}
)  # fmt: skip
_IRREGULAR_PAST = {
    "beginning": "began", "bringing": "brought", "building": "built", "buying": "bought",
    "choosing": "chose", "cutting": "cut", "dealing": "dealt", "doing": "did",
    "drawing": "drew", "driving": "drove", "feeding": "fed", "finding": "found",
    "getting": "got", "giving": "gave", "growing": "grew", "holding": "held",
    "keeping": "kept", "leading": "led", "making": "made", "meeting": "met",
    "overseeing": "oversaw", "paying": "paid", "putting": "put", "running": "ran",
    "selling": "sold", "sending": "sent", "setting": "set", "speaking": "spoke",
    "spending": "spent", "standing": "stood", "taking": "took", "teaching": "taught",
    "telling": "told", "understanding": "understood", "winning": "won", "writing": "wrote",
}  # fmt: skip


def past_tense(gerund: str) -> str:
    """'managing' -> 'managed', 'carrying' -> 'carried', 'teaching' -> 'taught'."""
    word = gerund.lower()
    if word in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[word]
    stem = word[:-3]
    if stem.endswith("y") and len(stem) > 1 and stem[-2] not in "aeiou":
        return f"{stem[:-1]}ied"
    return f"{stem}ed"  # e-dropping and doubled consonants already happened in the -ing form


def _capitalise(text: str) -> str:
    return text[:1].upper() + text[1:]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


@dataclass(frozen=True)
class _Line:
    text: str  # content without any bullet marker
    marker: str | None
    is_heading: bool
    section: str


def _is_heading(text: str) -> bool:
    name = text.rstrip(":").strip()
    if not name or len(name) > 40 or ":" in name:
        return False
    return bool(_SECTION_NAMES.match(name)) or (name.isupper() and len(name.split()) <= 4)


def _parse(resume_text: str) -> list[_Line]:
    lines: list[_Line] = []
    section = "Resume"
    for raw in resume_text.splitlines():
        if not raw.strip():
            continue
        bullet = _BULLET.match(raw)
        text = bullet["text"] if bullet else raw.strip()
        heading = bullet is None and _is_heading(text)
        if heading:
            section = text.rstrip(":").strip().title()
        lines.append(_Line(text, bullet["marker"] if bullet else None, heading, section))
    return lines


def strengthen_opening(text: str) -> tuple[str, str] | None:
    """Replace a weak opening phrase; returns (new text, phrase replaced) or ``None``."""
    for pattern, verb, verb_from_gerund in _WEAK_OPENERS:
        found = pattern.match(text)
        if not found:
            continue
        rest = text[found.end() :]
        gerund = _GERUND.match(rest) if verb_from_gerund else None
        if gerund and gerund["word"].lower() not in _NOT_GERUNDS:
            new = past_tense(gerund["word"]) + gerund["rest"]
        else:
            new = f"{verb} {rest}" if verb else rest
        return _capitalise(new.strip()), found.group(0).strip()
    return None


def _with_metric_placeholder(text: str) -> str:
    body = text.rstrip()
    period = "." if body.endswith(".") else ""
    return f"{body.rstrip('.').rstrip()}, {METRIC_PLACEHOLDER}{period}"


class RuleBasedEnhancer:
    def enhance(self, resume_text: str, job_title: str, job_text: str) -> EnhanceResult:
        lines = _parse(resume_text)
        job_skills = skills_in_order(f"{job_title}\n{job_text}")
        evidenced = find_skills(resume_text)
        drafts = [
            *self._profile(lines, job_title, [s for s in job_skills if s in evidenced]),
            *self._bullet_edits(lines),
            *self._skill_wording(lines, resume_text, job_skills, evidenced),
            *self._missing_skill(lines, self._missing(job_title, job_skills, evidenced)),
        ]
        return EnhanceResult(
            suggestions=finalize_suggestions(resume_text, drafts),
            engine=EnhanceEngine.RULES,
        )

    @staticmethod
    def _profile(
        lines: list[_Line], job_title: str, strengths: list[str]
    ) -> Iterator[SuggestionDraft]:
        if not lines or any(_PROFILE.match(line.text) for line in lines):
            return
        role = "this role" if job_title == "this role" else f"the {job_title} role"
        evidence = f", with hands-on experience of {_join(strengths[:3])}" if strengths else ""
        # Insert below the name line, unless the resume starts straight with a section.
        anchor = "" if lines[0].is_heading else lines[0].text
        yield SuggestionDraft(
            kind=SuggestionKind.ADD,
            section="Profile",
            original=anchor,
            replacement=(
                f"Profile: [Your course] student at [your university], applying for "
                f"{role}{evidence}."
            ),
            reason=(
                "A short profile aimed at this role is the first thing a recruiter reads. "
                "Fill in the brackets with your own details."
            ),
        )

    @staticmethod
    def _bullet_edits(lines: list[_Line]) -> Iterator[SuggestionDraft]:
        edits = metric_hints = 0
        for line in lines:
            if line.is_heading or edits == MAX_BULLET_EDITS:
                continue
            text, reasons = line.text, []
            if strengthened := strengthen_opening(text):
                text, weak = strengthened
                reasons.append(f"Opens with an action verb instead of '{weak}'.")
            wants_metric = (
                line.marker is not None
                and metric_hints < MAX_METRIC_HINTS
                and not _NO_METRIC_SECTIONS.search(line.section)
                and not re.search(r"\d|\[", text)
                and len(text.split()) >= 4
            )
            if wants_metric:
                text = _with_metric_placeholder(text)
                metric_hints += 1
                reasons.append("A number makes the impact concrete; replace the brackets.")
            if not reasons:
                continue
            edits += 1
            yield SuggestionDraft(
                kind=SuggestionKind.REWRITE,
                section=line.section,
                original=line.text,
                replacement=text,
                reason=" ".join(reasons),
            )

    @staticmethod
    def _skill_wording(
        lines: list[_Line], resume_text: str, job_skills: list[str], evidenced: set[str]
    ) -> Iterator[SuggestionDraft]:
        lowered = resume_text.casefold()
        unnamed = [s for s in job_skills if s in evidenced and s not in lowered]
        unnamed = unnamed[:MAX_SKILLS_TO_NAME]
        if not unnamed:
            return
        reason = (
            f"Your resume shows {_join(unnamed)}, but not in the advert's words. Recruiters "
            "and screening software look for the exact terms."
        )
        skills_line = next((line for line in lines if _SKILLS_LINE.match(line.text)), None)
        if skills_line:
            yield SuggestionDraft(
                kind=SuggestionKind.REWRITE,
                section="Skills",
                original=skills_line.text,
                replacement=f"{skills_line.text.rstrip(' .,;')}, {', '.join(unnamed)}",
                reason=reason,
            )
            return
        heading = next(
            (line for line in lines if line.is_heading and _SKILLS_HEADING.match(line.section)),
            None,
        )
        yield SuggestionDraft(
            kind=SuggestionKind.ADD,
            section="Skills",
            original=heading.text if heading else lines[-1].text,
            replacement=(
                _capitalise(", ".join(unnamed)) if heading else f"Skills: {', '.join(unnamed)}"
            ),
            reason=reason,
        )

    @staticmethod
    def _missing(job_title: str, job_skills: list[str], evidenced: set[str]) -> list[str]:
        """Missing skills, most prominent first; ones that merely name the job go last."""
        title_skills = find_skills(job_title)
        missing = [skill for skill in job_skills if skill not in evidenced]
        return sorted(missing, key=lambda skill: skill in title_skills)

    @staticmethod
    def _missing_skill(lines: list[_Line], missing: list[str]) -> Iterator[SuggestionDraft]:
        if not missing or not lines:
            return
        skill = missing[0]
        bullets = [
            line for line in lines if line.marker and not _NO_METRIC_SECTIONS.search(line.section)
        ]
        anchor = bullets[-1] if bullets else lines[-1]
        marker = anchor.marker if anchor.marker and not anchor.marker[0].isdigit() else "•"
        yield SuggestionDraft(
            kind=SuggestionKind.ADD,
            section=anchor.section,
            original=anchor.text,
            replacement=f"{marker} [Your experience of {skill}: where, what you did, the result]",
            reason=(
                f"The advert asks for {skill} and your resume does not show it yet. Only add "
                "this if you have real experience, from work, study, volunteering or a society."
            ),
        )
