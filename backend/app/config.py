"""Application settings, loaded from environment variables (prefix ``GG_``) or ``.env``."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    ghost_job_days: int = 45
    reminder_silence_days: int = 7

    cors_origins: list[str] = ["http://localhost:5173"]

    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "GG_ANTHROPIC_API_KEY"),
    )
    match_model: str = "claude-opus-5-5"
    match_timeout: float = 60.0

    def resolved_database_path(self) -> Path:
        """Relative paths are resolved against ``backend/`` so the CLI and API agree."""
        path = self.database_path
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
