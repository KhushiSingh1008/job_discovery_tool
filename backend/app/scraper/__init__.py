"""Our own job scraper: fetch pages, parse HTML, structure listings.

Pipeline: discover -> fetch -> extract (JSON-LD first, CSS fallback) -> normalise -> store.
"""
