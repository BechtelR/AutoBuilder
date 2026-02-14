"""Tests for health endpoint."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.gateway.deps import get_db_session, get_redis
from app.gateway.main import create_app
from tests.conftest import TEST_DB_URL


@pytest_asyncio.fixture
async def degraded_db_client(
    redis_client: Redis,  # type: ignore[type-arg]
) -> AsyncIterator[AsyncClient]:
    """Client with broken DB for degraded-postgres health tests.

    Requires PostgreSQL running (for Redis fixture) but points DB at a
    nonexistent database to trigger the degraded-postgres path.
    """
    app = create_app()
    broken_url = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/nonexistent_db_xyz"
    broken_engine = create_async_engine(broken_url)
    factory = async_sessionmaker(broken_engine, class_=AsyncSession)

    async def broken_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    def override_redis() -> Redis:  # type: ignore[type-arg]
        return redis_client

    app.dependency_overrides[get_db_session] = broken_db_session
    app.dependency_overrides[get_redis] = override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    await broken_engine.dispose()


@pytest_asyncio.fixture
async def degraded_redis_client(
    engine: object,  # noqa: ARG001 -- ensures tables exist
) -> AsyncIterator[AsyncClient]:
    """Client with broken Redis for degraded-redis health tests."""
    app = create_app()
    eng = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    broken_redis: Redis = Redis.from_url("redis://localhost:9999")  # type: ignore[type-arg]

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis] = lambda: broken_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    await broken_redis.aclose()
    await eng.dispose()


@pytest_asyncio.fixture
async def degraded_both_client() -> AsyncIterator[AsyncClient]:
    """Client with both DB and Redis broken."""
    app = create_app()
    broken_url = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/nonexistent_db_xyz"
    broken_engine = create_async_engine(broken_url)
    factory = async_sessionmaker(broken_engine, class_=AsyncSession)

    async def broken_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    broken_redis: Redis = Redis.from_url("redis://localhost:9999")  # type: ignore[type-arg]

    app.dependency_overrides[get_db_session] = broken_db_session
    app.dependency_overrides[get_redis] = lambda: broken_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    await broken_redis.aclose()
    await broken_engine.dispose()


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_ok(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["services"]["postgres"] == "ok"
        assert data["services"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_degraded_db(self, degraded_db_client: AsyncClient) -> None:
        """Requires Redis running (DB intentionally broken)."""
        response = await degraded_db_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "unavailable"
        assert data["services"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_degraded_redis(self, degraded_redis_client: AsyncClient) -> None:
        """Requires PostgreSQL running (Redis intentionally broken)."""
        response = await degraded_redis_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "ok"
        assert data["services"]["redis"] == "unavailable"

    @pytest.mark.asyncio
    async def test_health_both_degraded(self, degraded_both_client: AsyncClient) -> None:
        """No infra needed — both services intentionally broken."""
        response = await degraded_both_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "unavailable"
        assert data["services"]["redis"] == "unavailable"
