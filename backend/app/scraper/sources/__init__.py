"""Registry of site adapters. Add new adapters to ``ALL_SOURCES``."""

from app.scraper.sources.base import SourceAdapter
from app.scraper.sources.cambridge import CambridgeAdapter
from app.scraper.sources.greenhouse import GreenhouseAdapter
from app.scraper.sources.studentjob import StudentJobAdapter

ALL_SOURCES: tuple[type[SourceAdapter], ...] = (
    CambridgeAdapter,
    StudentJobAdapter,
    GreenhouseAdapter,
)

REGISTRY: dict[str, type[SourceAdapter]] = {source.name: source for source in ALL_SOURCES}


def get_adapters(names: list[str] | None = None) -> list[SourceAdapter]:
    """Instantiate the named adapters (all of them when ``names`` is empty)."""
    if not names:
        return [source() for source in ALL_SOURCES]
    unknown = sorted(set(names) - REGISTRY.keys())
    if unknown:
        raise KeyError(f"Unknown source(s): {', '.join(unknown)}. Known: {sorted(REGISTRY)}")
    return [REGISTRY[name]() for name in names]
