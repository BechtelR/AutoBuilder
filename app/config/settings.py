"""Pydantic Settings for AutoBuilder configuration."""

from functools import lru_cache
from urllib.parse import urlparse

from arq.connections import RedisSettings
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    db_url: str = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"

    default_code_model: str = "anthropic/claude-sonnet-4-5-20250929"
    default_plan_model: str = "anthropic/claude-opus-4-6"
    default_review_model: str = "anthropic/claude-sonnet-4-5-20250929"
    default_fast_model: str = "anthropic/claude-haiku-4-5-20251001"

    model_config = {
        "env_prefix": "AUTOBUILDER_",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()


def parse_redis_settings(redis_url: str) -> RedisSettings:
    """Parse a Redis URL into ARQ RedisSettings."""
    parsed = urlparse(redis_url)
    database = 0
    if parsed.path and parsed.path.strip("/").isdigit():
        database = int(parsed.path.strip("/"))
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        username=parsed.username,
    )
