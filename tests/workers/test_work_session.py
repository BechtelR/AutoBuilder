"""Tests for run_work_session task and work session agent builders.

Integration tests use real PostgreSQL and Redis; ADK/LLM components are mocked.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings, parse_redis_settings
from app.db.models import (
    Base,
    Deliverable,
    Project,
    ProjectConfig,
    StageExecution,
    TaskGroupExecution,
    Workflow,
)
from app.db.models import ValidatorResult as ValidatorResultModel
from app.events.publisher import EventPublisher
from app.models.enums import (
    DeliverableStatus,
    FormationStatus,
    PipelineEventType,
    ProjectStatus,
    StageStatus,
    WorkflowStatus,
)
from app.router import LlmRouter
from app.tools._context import ToolExecutionContext, register_tool_context
from app.workers.adk import create_session_service
from app.workflows.manifest import StageDef, WorkflowManifest
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_agent(name: str = "mock_agent") -> MagicMock:
    """Create a mock ADK BaseAgent with settable attributes."""
    agent = MagicMock()
    agent.name = name
    agent.sub_agents = []
    agent.before_agent_callback = None
    agent.after_agent_callback = None
    return agent


def _make_mock_runner(events: list[object] | None = None) -> MagicMock:
    """Create a mock runner whose run_async yields given events."""
    runner = MagicMock()

    async def _run_async(**kwargs: object):  # type: ignore[no-untyped-def]
        for ev in events or []:
            yield ev

    runner.run_async = _run_async
    return runner


def _standard_patches():  # type: ignore[no-untyped-def]
    """Return dict of standard patch targets for run_work_session.

    These mock ADK-level components (external API equivalents).
    """
    return {
        "assembler": patch("app.agents.assembler.InstructionAssembler"),
        "toolset": patch("app.tools._toolset.GlobalToolset"),
        "registry_cls": patch("app.agents._registry.AgentRegistry"),
        "formation": patch(
            "app.agents.formation.ensure_formation_state",
            new_callable=AsyncMock,
            return_value=FormationStatus.COMPLETE,
        ),
        "build_agents": patch(
            "app.workers.tasks.build_work_session_agents",
            new_callable=AsyncMock,
        ),
        "create_app": patch("app.workers.tasks.create_app_container"),
        "create_runner": patch("app.workers.tasks.create_runner"),
        "pipeline_callbacks": patch("app.workers.adk.create_pipeline_callbacks"),
    }


# ---------------------------------------------------------------------------
# build_work_session_agents (unit tests — no infra needed)
# ---------------------------------------------------------------------------


class TestBuildWorkSessionAgents:
    @pytest.mark.asyncio
    async def test_builds_director_with_pm_sub_agent(self) -> None:
        """Director is root, PM is wired as sub_agent with pipeline."""
        from app.workers.adk import build_work_session_agents

        director_mock = _make_mock_agent("director")
        pm_mock = _make_mock_agent("PM_proj1")
        pipeline_mock = _make_mock_agent("deliverable_pipeline")

        registry = MagicMock()
        registry.build = MagicMock(side_effect=[director_mock, pm_mock])

        ctx = MagicMock()
        publisher = MagicMock(spec=EventPublisher)

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=pipeline_mock)

        result = await build_work_session_agents(
            registry=registry,
            ctx=ctx,
            project_id="proj1",
            publisher=publisher,
            workflow_registry=mock_wf_registry,
        )

        assert result is director_mock
        assert director_mock.sub_agents == [pm_mock]
        assert pm_mock.sub_agents == [pipeline_mock]

        # Registry called with correct args
        calls = registry.build.call_args_list
        assert calls[0].args == ("director", ctx)
        assert calls[1].args == ("PM_proj1", ctx)
        assert calls[1].kwargs == {"definition": "pm"}

    @pytest.mark.asyncio
    async def test_supervision_callbacks_wired(self) -> None:
        """PM should have before/after agent callbacks set."""
        from app.workers.adk import build_work_session_agents

        director_mock = _make_mock_agent("director")
        pm_mock = _make_mock_agent("PM_proj1")
        pipeline_mock = _make_mock_agent("deliverable_pipeline")

        registry = MagicMock()
        registry.build = MagicMock(side_effect=[director_mock, pm_mock])

        ctx = MagicMock()
        publisher = MagicMock(spec=EventPublisher)

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=pipeline_mock)

        await build_work_session_agents(
            registry=registry,
            ctx=ctx,
            project_id="proj1",
            publisher=publisher,
            workflow_registry=mock_wf_registry,
        )

        assert pm_mock.before_agent_callback is not None
        assert pm_mock.after_agent_callback is not None
        assert callable(pm_mock.before_agent_callback)
        assert callable(pm_mock.after_agent_callback)

    @pytest.mark.asyncio
    async def test_pipeline_has_checkpoint_callback(self) -> None:
        """DeliverablePipeline should have checkpoint callback wired."""
        from app.workers.adk import build_work_session_agents

        director_mock = _make_mock_agent("director")
        pm_mock = _make_mock_agent("PM_proj1")
        pipeline_mock = _make_mock_agent("deliverable_pipeline")

        registry = MagicMock()
        registry.build = MagicMock(side_effect=[director_mock, pm_mock])

        ctx = MagicMock()
        publisher = MagicMock(spec=EventPublisher)

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=pipeline_mock)

        await build_work_session_agents(
            registry=registry,
            ctx=ctx,
            project_id="proj1",
            publisher=publisher,
            workflow_registry=mock_wf_registry,
        )

        assert pipeline_mock.after_agent_callback is not None
        assert callable(pipeline_mock.after_agent_callback)


class TestBuildChatSessionAgent:
    def test_builds_director_with_no_sub_agents(self) -> None:
        """Chat session Director has no sub_agents."""
        from app.workers.adk import build_chat_session_agent

        director_mock = _make_mock_agent("director")
        registry = MagicMock()
        registry.build = MagicMock(return_value=director_mock)
        ctx = MagicMock()

        result = build_chat_session_agent(registry=registry, ctx=ctx)

        assert result is director_mock
        registry.build.assert_called_once_with("director", ctx)


# ---------------------------------------------------------------------------
# run_work_session — integration tests with real PostgreSQL + Redis
# ---------------------------------------------------------------------------


@require_infra
class TestRunWorkSession:
    """Integration tests for run_work_session with real PostgreSQL and Redis.

    Only ADK/LLM components are mocked (build_work_session_agents, create_runner,
    create_app_container, ensure_formation_state, create_pipeline_callbacks).
    """

    @pytest.mark.asyncio
    async def test_loads_project_config(self, tmp_path: object) -> None:
        """Project config loaded from DB and written to session state."""
        from app.workers.tasks import run_work_session

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

            # Insert project config with custom limits
            project_id = f"proj_{uuid.uuid4().hex[:8]}"
            async with factory() as db_session:
                pc = ProjectConfig(
                    project_name=project_id,
                    config={"retry_budget": 5, "cost_ceiling": 50.0},
                )
                db_session.add(pc)
                await db_session.commit()

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                result = await run_work_session(ctx, project_id)

            assert result["status"] == "completed"

            # Verify the session was created with correct config by checking
            # that session_service persisted it (real DatabaseSessionService)
            from app.models.constants import APP_NAME, SYSTEM_USER_ID

            session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=f"work_session_{project_id}",
            )
            assert session is not None
            state: dict[str, object] = session.state  # type: ignore[reportUnknownMemberType]
            pc_state = state["project_config"]
            assert isinstance(pc_state, dict)
            assert pc_state["retry_budget"] == 5
            assert pc_state["cost_ceiling"] == 50.0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_default_config_created(self, tmp_path: object) -> None:
        """Missing project config uses settings defaults."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                result = await run_work_session(ctx, project_id)

            assert result["status"] == "completed"

            # Verify defaults from settings
            from app.models.constants import APP_NAME, SYSTEM_USER_ID

            session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=f"work_session_{project_id}",
            )
            assert session is not None
            state: dict[str, object] = session.state  # type: ignore[reportUnknownMemberType]
            pc_state = state["project_config"]
            assert isinstance(pc_state, dict)
            assert pc_state["retry_budget"] == settings.default_retry_budget
            assert pc_state["cost_ceiling"] == settings.default_cost_ceiling

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_ensures_formation_state(self, tmp_path: object) -> None:
        """Formation state is checked on invocation."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"] as mock_formation,
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                await run_work_session(ctx, project_id)

            mock_formation.assert_awaited_once_with(session_service, "system")

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_sets_redis_key(self, tmp_path: object) -> None:
        """Active work session Redis key is set with TTL."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            # We'll check that the key was set during execution by spying on redis.set
            original_set = redis.set
            set_calls: list[tuple[object, ...]] = []

            async def _spy_set(*args: object, **kwargs: object) -> object:
                set_calls.append(args)
                return await original_set(*args, **kwargs)  # type: ignore[reportUnknownMemberType]

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
                patch.object(redis, "set", side_effect=_spy_set),
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                await run_work_session(ctx, project_id)

            expected_key = f"director:work_session:{project_id}"
            matching = [c for c in set_calls if c[0] == expected_key]
            assert len(matching) == 1
            assert matching[0][1] == f"work_session_{project_id}"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cleans_redis_key_on_completion(self, tmp_path: object) -> None:
        """Redis key is cleaned up after successful completion."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                await run_work_session(ctx, project_id)

            # After completion, the Redis key should have been deleted
            redis_key = f"director:work_session:{project_id}"
            val = await redis.get(redis_key)  # type: ignore[reportUnknownMemberType]
            assert val is None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cleans_redis_key_on_failure(self, tmp_path: object) -> None:
        """Redis key is cleaned up even when session fails."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            # Runner that raises
            failing_runner = MagicMock()

            async def _failing_run(**kwargs: object):  # type: ignore[no-untyped-def]
                raise RuntimeError("Pipeline exploded")
                yield  # type: ignore[misc]  # noqa: RUF100 — unreachable yield for async gen

            failing_runner.run_async = _failing_run

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = failing_runner
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                with pytest.raises(RuntimeError, match="Pipeline exploded"):
                    await run_work_session(ctx, project_id)

            # After failure, the Redis key should have been deleted
            redis_key = f"director:work_session:{project_id}"
            val = await redis.get(redis_key)  # type: ignore[reportUnknownMemberType]
            assert val is None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_publishes_lifecycle_events(self, tmp_path: object) -> None:
        """Started and Completed lifecycle events are published to Redis Streams."""
        from app.workers.tasks import run_work_session

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

            project_id = f"proj_{uuid.uuid4().hex[:8]}"

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            # Capture EventPublisher to verify lifecycle events
            mock_pub = MagicMock(spec=EventPublisher)
            mock_pub.publish_lifecycle = AsyncMock()
            mock_pub.translate = MagicMock(return_value=None)
            mock_pub.flush_violations = AsyncMock()

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
                patch("app.workers.tasks.EventPublisher", return_value=mock_pub),
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                await run_work_session(ctx, project_id)

            lifecycle_calls = mock_pub.publish_lifecycle.call_args_list
            event_types = [c.args[1] for c in lifecycle_calls]
            assert PipelineEventType.WORKFLOW_STARTED in event_types
            assert PipelineEventType.WORKFLOW_COMPLETED in event_types

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Stage Loop & Batch Loop — integration tests with real DB
# ---------------------------------------------------------------------------


def _make_manifest_with_stages(stage_names: list[str]) -> WorkflowManifest:
    """Build a mock WorkflowManifest with given stage names."""
    stages = [StageDef(name=name, description=f"Stage {name}") for name in stage_names]
    return WorkflowManifest(
        name="test-workflow",
        description="Test workflow",
        stages=stages,
    )


def _register_stage_loop_tool_context(
    session_id: str,
    factory: async_sessionmaker[AsyncSession],
    redis: ArqRedis,
    publisher: EventPublisher,
    artifacts_root: object = None,
) -> None:
    """Register a ToolExecutionContext for stage loop integration tests."""
    from pathlib import Path

    from app.workflows.registry import WorkflowRegistry

    ctx = ToolExecutionContext(
        db_session_factory=factory,
        arq_pool=redis,
        workflow_registry=MagicMock(spec=WorkflowRegistry),
        publisher=publisher,
        artifacts_root=Path(str(artifacts_root)) if artifacts_root is not None else None,
    )
    register_tool_context(session_id, ctx)


@require_infra
class TestStageLoop:
    """Integration tests for _execute_stage_loop with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_creates_stage_execution_records(self, tmp_path: object) -> None:
        """Stage loop creates StageExecution records for each stage."""
        from app.workers.tasks import _execute_stage_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            # Create project and workflow records
            async with factory() as db:
                project = Project(
                    name="test-project",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            manifest = _make_manifest_with_stages(["planning", "coding", "review"])

            result = await _execute_stage_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            assert result["stages_completed"] == 3
            assert result["project_completed"] is True

            # Verify StageExecution records in DB
            async with factory() as db:
                stmt = (
                    select(StageExecution)
                    .where(StageExecution.project_id == project_id)
                    .order_by(StageExecution.stage_index)
                )
                se_result = await db.execute(stmt)
                stage_executions = list(se_result.scalars().all())

            assert len(stage_executions) == 3
            assert stage_executions[0].stage_name == "planning"
            assert stage_executions[1].stage_name == "coding"
            assert stage_executions[2].stage_name == "review"
            assert all(se.status == StageStatus.COMPLETED for se in stage_executions)

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_creates_taskgroup_execution_records(self, tmp_path: object) -> None:
        """Stage loop creates TaskGroupExecution records within stages."""
        from app.workers.tasks import _execute_stage_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            async with factory() as db:
                project = Project(
                    name="test-tg",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            manifest = _make_manifest_with_stages(["stage1", "stage2"])

            await _execute_stage_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            # Verify TaskGroupExecution records
            async with factory() as db:
                stmt = (
                    select(TaskGroupExecution)
                    .where(TaskGroupExecution.project_id == project_id)
                    .order_by(TaskGroupExecution.taskgroup_number)
                )
                tg_result = await db.execute(stmt)
                taskgroups = list(tg_result.scalars().all())

            assert len(taskgroups) == 2
            assert taskgroups[0].taskgroup_number == 1
            assert taskgroups[1].taskgroup_number == 2
            # Both should be COMPLETED (Tier 2 checkpoint)
            assert all(tg.status == StageStatus.COMPLETED for tg in taskgroups)

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_stage_transitions_forward_only(self, tmp_path: object) -> None:
        """Completed stages are skipped when loop resumes."""
        from app.workers.tasks import _execute_stage_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            async with factory() as db:
                project = Project(
                    name="test-forward",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                # Pre-create a completed StageExecution for "planning"
                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="planning",
                    stage_index=0,
                    status=StageStatus.COMPLETED,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
                db.add(se)
                await db.commit()

            manifest = _make_manifest_with_stages(["planning", "coding"])

            result = await _execute_stage_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            # Planning was already done, so only coding should have been created
            assert result["stages_completed"] == 2  # 1 pre-done + 1 newly done
            assert result["project_completed"] is True

            # Only 1 TaskGroup should have been created (for coding only)
            async with factory() as db:
                stmt = select(TaskGroupExecution).where(TaskGroupExecution.project_id == project_id)
                tg_result = await db.execute(stmt)
                taskgroups = list(tg_result.scalars().all())

            assert len(taskgroups) == 1  # only "coding" got a new TaskGroup

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_publishes_stage_events(self, tmp_path: object) -> None:
        """Stage loop publishes STAGE_STARTED and STAGE_COMPLETED events."""
        from app.workers.tasks import _execute_stage_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            publisher.publish_stage_completed = AsyncMock()
            publisher.publish_batch_completed = AsyncMock()
            publisher.publish_project_status_changed = AsyncMock()
            publisher.publish_context_recreated = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            async with factory() as db:
                project = Project(
                    name="test-events",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            manifest = _make_manifest_with_stages(["build"])

            await _execute_stage_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            # Verify lifecycle events published
            lifecycle_calls = publisher.publish_lifecycle.call_args_list
            event_types = [
                c.kwargs.get("event_type", c.args[1] if len(c.args) > 1 else None)
                for c in lifecycle_calls
            ]
            assert PipelineEventType.STAGE_STARTED in event_types
            assert publisher.publish_stage_completed.called

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_marks_project_completed(self, tmp_path: object) -> None:
        """When all stages complete, project status becomes COMPLETED."""
        from app.workers.tasks import _execute_stage_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            async with factory() as db:
                project = Project(
                    name="test-complete",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            manifest = _make_manifest_with_stages(["only-stage"])

            result = await _execute_stage_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            assert result["project_completed"] is True

            # Verify project record in DB
            async with factory() as db:
                proj_result = await db.execute(select(Project).where(Project.id == project_id))
                proj = proj_result.scalar_one()
                assert proj.status == ProjectStatus.COMPLETED
                assert proj.completed_at is not None

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


@require_infra
class TestBatchLoop:
    """Integration tests for _execute_batch_loop with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_executes_deliverables_sequentially(self) -> None:
        """Batch loop processes ready deliverables and marks them IN_PROGRESS."""
        from app.workers.tasks import _execute_batch_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                project = Project(
                    name="test-batch",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

                tge = TaskGroupExecution(
                    stage_execution_id=stage_execution_id,
                    project_id=project_id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

                # Add two PLANNED deliverables
                d1 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-1",
                    status=DeliverableStatus.PLANNED,
                    execution_order=1,
                )
                d2 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-2",
                    status=DeliverableStatus.PLANNED,
                    execution_order=2,
                )
                db.add_all([d1, d2])
                await db.commit()

            manifest = _make_manifest_with_stages(["build"])

            result = await _execute_batch_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                stage_execution_id=stage_execution_id,
                taskgroup_execution_id=tge_id,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            assert result["batch_count"] == 1  # Both in same batch (no deps)

            # Verify deliverables were marked IN_PROGRESS
            async with factory() as db:
                stmt = (
                    select(Deliverable)
                    .where(Deliverable.project_id == project_id)
                    .order_by(Deliverable.execution_order)
                )
                d_result = await db.execute(stmt)
                deliverables = list(d_result.scalars().all())

            assert len(deliverables) == 2
            # Both should be IN_PROGRESS (they were transitioned from PLANNED)
            assert all(d.status == DeliverableStatus.IN_PROGRESS for d in deliverables)

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cost_ceiling_exceeded_triggers_stop(self) -> None:
        """Batch loop stops when accumulated cost exceeds ceiling."""
        from app.workers.tasks import _execute_batch_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                project = Project(
                    name="test-cost",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                    accumulated_cost=Decimal("150.0"),  # Over ceiling
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

                tge = TaskGroupExecution(
                    stage_execution_id=stage_execution_id,
                    project_id=project_id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

                d1 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-1",
                    status=DeliverableStatus.PLANNED,
                    execution_order=1,
                )
                db.add(d1)
                await db.commit()

            manifest = _make_manifest_with_stages(["build"])

            result = await _execute_batch_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                stage_execution_id=stage_execution_id,
                taskgroup_execution_id=tge_id,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,  # ceiling is 100, but project cost is 150
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            assert result["cost_exceeded"] is True

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_publishes_batch_completion_events(self, tmp_path: object) -> None:
        """Batch loop publishes completion events after each batch."""
        from app.workers.tasks import _execute_batch_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()
            publisher.publish_stage_completed = AsyncMock()
            publisher.publish_batch_completed = AsyncMock()
            publisher.publish_project_status_changed = AsyncMock()
            publisher.publish_context_recreated = AsyncMock()
            _register_stage_loop_tool_context("test_session", factory, redis, publisher, tmp_path)

            async with factory() as db:
                project = Project(
                    name="test-events",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

                tge = TaskGroupExecution(
                    stage_execution_id=stage_execution_id,
                    project_id=project_id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

                d1 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-1",
                    status=DeliverableStatus.PLANNED,
                    execution_order=1,
                )
                db.add(d1)
                await db.commit()

            manifest = _make_manifest_with_stages(["build"])

            await _execute_batch_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                stage_execution_id=stage_execution_id,
                taskgroup_execution_id=tge_id,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            # Verify batch completion event was published
            assert publisher.publish_batch_completed.called

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_batch_failure_threshold_from_project_config(self) -> None:
        """Batch loop reads failure threshold from ProjectConfig when set."""
        from app.workers.tasks import _execute_batch_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                project = Project(
                    name="test-threshold",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                # Set a custom failure threshold via ProjectConfig
                config = ProjectConfig(
                    project_id=project_id,
                    project_name=project.name,
                    config={"batch_failure_threshold": 5},
                )
                db.add(config)

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

                tge = TaskGroupExecution(
                    stage_execution_id=stage_execution_id,
                    project_id=project_id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

                d1 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-1",
                    status=DeliverableStatus.PLANNED,
                    execution_order=1,
                )
                db.add(d1)
                await db.commit()

            manifest = _make_manifest_with_stages(["build"])

            # Run the batch loop -- it should read the custom threshold (5)
            # without failing, since we only have 1 batch and it won't exceed 5
            result = await _execute_batch_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                stage_execution_id=stage_execution_id,
                taskgroup_execution_id=tge_id,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            # Batch loop completed without threshold_exceeded
            assert result["threshold_exceeded"] is False

            # Verify the config row exists and was queryable
            async with factory() as db:
                cfg = (
                    await db.execute(
                        select(ProjectConfig).where(ProjectConfig.project_id == project_id)
                    )
                ).scalar_one_or_none()
                assert cfg is not None
                assert cfg.config["batch_failure_threshold"] == 5

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cost_ceiling_creates_escalation_queue_item(self) -> None:
        """Cost ceiling exceeded creates a DirectorQueueItem escalation."""
        from app.db.models import DirectorQueueItem
        from app.models.enums import DirectorQueueStatus, EscalationRequestType
        from app.workers.tasks import _execute_batch_loop  # type: ignore[reportPrivateUsage]

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                project = Project(
                    name="test-cost-escalation",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                    accumulated_cost=Decimal("150.0"),  # Over ceiling
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)
                project_id = project.id

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

                tge = TaskGroupExecution(
                    stage_execution_id=stage_execution_id,
                    project_id=project_id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

                d1 = Deliverable(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    name="deliverable-1",
                    status=DeliverableStatus.PLANNED,
                    execution_order=1,
                )
                db.add(d1)
                await db.commit()

            manifest = _make_manifest_with_stages(["build"])

            result = await _execute_batch_loop(
                project_id=project_id,
                workflow_id=workflow_id,
                manifest=manifest,
                stage_execution_id=stage_execution_id,
                taskgroup_execution_id=tge_id,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=100.0,  # ceiling 100, project cost 150
                runner=MagicMock(),
                session_id="test_session",
                adk_session_id="test_session",
            )

            assert result["cost_exceeded"] is True

            # Verify a DirectorQueueItem escalation was created
            async with factory() as db:
                items = (
                    (
                        await db.execute(
                            select(DirectorQueueItem).where(
                                DirectorQueueItem.source_project_id == project_id,
                                DirectorQueueItem.status == DirectorQueueStatus.PENDING,
                                DirectorQueueItem.type == EscalationRequestType.RESOURCE_REQUEST,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(items) == 1
                item = items[0]
                assert "Cost ceiling exceeded" in item.title
                assert str(project_id) in item.title
                assert "150" in item.context  # accumulated cost in context

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# Tier 1 & Tier 2 checkpoint tests — real DB
# ---------------------------------------------------------------------------


@require_infra
class TestTier1Checkpoint:
    """Tests for create_deliverable_checkpoint_callback with real DB."""

    @pytest.mark.asyncio
    async def test_persists_deliverable_status_to_db(self) -> None:
        """Tier 1 checkpoint writes deliverable status to the Deliverable table."""
        from app.agents.supervision import create_deliverable_checkpoint_callback

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis_pool: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            # Create test deliverable
            async with factory() as db:
                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)

                d = Deliverable(
                    workflow_id=workflow.id,
                    name="test-deliverable",
                    status=DeliverableStatus.IN_PROGRESS,
                )
                db.add(d)
                await db.commit()
                await db.refresh(d)
                deliverable_id = str(d.id)

            # Build mock CallbackContext
            mock_ctx = MagicMock()
            state: dict[str, object] = {
                "current_deliverable_id": deliverable_id,
                f"deliverable_status:{deliverable_id}": DeliverableStatus.COMPLETED,
                "workflow_id": "test_wf",
            }
            mock_ctx.state = state

            callback = create_deliverable_checkpoint_callback(factory, publisher)
            await callback(mock_ctx)

            # Verify DB was updated
            async with factory() as db:
                stmt = select(Deliverable).where(Deliverable.id == uuid.UUID(deliverable_id))
                result = await db.execute(stmt)
                updated = result.scalar_one()
                assert updated.status == DeliverableStatus.COMPLETED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis_pool.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis_pool.aclose()

    @pytest.mark.asyncio
    async def test_fallback_status_from_pipeline_output(self) -> None:
        """Tier 1 checkpoint infers status from pipeline_output when status key is missing."""
        from app.agents.supervision import create_deliverable_checkpoint_callback

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis_pool: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)

                d = Deliverable(
                    workflow_id=workflow.id,
                    name="test-d",
                    status=DeliverableStatus.IN_PROGRESS,
                )
                db.add(d)
                await db.commit()
                await db.refresh(d)
                deliverable_id = str(d.id)

            # No explicit status key, but pipeline_output has failed=True
            mock_ctx = MagicMock()
            state: dict[str, object] = {
                "current_deliverable_id": deliverable_id,
                "pipeline_output": {"failed": True},
                "workflow_id": "test_wf",
            }
            mock_ctx.state = state

            callback = create_deliverable_checkpoint_callback(factory, publisher)
            await callback(mock_ctx)

            # Should have been marked FAILED
            async with factory() as db:
                stmt = select(Deliverable).where(Deliverable.id == uuid.UUID(deliverable_id))
                result = await db.execute(stmt)
                updated = result.scalar_one()
                assert updated.status == DeliverableStatus.FAILED

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis_pool.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis_pool.aclose()


@require_infra
class TestTier2Checkpoint:
    """Tests for checkpoint_taskgroup with real DB."""

    @pytest.mark.asyncio
    async def test_persists_checkpoint_data_to_db(self) -> None:
        """Tier 2 checkpoint writes CriticalStateSnapshot to taskgroup_executions."""
        from app.agents.supervision import checkpoint_taskgroup

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis_pool: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            publisher = MagicMock(spec=EventPublisher)
            publisher.publish_lifecycle = AsyncMock()

            async with factory() as db:
                project = Project(
                    name="test-t2",
                    workflow_type="auto-code",
                    brief="Test brief",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.commit()
                await db.refresh(project)

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)

                se = StageExecution(
                    workflow_id=workflow.id,
                    project_id=project.id,
                    stage_name="build",
                    stage_index=0,
                    status=StageStatus.ACTIVE,
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)

                tge = TaskGroupExecution(
                    stage_execution_id=se.id,
                    project_id=project.id,
                    taskgroup_number=1,
                    status=StageStatus.ACTIVE,
                    started_at=datetime.now(UTC),
                )
                db.add(tge)
                await db.commit()
                await db.refresh(tge)
                tge_id = tge.id

            state: dict[str, object] = {
                "deliverable_status:abc123": "COMPLETED",
                "deliverable_status:def456": "FAILED",
                "pm:stage_progress": "stage1",
                "pm:total_cost": 42.5,
                "loaded_skill_names": ["skill-a", "skill-b"],
                "workflow_id": "test_wf",
                "pm:stages_completed": ["planning"],
            }

            await checkpoint_taskgroup(
                db_session_factory=factory,
                taskgroup_execution_id=tge_id,
                state=state,
                publisher=publisher,
                workflow_id="test_wf",
            )

            # Verify DB state
            async with factory() as db:
                stmt = select(TaskGroupExecution).where(TaskGroupExecution.id == tge_id)
                result = await db.execute(stmt)
                updated = result.scalar_one()
                # Tier 2 checkpoint saves state but does NOT mark as completed —
                # completion is determined by the close gate in _execute_stage_loop.
                assert updated.status == StageStatus.ACTIVE
                assert updated.checkpoint_data is not None

                cp = updated.checkpoint_data
                deliverable_statuses = cp["deliverable_statuses"]
                assert isinstance(deliverable_statuses, dict)
                assert "deliverable_status:abc123" in deliverable_statuses
                assert cp["accumulated_cost"] == 42.5
                assert cp["completed_stages"] == ["planning"]

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis_pool.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis_pool.aclose()


# ---------------------------------------------------------------------------
# Validator scheduling tests — real DB
# ---------------------------------------------------------------------------


@require_infra
class TestValidatorScheduling:
    """Tests for _run_scheduled_validators with real DB."""

    @pytest.mark.asyncio
    async def test_validators_run_at_configured_schedule(self) -> None:
        """Validators matching a schedule are executed and results persisted."""
        from app.models.enums import ValidatorSchedule, ValidatorType
        from app.workers.tasks import _run_scheduled_validators  # type: ignore[reportPrivateUsage]
        from app.workflows.manifest import ValidatorDefinition, WorkflowManifest

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis_pool: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Create workflow record
            async with factory() as db:
                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            # Build a manifest with a lint_check validator at PER_DELIVERABLE schedule
            manifest = WorkflowManifest(
                name="test-validators",
                description="Test validators",
                validators=[
                    ValidatorDefinition(
                        name="lint_check",
                        type=ValidatorType.DETERMINISTIC,
                        schedule=ValidatorSchedule.PER_DELIVERABLE,
                    ),
                ],
            )

            state: dict[str, object] = {
                "lint_results": {"passed": True, "errors": 0},
            }

            results = await _run_scheduled_validators(
                manifest=manifest,
                schedule=ValidatorSchedule.PER_DELIVERABLE,
                state=state,
                workflow_id=workflow_id,
                stage_execution_id=None,
                db_session_factory=factory,
            )

            assert len(results) == 1
            # lint_check should pass since lint_results.passed = True
            assert results[0].passed is True  # type: ignore[union-attr]

            # Verify ValidatorResult was persisted to DB
            async with factory() as db:
                stmt = select(ValidatorResultModel).where(
                    ValidatorResultModel.workflow_id == workflow_id
                )
                vr_result = await db.execute(stmt)
                vr_rows = list(vr_result.scalars().all())

            assert len(vr_rows) == 1
            assert vr_rows[0].validator_name == "lint_check"
            assert vr_rows[0].passed is True

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis_pool.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis_pool.aclose()

    @pytest.mark.asyncio
    async def test_non_matching_schedule_skipped(self) -> None:
        """Validators not matching the requested schedule are not run."""
        from app.models.enums import ValidatorSchedule, ValidatorType
        from app.workers.tasks import _run_scheduled_validators  # type: ignore[reportPrivateUsage]
        from app.workflows.manifest import ValidatorDefinition, WorkflowManifest

        engine = create_async_engine(TEST_DB_URL)
        redis_settings = parse_redis_settings(TEST_REDIS_URL)
        redis_pool: ArqRedis = await create_pool(redis_settings)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with factory() as db:
                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
                db.add(workflow)
                await db.commit()
                await db.refresh(workflow)
                workflow_id = workflow.id

            # Validator at PER_STAGE schedule
            manifest = WorkflowManifest(
                name="test-no-match",
                description="Test validators",
                validators=[
                    ValidatorDefinition(
                        name="lint_check",
                        type=ValidatorType.DETERMINISTIC,
                        schedule=ValidatorSchedule.PER_STAGE,
                    ),
                ],
            )

            # Request PER_BATCH -- should not match
            results = await _run_scheduled_validators(
                manifest=manifest,
                schedule=ValidatorSchedule.PER_BATCH,
                state={},
                workflow_id=workflow_id,
                stage_execution_id=None,
                db_session_factory=factory,
            )

            assert len(results) == 0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis_pool.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis_pool.aclose()


# ---------------------------------------------------------------------------
# ProjectConfig lookup with project_id FK — integration test
# ---------------------------------------------------------------------------


@require_infra
class TestProjectConfigLookup:
    """Tests for the updated ProjectConfig FK-based lookup."""

    @pytest.mark.asyncio
    async def test_loads_config_by_project_id_fk(self, tmp_path: object) -> None:
        """ProjectConfig is found via project_id FK when project_id is a UUID."""
        from app.workers.tasks import run_work_session

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

            # Create a Project with UUID and a ProjectConfig with project_id FK
            async with factory() as db_session:
                project = Project(
                    name="fk-test",
                    workflow_type="auto-code",
                    brief="FK test brief",
                    status=ProjectStatus.SHAPING,
                )
                db_session.add(project)
                await db_session.commit()
                await db_session.refresh(project)
                project_uuid = str(project.id)

                pc = ProjectConfig(
                    project_id=project.id,
                    project_name=project_uuid,
                    config={"retry_budget": 7, "cost_ceiling": 77.0},
                )
                db_session.add(pc)
                await db_session.commit()

            ctx: dict[str, object] = {
                "session_service": session_service,
                "llm_router": router,
                "redis": redis,
                "db_session_factory": factory,
                "artifacts_root": tmp_path,
            }

            patches = _standard_patches()
            with (
                patches["assembler"],
                patches["toolset"],
                patches["registry_cls"] as mock_reg_cls,
                patches["formation"],
                patches["build_agents"] as mock_build,
                patches["create_app"] as mock_app,
                patches["create_runner"] as mock_runner_fn,
                patches["pipeline_callbacks"],
            ):
                mock_build.return_value = _make_mock_agent("director")
                mock_runner_fn.return_value = _make_mock_runner()
                mock_app.return_value = MagicMock()
                mock_reg_cls.return_value = MagicMock()

                result = await run_work_session(ctx, project_uuid)

            assert result["status"] == "completed"

            # Verify session state has our custom config
            from app.models.constants import APP_NAME, SYSTEM_USER_ID

            session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=f"work_session_{project_uuid}",
            )
            assert session is not None
            state: dict[str, object] = session.state  # type: ignore[reportUnknownMemberType]
            pc_state = state["project_config"]
            assert isinstance(pc_state, dict)
            assert pc_state["retry_budget"] == 7
            assert pc_state["cost_ceiling"] == 77.0

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
            await redis.flushdb()  # type: ignore[reportUnknownMemberType]
            await redis.aclose()


# ---------------------------------------------------------------------------
# create_edit_taskgroup — integration tests with real DB
# ---------------------------------------------------------------------------


@require_infra
class TestCreateEditTaskgroup:
    """Integration tests for create_edit_taskgroup with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_creates_taskgroup_for_existing_project_with_stage(self) -> None:
        """create_edit_taskgroup creates a TaskGroupExecution linked to the project."""
        from app.workers.tasks import create_edit_taskgroup

        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Create project + workflow + stage execution
            async with factory() as db:
                project = Project(
                    name="edit-test-project",
                    workflow_type="auto-code",
                    brief="Test project for edit operations",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.flush()

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                )
                db.add(workflow)
                await db.flush()

                stage_exec = StageExecution(
                    workflow_id=workflow.id,
                    project_id=project.id,
                    stage_name="build",
                    stage_index=2,
                    status=StageStatus.ACTIVE,
                )
                db.add(stage_exec)
                await db.commit()
                project_id = project.id

            taskgroup_id = await create_edit_taskgroup(
                project_id=project_id,
                edit_operation="fix_bug",
                description="Fix the authentication bug",
                db_session_factory=factory,
            )

            assert taskgroup_id is not None

            # Verify TaskGroup was persisted
            async with factory() as db:
                tg = (
                    await db.execute(
                        select(TaskGroupExecution).where(TaskGroupExecution.id == taskgroup_id)
                    )
                ).scalar_one_or_none()

            assert tg is not None
            assert tg.project_id == project_id
            assert tg.taskgroup_number == 1
            assert tg.checkpoint_data is not None
            assert tg.checkpoint_data["edit_operation"] == "fix_bug"
            assert tg.checkpoint_data["edit_description"] == "Fix the authentication bug"

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_taskgroup_number_increments(self) -> None:
        """Second edit TaskGroup gets number 2 when one already exists."""
        from app.workers.tasks import create_edit_taskgroup

        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with factory() as db:
                project = Project(
                    name="edit-test-project-2",
                    workflow_type="auto-code",
                    brief="Test project",
                    status=ProjectStatus.ACTIVE,
                )
                db.add(project)
                await db.flush()

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                )
                db.add(workflow)
                await db.flush()

                stage_exec = StageExecution(
                    workflow_id=workflow.id,
                    project_id=project.id,
                    stage_name="build",
                    stage_index=2,
                    status=StageStatus.ACTIVE,
                )
                db.add(stage_exec)
                await db.commit()
                project_id = project.id

            tg1_id = await create_edit_taskgroup(
                project_id=project_id,
                edit_operation="fix_bug",
                description="First edit",
                db_session_factory=factory,
            )
            tg2_id = await create_edit_taskgroup(
                project_id=project_id,
                edit_operation="refactor",
                description="Second edit",
                db_session_factory=factory,
            )

            async with factory() as db:
                tg1 = (
                    await db.execute(
                        select(TaskGroupExecution).where(TaskGroupExecution.id == tg1_id)
                    )
                ).scalar_one()
                tg2 = (
                    await db.execute(
                        select(TaskGroupExecution).where(TaskGroupExecution.id == tg2_id)
                    )
                ).scalar_one()

            assert tg1.taskgroup_number == 1
            assert tg2.taskgroup_number == 2

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_project_not_found_raises_value_error(self) -> None:
        """create_edit_taskgroup raises ValueError for a non-existent project."""
        from app.workers.tasks import create_edit_taskgroup

        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            nonexistent_id = uuid.uuid4()
            with pytest.raises(ValueError, match=str(nonexistent_id)):
                await create_edit_taskgroup(
                    project_id=nonexistent_id,
                    edit_operation="fix_bug",
                    description="Irrelevant",
                    db_session_factory=factory,
                )

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    @pytest.mark.parametrize(
        "project_status",
        [
            ProjectStatus.SHAPING,
            ProjectStatus.ACTIVE,
            ProjectStatus.PAUSED,
            ProjectStatus.SUSPENDED,
            ProjectStatus.COMPLETED,
        ],
    )
    @pytest.mark.asyncio
    async def test_all_project_states_accept_edit_taskgroup(
        self, project_status: ProjectStatus
    ) -> None:
        """Projects in any state accept new edit TaskGroups."""
        from app.workers.tasks import create_edit_taskgroup

        engine = create_async_engine(TEST_DB_URL)

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with factory() as db:
                project = Project(
                    name=f"edit-test-{project_status.value.lower()}",
                    workflow_type="auto-code",
                    brief="Test project",
                    status=project_status,
                )
                db.add(project)
                await db.flush()

                workflow = Workflow(
                    workflow_type="auto-code",
                    status=WorkflowStatus.RUNNING,
                )
                db.add(workflow)
                await db.flush()

                stage_exec = StageExecution(
                    workflow_id=workflow.id,
                    project_id=project.id,
                    stage_name="build",
                    stage_index=2,
                    status=StageStatus.ACTIVE,
                )
                db.add(stage_exec)
                await db.commit()
                project_id = project.id

            taskgroup_id = await create_edit_taskgroup(
                project_id=project_id,
                edit_operation="fix_bug",
                description=f"Edit on {project_status.value} project",
                db_session_factory=factory,
            )

            assert taskgroup_id is not None

            async with factory() as db:
                tg = (
                    await db.execute(
                        select(TaskGroupExecution).where(TaskGroupExecution.id == taskgroup_id)
                    )
                ).scalar_one_or_none()

            assert tg is not None
            assert tg.project_id == project_id

        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
