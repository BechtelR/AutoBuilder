"""Integration tests for process_director_queue cron task.

Uses real PostgreSQL and Redis — skipped when unavailable.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import parse_redis_settings
from app.db.models import Base, CeoQueueItem, DirectorQueueItem, Project
from app.models.enums import (
    CeoItemType,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    ProjectStatus,
)
from app.workers.tasks import (
    _create_pattern_alert,  # type: ignore[reportPrivateUsage]
    _detect_cross_project_patterns,  # type: ignore[reportPrivateUsage]
    process_director_queue,
)
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra

_WORK_SESSION_KEY_PREFIX = "director:work_session:"


def _make_project(project_id: uuid.UUID) -> Project:
    """Create a minimal Project row to satisfy FK constraints on director_queue."""
    return Project(
        id=project_id,
        name=f"test-project-{project_id}",
        workflow_type="default",
        brief="Test brief",
        status=ProjectStatus.ACTIVE,
    )


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
    async def test_empty_queue_no_jobs(self, tmp_path: object) -> None:
        """No pending items -> no jobs enqueued."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)
                mock_enqueue.assert_not_called()

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_pending_items_idle_project_enqueues(self, tmp_path: object) -> None:
        """Pending item, no active session -> enqueues run_director_turn."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid = uuid.uuid4()

            # Insert a real Project row first (FK constraint), then a PENDING queue item
            async with factory() as session:
                session.add(_make_project(pid))
                await session.flush()
                session.add(_make_queue_item(pid))
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

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
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_pending_items_active_session_skipped(self, tmp_path: object) -> None:
        """Pending item, active work session -> skipped."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid))
                await session.flush()
                session.add(_make_queue_item(pid))
                await session.commit()

            # Set the active work session key in real Redis
            await redis.set(f"{_WORK_SESSION_KEY_PREFIX}{pid}", "1")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)
                mock_enqueue.assert_not_called()

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_multiple_projects_mixed(self, tmp_path: object) -> None:
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
                session.add(_make_project(idle_1))
                session.add(_make_project(active_1))
                session.add(_make_project(idle_2))
                await session.flush()
                session.add(_make_queue_item(idle_1))
                session.add(_make_queue_item(active_1))
                session.add(_make_queue_item(idle_2))
                await session.commit()

            # Mark one project as having an active session
            await redis.set(f"{_WORK_SESSION_KEY_PREFIX}{active_1}", "1")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

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
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Cross-project pattern detection tests
# ---------------------------------------------------------------------------


def _make_typed_queue_item(
    project_id: uuid.UUID,
    escalation_type: EscalationRequestType = EscalationRequestType.ESCALATION,
) -> DirectorQueueItem:
    """Create a PENDING DirectorQueueItem with a specific escalation type."""
    return DirectorQueueItem(
        type=escalation_type,
        priority=EscalationPriority.NORMAL,
        status=DirectorQueueStatus.PENDING,
        title=f"Escalation from {project_id}",
        source_project_id=project_id,
        source_agent="pm",
        context=f"Context for {escalation_type.value}",
    )


@require_infra
class TestDetectCrossProjectPatterns:
    """Integration tests for _detect_cross_project_patterns with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_no_items_returns_empty(self) -> None:
        """No DirectorQueueItems -> no patterns."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            patterns = await _detect_cross_project_patterns(factory)
            assert patterns == []
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_single_project_no_pattern(self) -> None:
        """Items from only 1 project -> no pattern."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid))
                await session.flush()
                session.add(_make_typed_queue_item(pid, EscalationRequestType.ESCALATION))
                session.add(_make_typed_queue_item(pid, EscalationRequestType.ESCALATION))
                await session.commit()

            patterns = await _detect_cross_project_patterns(factory)
            assert patterns == []
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_two_projects_same_type_creates_pattern(self) -> None:
        """2 projects with same escalation type within window -> pattern detected."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid1 = uuid.uuid4()
            pid2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid1))
                session.add(_make_project(pid2))
                await session.flush()
                session.add(_make_typed_queue_item(pid1, EscalationRequestType.RESOURCE_REQUEST))
                session.add(_make_typed_queue_item(pid2, EscalationRequestType.RESOURCE_REQUEST))
                await session.commit()

            patterns = await _detect_cross_project_patterns(factory)
            assert len(patterns) == 1
            assert patterns[0]["type"] == EscalationRequestType.RESOURCE_REQUEST.value
            assert patterns[0]["project_count"] == 2
            assert str(pid1) in patterns[0]["project_ids"]  # type: ignore[operator]
            assert str(pid2) in patterns[0]["project_ids"]  # type: ignore[operator]
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_old_items_outside_window_excluded(self) -> None:
        """Items older than the window are excluded from pattern detection."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid1 = uuid.uuid4()
            pid2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid1))
                session.add(_make_project(pid2))
                await session.flush()
                item1 = _make_typed_queue_item(pid1, EscalationRequestType.ESCALATION)
                item2 = _make_typed_queue_item(pid2, EscalationRequestType.ESCALATION)
                session.add(item1)
                session.add(item2)
                await session.flush()

                # Push item2's created_at to 2 hours ago (outside default 1h window)
                await session.execute(
                    update(DirectorQueueItem)
                    .where(DirectorQueueItem.id == item2.id)
                    .values(created_at=datetime.now(UTC) - timedelta(hours=2))
                )
                await session.commit()

            patterns = await _detect_cross_project_patterns(factory, window_hours=1.0)
            assert patterns == []
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_resolved_items_excluded(self) -> None:
        """Items with non-PENDING status are excluded."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid1 = uuid.uuid4()
            pid2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid1))
                session.add(_make_project(pid2))
                await session.flush()
                item1 = _make_typed_queue_item(pid1, EscalationRequestType.ESCALATION)
                item2 = _make_typed_queue_item(pid2, EscalationRequestType.ESCALATION)
                item2.status = DirectorQueueStatus.RESOLVED
                session.add(item1)
                session.add(item2)
                await session.commit()

            patterns = await _detect_cross_project_patterns(factory)
            assert patterns == []
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()


@require_infra
class TestCreatePatternAlert:
    """Integration tests for _create_pattern_alert with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_creates_ceo_queue_item(self) -> None:
        """Pattern alert creates a CeoQueueItem with correct attributes."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pattern: dict[str, object] = {
                "type": "RESOURCE_REQUEST",
                "project_count": 3,
                "project_ids": [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
            }

            await _create_pattern_alert(factory, pattern)

            async with factory() as session:
                result = await session.execute(select(CeoQueueItem))
                items = list(result.scalars().all())
                assert len(items) == 1
                item = items[0]
                assert item.type == CeoItemType.NOTIFICATION
                assert item.priority == EscalationPriority.HIGH
                assert "RESOURCE_REQUEST" in item.title
                assert "3 projects" in item.title
                assert item.metadata_["pattern_type"] == "RESOURCE_REQUEST"
                assert item.metadata_["project_count"] == 3
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_deduplicates_alerts(self) -> None:
        """Second call with same pattern type does not create a duplicate."""
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pattern: dict[str, object] = {
                "type": "ESCALATION",
                "project_count": 2,
                "project_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            }

            await _create_pattern_alert(factory, pattern)
            await _create_pattern_alert(factory, pattern)  # Should be deduplicated

            async with factory() as session:
                result = await session.execute(
                    select(CeoQueueItem).where(CeoQueueItem.type == CeoItemType.NOTIFICATION)
                )
                items = list(result.scalars().all())
                assert len(items) == 1
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()


@require_infra
class TestProcessDirectorQueuePatternDetection:
    """Verify process_director_queue runs cross-project pattern detection."""

    @pytest.mark.asyncio
    async def test_pattern_alert_created_during_queue_processing(self, tmp_path: object) -> None:
        """When 2+ projects have same escalation type, CEO alert is created."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid1 = uuid.uuid4()
            pid2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid1))
                session.add(_make_project(pid2))
                await session.flush()
                session.add(_make_typed_queue_item(pid1, EscalationRequestType.RESOURCE_REQUEST))
                session.add(_make_typed_queue_item(pid2, EscalationRequestType.RESOURCE_REQUEST))
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock):
                await process_director_queue(ctx)

            # Verify CeoQueueItem was created for the pattern
            async with factory() as session:
                result = await session.execute(
                    select(CeoQueueItem).where(CeoQueueItem.type == CeoItemType.NOTIFICATION)
                )
                items = list(result.scalars().all())
                assert len(items) == 1
                assert "RESOURCE_REQUEST" in items[0].title
                assert items[0].priority == EscalationPriority.HIGH

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_no_pattern_when_different_types(self, tmp_path: object) -> None:
        """Different escalation types from different projects -> no pattern."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            pid1 = uuid.uuid4()
            pid2 = uuid.uuid4()

            async with factory() as session:
                session.add(_make_project(pid1))
                session.add(_make_project(pid2))
                await session.flush()
                session.add(_make_typed_queue_item(pid1, EscalationRequestType.ESCALATION))
                session.add(_make_typed_queue_item(pid2, EscalationRequestType.RESOURCE_REQUEST))
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock):
                await process_director_queue(ctx)

            # No CeoQueueItem should be created
            async with factory() as session:
                result = await session.execute(
                    select(CeoQueueItem).where(CeoQueueItem.type == CeoItemType.NOTIFICATION)
                )
                items = list(result.scalars().all())
                assert len(items) == 0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()
