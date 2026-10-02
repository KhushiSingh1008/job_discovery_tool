"""Registry of site adapters. Add new adapters to ``ALL_SOURCES``."""

from app.scraper.sources.base import SourceAdapter

ALL_SOURCES: tuple[type[SourceAdapter], ...] = ()

REGISTRY: dict[str, type[SourceAdapter]] = {source.name: source for source in ALL_SOURCES}


def get_adapters(names: list[str] | None = None) -> list[SourceAdapter]:
    """Instantiate the named adapters (all of them when ``names`` is empty)."""
    if not names:
        return [source() for source in ALL_SOURCES]
    unknown = sorted(set(names) - REGISTRY.keys())
    if unknown:
        raise KeyError(f"Unknown source(s): {', '.join(unknown)}. Known: {sorted(REGISTRY)}")
    return [REGISTRY[name]() for name in names]
