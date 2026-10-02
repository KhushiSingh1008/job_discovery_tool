"""Resume vs job match (feature 3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbConn
from app.config import get_settings
from app.repositories.listings import ListingRepository
from app.schemas import MatchRequest, MatchResult
from app.services.matching.base import Matcher
from app.services.matching.factory import build_matcher

router = APIRouter(prefix="/api/match", tags=["match"])


def get_matcher() -> Matcher:
    return build_matcher(get_settings())


@router.post("", response_model=MatchResult)
def match_resume(
    data: MatchRequest, db: DbConn, matcher: Annotated[Matcher, Depends(get_matcher)]
) -> MatchResult:
    if data.listing_id is not None:
        listing = ListingRepository(db).get(data.listing_id)
        if listing is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
        title, job_text = listing.title, f"{listing.employer}\n{listing.description}"
    else:
        title, job_text = "this role", data.job_description or ""
    return matcher.match(data.resume_text, title, job_text)
