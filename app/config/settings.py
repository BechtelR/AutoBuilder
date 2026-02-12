"""Pydantic Settings for AutoBuilder configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    db_url: str = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"

    model_config = {
        "env_prefix": "AUTOBUILDER_",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
