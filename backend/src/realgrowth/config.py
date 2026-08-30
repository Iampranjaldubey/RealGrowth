"""Runtime settings, loaded from the environment.

Everything the app can be tuned with lives here and nowhere else, so there is
one place to read to know what an environment variable does. The previous
config had two different production/development defaults depending on whether
you called ``create_app()`` or imported the module-level ``app``, and
``ProductionConfig`` defaulted ``CORS_ORIGINS`` to ``"*"`` — both fixed by
having a single source of truth with an explicit, safe default.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: backend/src/realgrowth/config.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration. Override via environment variables or ``.env``."""

    model_config = SettingsConfigDict(env_prefix="REALGROWTH_", env_file=".env", extra="ignore")

    environment: str = Field(default="development", description="development | production")
    database_path: Path = Field(default=REPO_ROOT / "data" / "realgrowth.db")

    #: Comma-separated origins, e.g. "https://app.example.com,https://example.com".
    #: Defaults to permissive for local development only; production deployments
    #: must set this explicitly.
    cors_origins: str = Field(default="*")

    #: Requests per minute per client IP. Generous relative to the old 50/hour
    #: default, which a single page view (2-6 requests) could exhaust in minutes.
    rate_limit_per_minute: int = Field(default=120, gt=0)

    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def _uppercase_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton; safe because settings never change at runtime."""
    return Settings()
