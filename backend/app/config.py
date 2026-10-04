"""Application settings, loaded from environment variables (prefix ``GG_``) or ``.env``."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GG_",
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
    )

    database_path: Path = BACKEND_DIR / "data" / "jobs.db"

    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    )
    scraper_min_delay: float = 1.5
    scraper_max_delay: float = 3.5
    scraper_timeout: float = 20.0
    scraper_max_retries: int = 3
    # Detail pages read this recently are not downloaded again (just marked as still listed).
    scraper_refresh_days: float = 3
    # Listings no scrape has seen for this long are closed, whatever their source.
    listing_stale_days: int = 30
    # In-process schedule (production): scrape every N hours; 0 turns the scheduler off.
    scrape_interval_hours: float = 0
    scrape_start_delay_seconds: int = 60

    # Production: serve the built frontend from this folder (same origin as the API).
    static_dir: Path | None = None
    # Per-IP limit on the resume endpoints (AI calls and file parsing cost money and CPU).
    resume_requests_per_hour: int = 30

    ghost_job_days: int = 45
    reminder_silence_days: int = 7

    # NoDecode: read "a,b" from the environment as written instead of requiring JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # SecretStr keeps the key out of reprs, logs and tracebacks.
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "GG_ANTHROPIC_API_KEY"),
    )
    match_model: str = "claude-opus-5-5"
    match_timeout: float = 60.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def resolved_database_path(self) -> Path:
        """Relative paths are resolved against ``backend/`` so the CLI and API agree."""
        path = self.database_path
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
