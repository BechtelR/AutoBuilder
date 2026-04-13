"""Supervision callbacks for Director-PM hierarchy."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from google.genai.types import Content, Part
from sqlalchemy import select

from app.db.models import Deliverable as DeliverableModel
from app.db.models import Project as ProjectModel
from app.db.models import TaskGroupExecution
from app.models.constants import (
    BATCH_RESULT_KEY,
    DELIVERABLE_STATUS_PREFIX,
    DELIVERABLE_STATUSES_KEY,
    PM_ESCALATION_CONTEXT_KEY,
)
from app.models.enums import (
    DeliverableStatus,
    PipelineEventType,
    ProjectStatus,
    SupervisionEventType,
)

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
                    "supervision_event": SupervisionEventType.DIRECTOR_QUEUE_PENDING,
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
        terminal_statuses = {
            DeliverableStatus.COMPLETED,
            DeliverableStatus.FAILED,
            DeliverableStatus.SKIPPED,
        }
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
        skipped = sum(1 for s in results.values() if s == DeliverableStatus.SKIPPED)

        batch_id: object = ctx.state.get("current_batch_id", "unknown")
        ctx.state[BATCH_RESULT_KEY] = {
            "batch_id": str(batch_id),
            "total": len(batch_deliverables),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            DELIVERABLE_STATUSES_KEY: results,
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
                "skipped": skipped,
                "all_terminal": all_terminal,
            },
        )

        return None

    return verify_batch_completion


def _get_workflow_id(ctx: CallbackContext) -> str:
    """Extract workflow_id from callback context state."""
    wf_id: object = ctx.state.get("workflow_id", "")
    return str(wf_id) if wf_id else ""


# ---------------------------------------------------------------------------
# Tier 1: Deliverable-level DB checkpoint
# ---------------------------------------------------------------------------


def create_deliverable_checkpoint_callback(
    db_session_factory: async_sessionmaker[AsyncSession],
    publisher: EventPublisher,
) -> AgentCallback:
    """After-agent callback that persists deliverable status to DB after each pipeline run.

    Reads current_deliverable_id and the deliverable_status:{id} key from
    CallbackContext.state. If present, writes the status to the Deliverable
    table so a checkpointed deliverable never re-executes after crash.
    """

    async def _checkpoint_deliverable(ctx: CallbackContext) -> Content | None:
        deliverable_id: object = ctx.state.get("current_deliverable_id")
        if deliverable_id is None or not isinstance(deliverable_id, str):
            return None

        # Determine status from pipeline output or state key
        status_key = f"{DELIVERABLE_STATUS_PREFIX}{deliverable_id}"
        status_raw: object = ctx.state.get(status_key)

        # Fallback: infer from pipeline_output if no explicit status key
        if status_raw is None:
            pipeline_output: object = ctx.state.get("pipeline_output", {})
            if isinstance(pipeline_output, dict):
                output_dict = cast("dict[str, object]", pipeline_output)
                if output_dict.get("failed", False):
                    status_raw = DeliverableStatus.FAILED
                else:
                    status_raw = DeliverableStatus.COMPLETED
            else:
                status_raw = DeliverableStatus.FAILED

        # Also persist the status key to state (for downstream consumers)
        ctx.state[status_key] = str(status_raw)

        # Persist to DB
        try:
            did = uuid.UUID(deliverable_id)
        except ValueError:
            logger.warning("Invalid deliverable_id for checkpoint: %s", deliverable_id)
            return None

        checkpoint_ok = False
        try:
            async with db_session_factory() as db:
                stmt = select(DeliverableModel).where(DeliverableModel.id == did)
                result = await db.execute(stmt)
                deliverable = result.scalar_one_or_none()
                if deliverable is not None:
                    deliverable.status = DeliverableStatus(str(status_raw))
                    deliverable.updated_at = datetime.now(UTC)
                    await db.commit()
                    checkpoint_ok = True
                    logger.info(
                        "Tier 1 checkpoint: deliverable %s -> %s",
                        deliverable_id[:8],
                        status_raw,
                    )
                else:
                    logger.warning(
                        "Tier 1 checkpoint: deliverable %s not found in DB", deliverable_id[:8]
                    )
        except Exception:
            logger.exception("Tier 1 checkpoint failed for deliverable %s", deliverable_id[:8])
            raise

        # Publish lifecycle event (only reached on success — failure re-raises above)
        workflow_id = _get_workflow_id(ctx)
        try:
            await publisher.publish_lifecycle(
                workflow_id=workflow_id,
                event_type=PipelineEventType.STATE_UPDATED,
                metadata={
                    "checkpoint_tier": 1,
                    "deliverable_id": deliverable_id,
                    "deliverable_status": str(status_raw),
                    "checkpoint_persisted": checkpoint_ok,
                },
            )
        except Exception:
            # Checkpoint already persisted — event publish failure is non-fatal
            logger.warning(
                "Tier 1 checkpoint event publish failed for deliverable %s (checkpoint persisted)",
                deliverable_id[:8],
            )

        return None

    return _checkpoint_deliverable


# ---------------------------------------------------------------------------
# Tier 2: TaskGroup boundary checkpoint
# ---------------------------------------------------------------------------


async def checkpoint_taskgroup(
    db_session_factory: async_sessionmaker[AsyncSession],
    taskgroup_execution_id: uuid.UUID,
    state: dict[str, object],
    publisher: EventPublisher,
    workflow_id: str,
) -> None:
    """Persist critical PM state at TaskGroup boundary.

    Writes a CriticalStateSnapshot to taskgroup_executions.checkpoint_data.
    Single DB transaction; rolls back completely on failure (NFR-8a.03).
    """
    snapshot: dict[str, object] = {
        "deliverable_statuses": {
            k: v for k, v in state.items() if k.startswith(DELIVERABLE_STATUS_PREFIX)
        },
        "stage_progress": {k: v for k, v in state.items() if k.startswith("pm:stage")},
        "accumulated_cost": state.get("pm:total_cost", 0),
        "loaded_skill_names": state.get("loaded_skill_names", []),
        "workflow_id": state.get("workflow_id"),
        "completed_stages": state.get("pm:stages_completed", []),
        "current_taskgroup_id": str(taskgroup_execution_id),
        "project_config": state.get("project_config", {}),
    }

    try:
        async with db_session_factory() as db:
            stmt = select(TaskGroupExecution).where(TaskGroupExecution.id == taskgroup_execution_id)
            tge = (await db.execute(stmt)).scalar_one_or_none()
            if tge is None:
                logger.error(
                    "Tier 2 checkpoint failed: TaskGroupExecution %s not found",
                    str(taskgroup_execution_id)[:8],
                )
                return
            tge.checkpoint_data = snapshot
            await db.commit()
            logger.info(
                "Tier 2 checkpoint: taskgroup %s state saved",
                str(taskgroup_execution_id)[:8],
            )
    except Exception:
        logger.exception(
            "Tier 2 checkpoint failed for taskgroup %s",
            str(taskgroup_execution_id)[:8],
        )
        raise

    try:
        await publisher.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.STATE_UPDATED,
            metadata={
                "checkpoint_tier": 2,
                "taskgroup_execution_id": str(taskgroup_execution_id),
            },
        )
    except Exception:
        # Checkpoint already persisted — event publish failure is non-fatal observability loss
        logger.warning(
            "Tier 2 checkpoint event publish failed for taskgroup %s (checkpoint persisted)",
            str(taskgroup_execution_id)[:8],
        )


# ---------------------------------------------------------------------------
# Failure handling (P8a.D10)
# ---------------------------------------------------------------------------

BATCH_FAILURE_THRESHOLD_KEY: str = "pm:consecutive_batch_failures"
DEFAULT_BATCH_FAILURE_THRESHOLD: int = 3
DEFAULT_DELIVERABLE_RETRY_LIMIT: int = 2


async def handle_deliverable_failure(
    deliverable_id: uuid.UUID,
    retry_limit: int,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> str:
    """Handle a failed deliverable: retry if budget remains, mark FAILED otherwise.

    Returns: "retry" | "failed" | "error"
    """
    async with db_session_factory() as db:
        stmt = select(DeliverableModel).where(DeliverableModel.id == deliverable_id)
        deliverable = (await db.execute(stmt)).scalar_one_or_none()
        if deliverable is None:
            return "error"

        if deliverable.retry_count < retry_limit:
            deliverable.status = DeliverableStatus.IN_PROGRESS
            deliverable.retry_count += 1
            deliverable.updated_at = datetime.now(UTC)
            await db.commit()
            logger.info(
                "Deliverable %s retry %d/%d",
                str(deliverable_id)[:8],
                deliverable.retry_count,
                retry_limit,
            )
            return "retry"
        else:
            deliverable.status = DeliverableStatus.FAILED
            deliverable.updated_at = datetime.now(UTC)
            await db.commit()
            logger.info(
                "Deliverable %s retry exhausted (%d/%d) -> FAILED",
                str(deliverable_id)[:8],
                deliverable.retry_count,
                retry_limit,
            )
            return "failed"


async def evaluate_failure_impact(
    project_id: uuid.UUID,
    failed_deliverable_id: uuid.UUID,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, list[str]]:
    """Identify which remaining deliverables are blocked vs independent.

    Given a failed deliverable, traverses the dependency graph transitively to
    find all deliverables that depend on the failed one. Everything else is
    independent and can proceed.

    Returns: {"blocked": [ids], "independent": [ids]}
    """
    async with db_session_factory() as db:
        stmt = select(DeliverableModel).where(DeliverableModel.project_id == project_id)
        all_deliverables = list((await db.execute(stmt)).scalars().all())

    failed_id_str = str(failed_deliverable_id)

    # Find all deliverables transitively blocked by the failed one
    # using BFS over the dependency graph
    blocked: set[str] = set()
    frontier: list[str] = [failed_id_str]

    while frontier:
        current_id = frontier.pop()
        for d in all_deliverables:
            d_id = str(d.id)
            if d_id in blocked or d_id == failed_id_str:
                continue
            if current_id in (d.depends_on or []):
                blocked.add(d_id)
                frontier.append(d_id)

    # Independent = not failed, not blocked, not already terminal
    terminal = {DeliverableStatus.COMPLETED, DeliverableStatus.SKIPPED, DeliverableStatus.FAILED}
    independent = [
        str(d.id)
        for d in all_deliverables
        if str(d.id) != failed_id_str and str(d.id) not in blocked and d.status not in terminal
    ]

    return {"blocked": sorted(blocked), "independent": sorted(independent)}


async def track_batch_result(
    batch_had_failures: bool,
    state: dict[str, object],
    project_id: uuid.UUID,
    db_session_factory: async_sessionmaker[AsyncSession],
    threshold: int = DEFAULT_BATCH_FAILURE_THRESHOLD,
) -> str:
    """Track consecutive batch failures.

    - Successful batch: resets counter to 0
    - Failed batch: increments counter
    - Counter >= threshold: returns 'threshold_exceeded'

    Returns: "ok" | "threshold_exceeded"
    """
    raw_counter: object = state.get(BATCH_FAILURE_THRESHOLD_KEY, 0)
    counter: int = int(raw_counter) if isinstance(raw_counter, (int, float, str)) else 0

    if batch_had_failures:
        counter += 1
    else:
        counter = 0

    state[BATCH_FAILURE_THRESHOLD_KEY] = counter

    if counter >= threshold:
        logger.warning(
            "Batch failure threshold reached (%d/%d) for project %s",
            counter,
            threshold,
            str(project_id)[:8],
        )
        return "threshold_exceeded"

    return "ok"


async def suspend_project(
    project_id: uuid.UUID,
    reason: str,
    db_session_factory: async_sessionmaker[AsyncSession],
    publisher: EventPublisher | None = None,
) -> None:
    """Suspend a project and publish status change event."""
    old_status = ProjectStatus.ACTIVE  # default; overwritten below if project found
    async with db_session_factory() as db:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        project = (await db.execute(stmt)).scalar_one_or_none()
        if project is None:
            logger.error("Cannot suspend project: %s not found", str(project_id)[:8])
            return
        old_status = project.status
        terminal = {ProjectStatus.COMPLETED, ProjectStatus.ABORTED}
        if old_status in terminal:
            logger.warning(
                "Cannot suspend project %s: already in terminal status %s",
                str(project_id)[:8],
                old_status,
            )
            return
        project.status = ProjectStatus.SUSPENDED
        project.error_message = reason
        project.updated_at = datetime.now(UTC)
        await db.commit()
        logger.info(
            "Project %s suspended: %s",
            str(project_id)[:8],
            reason[:120],
        )

    if publisher is not None:
        await publisher.publish_project_status_changed(
            workflow_id=str(project_id),
            project_id=str(project_id),
            old_status=old_status,
            new_status=ProjectStatus.SUSPENDED,
        )
