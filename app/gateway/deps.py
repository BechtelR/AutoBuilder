"""FastAPI dependency injection functions."""

from collections.abc import AsyncIterator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession from the app's session factory."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:  # type: ignore[type-arg]
    """Return the Redis client from app.state."""
    result: Redis = request.app.state.redis  # type: ignore[type-arg]
    return result
