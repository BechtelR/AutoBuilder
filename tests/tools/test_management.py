"""Tests for management tools (PM and Director).

Uses real PostgreSQL for DB-writing tools. Stubs that return NOT_IMPLEMENTED
are tested for correct JSON structure without DB access.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from app.db.models import CeoQueueItem, Deliverable, DirectorQueueItem, Project, Workflow
from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    DeliverableStatus,
    DependencyAction,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    PmOverrideAction,
    ProjectStatus,
    WorkflowStatus,
)
from app.tools._context import (
    SESSION_ID_KEY,
    ToolExecutionContext,
    register_tool_context,
    unregister_tool_context,
)
from app.tools.management import (
    check_resources,
    create_project,
    delegate_to_pm,
    escalate_to_ceo,
    escalate_to_director,
    get_project_context,
    list_projects,
    manage_dependencies,
    override_pm,
    query_deliverables,
    query_dependency_graph,
    query_project_status,
    reorder_deliverables,
    select_ready_batch,
    update_deliverable,
    validate_brief,
)
from tests.conftest import require_infra

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_SESSION_ID = "mgmt-test-session"


def _make_tool_context() -> MagicMock:
    """Create a minimal ToolContext stand-in with session_id in state.

    ToolContext is an ADK framework type that cannot be instantiated outside
    ADK's agent lifecycle. We use a stand-in object with the .state dict that
    tools actually read. This is NOT mocking local infrastructure -- it's
    providing the ADK interface that tools consume.
    """
    ctx = MagicMock()
    ctx.state = {SESSION_ID_KEY: TEST_SESSION_ID}
    return ctx


@pytest.fixture
def tool_ctx() -> MagicMock:
    """ToolContext stand-in for tool calls."""
    return _make_tool_context()


@pytest_asyncio.fixture
async def db_tool_ctx(
    engine: AsyncEngine,
    async_session: AsyncSession,
    redis_client: object,
) -> AsyncGenerator[MagicMock, None]:
    """ToolContext backed by real DB infrastructure.

    Uses a real ArqRedis pool for job enqueueing (delegate_to_pm).
    """
    from arq.connections import ArqRedis, create_pool
    from sqlalchemy.ext.asyncio import AsyncSession as AS
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.config import parse_redis_settings

    factory = async_sessionmaker(engine, class_=AS, expire_on_commit=False)
    arq_pool: ArqRedis = await create_pool(parse_redis_settings("redis://localhost:6379/1"))

    tool_exec_ctx = ToolExecutionContext(
        db_session_factory=factory,
        arq_pool=arq_pool,
        workflow_registry=MagicMock(),
        publisher=MagicMock(),
    )
    register_tool_context(TEST_SESSION_ID, tool_exec_ctx)
    ctx = _make_tool_context()
    yield ctx
    unregister_tool_context(TEST_SESSION_ID)
    await arq_pool.aclose()


@pytest_asyncio.fixture
async def db_tool_ctx_with_registry(
    engine: AsyncEngine,
    async_session: AsyncSession,
    redis_client: object,
) -> AsyncGenerator[MagicMock, None]:
    """ToolContext with real DB AND real WorkflowRegistry."""
    from pathlib import Path as P

    from sqlalchemy.ext.asyncio import AsyncSession as AS
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.workflows.registry import WorkflowRegistry

    factory = async_sessionmaker(engine, class_=AS, expire_on_commit=False)
    workflows_dir = P(__file__).resolve().parent.parent.parent / "app" / "workflows"
    registry = WorkflowRegistry(workflows_dir=workflows_dir)
    registry.scan()
    tool_exec_ctx = ToolExecutionContext(
        db_session_factory=factory,
        arq_pool=redis_client,  # type: ignore[arg-type]
        workflow_registry=registry,
        publisher=MagicMock(),
    )
    register_tool_context(TEST_SESSION_ID, tool_exec_ctx)
    ctx = _make_tool_context()
    yield ctx
    unregister_tool_context(TEST_SESSION_ID)


@pytest.fixture(autouse=True)
def _register_stub_context() -> Generator[None, None, None]:  # type: ignore[misc]
    """Register a minimal context for stub tools that don't touch DB."""
    ctx = ToolExecutionContext(
        db_session_factory=MagicMock(),  # type: ignore[arg-type]
        arq_pool=MagicMock(),  # type: ignore[arg-type]
        workflow_registry=MagicMock(),  # type: ignore[arg-type]
        publisher=MagicMock(),  # type: ignore[arg-type]
    )
    register_tool_context(TEST_SESSION_ID, ctx)
    yield
    unregister_tool_context(TEST_SESSION_ID)


# ---------------------------------------------------------------------------
# Helper: create test project + workflow + deliverables
# ---------------------------------------------------------------------------


async def _create_project_with_deliverables(
    async_session: AsyncSession,
    deliverable_specs: list[dict[str, object]],
) -> tuple[Project, Workflow, list[Deliverable]]:
    """Create a project, workflow, and deliverables for testing."""
    project = Project(name="test-project", workflow_type="auto-code", brief="test brief")
    async_session.add(project)
    await async_session.flush()

    workflow = Workflow(
        workflow_type="auto-code",
        params={},
        status=WorkflowStatus.RUNNING,
    )
    async_session.add(workflow)
    await async_session.flush()

    deliverables: list[Deliverable] = []
    for spec in deliverable_specs:
        d = Deliverable(
            name=str(spec.get("name", f"d-{uuid.uuid4().hex[:6]}")),
            status=spec.get("status", DeliverableStatus.PENDING),  # type: ignore[arg-type]
            project_id=project.id,
            workflow_id=workflow.id,
            depends_on=spec.get("depends_on", []),  # type: ignore[arg-type]
            retry_count=spec.get("retry_count", 0),  # type: ignore[arg-type]
            execution_order=spec.get("execution_order"),  # type: ignore[arg-type]
        )
        async_session.add(d)
        deliverables.append(d)

    await async_session.commit()
    for d in deliverables:
        await async_session.refresh(d)
    await async_session.refresh(project)
    return project, workflow, deliverables


async def _create_test_project(
    session: AsyncSession,
    *,
    name: str = "test-project",
    status: ProjectStatus = ProjectStatus.SHAPING,
    workflow_type: str = "auto-code",
) -> Project:
    """Insert a Project row and return it."""
    project = Project(name=name, workflow_type=workflow_type, brief="Test brief", status=status)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def _create_test_workflow(session: AsyncSession) -> Workflow:
    """Insert a Workflow row and return it."""
    wf = Workflow(workflow_type="auto-code", status=WorkflowStatus.RUNNING)
    session.add(wf)
    await session.commit()
    await session.refresh(wf)
    return wf


async def _create_test_deliverable(
    session: AsyncSession,
    workflow_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    name: str = "deliverable-1",
    status: DeliverableStatus = DeliverableStatus.PENDING,
    depends_on: list[str] | None = None,
) -> Deliverable:
    """Insert a Deliverable row and return it."""
    d = Deliverable(
        workflow_id=workflow_id,
        project_id=project_id,
        name=name,
        status=status,
        depends_on=depends_on or [],
    )
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Director: escalate_to_ceo -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestEscalateToCeo:
    @pytest.mark.asyncio
    async def test_creates_real_db_record(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        result = await escalate_to_ceo(
            db_tool_ctx,
            CeoItemType.NOTIFICATION,
            EscalationPriority.HIGH,
            "Test escalation from real DB test",
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert "item_id" in data
        assert data["type"] == CeoItemType.NOTIFICATION.value
        assert data["priority"] == EscalationPriority.HIGH.value

        from sqlalchemy import select

        stmt = select(CeoQueueItem).where(CeoQueueItem.id == data["item_id"])
        row = (await async_session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.type == CeoItemType.NOTIFICATION
        assert row.priority == EscalationPriority.HIGH
        assert row.status == CeoQueueStatus.PENDING

    @pytest.mark.asyncio
    async def test_with_custom_metadata(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        result = await escalate_to_ceo(
            db_tool_ctx,
            CeoItemType.TASK,
            EscalationPriority.NORMAL,
            "Task with metadata",
            metadata='{"key": "value"}',
        )
        data = json.loads(result)
        assert data["status"] == "ok"

        from sqlalchemy import select

        stmt = select(CeoQueueItem).where(CeoQueueItem.id == data["item_id"])
        row = (await async_session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.metadata_.get("key") == "value"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_invalid_metadata_returns_error(self, db_tool_ctx: MagicMock) -> None:
        result = await escalate_to_ceo(
            db_tool_ctx,
            CeoItemType.NOTIFICATION,
            EscalationPriority.LOW,
            "msg",
            metadata="not-json{",
        )
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_invalid_item_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            CeoItemType("BOGUS")

    def test_invalid_priority_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            EscalationPriority("EXTREME")


# ---------------------------------------------------------------------------
# PM: escalate_to_director -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestEscalateToDirector:
    @pytest.mark.asyncio
    async def test_creates_real_db_record(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        result = await escalate_to_director(
            db_tool_ctx,
            priority=EscalationPriority.HIGH,
            context="Architecture needs review",
            request_type=EscalationRequestType.ESCALATION,
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert "item_id" in data
        assert data["type"] == EscalationRequestType.ESCALATION.value
        assert data["priority"] == EscalationPriority.HIGH.value

        from sqlalchemy import select

        stmt = select(DirectorQueueItem).where(DirectorQueueItem.id == data["item_id"])
        row = (await async_session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert row.type == EscalationRequestType.ESCALATION
        assert row.priority == EscalationPriority.HIGH
        assert row.status == DirectorQueueStatus.PENDING
        assert row.source_agent == "pm"
        assert "Architecture" in row.context

    @pytest.mark.asyncio
    async def test_reads_project_id_from_state(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project_id = str(uuid.uuid4())
        # Create a real Project row so the FK constraint is satisfied
        project = Project(
            id=uuid.UUID(project_id),
            name="test-project",
            workflow_type="default",
            brief="Test brief",
            status=ProjectStatus.ACTIVE,
        )
        async_session.add(project)
        await async_session.commit()

        db_tool_ctx.state["pm:project_id"] = project_id

        result = await escalate_to_director(
            db_tool_ctx,
            priority=EscalationPriority.NORMAL,
            context="Need resources",
            request_type=EscalationRequestType.RESOURCE_REQUEST,
        )
        data = json.loads(result)
        assert data["status"] == "ok"

        from sqlalchemy import select

        stmt = select(DirectorQueueItem).where(DirectorQueueItem.id == data["item_id"])
        row = (await async_session.execute(stmt)).scalar_one_or_none()
        assert row is not None
        assert str(row.source_project_id) == project_id

    def test_invalid_request_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            EscalationRequestType("INVALID_TYPE")


# ---------------------------------------------------------------------------
# PM: select_ready_batch -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestSelectReadyBatchReal:
    @pytest.mark.asyncio
    async def test_returns_ready_deliverables(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [
                {"name": "d1", "status": DeliverableStatus.PENDING},
                {"name": "d2", "status": DeliverableStatus.PENDING},
            ],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert "batch" in data
        assert len(data["batch"]) == 1
        assert data["batch"][0]["name"] == "d1"
        assert data["total_ready"] == 1
        assert data["total_remaining"] == 2

    @pytest.mark.asyncio
    async def test_completed_deps_are_satisfied(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [
                {"name": "d1", "status": DeliverableStatus.COMPLETED},
                {"name": "d2", "status": DeliverableStatus.PENDING},
            ],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert len(data["batch"]) == 1
        assert data["batch"][0]["name"] == "d2"
        assert data["total_remaining"] == 1

    @pytest.mark.asyncio
    async def test_failed_with_retries_remaining_is_actionable(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, _ = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.FAILED, "retry_count": 1}],
        )

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert len(data["batch"]) == 1
        assert data["batch"][0]["name"] == "d1"

    @pytest.mark.asyncio
    async def test_failed_exhausted_retries_excluded(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, _ = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.FAILED, "retry_count": 3}],
        )

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert len(data["batch"]) == 0

    @pytest.mark.asyncio
    async def test_empty_project(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        project = Project(name="empty", workflow_type="auto-code", brief="empty")
        async_session.add(project)
        await async_session.commit()

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["batch"] == []
        assert data["total_ready"] == 0

    @pytest.mark.asyncio
    async def test_invalid_uuid(self, db_tool_ctx: MagicMock) -> None:
        result = await select_ready_batch(db_tool_ctx, "not-a-uuid")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_planned_status_is_actionable(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, _ = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.PLANNED}],
        )

        result = await select_ready_batch(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert len(data["batch"]) == 1


# ---------------------------------------------------------------------------
# PM: update_deliverable -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestUpdateDeliverableReal:
    @pytest.mark.asyncio
    async def test_valid_transition_pending_to_in_progress(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.PENDING}],
        )
        d1 = deliverables[0]

        result = await update_deliverable(db_tool_ctx, str(d1.id), "IN_PROGRESS")
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["new_status"] == "IN_PROGRESS"
        assert data["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_valid_transition_in_progress_to_completed(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.IN_PROGRESS}],
        )
        d1 = deliverables[0]

        result = await update_deliverable(db_tool_ctx, str(d1.id), "COMPLETED")
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["new_status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_retry_increments_count(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.FAILED, "retry_count": 1}],
        )
        d1 = deliverables[0]

        result = await update_deliverable(db_tool_ctx, str(d1.id), "IN_PROGRESS")
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1", "status": DeliverableStatus.COMPLETED}],
        )
        d1 = deliverables[0]

        result = await update_deliverable(db_tool_ctx, str(d1.id), "IN_PROGRESS")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_TRANSITION"

    @pytest.mark.asyncio
    async def test_nonexistent_deliverable(self, db_tool_ctx: MagicMock) -> None:
        fake_id = str(uuid.uuid4())
        result = await update_deliverable(db_tool_ctx, fake_id, "IN_PROGRESS")
        data = json.loads(result)
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_uuid(self, db_tool_ctx: MagicMock) -> None:
        result = await update_deliverable(db_tool_ctx, "bad-uuid", "IN_PROGRESS")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_invalid_status_value(self, db_tool_ctx: MagicMock) -> None:
        result = await update_deliverable(db_tool_ctx, str(uuid.uuid4()), "BOGUS")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "BOGUS" in data["error"]["message"]


# ---------------------------------------------------------------------------
# PM: query_deliverables -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestQueryDeliverablesReal:
    @pytest.mark.asyncio
    async def test_returns_all_deliverables(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, _ = await _create_project_with_deliverables(
            async_session,
            [
                {"name": "d1", "status": DeliverableStatus.PENDING, "execution_order": 0},
                {"name": "d2", "status": DeliverableStatus.COMPLETED, "execution_order": 1},
            ],
        )

        result = await query_deliverables(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["total"] == 2
        assert len(data["deliverables"]) == 2
        assert data["deliverables"][0]["name"] == "d1"
        assert data["deliverables"][1]["name"] == "d2"

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, _ = await _create_project_with_deliverables(
            async_session,
            [
                {"name": "d1", "status": DeliverableStatus.PENDING},
                {"name": "d2", "status": DeliverableStatus.COMPLETED},
            ],
        )

        result = await query_deliverables(db_tool_ctx, str(project.id), status="COMPLETED")
        data = json.loads(result)
        assert data["total"] == 1
        assert data["deliverables"][0]["name"] == "d2"

    @pytest.mark.asyncio
    async def test_invalid_project_uuid(self, db_tool_ctx: MagicMock) -> None:
        result = await query_deliverables(db_tool_ctx, "bad-uuid")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_invalid_status_filter(self, db_tool_ctx: MagicMock) -> None:
        result = await query_deliverables(db_tool_ctx, str(uuid.uuid4()), status="BOGUS")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_empty_project(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        project = Project(name="empty", workflow_type="auto-code", brief="empty")
        async_session.add(project)
        await async_session.commit()

        result = await query_deliverables(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["total"] == 0
        assert data["deliverables"] == []


# ---------------------------------------------------------------------------
# PM: reorder_deliverables -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestReorderDeliverablesReal:
    @pytest.mark.asyncio
    async def test_reorders_successfully(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [
                {"name": "d1", "execution_order": 0},
                {"name": "d2", "execution_order": 1},
                {"name": "d3", "execution_order": 2},
            ],
        )
        d1, d2, d3 = deliverables

        new_order = [str(d3.id), str(d2.id), str(d1.id)]
        result = await reorder_deliverables(db_tool_ctx, str(project.id), new_order)
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["reordered"] == 3

        # Expire cached state so we see the tool's committed changes
        async_session.expire_all()

        from sqlalchemy import select

        for idx, did in enumerate(new_order):
            stmt = select(Deliverable).where(Deliverable.id == uuid.UUID(did))
            row = (await async_session.execute(stmt)).scalar_one()
            assert row.execution_order == idx

    @pytest.mark.asyncio
    async def test_invalid_deliverable_id(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}],
        )

        fake_id = str(uuid.uuid4())
        result = await reorder_deliverables(
            db_tool_ctx, str(project.id), [str(deliverables[0].id), fake_id]
        )
        data = json.loads(result)
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_uuid_in_order(self, db_tool_ctx: MagicMock) -> None:
        result = await reorder_deliverables(db_tool_ctx, str(uuid.uuid4()), ["bad-uuid"])
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_invalid_project_uuid(self, db_tool_ctx: MagicMock) -> None:
        result = await reorder_deliverables(db_tool_ctx, "bad-uuid", [])
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# PM: manage_dependencies -- REAL DB
# ---------------------------------------------------------------------------


@require_infra
class TestManageDependenciesReal:
    @pytest.mark.asyncio
    async def test_add_dependency(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.ADD,
            source_id=str(d2.id),
            target_id=str(d1.id),
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["action"] == "ADD"
        assert str(d1.id) in data["depends_on"]

    @pytest.mark.asyncio
    async def test_remove_dependency(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.REMOVE,
            source_id=str(d2.id),
            target_id=str(d1.id),
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["action"] == "REMOVE"
        assert str(d1.id) not in data["depends_on"]

    @pytest.mark.asyncio
    async def test_query_dependencies(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.QUERY,
            source_id=str(d2.id),
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert str(d1.id) in data["depends_on"]

    @pytest.mark.asyncio
    async def test_cycle_detection(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.ADD,
            source_id=str(d1.id),
            target_id=str(d2.id),
        )
        data = json.loads(result)
        assert data["error"]["code"] == "CYCLE_DETECTED"

    @pytest.mark.asyncio
    async def test_add_duplicate_is_idempotent(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables
        d2.depends_on = [str(d1.id)]
        await async_session.commit()

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.ADD,
            source_id=str(d2.id),
            target_id=str(d1.id),
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert "already exists" in data.get("message", "")

    @pytest.mark.asyncio
    async def test_add_without_target_returns_error(self, tool_ctx: MagicMock) -> None:
        result = await manage_dependencies(tool_ctx, action=DependencyAction.ADD, source_id="d1")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "target_id" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_remove_without_target_returns_error(self, tool_ctx: MagicMock) -> None:
        result = await manage_dependencies(tool_ctx, action=DependencyAction.REMOVE, source_id="d1")
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_remove_nonexistent_dep(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        _, _, deliverables = await _create_project_with_deliverables(
            async_session,
            [{"name": "d1"}, {"name": "d2"}],
        )
        d1, d2 = deliverables

        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.REMOVE,
            source_id=str(d2.id),
            target_id=str(d1.id),
        )
        data = json.loads(result)
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_nonexistent_source(self, db_tool_ctx: MagicMock) -> None:
        fake_id = str(uuid.uuid4())
        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.QUERY,
            source_id=fake_id,
        )
        data = json.loads(result)
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_source_uuid(self, db_tool_ctx: MagicMock) -> None:
        result = await manage_dependencies(
            db_tool_ctx,
            action=DependencyAction.QUERY,
            source_id="bad-uuid",
        )
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_invalid_action_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            DependencyAction("NUKE")


# ---------------------------------------------------------------------------
# Director: override_pm
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Director D4 tests
# ---------------------------------------------------------------------------


@require_infra
class TestCreateProject:
    @pytest.mark.asyncio
    async def test_creates_project(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        result = await create_project(
            db_tool_ctx,
            name="P1",
            workflow_type="auto-code",
            brief="Build",
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["entry_mode"] == "new"
        from sqlalchemy import select as sel

        stmt = sel(Project).where(Project.id == uuid.UUID(data["project_id"]))
        row = (await async_session.execute(stmt)).scalar_one()
        assert row.status == ProjectStatus.SHAPING


@require_infra
class TestValidateBrief:
    @pytest.mark.asyncio
    async def test_complete_brief(self, db_tool_ctx_with_registry: MagicMock) -> None:
        brief = json.dumps({"objective": "X", "acceptance_criteria": "Y", "scope_constraints": "Z"})
        data = json.loads(await validate_brief(db_tool_ctx_with_registry, brief, "auto-code"))
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_incomplete_brief(self, db_tool_ctx_with_registry: MagicMock) -> None:
        brief = json.dumps({"objective": "X"})
        data = json.loads(await validate_brief(db_tool_ctx_with_registry, brief, "auto-code"))
        assert data["status"] == "validation_failed"

    @pytest.mark.asyncio
    async def test_missing_workflow(self, db_tool_ctx_with_registry: MagicMock) -> None:
        data = json.loads(await validate_brief(db_tool_ctx_with_registry, "x", "no-exist"))
        assert data["error"]["code"] == "WORKFLOW_NOT_FOUND"


@require_infra
class TestCheckResources:
    @pytest.mark.asyncio
    async def test_cred_present(
        self, db_tool_ctx_with_registry: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        data = json.loads(await check_resources(db_tool_ctx_with_registry, "auto-code"))
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_cred_missing(
        self, db_tool_ctx_with_registry: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        data = json.loads(await check_resources(db_tool_ctx_with_registry, "auto-code"))
        assert data["status"] == "resources_failed"

    @pytest.mark.asyncio
    async def test_bad_workflow(self, db_tool_ctx_with_registry: MagicMock) -> None:
        data = json.loads(await check_resources(db_tool_ctx_with_registry, "no-exist"))
        assert data["error"]["code"] == "WORKFLOW_NOT_FOUND"


@require_infra
class TestDelegateToPm:
    @pytest.mark.asyncio
    async def test_ok(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        p = await _create_test_project(async_session, status=ProjectStatus.SHAPING)
        data = json.loads(await delegate_to_pm(db_tool_ctx, str(p.id)))
        assert data["status"] == "ok"
        assert data["new_status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_rejects_active(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        p = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        data = json.loads(await delegate_to_pm(db_tool_ctx, str(p.id)))
        assert data["error"]["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_not_found(self, db_tool_ctx: MagicMock) -> None:
        data = json.loads(await delegate_to_pm(db_tool_ctx, str(uuid.uuid4())))
        assert data["error"]["code"] == "NOT_FOUND"


@require_infra
class TestListProjectsD4:
    @pytest.mark.asyncio
    async def test_all(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        await _create_test_project(async_session, name="a")
        await _create_test_project(async_session, name="b", status=ProjectStatus.ACTIVE)
        data = json.loads(await list_projects(db_tool_ctx))
        assert len(data["projects"]) >= 2

    @pytest.mark.asyncio
    async def test_filter(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        await _create_test_project(async_session, name="s")
        await _create_test_project(async_session, name="a", status=ProjectStatus.ACTIVE)
        data = json.loads(await list_projects(db_tool_ctx, status="ACTIVE"))
        assert all(p["status"] == "ACTIVE" for p in data["projects"])

    @pytest.mark.asyncio
    async def test_invalid_status(self, db_tool_ctx: MagicMock) -> None:
        data = json.loads(await list_projects(db_tool_ctx, status="BOGUS"))
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "BOGUS" in data["error"]["message"]


@require_infra
class TestQueryProjectStatusD4:
    @pytest.mark.asyncio
    async def test_with_deliverables(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        p = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        wf = await _create_test_workflow(async_session)
        await _create_test_deliverable(
            async_session,
            wf.id,
            p.id,
            name="d1",
            status=DeliverableStatus.COMPLETED,
        )
        await _create_test_deliverable(
            async_session,
            wf.id,
            p.id,
            name="d2",
            status=DeliverableStatus.PENDING,
        )
        data = json.loads(await query_project_status(db_tool_ctx, str(p.id)))
        assert data["status"] == "ok"
        assert data["deliverables"]["total"] == 2

    @pytest.mark.asyncio
    async def test_not_found(self, db_tool_ctx: MagicMock) -> None:
        data = json.loads(await query_project_status(db_tool_ctx, str(uuid.uuid4())))
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_includes_duration_and_taskgroup(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        from datetime import UTC, datetime, timedelta

        started = datetime.now(UTC) - timedelta(hours=1)
        p = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        p.started_at = started
        await async_session.commit()
        await async_session.refresh(p)

        data = json.loads(await query_project_status(db_tool_ctx, str(p.id)))
        assert data["status"] == "ok"
        project_data = data["project"]
        assert "duration_seconds" in project_data
        assert project_data["duration_seconds"] >= 3600.0
        assert "current_taskgroup_id" in project_data
        assert project_data["current_taskgroup_id"] is None


@require_infra
class TestOverridePm:
    def test_invalid_action_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            PmOverrideAction("DESTROY")

    @pytest.mark.asyncio
    async def test_pause_active_project(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        result = await override_pm(
            db_tool_ctx,
            project_id=str(project.id),
            action=PmOverrideAction.PAUSE,
            reason="needs review",
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["action"] == "PAUSE"
        assert data["new_status"] == "PAUSED"

        # Verify DB status changed
        from sqlalchemy import select as sel

        project_id = project.id  # capture before expire_all invalidates the instance
        async_session.expire_all()  # Force fresh read from DB
        p = (await async_session.execute(sel(Project).where(Project.id == project_id))).scalar_one()
        assert p.status == ProjectStatus.PAUSED

    @pytest.mark.asyncio
    async def test_resume_paused_project(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project = await _create_test_project(async_session, status=ProjectStatus.PAUSED)
        result = await override_pm(
            db_tool_ctx,
            project_id=str(project.id),
            action=PmOverrideAction.RESUME,
            reason="ready to continue",
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["action"] == "RESUME"
        assert data["new_status"] == "ACTIVE"

        # Verify DB status changed
        from sqlalchemy import select as sel

        project_id = project.id  # capture before expire_all invalidates the instance
        async_session.expire_all()  # Force fresh read from DB
        p = (await async_session.execute(sel(Project).where(Project.id == project_id))).scalar_one()
        assert p.status == ProjectStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_pause_non_active_rejected(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project = await _create_test_project(async_session, status=ProjectStatus.SHAPING)
        result = await override_pm(
            db_tool_ctx,
            project_id=str(project.id),
            action=PmOverrideAction.PAUSE,
            reason="too early",
        )
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_resume_non_paused_rejected(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        result = await override_pm(
            db_tool_ctx,
            project_id=str(project.id),
            action=PmOverrideAction.RESUME,
            reason="not paused",
        )
        data = json.loads(result)
        assert data["error"]["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_not_found(self, db_tool_ctx: MagicMock) -> None:
        result = await override_pm(
            db_tool_ctx,
            project_id=str(uuid.uuid4()),
            action=PmOverrideAction.PAUSE,
            reason="test",
        )
        data = json.loads(result)
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_reorder_records_audit(
        self, db_tool_ctx: MagicMock, async_session: AsyncSession
    ) -> None:
        project = await _create_test_project(async_session, status=ProjectStatus.ACTIVE)
        result = await override_pm(
            db_tool_ctx,
            project_id=str(project.id),
            action=PmOverrideAction.REORDER,
            reason="priority change",
        )
        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["action"] == "REORDER"
        assert "message" in data


# ---------------------------------------------------------------------------
# Director: get_project_context (filesystem, no DB needed)
# ---------------------------------------------------------------------------


class TestGetProjectContext:
    @pytest.mark.asyncio
    async def test_detects_python_project(self, tool_ctx: MagicMock, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\ndependencies = ["fastapi", "uvicorn"]\n')

        result = await get_project_context(tool_ctx, str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "ok"
        assert len(data["projects"]) == 1
        proj = data["projects"][0]
        assert proj["language"] == "Python"
        assert proj["name"] == "myapp"
        assert "fastapi" in proj["dependencies"]

    @pytest.mark.asyncio
    async def test_detects_node_project(self, tool_ctx: MagicMock, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "my-dashboard", "dependencies": {"react": "^19.0.0"}}))

        result = await get_project_context(tool_ctx, str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "ok"
        assert len(data["projects"]) == 1
        proj = data["projects"][0]
        assert proj["language"] == "JavaScript/TypeScript"
        assert proj["name"] == "my-dashboard"
        assert "react" in proj["dependencies"]

    @pytest.mark.asyncio
    async def test_detects_rust_project(self, tool_ctx: MagicMock, tmp_path: Path) -> None:
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "myapp"\n')
        result = await get_project_context(tool_ctx, str(tmp_path))
        data = json.loads(result)
        assert data["status"] == "ok"
        assert any(p["language"] == "Rust" for p in data["projects"])


# ---------------------------------------------------------------------------
# Director: query_dependency_graph
# ---------------------------------------------------------------------------


@require_infra
class TestQueryDependencyGraph:
    @pytest.mark.asyncio
    async def test_builds_graph(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        project = await _create_test_project(async_session)
        wf = await _create_test_workflow(async_session)
        d1 = await _create_test_deliverable(async_session, wf.id, project.id, name="f1")
        await _create_test_deliverable(
            async_session,
            wf.id,
            project.id,
            name="f2",
            depends_on=[str(d1.id)],
        )
        result = await query_dependency_graph(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["status"] == "ok"
        assert len(data["nodes"]) == 2
        assert data["has_cycles"] is False

    @pytest.mark.asyncio
    async def test_detects_cycle(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        project = await _create_test_project(async_session)
        wf = await _create_test_workflow(async_session)
        id_a, id_b = uuid.uuid4(), uuid.uuid4()
        async_session.add_all(
            [
                Deliverable(
                    id=id_a,
                    workflow_id=wf.id,
                    project_id=project.id,
                    name="A",
                    depends_on=[str(id_b)],
                ),
                Deliverable(
                    id=id_b,
                    workflow_id=wf.id,
                    project_id=project.id,
                    name="B",
                    depends_on=[str(id_a)],
                ),
            ]
        )
        await async_session.commit()
        result = await query_dependency_graph(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["has_cycles"] is True

    @pytest.mark.asyncio
    async def test_empty(self, db_tool_ctx: MagicMock, async_session: AsyncSession) -> None:
        project = await _create_test_project(async_session)
        result = await query_dependency_graph(db_tool_ctx, str(project.id))
        data = json.loads(result)
        assert data["nodes"] == []


# ---------------------------------------------------------------------------
# Cross-cutting: remaining stubs return structured JSON
# ---------------------------------------------------------------------------


class TestToolsReturnStructuredJson:
    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_structured_error(self, tool_ctx: MagicMock) -> None:
        """Tools with invalid UUIDs return structured JSON errors."""
        results = [
            await override_pm(tool_ctx, "bad-uuid", PmOverrideAction.PAUSE, "reason"),
            await query_dependency_graph(tool_ctx, "bad-uuid"),
        ]
        for result in results:
            data = json.loads(result)
            assert "error" in data
            assert data["error"]["code"] == "INVALID_INPUT"
