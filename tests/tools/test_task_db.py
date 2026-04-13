"""Tests for DB-persisted task tools (FR-8a.25).

Uses real PostgreSQL -- skipped when unavailable.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ProjectTask
from app.models.enums import TaskStatus
from app.tools._context import (
    SESSION_ID_KEY,
    ToolExecutionContext,
    register_tool_context,
    unregister_tool_context,
)
from app.tools.task import task_create, task_query, task_update
from tests.conftest import require_postgres

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeActions:
    def __init__(self) -> None:
        self.state_delta: dict[str, object] = {}


class _FakeToolContext:
    """Minimal ToolContext stand-in that provides state and session ID."""

    def __init__(self, session_id: str, project_id: uuid.UUID | None = None) -> None:
        self._state: dict[str, object] = {SESSION_ID_KEY: session_id}
        if project_id is not None:
            self._state["project_id"] = str(project_id)
        self.actions = _FakeActions()

    @property
    def state(self) -> dict[str, object]:
        merged = dict(self._state)
        merged.update(self.actions.state_delta)
        return merged


@pytest.fixture
def session_id() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def db_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def tool_ctx(
    session_id: str,
    db_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[_FakeToolContext]:
    """Register tool context and yield a fake ToolContext wired to real DB."""

    class _Stub:
        pass

    exec_ctx = ToolExecutionContext(
        db_session_factory=db_factory,
        arq_pool=_Stub(),  # type: ignore[arg-type]
        workflow_registry=_Stub(),  # type: ignore[arg-type]
        publisher=_Stub(),  # type: ignore[arg-type]
    )
    register_tool_context(session_id, exec_ctx)
    try:
        yield _FakeToolContext(session_id)
    finally:
        unregister_tool_context(session_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@require_postgres
@pytest.mark.asyncio
class TestTaskCreateDB:
    async def test_creates_persistent_record(
        self,
        tool_ctx: _FakeToolContext,
        db_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        result_json = await task_create(
            "Build login page",
            "Implement OAuth login flow",
            tool_ctx,  # type: ignore[arg-type]
            assignee="coder",
            tags=["frontend", "auth"],
        )
        result = json.loads(result_json)
        assert result["title"] == "Build login page"
        assert result["status"] == TaskStatus.OPEN
        assert result["assignee"] == "coder"
        assert result["tags"] == ["frontend", "auth"]

        # Verify it's actually in the DB
        task_id = uuid.UUID(result["id"])
        async with db_factory() as db:
            row = (
                await db.execute(select(ProjectTask).where(ProjectTask.id == task_id))
            ).scalar_one_or_none()
            assert row is not None
            assert row.title == "Build login page"

    async def test_creates_without_optional_fields(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        result_json = await task_create(
            "Simple task",
            "No extras",
            tool_ctx,  # type: ignore[arg-type]
        )
        result = json.loads(result_json)
        assert result["title"] == "Simple task"
        assert result["assignee"] is None
        assert result["tags"] == []


@require_postgres
@pytest.mark.asyncio
class TestTaskUpdateDB:
    async def test_updates_status(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        create_json = await task_create(
            "Update me",
            "To be updated",
            tool_ctx,  # type: ignore[arg-type]
        )
        task_id = json.loads(create_json)["id"]

        update_json = await task_update(
            task_id,
            tool_ctx,  # type: ignore[arg-type]
            status=TaskStatus.IN_PROGRESS,
        )
        updated = json.loads(update_json)
        assert updated["status"] == TaskStatus.IN_PROGRESS

    async def test_appends_notes(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        create_json = await task_create(
            "Notes task",
            "Has notes",
            tool_ctx,  # type: ignore[arg-type]
        )
        task_id = json.loads(create_json)["id"]

        await task_update(task_id, tool_ctx, notes="First note")  # type: ignore[arg-type]
        update_json = await task_update(
            task_id,
            tool_ctx,  # type: ignore[reportArgumentType]
            notes="Second note",
        )
        result = json.loads(update_json)
        assert "First note" in result["notes"]
        assert "Second note" in result["notes"]

    async def test_invalid_status_returns_error(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        create_json = await task_create(
            "Bad status",
            "desc",
            tool_ctx,  # type: ignore[arg-type]
        )
        task_id = json.loads(create_json)["id"]
        result_json = await task_update(
            task_id,
            tool_ctx,  # type: ignore[reportArgumentType]
            status="INVALID",  # type: ignore[arg-type]
        )
        result = json.loads(result_json)
        assert "error" in result

    async def test_nonexistent_task_returns_error(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        fake_id = str(uuid.uuid4())
        result_json = await task_update(
            fake_id,
            tool_ctx,  # type: ignore[arg-type]
        )
        result = json.loads(result_json)
        assert "error" in result


@require_postgres
@pytest.mark.asyncio
class TestTaskQueryDB:
    async def test_queries_all_tasks(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        await task_create("Task A", "Desc A", tool_ctx)  # type: ignore[arg-type]
        await task_create("Task B", "Desc B", tool_ctx)  # type: ignore[arg-type]

        result_json = await task_query(tool_ctx)  # type: ignore[arg-type]
        results = json.loads(result_json)
        assert len(results) >= 2
        titles = {r["title"] for r in results}
        assert "Task A" in titles
        assert "Task B" in titles

    async def test_filters_by_status(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        create_json = await task_create(
            "Done task",
            "Finished",
            tool_ctx,  # type: ignore[arg-type]
        )
        task_id = json.loads(create_json)["id"]
        await task_update(
            task_id,
            tool_ctx,  # type: ignore[reportArgumentType]
            status=TaskStatus.DONE,  # type: ignore[arg-type]
        )

        await task_create(
            "Open task",
            "Still open",
            tool_ctx,  # type: ignore[arg-type]
        )

        done_json = await task_query(
            tool_ctx,  # type: ignore[reportArgumentType]
            filter=TaskStatus.DONE,  # type: ignore[arg-type]
        )
        done_tasks = json.loads(done_json)
        assert all(t["status"] == TaskStatus.DONE for t in done_tasks)

    async def test_filters_by_assignee(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        await task_create(
            "Alice task",
            "For alice",
            tool_ctx,  # type: ignore[arg-type]
            assignee="alice",
        )
        await task_create(
            "Bob task",
            "For bob",
            tool_ctx,  # type: ignore[arg-type]
            assignee="bob",
        )

        result_json = await task_query(
            tool_ctx,  # type: ignore[reportArgumentType]
            assignee="alice",
        )
        results = json.loads(result_json)
        assert all(r["assignee"] == "alice" for r in results)

    async def test_invalid_filter_returns_error(
        self,
        tool_ctx: _FakeToolContext,
    ) -> None:
        result_json = await task_query(
            tool_ctx,  # type: ignore[reportArgumentType]
            filter="INVALID",  # type: ignore[arg-type]
        )
        result = json.loads(result_json)
        assert "error" in result
