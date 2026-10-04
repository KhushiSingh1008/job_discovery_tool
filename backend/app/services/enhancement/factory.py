"""Choose the resume-enhancement engine from configuration."""

from app.config import Settings
from app.services.enhancement.base import Enhancer
from app.services.enhancement.claude_enhancer import ClaudeEnhancer
from app.services.enhancement.rules import RuleBasedEnhancer
from app.services.llm import build_claude_client


def build_enhancer(settings: Settings) -> Enhancer:
    """Claude when an API key is configured, otherwise the offline rules."""
    offline = RuleBasedEnhancer()
    client = build_claude_client(settings)
    if client is None:
        return offline
    return ClaudeEnhancer(client, settings.match_model, fallback=offline)
