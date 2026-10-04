"""Health, filter options and rule tables."""

from fastapi import APIRouter

from app.api.deps import DbConn
from app.repositories.listings import ListingRepository
from app.repositories.scrape_runs import ScrapeRunRepository
from app.rules import VisaRules, load_visa_rules
from app.schemas import FilterFacets, SourceHealth
from app.scraper.sources import ALL_SOURCES

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health(db: DbConn) -> dict[str, object]:
    runs = ScrapeRunRepository(db).latest_by_source().values()
    last_scraped = max((run.finished_at for run in runs), default=None)
    return {
        "status": "ok",
        "listings": ListingRepository(db).count(),
        "last_scraped_at": last_scraped.isoformat() if last_scraped else None,
    }


@router.get("/meta/sources", response_model=list[SourceHealth])
def sources(db: DbConn) -> list[SourceHealth]:
    """Each scraper source with its open listings and how its last run went."""
    open_counts = ListingRepository(db).open_counts_by_source()
    latest = ScrapeRunRepository(db).latest_by_source()
    return [
        SourceHealth(
            name=source.name,
            label=source.label,
            open_listings=open_counts.get(source.name, 0),
            last_run=latest.get(source.name),
        )
        for source in ALL_SOURCES
    ]


@router.get("/meta/filters", response_model=FilterFacets)
def filter_options(db: DbConn) -> FilterFacets:
    return ListingRepository(db).facets()


@router.get("/visa-rules", response_model=VisaRules)
def visa_rules() -> VisaRules:
    return load_visa_rules()
