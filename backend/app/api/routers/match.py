"""Resume vs job match (feature 3)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbConn, resume_rate_limit
from app.api.job_target import resolve_job
from app.config import get_settings
from app.schemas import MatchRequest, MatchResult
from app.services.matching.base import Matcher
from app.services.matching.factory import build_matcher

router = APIRouter(prefix="/api/match", tags=["match"])


def get_matcher() -> Matcher:
    return build_matcher(get_settings())


@router.post("", response_model=MatchResult, dependencies=[Depends(resume_rate_limit)])
def match_resume(
    data: MatchRequest, db: DbConn, matcher: Annotated[Matcher, Depends(get_matcher)]
) -> MatchResult:
    title, job_text = resolve_job(db, data)
    return matcher.match(data.resume_text, title, job_text)
