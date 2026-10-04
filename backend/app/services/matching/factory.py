"""Choose the matching engine from configuration."""

from app.config import Settings
from app.services.llm import build_claude_client
from app.services.matching.base import Matcher
from app.services.matching.claude_matcher import ClaudeMatcher
from app.services.matching.keyword_matcher import KeywordMatcher


def build_matcher(settings: Settings) -> Matcher:
    """Claude when an API key is configured, otherwise the offline keyword matcher."""
    offline = KeywordMatcher()
    client = build_claude_client(settings)
    if client is None:
        return offline
    return ClaudeMatcher(client, settings.match_model, fallback=offline)
