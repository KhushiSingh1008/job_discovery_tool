"""Offline matcher: deterministic, no network, works without an API key.

Score = 80% coverage of the skills the job asks for + 20% overlap of other keywords
(so a job description without any known skill still gets a meaningful score).
"""

import re

from app.schemas import MatchEngine, MatchResult
from app.services.matching.skills import find_skills, skills_in_order

SKILL_WEIGHT = 0.8
KEYWORD_WEIGHT = 0.2
MAX_MISSING = 8

_WORD = re.compile(r"[a-z][a-z+#.-]{3,}")
_STOPWORDS = frozenset(
    {
        # common English filler
        "about", "above", "after", "again", "also", "along", "being", "below", "between",
        "both", "could", "does", "doing", "during", "each", "every", "from", "further",
        "have", "having", "here", "into", "itself", "just", "more", "most", "must", "need",
        "only", "other", "over", "same", "should", "some", "such", "than", "that", "their",
        "them", "then", "there", "these", "they", "this", "those", "through", "under",
        "until", "very", "were", "what", "when", "where", "which", "while", "will", "with",
        "within", "would", "your", "yours",
        # words every job advert uses
        "role", "work", "working", "team", "able", "experience", "including", "years",
        "year", "join", "looking", "please", "apply", "company", "candidate", "candidates",
        "opportunity",
    }
)  # fmt: skip


def _keywords(text: str) -> set[str]:
    return {w.strip(".-") for w in _WORD.findall(text.casefold())} - _STOPWORDS


class KeywordMatcher:
    def match(self, resume_text: str, job_title: str, job_text: str) -> MatchResult:
        job_skills = skills_in_order(f"{job_title}\n{job_text}")  # most prominent first
        resume_skills = find_skills(resume_text)
        matched = [skill for skill in job_skills if skill in resume_skills]
        missing = [skill for skill in job_skills if skill not in resume_skills][:MAX_MISSING]

        job_words = _keywords(f"{job_title} {job_text}")
        overlap = len(job_words & _keywords(resume_text)) / len(job_words) if job_words else 0.0
        if job_skills:
            coverage = len(matched) / len(job_skills)
            score = SKILL_WEIGHT * coverage + KEYWORD_WEIGHT * overlap
        else:
            score = overlap

        return MatchResult(
            score=round(100 * min(score, 1.0)),
            summary=self._summary(len(matched), len(job_skills)),
            matched_skills=matched,
            missing_skills=missing,
            suggestions=self._suggestions(matched, missing, job_title),
            engine=MatchEngine.KEYWORD,
        )

    @staticmethod
    def _summary(matched: int, wanted: int) -> str:
        if wanted == 0:
            return "The advert names few specific skills; the score reflects shared keywords."
        return f"Your resume shows {matched} of the {wanted} skills this job mentions."

    @staticmethod
    def _suggestions(matched: list[str], missing: list[str], job_title: str) -> list[str]:
        suggestions = [
            f"Move your strongest '{skill}' example near the top and start it with an action "
            f"verb, e.g. 'Used {skill} to [what you did], resulting in [result/number].'"
            for skill in matched[:2]
        ]
        if missing:
            suggestions.append(
                f"If you have any experience of {', '.join(missing[:3])} (coursework, "
                "volunteering, societies or part-time work), add a bullet that names it "
                "using the advert's wording."
            )
        if not suggestions:
            suggestions.append(
                f"Mirror the language of the {job_title} advert in your summary and bullets "
                "so recruiters (and screening software) can see the match."
            )
        return suggestions
