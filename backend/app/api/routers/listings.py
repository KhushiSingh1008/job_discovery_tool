"""Job listings: search, filter, sort and detail."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbConn, Now
from app.models import EligibilityTag, JobType, Listing
from app.repositories.listings import ListingRepository, ListingSearch
from app.schemas import ListingPage, SortOrder

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=ListingPage)
def search_listings(
    db: DbConn,
    now: Now,
    q: Annotated[str | None, Query(max_length=200, description="Words to match")] = None,
    job_type: Annotated[list[JobType] | None, Query()] = None,
    location: Annotated[str | None, Query(max_length=100)] = None,
    min_pay: Annotated[float | None, Query(ge=0, description="Minimum £/hour")] = None,
    min_trust: Annotated[int | None, Query(ge=0, le=100)] = None,
    eligibility: Annotated[list[EligibilityTag] | None, Query()] = None,
    posted_within_days: Annotated[int | None, Query(ge=1, le=365)] = None,
    source: Annotated[str | None, Query(max_length=50)] = None,
    sort: SortOrder = SortOrder.NEWEST,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListingPage:
    search = ListingSearch(
        q=q,
        job_types=job_type or [],
        location=location,
        min_pay=min_pay,
        min_trust=min_trust,
        eligibility=eligibility or [],
        posted_since=(now - timedelta(days=posted_within_days)).date()
        if posted_within_days
        else None,
        source=source,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    items, total = ListingRepository(db).search(search)
    return ListingPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{listing_id}", response_model=Listing)
def get_listing(listing_id: str, db: DbConn) -> Listing:
    listing = ListingRepository(db).get(listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing
