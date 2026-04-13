"""Tests for supervision callbacks."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.supervision import (
    BATCH_FAILURE_THRESHOLD_KEY,
    create_after_pm_callback,
    create_batch_verification_callback,
    create_before_pm_callback,
    create_checkpoint_callback,
    evaluate_failure_impact,
    handle_deliverable_failure,
    suspend_project,
    track_batch_result,
)
from app.db.models import Deliverable, Project, Workflow
from app.models.constants import (
    BATCH_RESULT_KEY,
    DELIVERABLE_STATUS_PREFIX,
    PM_ESCALATION_CONTEXT_KEY,
)
from app.models.enums import (
    DeliverableStatus,
    ProjectStatus,
    WorkflowStatus,
)
from tests.conftest import require_infra


def _make_ctx(state: dict[str, object] | None = None) -> SimpleNamespace:
    """Mock CallbackContext with dict-based state and agent_name."""
    return SimpleNamespace(
        state=state if state is not None else {},
        agent_name="test_agent",
    )


class MockEventPublisher:
    """Records publish_lifecycle and publish_project_status_changed calls for assertion."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object] | None]] = []

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append((workflow_id, str(event_type), metadata))

    async def publish_project_status_changed(
        self,
        workflow_id: str,
        project_id: str,
        old_status: object,
        new_status: object,
        actor: str | None = None,
        scope: str | None = None,
    ) -> None:
        self.events.append(
            (
                workflow_id,
                "project_status_changed",
                {"project_id": project_id, "old_status": old_status, "new_status": new_status},
            )
        )


# ---------------------------------------------------------------------------
# before_pm_execution
# ---------------------------------------------------------------------------


class TestBeforePmCallback:
    @pytest.mark.asyncio
    async def test_within_limits_proceeds(self) -> None:
        """Under budget -> returns None (proceed)."""
        publisher = MockEventPublisher()
        cb = create_before_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "project_config": {"retry_budget": 10, "cost_ceiling": 100.0},
                "pm:retry_count": 2,
                "pm:total_cost": 10.0,
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None

    @pytest.mark.asyncio
    async def test_cost_exceeded_blocks(self) -> None:
        """Cost >= ceiling -> returns Content blocking PM."""
        publisher = MockEventPublisher()
        cb = create_before_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "project_config": {"retry_budget": 10, "cost_ceiling": 50.0},
                "pm:retry_count": 0,
                "pm:total_cost": 55.0,
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is not None
        text = result.parts[0].text  # type: ignore[union-attr]
        assert text is not None
        assert "cost ceiling exceeded" in text
        assert PM_ESCALATION_CONTEXT_KEY in ctx.state

    @pytest.mark.asyncio
    async def test_retries_exceeded_blocks(self) -> None:
        """Retries >= budget -> returns Content blocking PM."""
        publisher = MockEventPublisher()
        cb = create_before_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "project_config": {"retry_budget": 5, "cost_ceiling": 100.0},
                "pm:retry_count": 5,
                "pm:total_cost": 0.0,
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is not None
        text = result.parts[0].text  # type: ignore[union-attr]
        assert text is not None
        assert "retry budget exhausted" in text
        assert PM_ESCALATION_CONTEXT_KEY in ctx.state

    @pytest.mark.asyncio
    async def test_default_limits_when_no_config(self) -> None:
        """No project_config -> uses defaults, proceeds under limits."""
        publisher = MockEventPublisher()
        cb = create_before_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx({"workflow_id": "wf-1"})

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None


# ---------------------------------------------------------------------------
# after_pm_execution
# ---------------------------------------------------------------------------


class TestAfterPmCallback:
    @pytest.mark.asyncio
    async def test_detects_escalation(self) -> None:
        """Escalation context in state -> publishes escalation event."""
        publisher = MockEventPublisher()
        cb = create_after_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "pm:status": "blocked",
                PM_ESCALATION_CONTEXT_KEY: "Need approval for X",
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None  # Observation only

        # Should have completion + escalation events
        escalation_events = [
            e
            for e in publisher.events
            if e[2] and "ESCALATION_DETECTED" in str(e[2].get("supervision_event", ""))
        ]
        assert len(escalation_events) == 1

    @pytest.mark.asyncio
    async def test_no_escalation_clean(self) -> None:
        """No escalation -> returns None, no escalation event."""
        publisher = MockEventPublisher()
        cb = create_after_pm_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "pm:status": "completed",
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None

        escalation_events = [
            e
            for e in publisher.events
            if e[2] and "ESCALATION_DETECTED" in str(e[2].get("supervision_event", ""))
        ]
        assert len(escalation_events) == 0


# ---------------------------------------------------------------------------
# checkpoint_project
# ---------------------------------------------------------------------------


class TestCheckpointCallback:
    @pytest.mark.asyncio
    async def test_persists_deliverable_status(self) -> None:
        """Writes deliverable_status:{id} to state."""
        publisher = MockEventPublisher()
        cb = create_checkpoint_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "current_deliverable_id": "del-42",
                "pipeline_output": {"failed": False},
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None
        assert ctx.state[f"{DELIVERABLE_STATUS_PREFIX}del-42"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_fires_on_failure_too(self) -> None:
        """Status persisted as FAILED when pipeline reports failure."""
        publisher = MockEventPublisher()
        cb = create_checkpoint_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "current_deliverable_id": "del-99",
                "pipeline_output": {"failed": True},
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None
        assert ctx.state[f"{DELIVERABLE_STATUS_PREFIX}del-99"] == "FAILED"

    @pytest.mark.asyncio
    async def test_no_deliverable_id_skips(self) -> None:
        """No deliverable ID -> returns None without writing."""
        publisher = MockEventPublisher()
        cb = create_checkpoint_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx({"workflow_id": "wf-1"})

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None
        # No deliverable_status keys written
        status_keys = [k for k in ctx.state if k.startswith(DELIVERABLE_STATUS_PREFIX)]
        assert len(status_keys) == 0


# ---------------------------------------------------------------------------
# verify_batch_completion
# ---------------------------------------------------------------------------


class TestBatchVerificationCallback:
    @pytest.mark.asyncio
    async def test_all_terminal(self) -> None:
        """All deliverables terminal -> batch result correct."""
        publisher = MockEventPublisher()
        cb = create_batch_verification_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "current_batch_id": "batch-1",
                "current_batch_deliverables": ["d1", "d2", "d3"],
                f"{DELIVERABLE_STATUS_PREFIX}d1": "COMPLETED",
                f"{DELIVERABLE_STATUS_PREFIX}d2": "COMPLETED",
                f"{DELIVERABLE_STATUS_PREFIX}d3": "FAILED",
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None

        batch_result = ctx.state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is True
        assert batch_result["completed"] == 2
        assert batch_result["failed"] == 1
        assert batch_result["total"] == 3

    @pytest.mark.asyncio
    async def test_skipped_is_terminal(self) -> None:
        """SKIPPED deliverables count as terminal (PM can skip blocked work)."""
        publisher = MockEventPublisher()
        cb = create_batch_verification_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "current_batch_id": "batch-skip",
                "current_batch_deliverables": ["d1", "d2"],
                f"{DELIVERABLE_STATUS_PREFIX}d1": "COMPLETED",
                f"{DELIVERABLE_STATUS_PREFIX}d2": "SKIPPED",
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None

        batch_result = ctx.state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is True
        assert batch_result["completed"] == 1

    @pytest.mark.asyncio
    async def test_partial(self) -> None:
        """Some pending -> all_terminal = False."""
        publisher = MockEventPublisher()
        cb = create_batch_verification_callback(publisher)  # type: ignore[arg-type]
        ctx = _make_ctx(
            {
                "workflow_id": "wf-1",
                "current_batch_id": "batch-2",
                "current_batch_deliverables": ["d1", "d2"],
                f"{DELIVERABLE_STATUS_PREFIX}d1": "COMPLETED",
                # d2 has no status -> defaults to PENDING
            }
        )

        result = await cb(ctx)  # type: ignore[arg-type]
        assert result is None

        batch_result = ctx.state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is False
        assert batch_result["completed"] == 1
        assert batch_result["failed"] == 0


# ---------------------------------------------------------------------------
# Helpers for infra tests
# ---------------------------------------------------------------------------


def _make_session_factory(engine: object) -> async_sessionmaker[AsyncSession]:

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]


async def _create_workflow(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    """Insert a minimal Workflow and return its ID."""
    async with factory() as db:
        wf = Workflow(workflow_type="test", status=WorkflowStatus.RUNNING)
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return wf.id


async def _create_project(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    """Insert a minimal Project and return its ID."""
    async with factory() as db:
        proj = Project(name="test-project", workflow_type="test", brief="test brief")
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        return proj.id


async def _create_deliverable(
    factory: async_sessionmaker[AsyncSession],
    workflow_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    name: str = "d1",
    status: DeliverableStatus = DeliverableStatus.PENDING,
    retry_count: int = 0,
    depends_on: list[str] | None = None,
) -> uuid.UUID:
    """Insert a Deliverable and return its ID."""
    async with factory() as db:
        d = Deliverable(
            workflow_id=workflow_id,
            project_id=project_id,
            name=name,
            status=status,
            retry_count=retry_count,
            depends_on=depends_on or [],
        )
        db.add(d)
        await db.commit()
        await db.refresh(d)
        return d.id


# ---------------------------------------------------------------------------
# TestHandleDeliverableFailure
# ---------------------------------------------------------------------------


@require_infra
class TestHandleDeliverableFailure:
    @pytest.mark.asyncio
    async def test_retry_within_limit(self, engine: object) -> None:
        """retry_count < retry_limit -> status IN_PROGRESS, count incremented, returns 'retry'."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        proj_id = await _create_project(factory)
        d_id = await _create_deliverable(
            factory, wf_id, proj_id, status=DeliverableStatus.FAILED, retry_count=0
        )

        result = await handle_deliverable_failure(d_id, retry_limit=2, db_session_factory=factory)
        assert result == "retry"

        async with factory() as db:
            row = (await db.execute(select(Deliverable).where(Deliverable.id == d_id))).scalar_one()
            assert row.status == DeliverableStatus.IN_PROGRESS
            assert row.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, engine: object) -> None:
        """retry_count >= retry_limit -> status FAILED, returns 'failed'."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        proj_id = await _create_project(factory)
        d_id = await _create_deliverable(
            factory, wf_id, proj_id, status=DeliverableStatus.FAILED, retry_count=2
        )

        result = await handle_deliverable_failure(d_id, retry_limit=2, db_session_factory=factory)
        assert result == "failed"

        async with factory() as db:
            row = (await db.execute(select(Deliverable).where(Deliverable.id == d_id))).scalar_one()
            assert row.status == DeliverableStatus.FAILED

    @pytest.mark.asyncio
    async def test_nonexistent_deliverable(self, engine: object) -> None:
        """Unknown deliverable ID -> returns 'error'."""
        factory = _make_session_factory(engine)
        fake_id = uuid.uuid4()

        result = await handle_deliverable_failure(
            fake_id, retry_limit=2, db_session_factory=factory
        )
        assert result == "error"


# ---------------------------------------------------------------------------
# TestEvaluateFailureImpact
# ---------------------------------------------------------------------------


@require_infra
class TestEvaluateFailureImpact:
    @pytest.mark.asyncio
    async def test_independent_work_identified(self, engine: object) -> None:
        """Deliverable with no deps on failed one -> appears in independent list."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        proj_id = await _create_project(factory)

        failed_id = await _create_deliverable(
            factory, wf_id, proj_id, name="failed", status=DeliverableStatus.FAILED
        )
        indep_id = await _create_deliverable(
            factory, wf_id, proj_id, name="independent", status=DeliverableStatus.PENDING
        )

        result = await evaluate_failure_impact(proj_id, failed_id, factory)
        assert str(indep_id) in result["independent"]
        assert str(failed_id) not in result["independent"]
        assert str(failed_id) not in result["blocked"]

    @pytest.mark.asyncio
    async def test_blocked_work_identified(self, engine: object) -> None:
        """Deliverable that depends on failed one -> appears in blocked list."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        proj_id = await _create_project(factory)

        failed_id = await _create_deliverable(
            factory, wf_id, proj_id, name="failed", status=DeliverableStatus.FAILED
        )
        blocked_id = await _create_deliverable(
            factory,
            wf_id,
            proj_id,
            name="blocked",
            status=DeliverableStatus.PENDING,
            depends_on=[str(failed_id)],
        )

        result = await evaluate_failure_impact(proj_id, failed_id, factory)
        assert str(blocked_id) in result["blocked"]
        assert str(blocked_id) not in result["independent"]

    @pytest.mark.asyncio
    async def test_chain_dependencies(self, engine: object) -> None:
        """Transitive chain A -> B -> C: if A fails, both B and C are blocked."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        proj_id = await _create_project(factory)

        a_id = await _create_deliverable(
            factory, wf_id, proj_id, name="a", status=DeliverableStatus.FAILED
        )
        b_id = await _create_deliverable(
            factory,
            wf_id,
            proj_id,
            name="b",
            status=DeliverableStatus.PENDING,
            depends_on=[str(a_id)],
        )
        c_id = await _create_deliverable(
            factory,
            wf_id,
            proj_id,
            name="c",
            status=DeliverableStatus.PENDING,
            depends_on=[str(b_id)],
        )

        result = await evaluate_failure_impact(proj_id, a_id, factory)
        assert str(b_id) in result["blocked"]
        assert str(c_id) in result["blocked"]
        assert str(a_id) not in result["blocked"]
        assert str(a_id) not in result["independent"]


# ---------------------------------------------------------------------------
# TestTrackBatchResult
# ---------------------------------------------------------------------------


@require_infra
class TestTrackBatchResult:
    @pytest.mark.asyncio
    async def test_successful_batch_resets_counter(self, engine: object) -> None:
        """Successful batch resets counter to 0 and returns 'ok'."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)
        state: dict[str, object] = {BATCH_FAILURE_THRESHOLD_KEY: 2}

        result = await track_batch_result(
            batch_had_failures=False,
            state=state,
            project_id=proj_id,
            db_session_factory=factory,
        )
        assert result == "ok"
        assert state[BATCH_FAILURE_THRESHOLD_KEY] == 0

    @pytest.mark.asyncio
    async def test_failed_batch_increments_counter(self, engine: object) -> None:
        """Failed batch increments counter and returns 'ok' while under threshold."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)
        state: dict[str, object] = {BATCH_FAILURE_THRESHOLD_KEY: 0}

        result = await track_batch_result(
            batch_had_failures=True,
            state=state,
            project_id=proj_id,
            db_session_factory=factory,
            threshold=3,
        )
        assert result == "ok"
        assert state[BATCH_FAILURE_THRESHOLD_KEY] == 1

    @pytest.mark.asyncio
    async def test_threshold_triggers(self, engine: object) -> None:
        """Counter reaching threshold returns 'threshold_exceeded'."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)
        state: dict[str, object] = {BATCH_FAILURE_THRESHOLD_KEY: 2}

        result = await track_batch_result(
            batch_had_failures=True,
            state=state,
            project_id=proj_id,
            db_session_factory=factory,
            threshold=3,
        )
        assert result == "threshold_exceeded"
        assert state[BATCH_FAILURE_THRESHOLD_KEY] == 3


# ---------------------------------------------------------------------------
# TestSuspendProject
# ---------------------------------------------------------------------------


@require_infra
class TestSuspendProject:
    @pytest.mark.asyncio
    async def test_project_status_changes_to_suspended(self, engine: object) -> None:
        """suspend_project sets status to SUSPENDED."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)

        await suspend_project(
            project_id=proj_id,
            reason="too many failures",
            db_session_factory=factory,
        )

        async with factory() as db:
            proj = (await db.execute(select(Project).where(Project.id == proj_id))).scalar_one()
            assert proj.status == ProjectStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_error_message_set(self, engine: object) -> None:
        """suspend_project writes reason to error_message column."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)

        reason = "Batch failure threshold exceeded"
        await suspend_project(
            project_id=proj_id,
            reason=reason,
            db_session_factory=factory,
        )

        async with factory() as db:
            proj = (await db.execute(select(Project).where(Project.id == proj_id))).scalar_one()
            assert proj.error_message == reason

    @pytest.mark.asyncio
    async def test_suspend_publishes_event_when_publisher_given(self, engine: object) -> None:
        """Publisher receives PROJECT_SUSPENDED event."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)
        publisher = MockEventPublisher()

        await suspend_project(
            project_id=proj_id,
            reason="threshold",
            db_session_factory=factory,
            publisher=publisher,  # type: ignore[arg-type]
        )

        assert len(publisher.events) == 1
        _, event_type, metadata = publisher.events[0]
        assert event_type == "project_status_changed"
        assert metadata is not None
        assert metadata.get("new_status") == ProjectStatus.SUSPENDED.value

    @pytest.mark.asyncio
    async def test_suspend_no_publisher_no_error(self, engine: object) -> None:
        """suspend_project works without a publisher (publisher=None)."""
        factory = _make_session_factory(engine)
        proj_id = await _create_project(factory)

        # Should not raise
        await suspend_project(
            project_id=proj_id,
            reason="no publisher",
            db_session_factory=factory,
        )
