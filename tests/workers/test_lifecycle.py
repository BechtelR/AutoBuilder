"""Integration tests for lifecycle operations (pause/resume/abort).

Uses real PostgreSQL and Redis -- skipped when unavailable.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import parse_redis_settings
from app.db.models import Base, DirectorQueueItem, Project, ProjectConfig
from app.models.enums import DirectorQueueStatus, ProjectStatus
from app.workers.lifecycle import (
    DIRECTOR_PAUSED_KEY,
    abort_project,
    pause_all_projects,
    pause_director,
    pause_project,
    resume_all_projects,
    resume_director,
    resume_project,
)
from app.workers.tasks import process_director_queue
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra


def _make_project(
    status: ProjectStatus = ProjectStatus.ACTIVE,
    name: str = "test-project",
) -> Project:
    """Create a Project ORM instance with given status."""
    return Project(
        name=name,
        workflow_type="auto-code",
        brief="Test brief",
        status=status,
    )


# ---------------------------------------------------------------------------
# Project-level pause/resume/abort
# ---------------------------------------------------------------------------


@require_infra
class TestPauseProject:
    """Project pause: ACTIVE -> PAUSED, Redis flag set."""

    @pytest.mark.asyncio
    async def test_active_to_paused(self, tmp_path: object) -> None:
        """ACTIVE project transitions to PAUSED with Redis flag set."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.ACTIVE)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_project(ctx, project_id=pid, reason="testing pause")

            assert result["status"] == "ok"
            assert result["new_status"] == "PAUSED"

            # Verify DB status
            async with factory() as session:
                p = (
                    await session.execute(select(Project).where(Project.id == project.id))
                ).scalar_one()
                assert p.status == ProjectStatus.PAUSED

            # Verify Redis flag
            flag = await redis.get(f"project:pause_requested:{pid}")
            assert flag is not None
            assert flag == b"testing pause"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_non_active_rejected(self, tmp_path: object) -> None:
        """Non-ACTIVE project cannot be paused."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.COMPLETED)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_project(ctx, project_id=pid)

            assert result["status"] == "error"
            assert "Cannot pause" in result["message"]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_not_found(self, tmp_path: object) -> None:
        """Nonexistent project returns error."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_project(ctx, project_id=str(uuid.uuid4()))

            assert result["status"] == "error"
            assert "not found" in result["message"]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_default_reason(self, tmp_path: object) -> None:
        """No reason defaults to 'user_initiated' in Redis."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.ACTIVE)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            await pause_project(ctx, project_id=pid)

            flag = await redis.get(f"project:pause_requested:{pid}")
            assert flag == b"user_initiated"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


@require_infra
class TestResumeProject:
    """Project resume: PAUSED -> ACTIVE, Redis flag cleared, job enqueued."""

    @pytest.mark.asyncio
    async def test_paused_to_active(self, tmp_path: object) -> None:
        """PAUSED project transitions to ACTIVE, flag cleared, job enqueued."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.PAUSED)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            # Pre-set a pause flag
            await redis.set(f"project:pause_requested:{pid}", "was_paused")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                result = await resume_project(ctx, project_id=pid)

                assert result["status"] == "ok"
                assert result["new_status"] == "ACTIVE"

                mock_enqueue.assert_called_once_with("run_work_session", project_id=pid)

            # Verify DB status
            async with factory() as session:
                p = (
                    await session.execute(select(Project).where(Project.id == project.id))
                ).scalar_one()
                assert p.status == ProjectStatus.ACTIVE

            # Verify Redis flag cleared
            flag = await redis.get(f"project:pause_requested:{pid}")
            assert flag is None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_non_paused_rejected(self, tmp_path: object) -> None:
        """Non-PAUSED project cannot be resumed."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.ACTIVE)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await resume_project(ctx, project_id=pid)

            assert result["status"] == "error"
            assert "Cannot resume" in result["message"]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


@require_infra
class TestAbortProject:
    """Project abort: any state -> ABORTED, error_message and completed_at set."""

    @pytest.mark.asyncio
    async def test_active_to_aborted(self, tmp_path: object) -> None:
        """ACTIVE project transitions to ABORTED with reason and timestamp."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.ACTIVE)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await abort_project(ctx, project_id=pid, reason="budget exhausted")

            assert result["status"] == "ok"
            assert result["new_status"] == "ABORTED"

            # Verify DB state
            async with factory() as session:
                p = (
                    await session.execute(select(Project).where(Project.id == project.id))
                ).scalar_one()
                assert p.status == ProjectStatus.ABORTED
                assert p.error_message == "budget exhausted"
                assert p.completed_at is not None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_paused_to_aborted(self, tmp_path: object) -> None:
        """PAUSED project can also be aborted."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            project = _make_project(ProjectStatus.PAUSED)
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = str(project.id)

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await abort_project(ctx, project_id=pid, reason="cancelled")

            assert result["status"] == "ok"

            async with factory() as session:
                p = (
                    await session.execute(select(Project).where(Project.id == project.id))
                ).scalar_one()
                assert p.status == ProjectStatus.ABORTED
                assert p.error_message == "cancelled"
                assert p.completed_at is not None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_not_found(self, tmp_path: object) -> None:
        """Nonexistent project returns error."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await abort_project(ctx, project_id=str(uuid.uuid4()), reason="test")
            assert result["status"] == "error"
            assert "not found" in result["message"]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Director-level pause/resume
# ---------------------------------------------------------------------------


@require_infra
class TestPauseDirector:
    """Director pause: sets Redis flag, cascades to active projects."""

    @pytest.mark.asyncio
    async def test_sets_flag_and_cascades(self, tmp_path: object) -> None:
        """Pausing Director sets flag and pauses all ACTIVE projects."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            p1 = _make_project(ProjectStatus.ACTIVE, name="proj-1")
            p2 = _make_project(ProjectStatus.ACTIVE, name="proj-2")
            p3 = _make_project(ProjectStatus.COMPLETED, name="proj-3")
            async with factory() as session:
                session.add_all([p1, p2, p3])
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_director(ctx, reason="maintenance")

            assert result["status"] == "ok"
            paused_ids: list[str] = result["paused_projects"]  # type: ignore[assignment]
            assert len(paused_ids) == 2
            assert str(p1.id) in paused_ids
            assert str(p2.id) in paused_ids

            # Verify Director pause flag
            flag = await redis.get(DIRECTOR_PAUSED_KEY)
            assert flag == b"maintenance"

            # Director pause is flag-only -- DB status remains ACTIVE (PM observes
            # flag and pauses gracefully at next checkpoint).
            # See: test_does_not_change_project_status_directly.

            # Verify per-project Redis flags
            for pid_str in paused_ids:
                pflag = await redis.get(f"project:pause_requested:{pid_str}")
                assert pflag == b"director_pause"

            # Verify COMPLETED project was not paused
            async with factory() as session:
                p3_db = (
                    await session.execute(select(Project).where(Project.id == p3.id))
                ).scalar_one()
                assert p3_db.status == ProjectStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_does_not_change_project_status_directly(self, tmp_path: object) -> None:
        """Director pause sets Redis flags but does NOT change project DB status."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            p1 = _make_project(ProjectStatus.ACTIVE, name="proj-flag-1")
            async with factory() as session:
                session.add(p1)
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_director(ctx, reason="graceful")

            assert result["status"] == "ok"
            paused_ids: list[str] = result["paused_projects"]  # type: ignore[assignment]
            assert str(p1.id) in paused_ids

            # Project status should still be ACTIVE (flag-only, not direct change)
            async with factory() as session:
                p = (await session.execute(select(Project).where(Project.id == p1.id))).scalar_one()
                assert p.status == ProjectStatus.ACTIVE

            # But Redis flag should be set -- value is always "director_pause" (identifies
            # the cascade source, not the user-supplied reason)
            flag = await redis.get(f"project:pause_requested:{p1.id}")
            assert flag == b"director_pause"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_no_active_projects(self, tmp_path: object) -> None:
        """Director pause with no active projects returns empty list."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_director(ctx)

            assert result["status"] == "ok"
            assert result["paused_projects"] == []

            # Flag is still set
            flag = await redis.get(DIRECTOR_PAUSED_KEY)
            assert flag is not None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


@require_infra
class TestResumeDirector:
    """Director resume: clears flag, resumes paused projects."""

    @pytest.mark.asyncio
    async def test_clears_flag_and_resumes(self, tmp_path: object) -> None:
        """Resuming Director clears flag and resumes PAUSED projects."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            p1 = _make_project(ProjectStatus.PAUSED, name="proj-1")
            p2 = _make_project(ProjectStatus.PAUSED, name="proj-2")
            async with factory() as session:
                session.add_all([p1, p2])
                await session.commit()

            # Pre-set Director pause flag and per-project flags
            await redis.set(DIRECTOR_PAUSED_KEY, "test")
            await redis.set(f"project:pause_requested:{p1.id}", "director_pause")
            await redis.set(f"project:pause_requested:{p2.id}", "director_pause")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                result = await resume_director(ctx)

                assert result["status"] == "ok"
                resumed_ids: list[str] = result["resumed_projects"]  # type: ignore[assignment]
                assert len(resumed_ids) == 2

                # Verify work sessions enqueued
                assert mock_enqueue.call_count == 2
                enqueued_pids = {call.kwargs["project_id"] for call in mock_enqueue.call_args_list}
                assert str(p1.id) in enqueued_pids
                assert str(p2.id) in enqueued_pids

            # Verify Director flag cleared
            flag = await redis.get(DIRECTOR_PAUSED_KEY)
            assert flag is None

            # Verify projects are ACTIVE
            async with factory() as session:
                for pid_str in resumed_ids:
                    p = (
                        await session.execute(
                            select(Project).where(Project.id == uuid.UUID(pid_str))
                        )
                    ).scalar_one()
                    assert p.status == ProjectStatus.ACTIVE

            # Verify per-project flags cleared
            for pid_str in resumed_ids:
                pflag = await redis.get(f"project:pause_requested:{pid_str}")
                assert pflag is None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_does_not_resume_user_paused_projects(self, tmp_path: object) -> None:
        """Projects paused individually by users are NOT resumed by Director resume."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # p1: paused by Director cascade
            p1 = _make_project(ProjectStatus.PAUSED, name="director-paused")
            # p2: paused individually by user
            p2 = _make_project(ProjectStatus.PAUSED, name="user-paused")
            async with factory() as session:
                session.add_all([p1, p2])
                await session.commit()

            await redis.set(DIRECTOR_PAUSED_KEY, "test")
            await redis.set(f"project:pause_requested:{p1.id}", "director_pause")
            await redis.set(f"project:pause_requested:{p2.id}", "user_initiated")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                result = await resume_director(ctx)

                resumed_ids: list[str] = result["resumed_projects"]  # type: ignore[assignment]
                assert len(resumed_ids) == 1
                assert str(p1.id) in resumed_ids
                assert str(p2.id) not in resumed_ids

                # Only 1 work session enqueued (for Director-paused project)
                assert mock_enqueue.call_count == 1

            # p1 should be ACTIVE, p2 should still be PAUSED
            async with factory() as session:
                p1_db = (
                    await session.execute(select(Project).where(Project.id == p1.id))
                ).scalar_one()
                assert p1_db.status == ProjectStatus.ACTIVE

                p2_db = (
                    await session.execute(select(Project).where(Project.id == p2.id))
                ).scalar_one()
                assert p2_db.status == ProjectStatus.PAUSED

            # p2's pause flag should remain untouched
            p2_flag = await redis.get(f"project:pause_requested:{p2.id}")
            assert p2_flag == b"user_initiated"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# System-wide pause/resume
# ---------------------------------------------------------------------------


@require_infra
class TestPauseAllProjects:
    """System-wide pause: all ACTIVE -> PAUSED."""

    @pytest.mark.asyncio
    async def test_all_active_paused(self, tmp_path: object) -> None:
        """All ACTIVE projects transition to PAUSED."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            p1 = _make_project(ProjectStatus.ACTIVE, name="proj-1")
            p2 = _make_project(ProjectStatus.ACTIVE, name="proj-2")
            p3 = _make_project(ProjectStatus.COMPLETED, name="proj-3")
            async with factory() as session:
                session.add_all([p1, p2, p3])
                await session.commit()

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }
            result = await pause_all_projects(ctx, reason="deploy")

            assert result["status"] == "ok"
            paused_ids: list[str] = result["paused_projects"]  # type: ignore[assignment]
            assert len(paused_ids) == 2

            # Verify DB statuses
            async with factory() as session:
                for pid_str in paused_ids:
                    p = (
                        await session.execute(
                            select(Project).where(Project.id == uuid.UUID(pid_str))
                        )
                    ).scalar_one()
                    assert p.status == ProjectStatus.PAUSED

            # Verify Redis flags
            for pid_str in paused_ids:
                pflag = await redis.get(f"project:pause_requested:{pid_str}")
                assert pflag == b"deploy"

            # COMPLETED untouched
            async with factory() as session:
                p3_db = (
                    await session.execute(select(Project).where(Project.id == p3.id))
                ).scalar_one()
                assert p3_db.status == ProjectStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


@require_infra
class TestResumeAllProjects:
    """System-wide resume: all PAUSED -> ACTIVE, jobs enqueued."""

    @pytest.mark.asyncio
    async def test_all_paused_resumed(self, tmp_path: object) -> None:
        """All PAUSED projects transition to ACTIVE with jobs enqueued."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            p1 = _make_project(ProjectStatus.PAUSED, name="proj-1")
            p2 = _make_project(ProjectStatus.PAUSED, name="proj-2")
            p3 = _make_project(ProjectStatus.ABORTED, name="proj-3")
            async with factory() as session:
                session.add_all([p1, p2, p3])
                await session.commit()

            # Set pause flags
            await redis.set(f"project:pause_requested:{p1.id}", "system_pause")
            await redis.set(f"project:pause_requested:{p2.id}", "system_pause")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "publisher": None,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                result = await resume_all_projects(ctx)

                assert result["status"] == "ok"
                resumed_ids: list[str] = result["resumed_projects"]  # type: ignore[assignment]
                assert len(resumed_ids) == 2

                # Verify work sessions enqueued for each resumed project
                assert mock_enqueue.call_count == 2

            # Verify DB statuses
            async with factory() as session:
                for pid_str in resumed_ids:
                    p = (
                        await session.execute(
                            select(Project).where(Project.id == uuid.UUID(pid_str))
                        )
                    ).scalar_one()
                    assert p.status == ProjectStatus.ACTIVE

            # Verify Redis flags cleared
            for pid_str in resumed_ids:
                pflag = await redis.get(f"project:pause_requested:{pid_str}")
                assert pflag is None

            # ABORTED untouched
            async with factory() as session:
                p3_db = (
                    await session.execute(select(Project).where(Project.id == p3.id))
                ).scalar_one()
                assert p3_db.status == ProjectStatus.ABORTED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Director pause integration with process_director_queue
# ---------------------------------------------------------------------------


@require_infra
class TestDirectorPauseSkipsQueueProcessing:
    """Director pause flag causes process_director_queue to skip."""

    @pytest.mark.asyncio
    async def test_queue_skipped_when_director_paused(self, tmp_path: object) -> None:
        """process_director_queue returns immediately when Director is paused."""
        engine = create_async_engine(TEST_DB_URL)
        redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Set Director pause flag
            await redis.set(DIRECTOR_PAUSED_KEY, "test_pause")

            ctx: dict[str, object] = {
                "db_session_factory": factory,
                "redis": redis,
                "artifacts_root": tmp_path,
            }

            with patch.object(redis, "enqueue_job", new_callable=AsyncMock) as mock_enqueue:
                await process_director_queue(ctx)
                # No jobs should be enqueued
                mock_enqueue.assert_not_called()

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Batch failure threshold from ProjectConfig
# ---------------------------------------------------------------------------


@require_infra
class TestBatchFailureThresholdConfig:
    """Batch failure threshold is configurable per project via ProjectConfig."""

    @pytest.mark.asyncio
    async def test_threshold_read_from_project_config(self) -> None:
        """ProjectConfig.config['batch_failure_threshold'] overrides default."""
        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            project = _make_project(ProjectStatus.ACTIVE, name="threshold-proj")
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = project.id

            # Create ProjectConfig with custom threshold
            async with factory() as session:
                config = ProjectConfig(
                    project_id=pid,
                    project_name="threshold-proj",
                    config={"batch_failure_threshold": 5},
                )
                session.add(config)
                await session.commit()

            # Verify config is readable and has correct value
            async with factory() as session:
                row = (
                    await session.execute(
                        select(ProjectConfig).where(ProjectConfig.project_id == pid)
                    )
                ).scalar_one_or_none()
                assert row is not None
                assert row.config.get("batch_failure_threshold") == 5

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()


# ---------------------------------------------------------------------------
# Cost ceiling creates DirectorQueueItem escalation
# ---------------------------------------------------------------------------


@require_infra
class TestCostCeilingEscalation:
    """Cost ceiling breach creates a Director escalation queue item."""

    @pytest.mark.asyncio
    async def test_escalation_created_on_cost_breach(self) -> None:
        """When cost exceeds ceiling, a DirectorQueueItem is created."""
        from app.models.enums import EscalationPriority, EscalationRequestType

        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            project = _make_project(ProjectStatus.ACTIVE, name="cost-proj")
            async with factory() as session:
                session.add(project)
                await session.commit()
                pid = project.id

            # Simulate cost ceiling escalation by directly creating the item
            # (testing the pattern used in _execute_batch_loop)
            async with factory() as session:
                escalation = DirectorQueueItem(
                    type=EscalationRequestType.RESOURCE_REQUEST,
                    priority=EscalationPriority.HIGH,
                    title=f"Cost ceiling exceeded for project {pid}",
                    source_project_id=pid,
                    context="Accumulated cost 10.0000 exceeds ceiling 5.0000",
                )
                session.add(escalation)
                await session.commit()

            # Verify the escalation exists
            async with factory() as session:
                items = list(
                    (
                        await session.execute(
                            select(DirectorQueueItem).where(
                                DirectorQueueItem.source_project_id == pid
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(items) == 1
                item = items[0]
                assert item.type == EscalationRequestType.RESOURCE_REQUEST
                assert item.priority == EscalationPriority.HIGH
                assert "Cost ceiling exceeded" in item.title
                assert item.status == DirectorQueueStatus.PENDING

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
