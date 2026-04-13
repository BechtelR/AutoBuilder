"""Shared test fixtures and factories.

Infrastructure-aware: tests that need PostgreSQL or Redis are skipped with a
clear message when the service is unreachable, rather than failing or mocking.
"""

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any os.environ checks (API keys, config)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import asyncpg  # type: ignore[import-untyped]  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from arq.connections import ArqRedis, create_pool  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import parse_redis_settings  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.gateway.deps import get_db_session, get_redis  # noqa: E402
from app.gateway.main import create_app  # noqa: E402

TEST_DB_URL = "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder_test"
TEST_REDIS_URL = "redis://localhost:6379/1"  # DB 1 to isolate from dev

# ---------------------------------------------------------------------------
# Infrastructure availability probes
# ---------------------------------------------------------------------------

_INFRA_HINT = "Run `docker compose up -d` to start infrastructure."


def _probe_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


_pg_available: bool = _probe_tcp("localhost", 5432)
_redis_available: bool = _probe_tcp("localhost", 6379)
_llm_available: bool = bool(os.environ.get("ANTHROPIC_API_KEY"))

require_postgres = pytest.mark.skipif(
    not _pg_available,
    reason=f"PostgreSQL is not running on localhost:5432. {_INFRA_HINT}",
)
require_redis = pytest.mark.skipif(
    not _redis_available,
    reason=f"Redis is not running on localhost:6379. {_INFRA_HINT}",
)
require_infra = pytest.mark.skipif(
    not (_pg_available and _redis_available),
    reason=f"PostgreSQL and/or Redis not running. {_INFRA_HINT}",
)
require_llm = pytest.mark.skipif(
    not _llm_available,
    reason="ANTHROPIC_API_KEY not set. Set it to run LLM integration tests.",
)


# ---------------------------------------------------------------------------
# Session banner — loud warning when infrastructure is missing
# ---------------------------------------------------------------------------


def pytest_report_header() -> list[str]:
    """Print infrastructure status at the top of every test run."""
    lines: list[str] = []
    missing: list[str] = []
    if not _pg_available:
        missing.append("PostgreSQL (localhost:5432)")
    if not _redis_available:
        missing.append("Redis (localhost:6379)")
    if missing:
        services = ", ".join(missing)
        lines.extend(
            [
                "",
                f"  *** INFRASTRUCTURE UNAVAILABLE: {services} ***",
                f"  *** Tests requiring these services will be SKIPPED. {_INFRA_HINT} ***",
                "",
            ]
        )
    if not _llm_available:
        lines.extend(
            [
                "",
                "  *** LLM UNAVAILABLE: ANTHROPIC_API_KEY not set ***",
                "  *** Tests requiring LLM will be SKIPPED. ***",
                "",
            ]
        )
    return lines


# ---------------------------------------------------------------------------
# Database bootstrap (only when PostgreSQL is available)
# ---------------------------------------------------------------------------


def pytest_configure(config: object) -> None:
    """Create the test database if it doesn't exist."""
    if not _pg_available:
        return

    async def _create_test_db() -> None:
        conn = await asyncpg.connect(  # type: ignore[reportUnknownMemberType]
            "postgresql://autobuilder:autobuilder@localhost:5432/autobuilder"
        )
        try:
            await conn.execute(  # type: ignore[reportUnknownMemberType]
                "CREATE DATABASE autobuilder_test"
            )
        except asyncpg.DuplicateDatabaseError:
            pass
        finally:
            await conn.close()  # type: ignore[reportUnknownMemberType]

    asyncio.run(_create_test_db())


# ---------------------------------------------------------------------------
# Fixtures — each skips when its infrastructure is unavailable
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create async engine, ensure tables exist, truncate between tests.

    Uses TRUNCATE instead of DROP/CREATE SCHEMA for speed — schema is created
    once and reused.  Tables are truncated in teardown for isolation.
    """
    if not _pg_available:
        pytest.skip(f"PostgreSQL is not running on localhost:5432. {_INFRA_HINT}")
    eng = create_async_engine(TEST_DB_URL)
    # Ensure schema + tables exist (idempotent — fast if already present)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    # Truncate all tables in one statement for isolation
    table_names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with eng.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    await eng.dispose()


@pytest_asyncio.fixture
async def async_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a real AsyncSession for DB testing."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:  # type: ignore[type-arg]
    """Yield a real Redis client for testing."""
    if not _redis_available:
        pytest.skip(f"Redis is not running on localhost:6379. {_INFRA_HINT}")
    client: Redis = Redis.from_url(TEST_REDIS_URL)  # type: ignore[type-arg]
    yield client
    await client.flushdb()  # type: ignore[reportUnknownMemberType]
    await client.aclose()


@pytest_asyncio.fixture
async def test_client(
    engine: AsyncEngine,
    redis_client: Redis,  # type: ignore[type-arg]
) -> AsyncIterator[AsyncClient]:
    """AsyncClient with real DB and Redis dependencies."""
    app = create_app()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create ArqRedis pool for job enqueueing
    arq_pool: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    def override_redis() -> Redis:  # type: ignore[type-arg]
        return redis_client

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis] = override_redis

    # Set arq_pool on app.state
    app.state.arq_pool = arq_pool

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    # Clean up ArqRedis pool
    await arq_pool.aclose()
