"""robots.txt checks, cached per origin.

Follows the common convention: a missing robots.txt (4xx) allows everything, while a
server error or network failure disallows the whole site until the next run.
"""

import logging
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger(__name__)

# Given a robots.txt URL, return (status code, body).
RobotsFetcher = Callable[[str], tuple[int, str]]

_DISALLOW_ALL = ["User-agent: *", "Disallow: /"]


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class RobotsPolicy:
    def __init__(self, user_agent: str, fetch: RobotsFetcher) -> None:
        self._user_agent = user_agent
        self._fetch = fetch
        self._parsers: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        return self._parser_for(origin_of(url)).can_fetch(self._user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        delay = self._parser_for(origin_of(url)).crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None

    def _parser_for(self, origin: str) -> RobotFileParser:
        if origin not in self._parsers:
            self._parsers[origin] = self._load(origin)
        return self._parsers[origin]

    def _load(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser(f"{origin}/robots.txt")
        try:
            status, body = self._fetch(f"{origin}/robots.txt")
        except requests.RequestException as exc:
            logger.warning("robots.txt unreachable for %s (%s); not crawling it", origin, exc)
            parser.parse(_DISALLOW_ALL)
            return parser

        if status >= 500:
            parser.parse(_DISALLOW_ALL)
        elif status >= 400:
            parser.parse([])  # no rules: everything allowed
        else:
            parser.parse(body.splitlines())
        return parser
