"""Tests for run_work_session task and work session agent builders.

Integration tests use real PostgreSQL and Redis; ADK/LLM components are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings, parse_redis_settings
from app.db.models import Base, ProjectConfig
from app.events.publisher import EventPublisher
from app.models.enums import FormationStatus, PipelineEventType
from app.router import LlmRouter
from app.workers.adk import create_session_service
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

        with patch(
            "app.agents.pipeline.create_deliverable_pipeline",
            return_value=pipeline_mock,
        ):
            result = await build_work_session_agents(
                registry=registry,
                ctx=ctx,
                project_id="proj1",
                publisher=publisher,
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

        with patch(
            "app.agents.pipeline.create_deliverable_pipeline",
            return_value=pipeline_mock,
        ):
            await build_work_session_agents(
                registry=registry,
                ctx=ctx,
                project_id="proj1",
                publisher=publisher,
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

        with patch(
            "app.agents.pipeline.create_deliverable_pipeline",
            return_value=pipeline_mock,
        ):
            await build_work_session_agents(
                registry=registry,
                ctx=ctx,
                project_id="proj1",
                publisher=publisher,
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
    async def test_loads_project_config(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_default_config_created(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_ensures_formation_state(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_sets_redis_key(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cleans_redis_key_on_completion(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_cleans_redis_key_on_failure(self) -> None:
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
            await redis.aclose()

    @pytest.mark.asyncio
    async def test_publishes_lifecycle_events(self) -> None:
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
            await redis.aclose()
