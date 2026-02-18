"""Tests for ARQ worker tasks."""

import uuid

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings, parse_redis_settings
from app.db.models import Base, Workflow
from app.events.streams import stream_key
from app.lib import NotFoundError
from app.models.enums import TaskType, WorkflowStatus
from app.router import LlmRouter
from app.workers.adk import create_session_service
from app.workers.tasks import heartbeat, run_workflow
from app.workers.tasks import test_task as worker_test_task
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra, require_llm


class TestTestTask:
    @pytest.mark.asyncio
    async def test_returns_completed_status(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "hello")
        assert result == {"status": "completed", "payload": "hello"}

    @pytest.mark.asyncio
    async def test_returns_payload(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "world")
        assert result["payload"] == "world"

    @pytest.mark.asyncio
    async def test_status_is_completed(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "anything")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_empty_payload(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "")
        assert result == {"status": "completed", "payload": ""}


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_runs_without_error(self) -> None:
        ctx: dict[str, object] = {}
        # Should not raise
        result = await heartbeat(ctx)
        assert result is None


@require_infra
@require_llm
class TestRunWorkflowIntegration:
    """Integration tests for run_workflow with real PostgreSQL, Redis, and LLM."""

    @pytest.mark.asyncio
    async def test_run_workflow_completes(self) -> None:
        """Create a real Workflow, run it through ADK, verify COMPLETED status and events."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            # Create tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Create workflow record
            workflow_id = str(uuid.uuid4())
            async with factory() as session:
                workflow = Workflow(
                    id=uuid.UUID(workflow_id),
                    workflow_type="echo",
                    status=WorkflowStatus.PENDING,
                    params={"prompt": "Say hello"},
                )
                session.add(workflow)
                await session.commit()

            # Build ctx dict (mimics worker startup)
            settings = get_settings()
            session_service = create_session_service(TEST_DB_URL)
            router = LlmRouter.from_settings(settings)

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            # Execute the workflow
            result = await run_workflow(ctx, workflow_id)
            assert result["status"] == "completed"
            assert result["workflow_id"] == workflow_id

            # Verify workflow record is COMPLETED
            async with factory() as session:
                db_result = await session.execute(
                    select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
                )
                wf = db_result.scalar_one()
                assert wf.status == WorkflowStatus.COMPLETED
                assert wf.started_at is not None
                assert wf.completed_at is not None

            # Verify events exist in Redis Stream
            raw_events: list[  # type: ignore[reportUnknownVariableType]
                tuple[bytes, dict[bytes, bytes]]
            ] = await redis.xrange(stream_key(workflow_id))  # type: ignore[reportUnknownMemberType]
            assert len(raw_events) > 0  # type: ignore[reportUnknownArgumentType]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_run_workflow_not_found(self) -> None:
        """Calling run_workflow with a non-existent UUID raises NotFoundError."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            session_service = create_session_service(TEST_DB_URL)
            settings = get_settings()
            router = LlmRouter.from_settings(settings)

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            fake_id = str(uuid.uuid4())
            with pytest.raises(NotFoundError):
                await run_workflow(ctx, fake_id)

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_run_workflow_error_sets_message(self) -> None:
        """A broken LlmRouter model causes FAILED status with error_message set."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Create workflow record
            workflow_id = str(uuid.uuid4())
            async with factory() as session:
                workflow = Workflow(
                    id=uuid.UUID(workflow_id),
                    workflow_type="echo",
                    status=WorkflowStatus.PENDING,
                    params={"prompt": "This should fail"},
                )
                session.add(workflow)
                await session.commit()

            # Build ctx with a broken router (invalid model string)
            session_service = create_session_service(TEST_DB_URL)
            broken_router = LlmRouter(
                defaults={
                    TaskType.CODE: "invalid/nonexistent-model",
                    TaskType.PLAN: "invalid/nonexistent-model",
                    TaskType.REVIEW: "invalid/nonexistent-model",
                    TaskType.FAST: "invalid/nonexistent-model",
                }
            )

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": broken_router,
                "redis": redis,
                "db_session_factory": factory,
            }

            # The workflow should raise but update status to FAILED.
            # We catch BaseException because LiteLLM raises various error types
            # for invalid model strings; the specific type is not guaranteed.
            raised = False
            try:
                await run_workflow(ctx, workflow_id)
            except Exception:
                raised = True
            assert raised, "Expected run_workflow to raise for invalid model"

            # Verify workflow record is FAILED with error_message
            async with factory() as session:
                db_result = await session.execute(
                    select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
                )
                wf = db_result.scalar_one()
                assert wf.status == WorkflowStatus.FAILED
                assert wf.error_message is not None
                assert len(wf.error_message) > 0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()
