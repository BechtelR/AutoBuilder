"""Tests for ARQ worker tasks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings, parse_redis_settings
from app.db.models import Base, Chat, ChatMessage, Workflow
from app.events.streams import stream_key
from app.lib import NotFoundError
from app.models.enums import ChatMessageRole, ChatStatus, ChatType, ModelRole, WorkflowStatus
from app.router import LlmRouter
from app.workers.adk import create_session_service
from app.workers.tasks import heartbeat, run_director_turn, run_workflow
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
                    ModelRole.CODE: "invalid/nonexistent-model",
                    ModelRole.PLAN: "invalid/nonexistent-model",
                    ModelRole.REVIEW: "invalid/nonexistent-model",
                    ModelRole.FAST: "invalid/nonexistent-model",
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


@require_infra
class TestRunDirectorTurnIntegration:
    """Integration tests for run_director_turn with real infrastructure."""

    @pytest.mark.asyncio
    async def test_director_turn_stores_response(self) -> None:
        """Verify Director turn persists a response via mocked ADK runner."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            session_service = create_session_service(TEST_DB_URL)

            # Create chat + user message in real DB
            chat_id = str(uuid.uuid4())
            message_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            async with factory() as session:
                chat = Chat(
                    id=uuid.UUID(chat_id),
                    session_id=session_id,
                    type=ChatType.DIRECTOR,
                    status=ChatStatus.ACTIVE,
                )
                session.add(chat)
                await session.flush()

                user_msg = ChatMessage(
                    id=uuid.UUID(message_id),
                    chat_id=uuid.UUID(chat_id),
                    role=ChatMessageRole.USER,
                    content="Hello Director, what can you help me with?",
                )
                session.add(user_msg)
                await session.commit()

            settings = get_settings()
            router = LlmRouter.from_settings(settings)

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            # Mock the ADK runner to return a text response
            mock_event = MagicMock()
            mock_event.content = MagicMock()
            mock_part = MagicMock()
            mock_part.text = "Hello! I can help you with project management."
            mock_event.content.parts = [mock_part]

            async def mock_run_async(**kwargs: object):  # type: ignore[no-untyped-def]
                yield mock_event

            with (
                patch("app.workers.tasks.build_chat_session_agent") as mock_build,
                patch("app.workers.tasks.create_app_container"),
                patch("app.workers.tasks.create_runner") as mock_runner_factory,
                patch("app.agents.formation.ensure_formation_state", new_callable=AsyncMock),
            ):
                mock_build.return_value = MagicMock()
                mock_runner = MagicMock()
                mock_runner.run_async = mock_run_async
                mock_runner_factory.return_value = mock_runner

                result = await run_director_turn(ctx, chat_id, message_id)
                assert result["status"] == "completed"
                assert result["id"] == chat_id

            # Verify Director response was persisted in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.chat_id == chat_id)  # type: ignore[reportArgumentType]
                    .where(ChatMessage.role == ChatMessageRole.DIRECTOR)
                )
                director_msg = db_result.scalar_one_or_none()
                assert director_msg is not None
                assert len(director_msg.content) > 0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()


@require_infra
class TestRunWorkflowDeliverablePipeline:
    """Integration tests for deliverable pipeline code path in run_workflow."""

    @pytest.mark.asyncio
    async def test_deliverable_pipeline_triggers_new_path(self) -> None:
        """Verify pipeline_type=deliverable triggers create_workflow_pipeline."""
        from google.adk.agents import SequentialAgent

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            session_service = create_session_service(TEST_DB_URL)

            # Create real Workflow record
            workflow_id = str(uuid.uuid4())
            async with factory() as session:
                workflow = Workflow(
                    id=uuid.UUID(workflow_id),
                    workflow_type="deliverable",
                    status=WorkflowStatus.PENDING,
                    params={
                        "pipeline_type": "deliverable",
                        "prompt": "Build something",
                    },
                )
                session.add(workflow)
                await session.commit()

            router = MagicMock(spec=LlmRouter)
            router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            mock_pipeline = SequentialAgent(name="mock_pipeline", sub_agents=[])

            with (
                patch(
                    "app.workers.tasks.create_workflow_pipeline",
                    new_callable=AsyncMock,
                    return_value=mock_pipeline,
                ) as mock_create,
                patch("app.workers.tasks.create_app_container") as mock_app,
                patch("app.workers.tasks.create_runner") as mock_runner,
            ):
                mock_runner_instance = MagicMock()

                async def empty_iter(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
                    return
                    yield  # type: ignore[misc]  # pragma: no cover

                mock_runner_instance.run_async = empty_iter
                mock_runner.return_value = mock_runner_instance
                mock_app.return_value = MagicMock()

                result = await run_workflow(ctx, workflow_id)

            assert mock_create.called
            assert result["status"] == "completed"

            # Verify workflow status updated in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(Workflow).where(
                        Workflow.id == workflow_id  # type: ignore[reportArgumentType]
                    )
                )
                wf = db_result.scalar_one()
                assert wf.status == WorkflowStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_context_recreation_caught_not_reraised(self) -> None:
        """Verify ContextRecreationRequired triggers recreation pipeline, not re-raised.

        Phase 5b: catches ContextRecreationRequired, runs recreate_context, completes.
        """
        from app.agents.context_monitor import ContextRecreationRequired

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            session_service = create_session_service(TEST_DB_URL)

            # Create real Workflow record
            workflow_id = str(uuid.uuid4())
            async with factory() as session:
                workflow = Workflow(
                    id=uuid.UUID(workflow_id),
                    workflow_type="deliverable",
                    status=WorkflowStatus.PENDING,
                    params={
                        "pipeline_type": "deliverable",
                        "prompt": "Build something",
                    },
                )
                session.add(workflow)
                await session.commit()

            router = MagicMock(spec=LlmRouter)
            router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            err = ContextRecreationRequired(usage_pct=85.0, model="test-model", threshold_pct=80.0)

            with (
                patch(
                    "app.workers.tasks.create_workflow_pipeline",
                    new_callable=AsyncMock,
                    side_effect=err,
                ),
                patch(
                    "app.agents.context_recreation.recreate_context",
                    new_callable=AsyncMock,
                ) as mock_recreate,
            ):
                mock_recreate.return_value = MagicMock(
                    new_session_id="new-session-id",
                    remaining_stages=[],
                )
                result = await run_workflow(ctx, workflow_id)
                assert result["status"] == "completed"
                assert mock_recreate.called

            # Verify workflow completed in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(Workflow).where(
                        Workflow.id == workflow_id  # type: ignore[reportArgumentType]
                    )
                )
                wf = db_result.scalar_one()
                assert wf.status == WorkflowStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_echo_pipeline_still_works(self) -> None:
        """Verify existing echo pipeline is backward compatible (no pipeline_type)."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            session_service = create_session_service(TEST_DB_URL)

            # Create real Workflow record (no pipeline_type = echo path)
            workflow_id = str(uuid.uuid4())
            async with factory() as session:
                workflow = Workflow(
                    id=uuid.UUID(workflow_id),
                    workflow_type="echo",
                    status=WorkflowStatus.PENDING,
                    params={"prompt": "Hello"},
                )
                session.add(workflow)
                await session.commit()

            router = MagicMock(spec=LlmRouter)
            router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            with (
                patch("app.workers.tasks.create_echo_agent") as mock_echo,
                patch("app.workers.tasks.create_app_container") as mock_app,
                patch("app.workers.tasks.create_runner") as mock_runner,
            ):
                mock_runner_instance = MagicMock()

                async def empty_iter(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
                    return
                    yield  # type: ignore[misc]  # pragma: no cover

                mock_runner_instance.run_async = empty_iter
                mock_runner.return_value = mock_runner_instance
                mock_app.return_value = MagicMock()

                result = await run_workflow(ctx, workflow_id)

            # echo path should use create_echo_agent
            assert mock_echo.called
            assert result["status"] == "completed"

            # Verify workflow completed in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(Workflow).where(
                        Workflow.id == workflow_id  # type: ignore[reportArgumentType]
                    )
                )
                wf = db_result.scalar_one()
                assert wf.status == WorkflowStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.aclose()
