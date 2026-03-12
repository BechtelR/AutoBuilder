"""FastAPI dependency injection functions."""

from collections.abc import AsyncIterator

from arq.connections import ArqRedis
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.skills.library import SkillLibrary


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession from the app's session factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:  # type: ignore[type-arg]
    """Return the Redis client from app.state (ArqRedis is a Redis superset)."""
    result: Redis = request.app.state.arq_pool  # type: ignore[type-arg]
    return result


def get_arq_pool(request: Request) -> ArqRedis:
    """Return the ArqRedis pool from app.state."""
    pool: ArqRedis = request.app.state.arq_pool
    return pool


def get_skill_library(request: Request) -> SkillLibrary:
    """Return the shared SkillLibrary instance from app.state."""
    library: SkillLibrary = request.app.state.skill_library
    return library
