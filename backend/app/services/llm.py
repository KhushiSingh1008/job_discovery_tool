"""Shared access to Claude for the resume features (match and enhance).

Claude only analyses text the student provides; it is never used to scrape or extract
listings. Every failure surfaces as ``ClaudeUnavailableError`` so callers can fall back to
their offline engine in one place.
"""

from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from app.config import Settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TOKENS = 16_000


class ClaudeUnavailableError(Exception):
    """No usable answer: API error, timeout, refusal, truncation or invalid JSON."""


def build_claude_client(settings: Settings) -> anthropic.Anthropic | None:
    """A client when an API key is configured, otherwise ``None`` (offline mode).

    Gating on an explicit key (rather than any credential the SDK could discover) keeps
    the behaviour predictable for reviewers running the app locally.
    """
    if not settings.anthropic_api_key:
        return None
    return anthropic.Anthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=settings.match_timeout,
        max_retries=1,
    )


def ask_structured[T: BaseModel](
    client: anthropic.Anthropic,
    *,
    model: str,
    system: str,
    user_message: str,
    schema: dict[str, Any],
    answer_type: type[T],
) -> T:
    """One structured-output request, validated into ``answer_type``."""
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            # On a policy decline the API retries on a suitable model within the same call.
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": schema},
            },
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIStatusError as exc:  # 4xx/5xx after the SDK's own retries
        raise ClaudeUnavailableError(f"HTTP {exc.status_code} ({exc.message})") from exc
    except anthropic.APIConnectionError as exc:  # network error or timeout
        raise ClaudeUnavailableError(f"unreachable: {exc}") from exc

    if response.stop_reason != "end_turn":
        raise ClaudeUnavailableError(f"stop_reason={response.stop_reason}")
    text = next((block.text for block in response.content if block.type == "text"), None)
    if text is None:
        raise ClaudeUnavailableError("no text block in response")
    try:
        return answer_type.model_validate_json(text)
    except ValidationError as exc:
        raise ClaudeUnavailableError(f"invalid JSON answer: {exc}") from exc
