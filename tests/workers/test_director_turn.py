"""Integration tests for run_director_turn with real PostgreSQL and Redis.

External APIs (ADK agent/runner) are mocked; local infrastructure is real.
"""

from __future__ import annotations

import contextlib
import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest
from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import parse_redis_settings
from app.db.models import Base, Chat, ChatMessage, DirectorQueueItem
from app.models.enums import (
    ChatMessageRole,
    ChatStatus,
    ChatType,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    FormationStatus,
)
from app.workers.tasks import run_director_turn
from tests.conftest import TEST_DB_URL, TEST_REDIS_URL, require_infra

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_runner_with_response(text: str) -> MagicMock:
    """Create a mock runner whose run_async yields an event with text content."""
    mock_event = MagicMock()
    mock_content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = text
    mock_content.parts = [mock_part]
    mock_event.content = mock_content

    async def _run_async(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        yield mock_event  # type: ignore[misc]

    runner = MagicMock()
    runner.run_async = _run_async
    return runner


def _mock_runner_empty() -> MagicMock:
    """Create a mock runner whose run_async yields nothing."""

    async def _run_async(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        return
        yield  # type: ignore[misc]  # pragma: no cover

    runner = MagicMock()
    runner.run_async = _run_async
    return runner


@contextlib.contextmanager
def _patch_director_infra(
    *,
    runner: MagicMock | None = None,
    build_side_effect: object = None,
    build_return: MagicMock | None = None,
    formation_status: FormationStatus = FormationStatus.COMPLETE,
) -> Iterator[MagicMock]:
    """Patch external APIs: AgentRegistry, GlobalToolset, formation, runner.

    Yields the mock for build_chat_session_agent.
    """
    if runner is None:
        runner = _mock_runner_empty()

    build_kwargs: dict[str, object] = {}
    if build_side_effect is not None:
        build_kwargs["side_effect"] = build_side_effect
    else:
        build_kwargs["return_value"] = build_return or MagicMock()

    with (
        patch(
            "app.workers.tasks.build_chat_session_agent",
            **build_kwargs,  # type: ignore[arg-type]
        ) as mock_build,  # type: ignore[reportUnknownVariableType]
        patch("app.workers.tasks.create_app_container"),
        patch("app.workers.tasks.create_runner", return_value=runner),
        patch(
            "app.agents.formation.ensure_formation_state",
            new_callable=AsyncMock,
            return_value=formation_status,
        ),
        patch("app.agents._registry.AgentRegistry"),
        patch("app.tools._toolset.GlobalToolset"),
    ):
        yield mock_build


async def _make_infra() -> tuple[
    AsyncSession,  # not used directly, typed for reference
    async_sessionmaker[AsyncSession],
    ArqRedis,
    object,  # engine
]:
    """Spin up real engine + redis, create tables, return factory/redis/engine."""
    engine = create_async_engine(TEST_DB_URL)
    redis: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return None, factory, redis, engine  # type: ignore[return-value]


async def _cleanup(engine: object, redis: ArqRedis) -> None:
    from sqlalchemy.ext.asyncio import AsyncEngine

    eng: AsyncEngine = engine  # type: ignore[assignment]
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()
    await redis.aclose()


async def _insert_chat_and_message(
    factory: async_sessionmaker[AsyncSession],
    *,
    chat_type: ChatType = ChatType.DIRECTOR,
) -> tuple[str, str, str]:
    """Insert a real Chat + ChatMessage. Returns (chat_id, message_id, session_id)."""
    chat_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    async with factory() as session:
        chat = Chat(
            id=uuid.UUID(chat_id),
            session_id=session_id,
            type=chat_type,
            status=ChatStatus.ACTIVE,
        )
        session.add(chat)
        await session.flush()

        user_msg = ChatMessage(
            id=uuid.UUID(message_id),
            chat_id=uuid.UUID(chat_id),
            role=ChatMessageRole.USER,
            content="Hello Director",
        )
        session.add(user_msg)
        await session.commit()

    return chat_id, message_id, session_id


def _make_worker_ctx(
    factory: async_sessionmaker[AsyncSession],
    redis: ArqRedis,
) -> dict[str, object]:
    """Build worker context with real DB/Redis and mock session_service."""
    mock_session_service = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "adk_session_id"
    mock_session_service.get_session = AsyncMock(return_value=None)
    mock_session_service.create_session = AsyncMock(return_value=mock_session)

    mock_router = MagicMock()
    mock_router.select_model = MagicMock(return_value="anthropic/claude-haiku-4-5-20251001")

    return {
        "session_service": mock_session_service,
        "llm_router": mock_router,
        "redis": redis,
        "db_session_factory": factory,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@require_infra
class TestRunDirectorTurnBuildsDirector:
    """Verify Director is built from AgentRegistry."""

    @pytest.mark.asyncio
    async def test_builds_director_via_registry(self) -> None:
        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(factory)
            ctx = _make_worker_ctx(factory, redis)

            runner = _mock_runner_with_response("Hello from Director")

            with _patch_director_infra(runner=runner) as mock_build:
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"
            assert mock_build.called
            assert mock_build.call_args is not None
        finally:
            await _cleanup(engine, redis)


@require_infra
class TestRunDirectorTurnPersistsResponse:
    """Verify Director response is saved as ChatMessage(DIRECTOR) in real DB."""

    @pytest.mark.asyncio
    async def test_persists_response_text(self) -> None:
        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(factory)
            ctx = _make_worker_ctx(factory, redis)

            runner = _mock_runner_with_response("Director says hi")

            with _patch_director_infra(runner=runner):
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"

            # Verify in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.chat_id == chat_id)  # type: ignore[reportArgumentType]
                    .where(ChatMessage.role == ChatMessageRole.DIRECTOR)
                )
                director_msg = db_result.scalar_one_or_none()
                assert director_msg is not None
                assert director_msg.content == "Director says hi"
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_empty_response_gets_fallback(self) -> None:
        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(factory)
            ctx = _make_worker_ctx(factory, redis)

            with _patch_director_infra():
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"

            # Verify fallback text in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.chat_id == chat_id)  # type: ignore[reportArgumentType]
                    .where(ChatMessage.role == ChatMessageRole.DIRECTOR)
                )
                director_msg = db_result.scalar_one_or_none()
                assert director_msg is not None
                assert director_msg.content == "(No response from Director)"
        finally:
            await _cleanup(engine, redis)


@require_infra
class TestRunDirectorTurnSettingsMode:
    """Verify Settings session triggers formation/evolution instructions."""

    @pytest.mark.asyncio
    async def test_settings_formation_mode(self) -> None:
        """SETTINGS chat with PENDING formation uses FORMATION_INSTRUCTION."""
        from app.agents.formation import FORMATION_INSTRUCTION

        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(
                factory, chat_type=ChatType.SETTINGS
            )
            ctx = _make_worker_ctx(factory, redis)

            runner = _mock_runner_with_response("Formation response")
            captured_ctx: list[object] = []

            def _capturing_build(registry: object, instruction_ctx: object) -> MagicMock:
                captured_ctx.append(instruction_ctx)
                return MagicMock()

            with _patch_director_infra(
                runner=runner,
                build_side_effect=_capturing_build,
                formation_status=FormationStatus.PENDING,
            ):
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"
            assert len(captured_ctx) == 1
            from app.agents.assembler import InstructionContext

            ic = captured_ctx[0]
            assert isinstance(ic, InstructionContext)
            assert ic.task_context == FORMATION_INSTRUCTION
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_settings_evolution_mode(self) -> None:
        """SETTINGS chat with COMPLETE formation uses EVOLUTION_INSTRUCTION."""
        from app.agents.formation import EVOLUTION_INSTRUCTION

        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(
                factory, chat_type=ChatType.SETTINGS
            )
            ctx = _make_worker_ctx(factory, redis)

            runner = _mock_runner_with_response("Evolution response")
            captured_ctx: list[object] = []

            def _capturing_build(registry: object, instruction_ctx: object) -> MagicMock:
                captured_ctx.append(instruction_ctx)
                return MagicMock()

            with _patch_director_infra(
                runner=runner,
                build_side_effect=_capturing_build,
                formation_status=FormationStatus.COMPLETE,
            ):
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"
            assert len(captured_ctx) == 1
            from app.agents.assembler import InstructionContext

            ic = captured_ctx[0]
            assert isinstance(ic, InstructionContext)
            assert ic.task_context == EVOLUTION_INSTRUCTION
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_director_chat_no_task_context(self) -> None:
        """DIRECTOR chat does not inject formation/evolution instructions."""
        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(
                factory, chat_type=ChatType.DIRECTOR
            )
            ctx = _make_worker_ctx(factory, redis)

            runner = _mock_runner_with_response("Director response")
            captured_ctx: list[object] = []

            def _capturing_build(registry: object, instruction_ctx: object) -> MagicMock:
                captured_ctx.append(instruction_ctx)
                return MagicMock()

            with _patch_director_infra(
                runner=runner,
                build_side_effect=_capturing_build,
                formation_status=FormationStatus.COMPLETE,
            ):
                result = await run_director_turn(ctx, chat_id, message_id)

            assert result["status"] == "completed"
            from app.agents.assembler import InstructionContext

            ic = captured_ctx[0]
            assert isinstance(ic, InstructionContext)
            assert ic.task_context is None
        finally:
            await _cleanup(engine, redis)


@require_infra
class TestRunDirectorTurnErrorHandling:
    """Verify agent build failures are persisted as error messages in real DB."""

    @pytest.mark.asyncio
    async def test_build_failure_persists_error(self) -> None:
        _, factory, redis, engine = await _make_infra()
        try:
            chat_id, message_id, _ = await _insert_chat_and_message(factory)
            ctx = _make_worker_ctx(factory, redis)

            with (
                _patch_director_infra(
                    build_side_effect=RuntimeError("Registry scan failed"),
                ),
                pytest.raises(RuntimeError, match="Registry scan failed"),
            ):
                await run_director_turn(ctx, chat_id, message_id)

            # Error should be persisted as a Director message in real DB
            async with factory() as session:
                db_result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.chat_id == chat_id)  # type: ignore[reportArgumentType]
                    .where(ChatMessage.role == ChatMessageRole.DIRECTOR)
                )
                error_msg = db_result.scalar_one_or_none()
                assert error_msg is not None
                assert "Registry scan failed" in error_msg.content
        finally:
            await _cleanup(engine, redis)


# ---------------------------------------------------------------------------
# Queue-mode helpers
# ---------------------------------------------------------------------------


def _make_queue_item(project_id: uuid.UUID) -> DirectorQueueItem:
    """Create a PENDING DirectorQueueItem."""
    return DirectorQueueItem(
        type=EscalationRequestType.ESCALATION,
        priority=EscalationPriority.NORMAL,
        status=DirectorQueueStatus.PENDING,
        title="Test escalation",
        source_project_id=project_id,
        source_agent="test",
        context="test context",
    )


# ---------------------------------------------------------------------------
# Queue-mode tests
# ---------------------------------------------------------------------------


@require_infra
class TestRunDirectorTurnQueueMode:
    """Verify run_director_turn queue mode (project_id) with real DB/Redis."""

    @pytest.mark.asyncio
    async def test_queue_mode_skips_when_no_pending_items(self) -> None:
        """No pending items for project → returns skipped, no Director run."""
        _, factory, redis, engine = await _make_infra()
        try:
            ctx = _make_worker_ctx(factory, redis)
            pid = str(uuid.uuid4())

            with _patch_director_infra() as mock_build:
                result = await run_director_turn(ctx, project_id=pid)

            assert result["status"] == "skipped"
            assert result["project_id"] == pid
            mock_build.assert_not_called()
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_queue_mode_runs_director_with_pending_items(self) -> None:
        """Pending items exist → Director runs with synthetic prompt."""
        _, factory, redis, engine = await _make_infra()
        try:
            pid = uuid.uuid4()
            async with factory() as session:
                session.add(_make_queue_item(pid))
                await session.commit()

            ctx = _make_worker_ctx(factory, redis)
            runner = _mock_runner_with_response("Queue evaluated")

            with _patch_director_infra(runner=runner) as mock_build:
                result = await run_director_turn(ctx, project_id=str(pid))

            assert result["status"] == "completed"
            mock_build.assert_called_once()
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_queue_mode_no_chat_message_persisted(self) -> None:
        """Queue mode should NOT persist ChatMessage records."""
        _, factory, redis, engine = await _make_infra()
        try:
            pid = uuid.uuid4()
            async with factory() as session:
                session.add(_make_queue_item(pid))
                await session.commit()

            ctx = _make_worker_ctx(factory, redis)
            runner = _mock_runner_with_response("Queue response")

            with _patch_director_infra(runner=runner):
                await run_director_turn(ctx, project_id=str(pid))

            # Verify no ChatMessage was created
            async with factory() as session:
                db_result = await session.execute(select(ChatMessage))
                messages = list(db_result.scalars().all())
                assert len(messages) == 0
        finally:
            await _cleanup(engine, redis)

    @pytest.mark.asyncio
    async def test_invalid_invocation_raises(self) -> None:
        """Neither chat_id+message_id nor project_id → ValueError."""
        _, factory, redis, engine = await _make_infra()
        try:
            ctx = _make_worker_ctx(factory, redis)
            with pytest.raises(ValueError, match="requires"):
                await run_director_turn(ctx)
        finally:
            await _cleanup(engine, redis)
