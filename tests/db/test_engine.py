"""Tests for database engine and session factory."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db import async_session_factory, create_engine


class TestCreateEngine:
    def test_returns_async_engine(self) -> None:
        engine = create_engine("postgresql+asyncpg://user:pass@localhost/test")
        assert isinstance(engine, AsyncEngine)

    def test_engine_url_contains_driver(self) -> None:
        url = "postgresql+asyncpg://user:pass@localhost/test"
        engine = create_engine(url)
        assert engine.url.drivername == "postgresql+asyncpg"
        assert engine.url.host == "localhost"
        assert engine.url.database == "test"


class TestAsyncSessionFactory:
    def test_returns_sessionmaker(self) -> None:
        engine = create_engine("postgresql+asyncpg://user:pass@localhost/test")
        factory = async_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)

    def test_factory_is_callable(self) -> None:
        engine = create_engine("postgresql+asyncpg://user:pass@localhost/test")
        factory = async_session_factory(engine)
        assert callable(factory)


class TestRealDatabaseSession:
    @pytest.mark.asyncio
    async def test_session_executes_query(self, async_session: AsyncSession) -> None:
        """Verify a real session can execute a query against PostgreSQL."""
        result = await async_session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1
