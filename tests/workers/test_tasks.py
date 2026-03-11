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
@require_llm
class TestRunDirectorTurnIntegration:
    """Integration tests for run_director_turn with real infrastructure + LLM."""

    @pytest.mark.asyncio
    async def test_director_turn_stores_response(self) -> None:
        """Send a message to the Director and verify the response is persisted."""
        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Create chat + user message
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

            # Build worker context
            settings = get_settings()
            session_service = create_session_service(TEST_DB_URL)
            router = LlmRouter.from_settings(settings)

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
            }

            result = await run_director_turn(ctx, chat_id, message_id)
            assert result["status"] == "completed"
            assert result["chat_id"] == chat_id

            # Verify Director response was persisted
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


class TestRunWorkflowDeliverablePipeline:
    """Unit tests for deliverable pipeline code path in run_workflow."""

    @pytest.mark.asyncio
    async def test_deliverable_pipeline_triggers_new_path(self) -> None:
        """Verify pipeline_type=deliverable triggers create_deliverable_pipeline_from_context."""
        from google.adk.agents import SequentialAgent

        # Build a minimal mock pipeline (SequentialAgent with no real sub_agents)
        mock_pipeline = SequentialAgent(name="mock_pipeline", sub_agents=[])

        mock_session_service = MagicMock()
        mock_router = MagicMock(spec=LlmRouter)
        mock_router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock()

        mock_factory = MagicMock()
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock workflow DB record
        mock_workflow = MagicMock()
        mock_workflow.params = {
            "pipeline_type": "deliverable",
            "prompt": "Build something",
        }
        mock_workflow.status = WorkflowStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_workflow)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()

        ctx: dict[str, object] = {
            "session_service": mock_session_service,
            "llm_router": mock_router,
            "redis": mock_redis,
            "db_session_factory": mock_factory,
        }

        with (
            patch(
                "app.workers.tasks.create_deliverable_pipeline_from_context",
                return_value=mock_pipeline,
            ) as mock_create,
            patch("app.workers.tasks.create_app_container") as mock_app,
            patch("app.workers.tasks.create_runner") as mock_runner,
        ):
            # Make runner.run_async return empty async iterator
            mock_runner_instance = MagicMock()

            async def empty_iter(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
                return
                yield  # type: ignore[misc]  # pragma: no cover

            mock_runner_instance.run_async = empty_iter
            mock_runner.return_value = mock_runner_instance
            mock_app.return_value = MagicMock()

            mock_session_obj = MagicMock()
            mock_session_obj.id = "test-session-id"
            mock_session_service.get_session = AsyncMock(return_value=mock_session_obj)

            workflow_id = str(uuid.uuid4())
            result = await run_workflow(ctx, workflow_id)

        assert mock_create.called
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_context_recreation_caught_not_reraised(self) -> None:
        """Verify ContextRecreationRequired is caught and logged, not re-raised.

        Phase 5a: log and continue. Phase 5b: trigger recreation pipeline.
        """
        from app.agents.context_monitor import ContextRecreationRequired

        mock_session_service = MagicMock()
        mock_router = MagicMock(spec=LlmRouter)
        mock_router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock()

        mock_factory = MagicMock()
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_workflow = MagicMock()
        mock_workflow.params = {
            "pipeline_type": "deliverable",
            "prompt": "Build something",
        }
        mock_workflow.status = WorkflowStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_workflow)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()

        ctx: dict[str, object] = {
            "session_service": mock_session_service,
            "llm_router": mock_router,
            "redis": mock_redis,
            "db_session_factory": mock_factory,
        }

        err = ContextRecreationRequired(usage_pct=85.0, model="test-model", threshold_pct=80.0)

        with patch(
            "app.workers.tasks.create_deliverable_pipeline_from_context",
            side_effect=err,
        ):
            workflow_id = str(uuid.uuid4())
            # ContextRecreationRequired is caught and logged; workflow completes
            result = await run_workflow(ctx, workflow_id)
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_echo_pipeline_still_works(self) -> None:
        """Verify existing echo pipeline is backward compatible (no pipeline_type)."""
        mock_session_service = MagicMock()
        mock_router = MagicMock(spec=LlmRouter)
        mock_router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock()

        mock_factory = MagicMock()
        mock_db_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # No pipeline_type in params means echo
        mock_workflow = MagicMock()
        mock_workflow.params = {"prompt": "Hello"}
        mock_workflow.status = WorkflowStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_workflow)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()

        ctx: dict[str, object] = {
            "session_service": mock_session_service,
            "llm_router": mock_router,
            "redis": mock_redis,
            "db_session_factory": mock_factory,
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

            mock_session_obj = MagicMock()
            mock_session_obj.id = "test-session-id"
            mock_session_service.get_session = AsyncMock(return_value=mock_session_obj)

            workflow_id = str(uuid.uuid4())
            result = await run_workflow(ctx, workflow_id)

        # echo path should use create_echo_agent
        assert mock_echo.called
        assert result["status"] == "completed"
