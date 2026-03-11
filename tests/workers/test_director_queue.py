"""Integration tests for process_director_queue cron task.

Uses real PostgreSQL and Redis — skipped when unavailable.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import parse_redis_settings
from app.db.models import Base, DirectorQueueItem
from app.models.enums import (
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
)
from app.workers.tasks import process_director_queue
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra

_WORK_SESSION_KEY_PREFIX = "director:work_session:"


def _make_queue_item(project_id: uuid.UUID) -> DirectorQueueItem:
    """Create a PENDING DirectorQueueItem for the given project."""
    return DirectorQueueItem(
        type=EscalationRequestType.ESCALATION,
        priority=EscalationPriority.NORMAL,
        status=DirectorQueueStatus.PENDING,
        title="Test escalation",
        source_project_id=project_id,
        source_agent="test",
        context="test context",
    )


@require_infra
class TestProcessDirectorQueue:
    """Integration tests for process_director_queue with real PostgreSQL and Redis."""

    @pytest.mark.asyncio
    async def test_empty_queue_no_jobs(self) -> None:
        """No pending items -> no jobs enqueued."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            ctx: dict[str, object] = {"db_session_factory": factory, "redis": redis}

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)
                mock_enqueue.assert_not_called()

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_pending_items_idle_project_enqueues(self) -> None:
        """Pending item, no active session -> enqueues run_director_turn."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid = uuid.uuid4()

            # Insert a real PENDING queue item
            async with factory() as session:
                session.add(_make_queue_item(pid))
                await session.commit()

            ctx: dict[str, object] = {"db_session_factory": factory, "redis": redis}

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)

                mock_enqueue.assert_called_once()
                call_args = mock_enqueue.call_args
                assert call_args[0][0] == "run_director_turn"
                assert call_args[1]["project_id"] == str(pid)
                assert call_args[1]["_queue_name"] == "arq:queue"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_pending_items_active_session_skipped(self) -> None:
        """Pending item, active work session -> skipped."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid = uuid.uuid4()

            async with factory() as session:
                session.add(_make_queue_item(pid))
                await session.commit()

            # Set the active work session key in real Redis
            await redis.set(f"{_WORK_SESSION_KEY_PREFIX}{pid}", "1")

            ctx: dict[str, object] = {"db_session_factory": factory, "redis": redis}

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)
                mock_enqueue.assert_not_called()

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_multiple_projects_mixed(self) -> None:
        """Multiple projects: idle ones enqueued, active ones skipped."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            idle_1 = uuid.uuid4()
            active_1 = uuid.uuid4()
            idle_2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_queue_item(idle_1))
                session.add(_make_queue_item(active_1))
                session.add(_make_queue_item(idle_2))
                await session.commit()

            # Mark one project as having an active session
            await redis.set(f"{_WORK_SESSION_KEY_PREFIX}{active_1}", "1")

            ctx: dict[str, object] = {"db_session_factory": factory, "redis": redis}

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)

                assert mock_enqueue.call_count == 2
                enqueued_pids = {call[1]["project_id"] for call in mock_enqueue.call_args_list}
                assert str(idle_1) in enqueued_pids
                assert str(idle_2) in enqueued_pids
                assert str(active_1) not in enqueued_pids

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()
