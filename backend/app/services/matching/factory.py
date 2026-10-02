"""Choose the matching engine from configuration."""

import anthropic

from app.config import Settings
from app.services.matching.base import Matcher
from app.services.matching.claude_matcher import ClaudeMatcher
from app.services.matching.keyword_matcher import KeywordMatcher


def build_matcher(settings: Settings) -> Matcher:
    """Claude when an API key is configured, otherwise the offline keyword matcher.

    Gating on an explicit key (rather than any credential the SDK could discover) keeps
    the behaviour predictable for reviewers running the app locally.
    """
    offline = KeywordMatcher()
    if not settings.anthropic_api_key:
        return offline
    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.match_timeout,
        max_retries=1,
    )
    return ClaudeMatcher(client, settings.match_model, fallback=offline)
