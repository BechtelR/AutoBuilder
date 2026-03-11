"""Tests for supervision callbacks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.supervision import (
    create_after_pm_callback,
    create_batch_verification_callback,
    create_before_pm_callback,
    create_checkpoint_callback,
)
from app.models.constants import (
    BATCH_RESULT_KEY,
    DELIVERABLE_STATUS_PREFIX,
    PM_ESCALATION_CONTEXT_KEY,
)


def _make_ctx(state: dict[str, object] | None = None) -> SimpleNamespace:
    """Mock CallbackContext with dict-based state and agent_name."""
    return SimpleNamespace(
        state=state if state is not None else {},
        agent_name="test_agent",
    )


class MockEventPublisher:
    """Records publish_lifecycle calls for assertion."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object] | None]] = []

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append((workflow_id, str(event_type), metadata))


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
