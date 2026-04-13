"""Management tools for PM and Director agents.

PM tools handle deliverable lifecycle, batching, escalation, and dependencies.
Director tools handle project oversight, CEO escalation, and PM overrides.
"""

from __future__ import annotations

import contextlib
import json
import os
import tomllib
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from google.adk.tools.tool_context import (
    ToolContext,  # noqa: TC002 - runtime import required by ADK FunctionTool
)
from sqlalchemy import func, select

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from arq.connections import ArqRedis
    from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CeoQueueItem, Deliverable, DirectorQueueItem, Project
from app.lib.logging import get_logger
from app.models.constants import (
    STAGE_WORKFLOW_STAGES,
)
from app.models.enums import (
    CeoItemType,
    DeliverableStatus,
    DependencyAction,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    PmOverrideAction,
    ProjectStatus,
)
from app.tools._context import SESSION_ID_KEY, ToolExecutionContext, get_tool_context

logger = get_logger("tools.management")

# Maximum number of retries before a FAILED deliverable is no longer considered actionable
MAX_DELIVERABLE_RETRIES = 3

# Valid status transitions for deliverables
_VALID_TRANSITIONS: dict[DeliverableStatus, set[DeliverableStatus]] = {
    DeliverableStatus.PLANNED: {DeliverableStatus.PENDING, DeliverableStatus.IN_PROGRESS},
    DeliverableStatus.PENDING: {DeliverableStatus.IN_PROGRESS, DeliverableStatus.BLOCKED},
    DeliverableStatus.IN_PROGRESS: {
        DeliverableStatus.COMPLETED,
        DeliverableStatus.FAILED,
        DeliverableStatus.SKIPPED,
        DeliverableStatus.BLOCKED,
    },
    DeliverableStatus.FAILED: {DeliverableStatus.IN_PROGRESS, DeliverableStatus.SKIPPED},
    DeliverableStatus.BLOCKED: {DeliverableStatus.PENDING, DeliverableStatus.IN_PROGRESS},
}

# Config files that indicate a project and its ecosystem
_PROJECT_CONFIG_FILES: dict[str, str] = {
    "pyproject.toml": "Python",
    "package.json": "JavaScript/TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
}


def _extract_field_names(field_defs: object) -> list[str]:
    """Extract field name strings from brief_template field definitions.

    Each element is either a dict with a "name" key or a plain string.
    """
    if not isinstance(field_defs, list):
        return []
    names: list[str] = []
    for item in cast("list[object]", field_defs):
        if isinstance(item, dict):
            name_val = cast("dict[str, object]", item).get("name", "")
            names.append(str(name_val))
        else:
            names.append(str(item))
    return names


# ---------------------------------------------------------------------------
# Helpers for DB / ARQ access
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _get_db_session(tool_context: ToolContext) -> AsyncIterator[AsyncSession]:
    """Get a DB session from the tool execution context registry."""
    ctx = _get_exec_context(tool_context)
    async with ctx.db_session_factory() as session:
        yield session


def _get_arq_pool(tool_context: ToolContext) -> ArqRedis:
    """Get the ARQ pool from the tool execution context registry."""
    ctx = _get_exec_context(tool_context)
    return ctx.arq_pool


def _get_exec_context(tool_context: ToolContext) -> ToolExecutionContext:
    """Get the full ToolExecutionContext from the registry."""
    session_id = tool_context.state.get(SESSION_ID_KEY)  # type: ignore[union-attr]
    if session_id is None:
        raise ValueError("Session ID not available in tool context")
    return get_tool_context(str(session_id))


# ===================================================================
# PM Tools
# ===================================================================


async def select_ready_batch(tool_context: ToolContext, project_id: str) -> str:
    """Dependency-aware batch selection via topological sort.

    Returns the next set of deliverables whose prerequisites are satisfied.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project to select a ready batch for.

    Returns:
        JSON result or error.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid project_id: {project_id}"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(Deliverable).where(Deliverable.project_id == pid)
            result = await db.execute(stmt)
            all_deliverables = list(result.scalars().all())

            if not all_deliverables:
                return json.dumps({"batch": [], "total_ready": 0, "total_remaining": 0})

            # Completed/skipped IDs count as satisfied dependencies
            satisfied = {
                str(d.id)
                for d in all_deliverables
                if d.status in {DeliverableStatus.COMPLETED, DeliverableStatus.SKIPPED}
            }

            # Filter to actionable deliverables
            actionable: list[Deliverable] = []
            for d in all_deliverables:
                if d.status in {DeliverableStatus.PLANNED, DeliverableStatus.PENDING} or (
                    d.status == DeliverableStatus.FAILED and d.retry_count < MAX_DELIVERABLE_RETRIES
                ):
                    actionable.append(d)

            # Build in-degree map for Kahn's algorithm among actionable set
            in_degree: dict[str, int] = {str(d.id): 0 for d in actionable}

            for d in actionable:
                for dep_id in d.depends_on or []:
                    # Only count unsatisfied deps
                    if dep_id not in satisfied:
                        in_degree[str(d.id)] += 1

            # Frontier: actionable nodes with in-degree 0
            frontier = [d for d in actionable if in_degree[str(d.id)] == 0]
            # Sort by execution_order for deterministic output
            frontier.sort(key=lambda d: (d.execution_order or 0, str(d.id)))

            total_remaining = sum(
                1
                for d in all_deliverables
                if d.status not in {DeliverableStatus.COMPLETED, DeliverableStatus.SKIPPED}
            )

            return json.dumps(
                {
                    "batch": [
                        {"id": str(d.id), "name": d.name, "status": d.status.value}
                        for d in frontier
                    ],
                    "total_ready": len(frontier),
                    "total_remaining": total_remaining,
                }
            )
    except Exception as e:
        logger.exception("Failed to select ready batch")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def escalate_to_director(
    tool_context: ToolContext,
    priority: EscalationPriority,
    context: str,
    request_type: EscalationRequestType,
) -> str:
    """Escalate an issue from PM to the Director queue for resolution.

    Used by PM agents when they encounter situations requiring
    higher-level decision-making or cross-project coordination.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        priority: Urgency level -- LOW, NORMAL, HIGH, or CRITICAL.
        context: Detailed description of the situation.
        request_type: Category -- ESCALATION, STATUS_REPORT,
            RESOURCE_REQUEST, or PATTERN_ALERT.

    Returns:
        JSON result or error.
    """
    try:
        async with _get_db_session(tool_context) as db:
            # Read source project from tool context state if available
            source_project_raw = tool_context.state.get("pm:project_id")  # type: ignore[union-attr]
            source_project_id: uuid.UUID | None = None
            if source_project_raw is not None:
                with contextlib.suppress(ValueError):
                    source_project_id = uuid.UUID(str(source_project_raw))

            item = DirectorQueueItem(
                type=request_type,
                priority=priority,
                title=context[:255],
                context=context,
                source_project_id=source_project_id,
                source_agent="pm",
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)

            logger.info(
                "Escalation %s queued: type=%s priority=%s context=%s",
                str(item.id)[:8],
                request_type,
                priority,
                context[:120],
            )

            return json.dumps(
                {
                    "status": "ok",
                    "item_id": str(item.id),
                    "priority": priority.value,
                    "type": request_type.value,
                }
            )
    except Exception as e:
        logger.exception("Failed to create director queue item")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def update_deliverable(
    tool_context: ToolContext,
    deliverable_id: str,
    status: str,
    notes: str | None = None,
) -> str:
    """Update a deliverable's lifecycle status with optional notes.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        deliverable_id: Unique identifier of the deliverable.
        status: New status value to set.
        notes: Optional freeform notes about the update.

    Returns:
        JSON result or error.
    """
    try:
        did = uuid.UUID(deliverable_id)
    except ValueError:
        return json.dumps(
            {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": f"Invalid deliverable_id: {deliverable_id}",
                }
            }
        )

    try:
        new_status = DeliverableStatus(status)
    except ValueError:
        valid = [s.value for s in DeliverableStatus]
        return json.dumps(
            {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": f"Invalid status '{status}'. Valid: {valid}",
                }
            }
        )

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(Deliverable).where(Deliverable.id == did)
            result = await db.execute(stmt)
            deliverable = result.scalar_one_or_none()

            if deliverable is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Deliverable {deliverable_id} not found",
                        }
                    }
                )

            old_status = deliverable.status

            # Validate transition
            allowed = _VALID_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                return json.dumps(
                    {
                        "error": {
                            "code": "INVALID_TRANSITION",
                            "message": (
                                f"Cannot transition from {old_status.value} "
                                f"to {new_status.value}. "
                                f"Allowed: {sorted(s.value for s in allowed)}"
                            ),
                        }
                    }
                )

            # Retry: FAILED -> IN_PROGRESS increments retry_count
            if (
                old_status == DeliverableStatus.FAILED
                and new_status == DeliverableStatus.IN_PROGRESS
            ):
                deliverable.retry_count += 1

            deliverable.status = new_status
            deliverable.updated_at = datetime.now(UTC)

            if notes:
                logger.info(
                    "Deliverable %s status %s -> %s: %s",
                    deliverable_id,
                    old_status.value,
                    new_status.value,
                    notes[:200],
                )

            await db.commit()
            await db.refresh(deliverable)

            return json.dumps(
                {
                    "status": "ok",
                    "deliverable_id": str(deliverable.id),
                    "new_status": deliverable.status.value,
                    "retry_count": deliverable.retry_count,
                }
            )
    except Exception as e:
        logger.exception("Failed to update deliverable")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def query_deliverables(
    tool_context: ToolContext,
    project_id: str,
    status: str | None = None,
    stage: str | None = None,
) -> str:
    """Query deliverable state for a project, optionally filtered by status or stage.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project whose deliverables to query.
        status: Optional status filter.
        stage: Optional stage filter. Deliverables lack a direct stage column, so this
            filters via the parent project's current_stage. Only returns results if the
            project's current_stage matches.

    Returns:
        JSON result or error.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid project_id: {project_id}"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            # Stage filter: Deliverables lack a direct stage column. Check the parent
            # project's current_stage. If it doesn't match, return empty results.
            if stage is not None:
                proj_stmt = select(Project).where(Project.id == pid)
                proj = (await db.execute(proj_stmt)).scalar_one_or_none()
                if proj is None or proj.current_stage != stage:
                    return json.dumps({"deliverables": [], "total": 0})

            stmt = select(Deliverable).where(Deliverable.project_id == pid)

            if status is not None:
                try:
                    status_enum = DeliverableStatus(status)
                except ValueError:
                    valid = [s.value for s in DeliverableStatus]
                    return json.dumps(
                        {
                            "error": {
                                "code": "INVALID_INPUT",
                                "message": f"Invalid status '{status}'. Valid: {valid}",
                            }
                        }
                    )
                stmt = stmt.where(Deliverable.status == status_enum)

            stmt = stmt.order_by(Deliverable.execution_order.asc().nulls_last())
            result = await db.execute(stmt)
            deliverables = list(result.scalars().all())

            return json.dumps(
                {
                    "deliverables": [
                        {
                            "id": str(d.id),
                            "name": d.name,
                            "status": d.status.value,
                            "depends_on": d.depends_on or [],
                            "retry_count": d.retry_count,
                            "execution_order": d.execution_order,
                        }
                        for d in deliverables
                    ],
                    "total": len(deliverables),
                }
            )
    except Exception as e:
        logger.exception("Failed to query deliverables")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def reorder_deliverables(tool_context: ToolContext, project_id: str, order: list[str]) -> str:
    """Change execution priority by reordering deliverables.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project to reorder deliverables in.
        order: Ordered list of deliverable IDs defining the new sequence.

    Returns:
        JSON result or error.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid project_id: {project_id}"}}
        )

    # Validate all UUIDs upfront
    for did_str in order:
        try:
            uuid.UUID(did_str)
        except ValueError:
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid deliverable_id in order: {did_str}",
                    }
                }
            )

    try:
        async with _get_db_session(tool_context) as db:
            # Load all deliverables for this project
            stmt = select(Deliverable).where(Deliverable.project_id == pid)
            result = await db.execute(stmt)
            deliverables = {str(d.id): d for d in result.scalars().all()}

            # Validate all IDs belong to this project
            for did_str in order:
                if did_str not in deliverables:
                    return json.dumps(
                        {
                            "error": {
                                "code": "NOT_FOUND",
                                "message": (
                                    f"Deliverable {did_str} not found in project {project_id}"
                                ),
                            }
                        }
                    )

            # Update execution_order
            for idx, did_str in enumerate(order):
                deliverables[did_str].execution_order = idx

            await db.commit()

            return json.dumps(
                {
                    "status": "ok",
                    "reordered": len(order),
                    "order": order,
                }
            )
    except Exception as e:
        logger.exception("Failed to reorder deliverables")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def reconfigure_stage(
    tool_context: ToolContext,
    target_stage: str,
    reason: str,
) -> str:
    """Advance the workflow to the next sequential stage.

    Validates that the transition is legal (no backwards, no skipping),
    then writes the stage state delta via ToolContext. Delegates validation
    and delta computation to the domain function in ``app.workflows.stages``.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        target_stage: Name of the stage to transition to.
        reason: Why the PM is transitioning to this stage.

    Returns:
        JSON string describing the transition result, or an error message.
    """
    from app.models.constants import (
        STAGE_COMPLETED_LIST,
        STAGE_CURRENT,
        STAGE_INDEX,
        STAGE_STATUS,
    )
    from app.workflows.manifest import StageDef, WorkflowManifest
    from app.workflows.stages import reconfigure_stage as _domain_reconfigure

    # Read serialized stage schema from session state
    raw_stages: object = tool_context.state.get(STAGE_WORKFLOW_STAGES)  # type: ignore[union-attr]
    if raw_stages is None or not isinstance(raw_stages, list):
        return json.dumps({"error": "No workflow stages configured in session state"})

    stages_data: list[dict[str, object]] = cast("list[dict[str, object]]", raw_stages)

    # Reconstruct minimal manifest from serialized state for domain function
    stage_defs = [StageDef.model_validate(s) for s in stages_data]
    manifest = WorkflowManifest(name="__tool_ctx__", description="", stages=stage_defs)

    # Build current state snapshot for domain function
    state: dict[str, object] = {
        STAGE_CURRENT: tool_context.state.get(STAGE_CURRENT, ""),  # type: ignore[union-attr]
        STAGE_INDEX: tool_context.state.get(STAGE_INDEX, 0),  # type: ignore[union-attr]
        STAGE_STATUS: tool_context.state.get(STAGE_STATUS, ""),  # type: ignore[union-attr]
        STAGE_COMPLETED_LIST: tool_context.state.get(  # type: ignore[union-attr]
            STAGE_COMPLETED_LIST, []
        ),
    }

    try:
        delta = _domain_reconfigure(state, manifest, target_stage)
    except ValueError as exc:
        stage_names = [s.name for s in stage_defs]
        current_name = str(state.get(STAGE_CURRENT, ""))
        return json.dumps(
            {
                "error": str(exc),
                "current_stage": current_name,
                "target_stage": target_stage,
                "available_stages": stage_names,
            }
        )

    if not delta:
        # No-stages workflow -- no-op
        return json.dumps({"status": "ok", "message": "No stages configured (no-op)"})

    # Write state delta via ToolContext (ADK pattern)
    for key, value in delta.items():
        tool_context.actions.state_delta[key] = value  # type: ignore[index]

    previous_stage = str(state.get(STAGE_CURRENT, ""))
    logger.info(
        "Stage transition: %s -> %s (reason: %s)",
        previous_stage,
        target_stage,
        reason[:120],
    )

    return json.dumps(
        {
            "status": "ok",
            "previous_stage": previous_stage,
            "current_stage": target_stage,
            "stage_index": delta.get(STAGE_INDEX),
            "completed_stages": delta.get(STAGE_COMPLETED_LIST),
            "reason": reason,
        }
    )


def _detect_cycle(
    all_deliverables: list[Deliverable],
    source_id: str,
    target_id: str,
) -> list[str] | None:
    """BFS cycle detection: check if adding source depends-on target creates a cycle.

    A cycle exists if target can reach source through existing dependencies
    (i.e., source already transitively depends on target, or target depends on source).
    """
    # Build adjacency list: node -> nodes it depends on
    adj: dict[str, list[str]] = {}
    for d in all_deliverables:
        adj[str(d.id)] = list(d.depends_on or [])

    # BFS from target_id following dependency edges to see if we can reach source_id
    # If target depends (transitively) on source, then adding source->target creates a cycle
    visited: set[str] = set()
    queue: deque[str] = deque([target_id])

    while queue:
        node = queue.popleft()
        if node == source_id:
            return [source_id, target_id, source_id]
        if node in visited:
            continue
        visited.add(node)
        for dep in adj.get(node, []):
            if dep not in visited:
                queue.append(dep)

    return None


async def manage_dependencies(
    tool_context: ToolContext,
    action: DependencyAction,
    source_id: str,
    target_id: str | None = None,
) -> str:
    """Add, remove, or query deliverable dependency relationships.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        action: Operation to perform -- ADD, REMOVE, or QUERY.
        source_id: The deliverable that depends on another.
        target_id: The deliverable being depended upon (required for
            ADD and REMOVE).

    Returns:
        JSON result or error.
    """
    if action in {DependencyAction.ADD, DependencyAction.REMOVE} and target_id is None:
        return json.dumps(
            {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": f"target_id is required for {action.value} action",
                }
            }
        )

    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid source_id: {source_id}"}}
        )

    if target_id is not None:
        try:
            uuid.UUID(target_id)
        except ValueError:
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid target_id: {target_id}",
                    }
                }
            )

    try:
        async with _get_db_session(tool_context) as db:
            # Load source deliverable
            stmt = select(Deliverable).where(Deliverable.id == sid)
            result = await db.execute(stmt)
            source = result.scalar_one_or_none()

            if source is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Source deliverable {source_id} not found",
                        }
                    }
                )

            if action == DependencyAction.QUERY:
                return json.dumps(
                    {
                        "status": "ok",
                        "source_id": source_id,
                        "depends_on": source.depends_on or [],
                    }
                )

            assert target_id is not None  # guaranteed by validation above

            if action == DependencyAction.ADD:
                # Check target exists
                tid = uuid.UUID(target_id)
                target_stmt = select(Deliverable).where(Deliverable.id == tid)
                target_result = await db.execute(target_stmt)
                target_del = target_result.scalar_one_or_none()
                if target_del is None:
                    return json.dumps(
                        {
                            "error": {
                                "code": "NOT_FOUND",
                                "message": f"Target deliverable {target_id} not found",
                            }
                        }
                    )

                # Check not already present
                current_deps: list[str] = list(source.depends_on or [])
                if target_id in current_deps:
                    return json.dumps(
                        {
                            "status": "ok",
                            "message": "Dependency already exists",
                            "source_id": source_id,
                            "depends_on": current_deps,
                        }
                    )

                # Cycle detection: load all deliverables in the project
                project_stmt = select(Deliverable).where(
                    Deliverable.project_id == source.project_id
                )
                project_result = await db.execute(project_stmt)
                all_project_deliverables = list(project_result.scalars().all())

                cycle = _detect_cycle(all_project_deliverables, source_id, target_id)
                if cycle is not None:
                    return json.dumps(
                        {
                            "error": {
                                "code": "CYCLE_DETECTED",
                                "message": (
                                    f"Adding dependency {source_id} -> {target_id} "
                                    f"would create a cycle: {' -> '.join(cycle)}"
                                ),
                            }
                        }
                    )

                # Add dependency
                current_deps.append(target_id)
                source.depends_on = current_deps
                await db.commit()
                await db.refresh(source)

                return json.dumps(
                    {
                        "status": "ok",
                        "action": "ADD",
                        "source_id": source_id,
                        "target_id": target_id,
                        "depends_on": source.depends_on or [],
                    }
                )

            # REMOVE
            current_deps = list(source.depends_on or [])
            if target_id not in current_deps:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Dependency {source_id} -> {target_id} does not exist",
                        }
                    }
                )

            current_deps.remove(target_id)
            source.depends_on = current_deps
            await db.commit()
            await db.refresh(source)

            return json.dumps(
                {
                    "status": "ok",
                    "action": "REMOVE",
                    "source_id": source_id,
                    "target_id": target_id,
                    "depends_on": source.depends_on or [],
                }
            )
    except Exception as e:
        logger.exception("Failed to manage dependencies")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


# ===================================================================
# Director Tools
# ===================================================================


async def escalate_to_ceo(
    tool_context: ToolContext,
    item_type: CeoItemType,
    priority: EscalationPriority,
    message: str,
    metadata: str = "{}",
) -> str:
    """Push a notification, approval request, escalation, or task to the unified CEO queue.

    Director-only -- PM uses escalate_to_director instead.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        item_type: Category -- NOTIFICATION, APPROVAL, ESCALATION,
            or TASK.
        priority: Urgency level -- LOW, NORMAL, HIGH, or CRITICAL.
        message: Human-readable description of the item.
        metadata: JSON-encoded supplementary data.

    Returns:
        JSON confirmation with the queued item ID, or error.
    """
    try:
        meta: dict[str, object] = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": "metadata must be valid JSON"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            item = CeoQueueItem(
                type=item_type,
                priority=priority,
                title=message[:255],
                metadata_=meta,
                source_agent="director",
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return json.dumps(
                {
                    "status": "ok",
                    "item_id": str(item.id),
                    "type": item_type.value,
                    "priority": priority.value,
                    "message": f"CEO queue item created: {message[:100]}",
                }
            )
    except Exception as e:
        logger.exception("Failed to create CEO queue item")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def create_project(
    tool_context: ToolContext,
    name: str,
    workflow_type: str,
    brief: str,
    entry_mode: str = "new",
) -> str:
    """Create a new Project record in the database with SHAPING status.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        name: Human-readable project name.
        workflow_type: Workflow type identifier (e.g. "auto-code").
        brief: Project brief describing what should be built.
        entry_mode: How the project was initiated -- "new" or "edit".

    Returns:
        JSON with project_id and creation details, including entry_mode.

    Note:
        entry_mode is a routing hint (new vs edit) returned in the response for
        downstream consumers but not persisted as a separate DB column. The Project
        model has no JSONB metadata field; entry_mode is ephemeral context used by
        the Director to decide initial workflow behavior.
    """
    try:
        async with _get_db_session(tool_context) as db:
            project = Project(
                name=name,
                workflow_type=workflow_type,
                brief=brief,
                status=ProjectStatus.SHAPING,
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            return json.dumps(
                {
                    "status": "ok",
                    "project_id": str(project.id),
                    "name": name,
                    "workflow_type": workflow_type,
                    "entry_mode": entry_mode,
                }
            )
    except Exception as e:
        logger.exception("Failed to create project")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def validate_brief(
    tool_context: ToolContext,
    brief: str,
    workflow_type: str | None = None,
) -> str:
    """Validate a project brief against the workflow's brief_template.

    Resolves the workflow via WorkflowRegistry and checks that required
    fields defined in the manifest's ``brief_template`` are present in
    the brief. When ``workflow_type`` is omitted, attempts to resolve the
    best-matching workflow from the brief content.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        brief: The project brief (JSON string or plain text).
        workflow_type: Workflow type to validate against. If omitted,
            resolves via WorkflowRegistry.match().

    Returns:
        JSON with validation status and per-field results.
    """
    from app.lib.exceptions import NotFoundError

    exec_ctx = _get_exec_context(tool_context)
    registry = exec_ctx.workflow_registry

    # Resolve workflow type if not provided
    resolved_type = workflow_type
    if resolved_type is None:
        matches = registry.match(brief)
        if len(matches) == 1:
            resolved_type = matches[0].name
        elif len(matches) > 1:
            return json.dumps(
                {
                    "status": "ambiguous",
                    "message": "Multiple workflows match this brief",
                    "matches": [{"name": m.name, "description": m.description} for m in matches],
                }
            )
        else:
            available = registry.list_available()
            return json.dumps(
                {
                    "error": {
                        "code": "WORKFLOW_NOT_FOUND",
                        "message": "No workflow matches this brief",
                        "available_workflows": [w.name for w in available],
                    }
                }
            )

    try:
        manifest = registry.get_manifest(resolved_type)
    except NotFoundError:
        available = registry.list_available()
        return json.dumps(
            {
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"No workflow '{resolved_type}' found",
                    "available_workflows": [w.name for w in available],
                }
            }
        )

    brief_template = manifest.brief_template
    if not brief_template:
        return json.dumps(
            {
                "status": "ok",
                "workflow_type": resolved_type,
                "message": "No brief_template defined; brief accepted",
            }
        )

    # Parse brief as JSON if possible, otherwise treat as plain text
    try:
        brief_data: dict[str, object] = json.loads(brief)
    except json.JSONDecodeError:
        brief_data = {"content": brief}

    results: dict[str, dict[str, str]] = {}

    # Check required_fields
    for field_name in _extract_field_names(brief_template.get("required_fields")):
        if field_name in brief_data:
            results[field_name] = {"status": "pass"}
        else:
            results[field_name] = {
                "status": "fail",
                "message": f"Required field '{field_name}' missing",
            }

    # Check optional_fields
    for field_name in _extract_field_names(brief_template.get("optional_fields")):
        if field_name in brief_data:
            results[field_name] = {"status": "pass"}
        else:
            results[field_name] = {
                "status": "optional_missing",
                "message": f"Optional field '{field_name}' missing",
            }

    all_passed = all(r["status"] != "fail" for r in results.values())
    return json.dumps(
        {
            "status": "ok" if all_passed else "validation_failed",
            "workflow_type": resolved_type,
            "fields": results,
        }
    )


async def _check_service_health(url: str) -> bool:
    """Check if a service URL is reachable via HTTP health check."""
    import asyncio
    import urllib.request

    def _do_check() -> bool:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return bool(resp.status < 500)

    try:
        return await asyncio.to_thread(_do_check)
    except Exception:
        return False


async def check_resources(
    tool_context: ToolContext,
    workflow_type: str,
    project_id: str | None = None,
) -> str:
    """Check that resources declared in a workflow manifest are available.

    Verifies credentials (environment variables present), services (reachable
    via health check), and knowledge (files/directories exist).

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        workflow_type: Workflow type whose resources to check.
        project_id: Optional project ID for project-scoped resource checks.

    Returns:
        JSON with per-resource check results.
    """
    from app.lib.exceptions import NotFoundError

    exec_ctx = _get_exec_context(tool_context)
    registry = exec_ctx.workflow_registry

    try:
        manifest = registry.get_manifest(workflow_type)
    except NotFoundError:
        return json.dumps(
            {
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"No workflow '{workflow_type}'",
                }
            }
        )

    resources = manifest.resources
    has_any = resources.credentials or resources.services or resources.knowledge
    if not has_any:
        return json.dumps({"status": "ok", "message": "No resources declared"})

    results: dict[str, dict[str, str]] = {}
    all_passed = True

    # Check credentials (env vars)
    for cred in resources.credentials:
        present = bool(os.environ.get(cred))
        results[f"credential:{cred}"] = {"status": "pass" if present else "fail"}
        if not present:
            all_passed = False

    # Check services (health check URLs)
    for svc in resources.services:
        reachable = await _check_service_health(svc)
        results[f"service:{svc}"] = {"status": "pass" if reachable else "fail"}
        if not reachable:
            all_passed = False

    # Check knowledge files
    for kf in resources.knowledge:
        exists = Path(kf).exists()
        results[f"knowledge:{kf}"] = {"status": "pass" if exists else "fail"}
        if not exists:
            all_passed = False

    return json.dumps(
        {
            "status": "ok" if all_passed else "resources_failed",
            "results": results,
        }
    )


async def delegate_to_pm(
    tool_context: ToolContext,
    project_id: str,
) -> str:
    """Delegate a project to its PM by transitioning SHAPING -> ACTIVE.

    Enqueues an ARQ ``run_work_session`` job so the PM worker picks it up.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project to delegate.

    Returns:
        JSON confirmation with new status.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {
                "error": {
                    "code": "INVALID_INPUT",
                    "message": f"Invalid UUID: {project_id}",
                }
            }
        )

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(Project).where(Project.id == pid)
            project = (await db.execute(stmt)).scalar_one_or_none()
            if project is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Project {project_id} not found",
                        }
                    }
                )
            if project.status != ProjectStatus.SHAPING:
                return json.dumps(
                    {
                        "error": {
                            "code": "INVALID_STATE",
                            "message": (
                                f"Project status is {project.status.value}, expected SHAPING"
                            ),
                        }
                    }
                )

            # Enqueue work session BEFORE committing status change.
            # If enqueue fails, the DB transaction rolls back automatically.
            pool = _get_arq_pool(tool_context)
            await pool.enqueue_job(
                "run_work_session",
                project_id=str(pid),
            )

            project.status = ProjectStatus.ACTIVE
            project.started_at = datetime.now(UTC)
            await db.commit()

        return json.dumps(
            {
                "status": "ok",
                "project_id": project_id,
                "new_status": ProjectStatus.ACTIVE.value,
            }
        )
    except Exception as e:
        logger.exception("Failed to delegate to PM")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def list_projects(tool_context: ToolContext, status: str | None = None) -> str:
    """List all projects with optional status filter for cross-project visibility.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        status: Optional status filter (e.g. SHAPING, ACTIVE, PAUSED).

    Returns:
        JSON list of projects with id, name, workflow_type, status, current_stage, cost.
    """
    if status:
        try:
            status_enum = ProjectStatus(status)
        except ValueError:
            valid = [s.value for s in ProjectStatus]
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid status '{status}'. Valid: {valid}",
                    }
                }
            )
    else:
        status_enum = None

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(Project)
            if status_enum is not None:
                stmt = stmt.where(Project.status == status_enum)
            result = await db.execute(stmt.order_by(Project.created_at.desc()))
            projects = result.scalars().all()
            return json.dumps(
                {
                    "projects": [
                        {
                            "id": str(p.id),
                            "name": p.name,
                            "workflow_type": p.workflow_type,
                            "status": p.status.value,
                            "current_stage": p.current_stage,
                            "accumulated_cost": str(p.accumulated_cost),
                        }
                        for p in projects
                    ]
                }
            )
    except Exception as e:
        logger.exception("Failed to list projects")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def query_project_status(tool_context: ToolContext, project_id: str) -> str:
    """Query detailed project status including deliverable counts, stage, and cost.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project to query.

    Returns:
        JSON with project details, deliverable status counts, and pending escalations.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid UUID: {project_id}"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            # Load project
            stmt = select(Project).where(Project.id == pid)
            project = (await db.execute(stmt)).scalar_one_or_none()
            if project is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Project {project_id} not found",
                        }
                    }
                )

            # Deliverable counts by status
            count_stmt = (
                select(Deliverable.status, func.count())
                .where(Deliverable.project_id == pid)
                .group_by(Deliverable.status)
            )
            count_rows = (await db.execute(count_stmt)).all()
            deliverable_counts: dict[str, int] = {
                str(row[0].value): int(row[1]) for row in count_rows
            }
            total_deliverables = sum(deliverable_counts.values())

            # Pending escalations to director
            esc_stmt = (
                select(func.count())
                .select_from(DirectorQueueItem)
                .where(
                    DirectorQueueItem.source_project_id == pid,
                    DirectorQueueItem.status == DirectorQueueStatus.PENDING,
                )
            )
            pending_escalations: int = (await db.execute(esc_stmt)).scalar_one()

            # Compute duration_seconds
            duration_seconds: float | None = None
            if project.started_at is not None:
                end = project.completed_at or datetime.now(UTC)
                duration_seconds = (end - project.started_at).total_seconds()

            return json.dumps(
                {
                    "status": "ok",
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "workflow_type": project.workflow_type,
                        "status": project.status.value,
                        "current_stage": project.current_stage,
                        "current_taskgroup_id": (
                            str(project.current_taskgroup_id)
                            if project.current_taskgroup_id
                            else None
                        ),
                        "accumulated_cost": str(project.accumulated_cost),
                        "started_at": (
                            project.started_at.isoformat() if project.started_at else None
                        ),
                        "duration_seconds": duration_seconds,
                    },
                    "deliverables": {
                        "total": total_deliverables,
                        "by_status": deliverable_counts,
                    },
                    "pending_escalations": pending_escalations,
                }
            )
    except Exception as e:
        logger.exception("Failed to query project status")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def override_pm(
    tool_context: ToolContext, project_id: str, action: PmOverrideAction, reason: str
) -> str:
    """Direct PM intervention: pause, resume, reorder, or correct a PM's behavior.

    Applies the requested action to the project and records an audit trail
    in the Director queue.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project whose PM to override.
        action: Override type -- PAUSE, RESUME, REORDER, or CORRECT.
        reason: Justification for the override.

    Returns:
        JSON result with action outcome and audit record.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid UUID: {project_id}"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            # Verify project exists
            stmt = select(Project).where(Project.id == pid)
            project = (await db.execute(stmt)).scalar_one_or_none()
            if project is None:
                return json.dumps(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Project {project_id} not found",
                        }
                    }
                )

            result: dict[str, object] = {"action": action.value, "project_id": project_id}

            # Apply the action
            if action == PmOverrideAction.PAUSE:
                if project.status != ProjectStatus.ACTIVE:
                    return json.dumps(
                        {
                            "error": {
                                "code": "INVALID_STATE",
                                "message": (f"Cannot pause: status is {project.status.value}"),
                            }
                        }
                    )
                project.status = ProjectStatus.PAUSED
                result["new_status"] = ProjectStatus.PAUSED.value
            elif action == PmOverrideAction.RESUME:
                if project.status != ProjectStatus.PAUSED:
                    return json.dumps(
                        {
                            "error": {
                                "code": "INVALID_STATE",
                                "message": (f"Cannot resume: status is {project.status.value}"),
                            }
                        }
                    )
                project.status = ProjectStatus.ACTIVE
                result["new_status"] = ProjectStatus.ACTIVE.value
            elif action == PmOverrideAction.REORDER:
                result["message"] = "Reorder noted; PM will apply on next batch selection"
            elif action == PmOverrideAction.CORRECT:
                result["message"] = "Correction noted; PM will apply on next decision point"

            # Record audit trail (pre-resolved: Director already performed this action)
            item = DirectorQueueItem(
                type=EscalationRequestType.STATUS_REPORT,
                priority=EscalationPriority.NORMAL,
                status=DirectorQueueStatus.RESOLVED,
                title=f"PM override: {action.value} — {reason}",
                source_project_id=pid,
                source_agent="director",
                context=json.dumps(result),
                resolved_at=datetime.now(UTC),
                resolved_by="director",
                resolution=reason,
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)

            result["status"] = "ok"
            result["override_id"] = str(item.id)

            logger.info(
                "PM override on project %s: action=%s reason=%s",
                project_id,
                action,
                reason[:120],
            )

            return json.dumps(result)
    except Exception as e:
        logger.exception("Failed to record PM override")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def get_project_context(tool_context: ToolContext, path: str | None = None) -> str:
    """Detect project type, technology stack, and conventions from the codebase.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        path: Directory to scan. Defaults to current working directory.

    Returns:
        JSON with detected project context or error.
    """
    scan_dir = Path(path) if path else Path.cwd()

    if not scan_dir.is_dir():
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Path is not a directory: {scan_dir}"}}
        )

    findings: list[dict[str, object]] = []

    for config_file, language in _PROJECT_CONFIG_FILES.items():
        config_path = scan_dir / config_file

        if not config_path.is_file():
            continue

        try:
            if config_file == "pyproject.toml":
                findings.append(_parse_pyproject(config_path))
            elif config_file == "package.json":
                findings.append(_parse_package_json(config_path))
            else:
                findings.append({"language": language, "config_file": config_file})
        except Exception as exc:  # noqa: BLE001
            findings.append({"config_file": config_file, "error": str(exc)})

    if not findings:
        return json.dumps(
            {
                "status": "ok",
                "path": str(scan_dir),
                "projects": [],
                "message": "No recognised project config files found",
            }
        )

    return json.dumps(
        {
            "status": "ok",
            "path": str(scan_dir),
            "projects": findings,
        }
    )


def _parse_pyproject(config_path: Path) -> dict[str, object]:
    """Extract name and dependencies from pyproject.toml."""
    with config_path.open("rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    name = project.get("name", "unknown")
    deps: list[str] = project.get("dependencies", [])

    return {
        "language": "Python",
        "config_file": "pyproject.toml",
        "name": name,
        "dependencies": deps[:20],
        "total_dependencies": len(deps),
    }


class _PackageJson:
    """Typed wrapper for package.json parsing."""

    def __init__(self, name: str, dependencies: dict[str, str]) -> None:
        self.name = name
        self.dependencies = dependencies

    @classmethod
    def from_file(cls, path: Path) -> _PackageJson:
        raw_text = path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw_text)
        name = str(data.get("name", "unknown"))
        raw_deps = data.get("dependencies")
        deps: dict[str, str] = {}
        if isinstance(raw_deps, dict):
            # json.loads guarantees str keys for JSON objects
            for k, v in raw_deps.items():  # type: ignore[reportUnknownVariableType]
                deps[str(k)] = str(v)  # type: ignore[reportUnknownArgumentType]
        return cls(name=name, dependencies=deps)


def _parse_package_json(config_path: Path) -> dict[str, object]:
    """Extract name and dependencies from package.json."""
    pkg = _PackageJson.from_file(config_path)
    deps = list(pkg.dependencies.keys())

    return {
        "language": "JavaScript/TypeScript",
        "config_file": "package.json",
        "name": pkg.name,
        "dependencies": deps[:20],
        "total_dependencies": len(deps),
    }


async def query_dependency_graph(
    tool_context: ToolContext,
    project_id: str,
    deliverable_id: str | None = None,
) -> str:
    """Query the deliverable dependency graph for a project.

    Loads all deliverables, builds adjacency from ``depends_on`` fields,
    detects cycles, and returns the graph with statuses.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        project_id: The project whose dependency graph to query.
        deliverable_id: Optional deliverable to focus the query on.

    Returns:
        JSON graph with nodes, edges, and cycle detection result.
    """
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid UUID: {project_id}"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(Deliverable).where(Deliverable.project_id == pid)
            result = await db.execute(stmt)
            deliverables = result.scalars().all()

            if not deliverables:
                return json.dumps(
                    {
                        "status": "ok",
                        "nodes": [],
                        "edges": [],
                        "has_cycles": False,
                    }
                )

            # Build node map and edges
            nodes: list[dict[str, object]] = []
            edges: list[dict[str, str]] = []

            for d in deliverables:
                did = str(d.id)
                node: dict[str, object] = {
                    "id": did,
                    "name": d.name,
                    "status": d.status.value,
                    "depends_on": d.depends_on or [],
                }
                nodes.append(node)

                for dep_id in d.depends_on or []:
                    edges.append({"source": did, "target": dep_id})

            # Filter to focused deliverable if requested
            if deliverable_id:
                focus_set = {deliverable_id}
                changed = True
                while changed:
                    changed = False
                    for e in edges:
                        if e["source"] in focus_set and e["target"] not in focus_set:
                            focus_set.add(e["target"])
                            changed = True
                        if e["target"] in focus_set and e["source"] not in focus_set:
                            focus_set.add(e["source"])
                            changed = True
                nodes = [n for n in nodes if str(n["id"]) in focus_set]
                edges = [e for e in edges if e["source"] in focus_set and e["target"] in focus_set]

            # Cycle detection via DFS
            has_cycles = _detect_graph_cycles(nodes, edges)

            return json.dumps(
                {
                    "status": "ok",
                    "nodes": nodes,
                    "edges": edges,
                    "has_cycles": has_cycles,
                }
            )
    except Exception as e:
        logger.exception("Failed to query dependency graph")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


def _detect_graph_cycles(nodes: list[dict[str, object]], edges: list[dict[str, str]]) -> bool:
    """Detect cycles in a directed graph using iterative DFS."""
    adjacency: dict[str, list[str]] = {}
    all_ids: set[str] = set()
    for n in nodes:
        nid = str(n["id"])
        all_ids.add(nid)
        adjacency.setdefault(nid, [])
    for e in edges:
        adjacency.setdefault(e["source"], []).append(e["target"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in all_ids}

    for start in all_ids:
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        color[start] = GRAY
        while stack:
            node, idx = stack.pop()
            neighbors = adjacency.get(node, [])
            if idx < len(neighbors):
                stack.append((node, idx + 1))
                neighbor = neighbors[idx]
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE:
                    color[neighbor] = GRAY
                    stack.append((neighbor, 0))
            else:
                color[node] = BLACK

    return False
