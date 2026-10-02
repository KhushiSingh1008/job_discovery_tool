"""The matcher interface shared by every engine."""

from typing import Protocol

from app.schemas import MatchResult


class Matcher(Protocol):
    def match(self, resume_text: str, job_title: str, job_text: str) -> MatchResult: ...
