"""Supervision callbacks for Director-PM hierarchy."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from google.genai.types import Content, Part

from app.models.constants import (
    BATCH_RESULT_KEY,
    DELIVERABLE_STATUS_PREFIX,
    PM_ESCALATION_CONTEXT_KEY,
)
from app.models.enums import DeliverableStatus, PipelineEventType, SupervisionEventType

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext

    from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)

# Type alias for before/after agent callbacks
AgentCallback = Callable[["CallbackContext"], Awaitable[Content | None]]


def create_before_pm_callback(publisher: EventPublisher) -> AgentCallback:
    """Return before_agent_callback enforcing cost ceiling and retry budget."""

    async def before_pm_execution(ctx: CallbackContext) -> Content | None:
        workflow_id = _get_workflow_id(ctx)

        # Publish PM invocation event
        await publisher.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.AGENT_STARTED,
            metadata={
                "supervision_event": SupervisionEventType.PM_INVOCATION,
                "agent": ctx.agent_name,
            },
        )

        # Read project hard limits
        # ADK State.get() returns Any — cast to known types
        raw_config: object = ctx.state.get("project_config", {})
        config: dict[str, object] = (
            cast("dict[str, object]", raw_config) if isinstance(raw_config, dict) else {}
        )
        retry_budget: object = config.get("retry_budget", 10)
        cost_ceiling: object = config.get("cost_ceiling", 100.0)

        # Read current usage
        current_retries: object = ctx.state.get("pm:retry_count", 0)
        current_cost: object = ctx.state.get("pm:total_cost", 0.0)

        # Check cost ceiling
        if (
            isinstance(current_cost, (int, float))
            and isinstance(cost_ceiling, (int, float))
            and current_cost >= cost_ceiling
        ):
            msg = f"PM execution blocked: cost ceiling exceeded ({current_cost}/{cost_ceiling})"
            ctx.state[PM_ESCALATION_CONTEXT_KEY] = (
                f"Cost ceiling exceeded: {current_cost} >= {cost_ceiling}"
            )
            await publisher.publish_lifecycle(
                workflow_id=workflow_id,
                event_type=PipelineEventType.ERROR,
                metadata={
                    "supervision_event": SupervisionEventType.LIMIT_EXCEEDED,
                    "limit": "cost_ceiling",
                    "current": current_cost,
                    "ceiling": cost_ceiling,
                },
            )
            return Content(parts=[Part(text=msg)])

        # Check retry budget
        if (
            isinstance(current_retries, int)
            and isinstance(retry_budget, int)
            and current_retries >= retry_budget
        ):
            msg = f"PM execution blocked: retry budget exhausted ({current_retries}/{retry_budget})"
            ctx.state[PM_ESCALATION_CONTEXT_KEY] = (
                f"Retry budget exhausted: {current_retries} >= {retry_budget}"
            )
            await publisher.publish_lifecycle(
                workflow_id=workflow_id,
                event_type=PipelineEventType.ERROR,
                metadata={
                    "supervision_event": SupervisionEventType.LIMIT_EXCEEDED,
                    "limit": "retry_budget",
                    "current": current_retries,
                    "budget": retry_budget,
                },
            )
            return Content(parts=[Part(text=msg)])

        return None

    return before_pm_execution


def create_after_pm_callback(publisher: EventPublisher) -> AgentCallback:
    """Return after_agent_callback observing PM completion, escalation, and inline queue check."""

    async def after_pm_execution(ctx: CallbackContext) -> Content | None:
        workflow_id = _get_workflow_id(ctx)
        pm_status: object = ctx.state.get("pm:status", "unknown")

        # Publish PM completion event
        await publisher.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.AGENT_COMPLETED,
            metadata={
                "supervision_event": SupervisionEventType.PM_COMPLETION,
                "agent": ctx.agent_name,
                "pm_status": str(pm_status),
            },
        )

        # Detect escalation signals
        escalation: object = ctx.state.get(PM_ESCALATION_CONTEXT_KEY)
        if escalation is not None and escalation != "":
            await publisher.publish_lifecycle(
                workflow_id=workflow_id,
                event_type=PipelineEventType.STATE_UPDATED,
                metadata={
                    "supervision_event": (SupervisionEventType.ESCALATION_DETECTED),
                    "escalation_context": str(escalation),
                },
            )

        # Inline Director Queue check (DD-5): lightweight state flag for Director
        # to discover pending queue items on its next turn. The Director reads this
        # flag and processes items via its tools — no DB query in the callback.
        pending_count: object = ctx.state.get("director:pending_queue_count", 0)
        if isinstance(pending_count, int) and pending_count > 0:
            ctx.state["director:queue_check_needed"] = True
            await publisher.publish_lifecycle(
                workflow_id=workflow_id,
                event_type=PipelineEventType.STATE_UPDATED,
                metadata={
                    "supervision_event": "DIRECTOR_QUEUE_PENDING",
                    "pending_count": pending_count,
                },
            )

        return None  # Observation only

    return after_pm_execution


def create_checkpoint_callback(publisher: EventPublisher) -> AgentCallback:
    """Return after_agent_callback persisting deliverable status."""

    async def checkpoint_project(ctx: CallbackContext) -> Content | None:
        workflow_id = _get_workflow_id(ctx)
        deliverable_id: object = ctx.state.get("current_deliverable_id", "")

        if not deliverable_id or not isinstance(deliverable_id, str):
            return None

        # Determine status from pipeline output
        pipeline_output: object = ctx.state.get("pipeline_output", {})
        status: str = DeliverableStatus.COMPLETED
        if isinstance(pipeline_output, dict):
            output_dict = cast("dict[str, object]", pipeline_output)
            if output_dict.get("failed", False):
                status = DeliverableStatus.FAILED
        else:
            status = DeliverableStatus.FAILED

        # Persist deliverable status to durable state
        status_key = f"{DELIVERABLE_STATUS_PREFIX}{deliverable_id}"
        ctx.state[status_key] = status

        await publisher.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.STATE_UPDATED,
            metadata={
                "deliverable_id": deliverable_id,
                "deliverable_status": status,
            },
        )

        return None

    return checkpoint_project


def create_batch_verification_callback(publisher: EventPublisher) -> AgentCallback:
    """Return after_agent_callback validating batch terminal states."""

    async def verify_batch_completion(
        ctx: CallbackContext,
    ) -> Content | None:
        workflow_id = _get_workflow_id(ctx)
        raw_deliverables: object = ctx.state.get("current_batch_deliverables", [])

        if not isinstance(raw_deliverables, list):
            return None

        batch_deliverables: list[object] = raw_deliverables  # type: ignore[assignment]

        # Check each deliverable reached terminal state
        terminal_statuses = {DeliverableStatus.COMPLETED, DeliverableStatus.FAILED}
        results: dict[str, str] = {}
        all_terminal = True
        for did in batch_deliverables:
            did_str = str(did)
            status_key = f"{DELIVERABLE_STATUS_PREFIX}{did_str}"
            status: object = ctx.state.get(status_key, DeliverableStatus.PENDING)
            results[did_str] = str(status)
            if str(status) not in terminal_statuses:
                all_terminal = False

        completed = sum(1 for s in results.values() if s == DeliverableStatus.COMPLETED)
        failed = sum(1 for s in results.values() if s == DeliverableStatus.FAILED)

        batch_id: object = ctx.state.get("current_batch_id", "unknown")
        ctx.state[BATCH_RESULT_KEY] = {
            "batch_id": str(batch_id),
            "total": len(batch_deliverables),
            "completed": completed,
            "failed": failed,
            "deliverable_statuses": results,
            "all_terminal": all_terminal,
        }

        await publisher.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.STATE_UPDATED,
            metadata={
                "batch_id": str(batch_id),
                "total": len(batch_deliverables),
                "completed": completed,
                "failed": failed,
                "all_terminal": all_terminal,
            },
        )

        return None

    return verify_batch_completion


def _get_workflow_id(ctx: CallbackContext) -> str:
    """Extract workflow_id from callback context state."""
    wf_id: object = ctx.state.get("workflow_id", "")
    return str(wf_id) if wf_id else ""
