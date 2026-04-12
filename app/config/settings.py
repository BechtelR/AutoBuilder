"""Pydantic Settings for AutoBuilder configuration."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from arq.connections import RedisSettings
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    db_url: str = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"

    default_code_model: str = "anthropic/claude-sonnet-4-6"
    default_plan_model: str = "anthropic/claude-opus-4-6"
    default_review_model: str = "anthropic/claude-sonnet-4-6"
    default_fast_model: str = "anthropic/claude-haiku-4-5-20251001"

    workflows_dir: Path = Path.home() / ".autobuilder" / "workflows"

    @field_validator("workflows_dir")
    @classmethod
    def _expand_workflows_dir(cls, v: Path) -> Path:
        return v.expanduser()

    search_provider: str = "tavily"
    context_budget_threshold: int = 80

    default_retry_budget: int = 10
    default_cost_ceiling: float = 100.0
    director_queue_interval: int = 60

    @field_validator("context_budget_threshold")
    @classmethod
    def _validate_threshold(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("context_budget_threshold must be between 0 and 100")
        return v

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
