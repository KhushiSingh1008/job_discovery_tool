"""Health, filter options and rule tables."""

from fastapi import APIRouter

from app.api.deps import DbConn
from app.repositories.listings import ListingRepository
from app.rules import VisaRules, load_visa_rules
from app.schemas import FilterFacets

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health(db: DbConn) -> dict[str, object]:
    return {"status": "ok", "listings": ListingRepository(db).count()}


@router.get("/meta/filters", response_model=FilterFacets)
def filter_options(db: DbConn) -> FilterFacets:
    return ListingRepository(db).facets()


@router.get("/visa-rules", response_model=VisaRules)
def visa_rules() -> VisaRules:
    return load_visa_rules()
