"""Whitespace and HTML clean-up helpers."""

import html
import re

from bs4 import BeautifulSoup

_WHITESPACE = re.compile(r"\s+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_text(value: str | None) -> str:
    """Unescape entities and collapse all whitespace to single spaces."""
    if not value:
        return ""
    return _WHITESPACE.sub(" ", html.unescape(value)).strip()


def html_to_text(markup: str | None) -> str:
    """Convert an HTML fragment (possibly entity-escaped) into readable plain text."""
    if not markup:
        return ""
    # Some sites double-escape descriptions inside JSON-LD (&lt;p&gt;...).
    unescaped = html.unescape(markup)
    text = BeautifulSoup(unescaped, "lxml").get_text("\n")
    lines = (_WHITESPACE.sub(" ", line).strip() for line in text.splitlines())
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
