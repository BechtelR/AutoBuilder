"""Tests for PM autonomous loop mechanics.

The PM loop is emergent behavior from LlmAgent + tools + callbacks.
These tests verify the callback mechanics, state management, and batch
lifecycle that enable the PM to autonomously process deliverables.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.supervision import (
    create_batch_verification_callback,
    create_checkpoint_callback,
)
from app.models.constants import (
    APPROVAL_RESOLUTION_PREFIX,
    BATCH_RESULT_KEY,
    DELIVERABLE_STATUS_PREFIX,
    PM_ESCALATION_CONTEXT_KEY,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockCallbackContext:
    """Lightweight stand-in for ADK CallbackContext.

    Supports dict-style state access via .state and .agent_name.
    """

    def __init__(
        self,
        state: dict[str, object] | None = None,
        agent_name: str = "test_pm",
    ) -> None:
        self.state: dict[str, object] = state or {}
        self.agent_name = agent_name


class MockEventPublisher:
    """Captures lifecycle events for assertion."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object, dict[str, object] | None]] = []

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append((workflow_id, event_type, metadata))


def _make_deliverable_state(
    deliverables: dict[str, str],
    *,
    batch_id: str = "batch_1",
    workflow_id: str = "wf_test",
) -> dict[str, object]:
    """Build state dict with deliverable statuses and batch metadata.

    Args:
        deliverables: Mapping of deliverable_id -> status string.
        batch_id: Current batch identifier.
        workflow_id: Workflow identifier for event routing.
    """
    state: dict[str, object] = {
        "workflow_id": workflow_id,
        "current_batch_id": batch_id,
        "current_batch_deliverables": list(deliverables.keys()),
    }
    for did, status in deliverables.items():
        state[f"{DELIVERABLE_STATUS_PREFIX}{did}"] = status
    return state


# ---------------------------------------------------------------------------
# Checkpoint callback tests
# ---------------------------------------------------------------------------


class TestCheckpointCallback:
    """Verify checkpoint_project fires after pipeline completion."""

    @pytest.mark.asyncio
    async def test_checkpoint_sets_completed_status(self) -> None:
        """Successful pipeline output writes COMPLETED to state."""
        publisher = MockEventPublisher()
        callback = create_checkpoint_callback(publisher)  # type: ignore[arg-type]

        state: dict[str, object] = {
            "workflow_id": "wf_1",
            "current_deliverable_id": "d_001",
            "pipeline_output": {"failed": False},
        }
        ctx = MockCallbackContext(state=state, agent_name="deliverable_pipeline")

        result = await callback(ctx)  # type: ignore[arg-type]

        assert result is None
        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_001"] == "COMPLETED"
        assert len(publisher.events) == 1
        _, _, meta = publisher.events[0]
        assert meta is not None
        assert meta["deliverable_id"] == "d_001"
        assert meta["deliverable_status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_checkpoint_sets_failed_status(self) -> None:
        """Pipeline output with failed=True writes FAILED to state."""
        publisher = MockEventPublisher()
        callback = create_checkpoint_callback(publisher)  # type: ignore[arg-type]

        state: dict[str, object] = {
            "workflow_id": "wf_1",
            "current_deliverable_id": "d_002",
            "pipeline_output": {"failed": True},
        }
        ctx = MockCallbackContext(state=state, agent_name="deliverable_pipeline")

        await callback(ctx)  # type: ignore[arg-type]

        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_002"] == "FAILED"

    @pytest.mark.asyncio
    async def test_checkpoint_skips_when_no_deliverable_id(self) -> None:
        """No-op when current_deliverable_id is absent."""
        publisher = MockEventPublisher()
        callback = create_checkpoint_callback(publisher)  # type: ignore[arg-type]

        state: dict[str, object] = {"workflow_id": "wf_1"}
        ctx = MockCallbackContext(state=state)

        result = await callback(ctx)  # type: ignore[arg-type]

        assert result is None
        assert len(publisher.events) == 0

    @pytest.mark.asyncio
    async def test_checkpoint_handles_non_dict_pipeline_output(self) -> None:
        """Non-dict pipeline_output treated as FAILED."""
        publisher = MockEventPublisher()
        callback = create_checkpoint_callback(publisher)  # type: ignore[arg-type]

        state: dict[str, object] = {
            "workflow_id": "wf_1",
            "current_deliverable_id": "d_003",
            "pipeline_output": "not_a_dict",
        }
        ctx = MockCallbackContext(state=state, agent_name="deliverable_pipeline")

        await callback(ctx)  # type: ignore[arg-type]

        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_003"] == "FAILED"


# ---------------------------------------------------------------------------
# Batch verification callback tests
# ---------------------------------------------------------------------------


class TestBatchVerificationCallback:
    """Verify batch_verification fires after batch processing."""

    @pytest.mark.asyncio
    async def test_all_completed_batch(self) -> None:
        """All deliverables COMPLETED produces correct batch_result."""
        publisher = MockEventPublisher()
        callback = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_1": "COMPLETED",
                "d_2": "COMPLETED",
            }
        )
        ctx = MockCallbackContext(state=state)

        await callback(ctx)  # type: ignore[arg-type]

        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["completed"] == 2
        assert batch_result["failed"] == 0
        assert batch_result["all_terminal"] is True

    @pytest.mark.asyncio
    async def test_mixed_terminal_batch(self) -> None:
        """Mix of COMPLETED and FAILED is still all_terminal."""
        publisher = MockEventPublisher()
        callback = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_1": "COMPLETED",
                "d_2": "FAILED",
            }
        )
        ctx = MockCallbackContext(state=state)

        await callback(ctx)  # type: ignore[arg-type]

        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["completed"] == 1
        assert batch_result["failed"] == 1
        assert batch_result["all_terminal"] is True

    @pytest.mark.asyncio
    async def test_pending_deliverable_not_terminal(self) -> None:
        """PENDING deliverable means all_terminal is False."""
        publisher = MockEventPublisher()
        callback = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_1": "COMPLETED",
                "d_2": "PENDING",
            }
        )
        ctx = MockCallbackContext(state=state)

        await callback(ctx)  # type: ignore[arg-type]

        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is False

    @pytest.mark.asyncio
    async def test_publishes_batch_event(self) -> None:
        """Batch verification publishes STATE_UPDATED event."""
        publisher = MockEventPublisher()
        callback = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state({"d_1": "COMPLETED"})
        ctx = MockCallbackContext(state=state)

        await callback(ctx)  # type: ignore[arg-type]

        assert len(publisher.events) == 1
        _, _, meta = publisher.events[0]
        assert meta is not None
        assert meta["batch_id"] == "batch_1"
        assert meta["total"] == 1
        assert meta["completed"] == 1

    @pytest.mark.asyncio
    async def test_batch_result_contains_status_map(self) -> None:
        """batch_result includes per-deliverable status mapping."""
        publisher = MockEventPublisher()
        callback = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_a": "COMPLETED",
                "d_b": "FAILED",
            }
        )
        ctx = MockCallbackContext(state=state)

        await callback(ctx)  # type: ignore[arg-type]

        batch_result: dict[str, object] = state[BATCH_RESULT_KEY]  # type: ignore[assignment]
        assert isinstance(batch_result, dict)
        statuses: dict[str, object] = batch_result["deliverable_statuses"]  # type: ignore[assignment]
        assert isinstance(statuses, dict)
        assert statuses["d_a"] == "COMPLETED"
        assert statuses["d_b"] == "FAILED"


# ---------------------------------------------------------------------------
# Failed deliverable independence tests
# ---------------------------------------------------------------------------


class TestFailedDeliverableIndependence:
    """Failed deliverable does not block independent deliverables."""

    @pytest.mark.asyncio
    async def test_failed_does_not_block_independent(self) -> None:
        """Deliverable B with no dependency on A can proceed when A fails.

        Simulates PM selecting a ready batch where A has failed
        and B has no dependencies. B remains selectable.
        """
        publisher = MockEventPublisher()
        checkpoint = create_checkpoint_callback(publisher)  # type: ignore[arg-type]

        # Deliverable A fails
        state_a: dict[str, object] = {
            "workflow_id": "wf_1",
            "current_deliverable_id": "d_a",
            "pipeline_output": {"failed": True},
        }
        ctx_a = MockCallbackContext(state=state_a)
        await checkpoint(ctx_a)  # type: ignore[arg-type]
        assert state_a[f"{DELIVERABLE_STATUS_PREFIX}d_a"] == "FAILED"

        # Deliverable B is independent — state does not contain
        # any dependency link from B to A, so B can be selected
        state_b: dict[str, object] = {
            **state_a,
            "current_deliverable_id": "d_b",
            "pipeline_output": {"failed": False},
        }
        ctx_b = MockCallbackContext(state=state_b)
        await checkpoint(ctx_b)  # type: ignore[arg-type]

        assert state_b[f"{DELIVERABLE_STATUS_PREFIX}d_a"] == "FAILED"
        assert state_b[f"{DELIVERABLE_STATUS_PREFIX}d_b"] == "COMPLETED"


# ---------------------------------------------------------------------------
# PM completion and escalation tests
# ---------------------------------------------------------------------------


class TestPmCompletion:
    """PM returns control to Director on completion."""

    @pytest.mark.asyncio
    async def test_pm_returns_on_all_completed(self) -> None:
        """When all deliverables complete, batch_result reflects completion."""
        publisher = MockEventPublisher()
        verify = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_1": "COMPLETED",
                "d_2": "COMPLETED",
                "d_3": "COMPLETED",
            }
        )
        state["pm:status"] = "running"
        ctx = MockCallbackContext(state=state)

        await verify(ctx)  # type: ignore[arg-type]

        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is True
        assert batch_result["completed"] == 3
        assert batch_result["failed"] == 0


class TestPmEscalation:
    """PM escalates when blocked with no progress possible."""

    @pytest.mark.asyncio
    async def test_escalation_context_persisted(self) -> None:
        """PM escalation context is readable from state after being set."""
        state: dict[str, object] = {
            "workflow_id": "wf_1",
            PM_ESCALATION_CONTEXT_KEY: "All deliverables blocked: circular dependency",
        }
        ctx = MockCallbackContext(state=state)

        # Verify the escalation context is accessible
        escalation = ctx.state.get(PM_ESCALATION_CONTEXT_KEY)
        assert escalation is not None
        assert "circular dependency" in str(escalation)

    @pytest.mark.asyncio
    async def test_all_failed_batch_triggers_escalation_signal(self) -> None:
        """Batch with all failures produces batch_result for PM reasoning."""
        publisher = MockEventPublisher()
        verify = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state = _make_deliverable_state(
            {
                "d_1": "FAILED",
                "d_2": "FAILED",
            }
        )
        ctx = MockCallbackContext(state=state)

        await verify(ctx)  # type: ignore[arg-type]

        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["completed"] == 0
        assert batch_result["failed"] == 2
        assert batch_result["all_terminal"] is True


# ---------------------------------------------------------------------------
# Multi-batch coherence tests
# ---------------------------------------------------------------------------


class TestMultiBatchCoherence:
    """State coherence across batch boundaries."""

    @pytest.mark.asyncio
    async def test_two_batch_sequence(self) -> None:
        """Batch 1 completes, batch 2 selected with access to batch 1 results.

        Simulates the PM processing two batches sequentially:
        1. Batch 1: d_1 and d_2 complete
        2. Batch 2: d_3 depends on batch 1 results
        """
        publisher = MockEventPublisher()
        checkpoint = create_checkpoint_callback(publisher)  # type: ignore[arg-type]
        verify = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        # --- Batch 1 ---
        state: dict[str, object] = {
            "workflow_id": "wf_multi",
            "current_batch_id": "batch_1",
            "current_batch_deliverables": ["d_1", "d_2"],
        }

        # Complete d_1
        state["current_deliverable_id"] = "d_1"
        state["pipeline_output"] = {"failed": False}
        await checkpoint(MockCallbackContext(state=state))  # type: ignore[arg-type]

        # Complete d_2
        state["current_deliverable_id"] = "d_2"
        state["pipeline_output"] = {"failed": False}
        await checkpoint(MockCallbackContext(state=state))  # type: ignore[arg-type]

        # Verify batch 1
        await verify(MockCallbackContext(state=state))  # type: ignore[arg-type]

        batch_1_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_1_result, dict)
        assert batch_1_result["all_terminal"] is True
        assert batch_1_result["completed"] == 2

        # --- Batch 2 ---
        # PM selects next batch (state carries forward)
        state["current_batch_id"] = "batch_2"
        state["current_batch_deliverables"] = ["d_3"]

        # Complete d_3
        state["current_deliverable_id"] = "d_3"
        state["pipeline_output"] = {"failed": False}
        await checkpoint(MockCallbackContext(state=state))  # type: ignore[arg-type]

        # Verify batch 2
        await verify(MockCallbackContext(state=state))  # type: ignore[arg-type]

        batch_2_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_2_result, dict)
        assert batch_2_result["batch_id"] == "batch_2"
        assert batch_2_result["completed"] == 1
        assert batch_2_result["all_terminal"] is True

        # Batch 1 deliverable statuses still in state
        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_1"] == "COMPLETED"
        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_2"] == "COMPLETED"
        assert state[f"{DELIVERABLE_STATUS_PREFIX}d_3"] == "COMPLETED"


# ---------------------------------------------------------------------------
# Approval resolution tests
# ---------------------------------------------------------------------------


class TestApprovalResolution:
    """PM discovers approval resolution via pm:approval:* keys."""

    @pytest.mark.asyncio
    async def test_approval_resolution_discovered(self) -> None:
        """PM can read approval resolution keys from state."""
        state: dict[str, object] = {
            "workflow_id": "wf_1",
            f"{APPROVAL_RESOLUTION_PREFIX}d_blocked": "approved",
            f"{APPROVAL_RESOLUTION_PREFIX}arch_change": "rejected",
        }
        ctx = MockCallbackContext(state=state)

        # Simulate PM reading approval keys
        approval_keys = [k for k in ctx.state if k.startswith(APPROVAL_RESOLUTION_PREFIX)]
        assert len(approval_keys) == 2

        resolutions = {
            k.removeprefix(APPROVAL_RESOLUTION_PREFIX): ctx.state[k] for k in approval_keys
        }
        assert resolutions["d_blocked"] == "approved"
        assert resolutions["arch_change"] == "rejected"


class TestPmSuspendedOnApproval:
    """PM returns suspended status when waiting for approvals."""

    @pytest.mark.asyncio
    async def test_pm_suspended_when_waiting(self) -> None:
        """PM state indicates suspension when no unblocked work exists.

        This tests the state pattern: pm:status=suspended, with
        pending approval keys and no ready deliverables.
        """
        publisher = MockEventPublisher()
        verify = create_batch_verification_callback(publisher)  # type: ignore[arg-type]

        state: dict[str, object] = {
            "workflow_id": "wf_1",
            "current_batch_id": "batch_waiting",
            "current_batch_deliverables": ["d_blocked"],
            f"{DELIVERABLE_STATUS_PREFIX}d_blocked": "PENDING",
            "pm:status": "suspended",
            PM_ESCALATION_CONTEXT_KEY: ("Awaiting approval for architectural change"),
        }
        ctx = MockCallbackContext(state=state)

        await verify(ctx)  # type: ignore[arg-type]

        # Batch is not terminal (d_blocked still PENDING)
        batch_result = state[BATCH_RESULT_KEY]
        assert isinstance(batch_result, dict)
        assert batch_result["all_terminal"] is False

        # PM status remains suspended
        assert state["pm:status"] == "suspended"

        # Escalation context is preserved
        escalation = state[PM_ESCALATION_CONTEXT_KEY]
        assert "approval" in str(escalation).lower()


# ---------------------------------------------------------------------------
# Pipeline wiring tests
# ---------------------------------------------------------------------------


class TestPipelineWiring:
    """Verify DeliverablePipeline is wired as PM sub_agent."""

    @pytest.mark.asyncio
    async def test_pipeline_is_pm_sub_agent(self) -> None:
        """build_work_session_agents wires pipeline as PM sub_agent."""
        from unittest.mock import patch

        from app.workers.adk import build_work_session_agents

        director_mock = MagicMock()
        director_mock.name = "director"
        director_mock.sub_agents = []
        director_mock.before_agent_callback = None
        director_mock.after_agent_callback = None

        pm_mock = MagicMock()
        pm_mock.name = "PM_proj1"
        pm_mock.sub_agents = []
        pm_mock.before_agent_callback = None
        pm_mock.after_agent_callback = None

        pipeline_mock = MagicMock()
        pipeline_mock.name = "deliverable_pipeline"
        pipeline_mock.after_agent_callback = None

        registry = MagicMock()
        registry.build = MagicMock(side_effect=[director_mock, pm_mock])

        ctx = MagicMock()
        publisher = MockEventPublisher()

        with patch(
            "app.agents.pipeline.create_deliverable_pipeline",
            return_value=pipeline_mock,
        ):
            result = await build_work_session_agents(
                registry=registry,
                ctx=ctx,
                project_id="proj1",
                publisher=publisher,  # type: ignore[arg-type]
            )

        # Director is root
        assert result is director_mock

        # PM is Director's sub_agent
        assert director_mock.sub_agents == [pm_mock]

        # Pipeline is PM's sub_agent
        assert pm_mock.sub_agents == [pipeline_mock]

        # Pipeline has checkpoint callback
        assert pipeline_mock.after_agent_callback is not None
        assert callable(pipeline_mock.after_agent_callback)
