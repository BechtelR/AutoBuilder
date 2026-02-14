"""Shared test fixtures and factories."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.gateway.deps import get_db_session, get_redis
from app.gateway.main import create_app


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock AsyncSession for testing."""
    session = AsyncMock()
    # Mock execute to return a result with .scalar() == 1
    result = MagicMock()
    result.scalar.return_value = 1
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client for testing."""
    redis = AsyncMock()
    redis.ping.return_value = True
    return redis


@pytest.fixture
async def test_client(
    mock_db_session: AsyncMock,
    mock_redis: AsyncMock,
) -> AsyncIterator[AsyncClient]:
    """AsyncClient with mocked dependencies for gateway testing."""
    app = create_app()

    async def override_db_session() -> AsyncIterator[AsyncMock]:
        yield mock_db_session

    async def override_redis() -> AsyncMock:
        return mock_redis

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis] = override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
