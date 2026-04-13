"""ARQ task definitions for AutoBuilder workers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from google.genai.types import Content, Part
from sqlalchemy import func, select

from app.agents.supervision import (
    DEFAULT_BATCH_FAILURE_THRESHOLD,
    DEFAULT_DELIVERABLE_RETRY_LIMIT,
    suspend_project,
    track_batch_result,
)
from app.db.models import (
    CeoQueueItem,
    Chat,
    ChatMessage,
    Deliverable,
    DirectorQueueItem,
    Project,
    ProjectConfig,
    StageExecution,
    TaskGroupExecution,
    Workflow,
)
from app.db.models import ValidatorResult as ValidatorResultModel
from app.events.publisher import EventPublisher
from app.lib import NotFoundError, get_logger
from app.models.constants import (
    APP_NAME,
    APPROVAL_RESOLUTION_PREFIX,
    ARTIFACT_ENTITY_STAGE,
    ARTIFACT_ENTITY_TASKGROUP,
    DEFAULT_EDIT_STAGE_NAME,
    DEFAULT_WORKFLOW_NAME,
    DELIVERABLE_STATUS_PREFIX,
    SYSTEM_USER_ID,
)
from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    ChatMessageRole,
    DeliverableStatus,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    ModelRole,
    PipelineEventType,
    ProjectStatus,
    StageStatus,
    ValidatorSchedule,
    WorkflowStatus,
)
from app.router import LlmRouter, create_model_override_callback
from app.tools._context import (
    SESSION_ID_KEY,
    ToolExecutionContext,
    get_tool_context,
    register_tool_context,
    unregister_tool_context,
)
from app.workers.adk import (
    build_chat_session_agent,
    build_work_session_agents,
    create_app_container,
    create_echo_agent,
    create_runner,
    create_workflow_pipeline,
)
from app.workers.lifecycle import DIRECTOR_PAUSED_KEY

if TYPE_CHECKING:
    from pathlib import Path

    from arq.connections import ArqRedis
    from google.adk.sessions.base_session_service import BaseSessionService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.skills.library import SkillLibrary
    from app.workflows.manifest import ValidatorDefinition, WorkflowManifest
    from app.workflows.registry import WorkflowRegistry

logger = get_logger("workers.tasks")


def _resolve_workflow_stages(
    workflow_name: str,
) -> tuple[list[str] | None, dict[str, str] | None]:
    """Resolve PIPELINE_STAGE_NAMES and STAGE_COMPLETION_KEYS from a loaded workflow module.

    Returns (stages, stage_completion_keys). Both are None if the workflow module
    has not been dynamically imported yet (i.e., pipeline was not created via
    WorkflowRegistry.create_pipeline()).
    """
    import sys as _sys

    module_name = f"_autobuilder_workflow_{workflow_name.replace('-', '_')}"
    module = _sys.modules.get(module_name)
    if module is None:
        return None, None

    stages: list[str] | None = getattr(module, "PIPELINE_STAGE_NAMES", None)
    stage_keys: dict[str, str] | None = getattr(module, "STAGE_COMPLETION_KEYS", None)
    return stages, stage_keys


def _build_workflow_registry(ctx: dict[str, object]) -> WorkflowRegistry:
    """Get or construct a WorkflowRegistry from worker context."""
    from pathlib import Path

    from app.workflows.registry import WorkflowRegistry as WfReg

    existing: WorkflowRegistry | None = ctx.get("workflow_registry")  # type: ignore[assignment]
    if existing is not None:
        return existing

    from app.config import get_settings as _get_settings

    _settings = _get_settings()
    builtin_dir = Path(__file__).resolve().parent.parent / "workflows"
    redis: object | None = ctx.get("redis")
    registry = WfReg(
        builtin_dir,
        user_workflows_dir=_settings.workflows_dir,
        redis=redis,  # type: ignore[arg-type]
    )
    registry.scan()
    return registry


def _make_tool_execution_context(
    factory: async_sessionmaker[AsyncSession],
    redis: ArqRedis,
    publisher: EventPublisher,
    workflow_registry: WorkflowRegistry,
    artifacts_root: Path | None = None,
) -> ToolExecutionContext:
    """Build a ToolExecutionContext for registering with the tool context registry."""
    return ToolExecutionContext(
        db_session_factory=factory,
        arq_pool=redis,
        workflow_registry=workflow_registry,
        publisher=publisher,
        artifacts_root=artifacts_root,
    )


# ---------------------------------------------------------------------------
# Validator scheduling
# ---------------------------------------------------------------------------


async def _run_scheduled_validators(
    manifest: WorkflowManifest,
    schedule: ValidatorSchedule,
    state: dict[str, object],
    workflow_id: uuid.UUID,
    stage_execution_id: uuid.UUID | None,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> list[object]:
    """Run all validators matching the given schedule and persist results.

    Returns list of ValidatorResult DTOs from the manifest framework.
    """
    from app.workflows.manifest import ValidatorResult as ValidatorResultDTO  # noqa: TC001
    from app.workflows.validators import ValidatorRunner

    runner = ValidatorRunner()
    results: list[ValidatorResultDTO] = []

    # Gather validators from all stages + top-level manifest
    all_validators: list[ValidatorDefinition] = list(manifest.validators or [])
    for stage_def in manifest.stages:
        all_validators.extend(stage_def.validators)

    for vdef in all_validators:
        if vdef.schedule != schedule:
            continue

        result = runner.evaluate(vdef, state)
        results.append(result)

        # Persist to DB
        try:
            async with db_session_factory() as db:
                db_result = ValidatorResultModel(
                    workflow_id=workflow_id,
                    stage_execution_id=stage_execution_id,
                    validator_name=vdef.name,
                    passed=result.passed,
                    evidence=result.evidence if result.evidence else None,
                    message=result.message or None,
                )
                db.add(db_result)
                await db.commit()
        except Exception:
            logger.exception("Failed to persist validator result: %s", vdef.name)

    return results  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Regression testing (D9: RegressionTestAgent simplified for Phase 8a)
# ---------------------------------------------------------------------------


async def _run_regression_tests(
    state: dict[str, object],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, object]:
    """Run regression tests if PM's regression policy requires it.

    Reads ``pm:regression_policy`` from state. When policy is ``"always"`` or
    ``"after_batch"``, runs ``uv run pytest`` via subprocess.  When policy is
    ``"none"`` or absent, no-ops.

    Returns a result dict: ``{ran: bool, passed: bool | None, output: str}``.
    """
    import asyncio
    import shlex

    raw_policy = state.get("pm:regression_policy")
    policy: str
    command: str = "uv run pytest --tb=short -q"

    if isinstance(raw_policy, dict):
        policy_dict = cast("dict[str, object]", raw_policy)
        policy = str(policy_dict.get("schedule", "none"))
        cmd_override: object = policy_dict.get("command")
        if isinstance(cmd_override, str) and cmd_override:
            command = cmd_override
    elif isinstance(raw_policy, str):
        policy = raw_policy
    else:
        policy = "none"

    if policy not in ("always", "after_batch"):
        logger.debug("Regression tests skipped: policy=%s", policy)
        return {"ran": False, "passed": None, "output": ""}

    logger.info("Running regression tests: policy=%s command=%s", policy, command)
    args = shlex.split(command)

    working_dir = str(state.get("working_directory", "."))

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
    except Exception as exc:
        logger.warning("Regression test execution failed: %s", exc)
        return {"ran": True, "passed": False, "output": str(exc)}

    passed = exit_code == 0
    output = (stdout + stderr)[-2000:]  # Truncate to last 2000 chars

    logger.info("Regression tests %s (exit=%d)", "passed" if passed else "failed", exit_code)
    return {"ran": True, "passed": passed, "output": output}


# ---------------------------------------------------------------------------
# Batch loop execution
# ---------------------------------------------------------------------------


async def _execute_batch_loop(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    manifest: WorkflowManifest,
    stage_execution_id: uuid.UUID,
    taskgroup_execution_id: uuid.UUID,
    db_session_factory: async_sessionmaker[AsyncSession],
    publisher: EventPublisher,
    cost_ceiling: float,
    runner: object,
    session_id: str,
    adk_session_id: str,
    redis: ArqRedis | None = None,
    retry_limit: int = 2,
) -> dict[str, object]:
    """Execute the batch loop for a TaskGroup.

    Sequentially processes batches of deliverables:
    1. Calls select_ready_batch equivalent logic to get next batch
    2. For each deliverable: runs pipeline, Tier 1 checkpoint fires via callback
    3. Runs PER_DELIVERABLE validators after each deliverable
    4. Runs PER_BATCH validators after each batch
    5. Publishes batch completion events
    6. Tracks consecutive batch failures; suspends project on threshold breach
    7. Checks cost ceiling between batches
    8. Checks project pause flag between batches (DD-5)

    Returns summary dict with batch_count, deliverables_completed, deliverables_failed.
    """
    batch_count = 0
    total_completed = 0
    total_failed = 0
    cost_exceeded = False
    threshold_exceeded = False
    pause_requested = False
    # Mutable state dict for tracking consecutive batch failure counter
    failure_tracking_state: dict[str, object] = {}

    while True:
        # Check project pause flag between batches (DD-5: PM checks between deliverables)
        if redis is not None:
            pause_key = f"project:pause_requested:{project_id}"
            if await redis.exists(pause_key):
                pause_requested = True
                logger.info(
                    "Pause requested for project %s — stopping batch loop",
                    str(project_id)[:8],
                )
                break

        # Query for next ready batch
        async with db_session_factory() as db:
            stmt = select(Deliverable).where(Deliverable.project_id == project_id)
            result = await db.execute(stmt)
            all_deliverables = list(result.scalars().all())

        if not all_deliverables:
            break

        # Compute ready batch (same logic as select_ready_batch tool)
        satisfied = {
            str(d.id)
            for d in all_deliverables
            if d.status in {DeliverableStatus.COMPLETED, DeliverableStatus.SKIPPED}
        }

        actionable = [
            d
            for d in all_deliverables
            if d.status in {DeliverableStatus.PLANNED, DeliverableStatus.PENDING}
            or (d.status == DeliverableStatus.FAILED and d.retry_count < retry_limit)
        ]

        # Build in-degree map for Kahn's algorithm
        in_degree: dict[str, int] = {str(d.id): 0 for d in actionable}
        for d in actionable:
            for dep_id in d.depends_on or []:
                if dep_id not in satisfied:
                    in_degree[str(d.id)] += 1

        frontier = [d for d in actionable if in_degree[str(d.id)] == 0]
        frontier.sort(key=lambda d: (d.execution_order or 0, str(d.id)))

        if not frontier:
            break

        batch_count += 1
        batch_deliverable_ids = [str(d.id) for d in frontier]
        batch_failed_count = 0

        # Execute each deliverable in batch sequentially
        for deliverable in frontier:
            # DD-5: PM checks pause flag between deliverables within a batch
            if redis is not None:
                pause_key = f"project:pause_requested:{project_id}"
                if await redis.exists(pause_key):
                    pause_requested = True
                    logger.info(
                        "Pause requested for project %s — stopping mid-batch",
                        str(project_id)[:8],
                    )
                    break

            did = str(deliverable.id)

            # Mark as IN_PROGRESS
            async with db_session_factory() as db:
                stmt = select(Deliverable).where(Deliverable.id == deliverable.id)
                d_row = (await db.execute(stmt)).scalar_one_or_none()
                if d_row is not None and d_row.status != DeliverableStatus.IN_PROGRESS:
                    # Increment retry_count BEFORE overwriting status
                    if d_row.status == DeliverableStatus.FAILED:
                        d_row.retry_count += 1
                    d_row.status = DeliverableStatus.IN_PROGRESS
                    d_row.updated_at = datetime.now(UTC)
                    await db.commit()

            # The actual ADK pipeline execution happens via the runner.
            # In the batch loop, we invoke the runner for each deliverable.
            # The Tier 1 checkpoint callback (create_deliverable_checkpoint_callback)
            # fires automatically via after_agent_callback on the pipeline.

            # For Phase 8a sequential: the PM is invoked per-batch and uses
            # tools to drive deliverable execution. Here we track the state
            # that the PM's tool calls produce.

            # Run PER_DELIVERABLE validators
            state: dict[str, object] = {"current_deliverable_id": did}
            await _run_scheduled_validators(
                manifest=manifest,
                schedule=ValidatorSchedule.PER_DELIVERABLE,
                state=state,
                workflow_id=workflow_id,
                stage_execution_id=stage_execution_id,
                db_session_factory=db_session_factory,
            )

            # Check deliverable final status from DB
            async with db_session_factory() as db:
                stmt = select(Deliverable).where(Deliverable.id == deliverable.id)
                d_check = (await db.execute(stmt)).scalar_one_or_none()
                if d_check is not None:
                    if d_check.status == DeliverableStatus.COMPLETED:
                        total_completed += 1
                    elif d_check.status == DeliverableStatus.FAILED:
                        total_failed += 1
                        batch_failed_count += 1

        # If pause was requested mid-batch, skip post-batch processing
        if pause_requested:
            break

        # Run PER_BATCH validators
        batch_state: dict[str, object] = {
            "current_batch_deliverables": batch_deliverable_ids,
        }
        await _run_scheduled_validators(
            manifest=manifest,
            schedule=ValidatorSchedule.PER_BATCH,
            state=batch_state,
            workflow_id=workflow_id,
            stage_execution_id=stage_execution_id,
            db_session_factory=db_session_factory,
        )

        # Run regression tests after batch (D9: RegressionTestAgent)
        regression_result = await _run_regression_tests(batch_state, db_session_factory)
        if regression_result.get("ran") and not regression_result.get("passed", True):
            logger.warning(
                "Regression tests failed after batch %d for project %s",
                batch_count,
                str(project_id)[:8],
            )

        # Determine whether THIS batch had failures (per-batch, not cumulative)
        batch_had_failures = batch_failed_count > 0

        # Publish batch completion event (D14: BATCH_COMPLETED with statuses + validator results)
        batch_statuses: dict[str, str] = {}
        async with db_session_factory() as db:
            for d in frontier:
                _d_row = (
                    await db.execute(select(Deliverable).where(Deliverable.id == d.id))
                ).scalar_one_or_none()
                if _d_row is not None:
                    batch_statuses[str(d.id)] = _d_row.status.value

        await publisher.publish_batch_completed(
            workflow_id=str(workflow_id),
            project_id=str(project_id),
            deliverable_statuses=batch_statuses,
        )

        # Track consecutive batch failures and check threshold (configurable per project)
        threshold = DEFAULT_BATCH_FAILURE_THRESHOLD
        async with db_session_factory() as db:
            config_row = (
                await db.execute(
                    select(ProjectConfig).where(ProjectConfig.project_id == project_id)
                )
            ).scalar_one_or_none()
            if config_row is not None:
                raw_threshold = config_row.config.get("batch_failure_threshold")
                if isinstance(raw_threshold, int):
                    threshold = raw_threshold

        batch_outcome = await track_batch_result(
            batch_had_failures=batch_had_failures,
            state=failure_tracking_state,
            project_id=project_id,
            db_session_factory=db_session_factory,
            threshold=threshold,
        )
        if batch_outcome == "threshold_exceeded":
            threshold_exceeded = True
            await suspend_project(
                project_id=project_id,
                reason=(
                    f"Batch failure threshold exceeded: "
                    f"{threshold} consecutive batches with failures"
                ),
                db_session_factory=db_session_factory,
                publisher=publisher,
            )
            break

        # Check cost ceiling
        async with db_session_factory() as db:
            stmt = select(Project).where(Project.id == project_id)
            proj = (await db.execute(stmt)).scalar_one_or_none()
            accumulated_cost = float(proj.accumulated_cost) if proj else 0.0

        if accumulated_cost > cost_ceiling:
            cost_exceeded = True
            logger.warning(
                "Cost ceiling exceeded: %.2f > %.2f for project %s",
                accumulated_cost,
                cost_ceiling,
                str(project_id)[:8],
            )
            # Escalate to Director via queue item
            async with db_session_factory() as db:
                escalation = DirectorQueueItem(
                    type=EscalationRequestType.RESOURCE_REQUEST,
                    priority=EscalationPriority.HIGH,
                    title=f"Cost ceiling exceeded for project {project_id}",
                    source_project_id=project_id,
                    context=(
                        f"Accumulated cost {accumulated_cost:.4f} "
                        f"exceeds ceiling {cost_ceiling:.4f}"
                    ),
                )
                db.add(escalation)
                await db.commit()
            break

    # Mark deliverables blocked by permanently failed dependencies as SKIPPED.
    # When the batch loop exits with no frontier but remaining non-terminal
    # deliverables exist, those are blocked by unsatisfied dependencies from
    # permanently failed deliverables (retry exhausted). D10: "Failed
    # deliverables do not block deliverables with no dependency path through
    # the failure" -- blocked ones get SKIPPED so stage completion can proceed.
    if not pause_requested and not cost_exceeded and not threshold_exceeded:
        async with db_session_factory() as db:
            stmt = select(Deliverable).where(Deliverable.project_id == project_id)
            result = await db.execute(stmt)
            remaining = list(result.scalars().all())

            satisfied = {
                str(d.id)
                for d in remaining
                if d.status in {DeliverableStatus.COMPLETED, DeliverableStatus.SKIPPED}
            }
            permanently_failed = {
                str(d.id)
                for d in remaining
                if d.status == DeliverableStatus.FAILED and d.retry_count >= retry_limit
            }
            # Seed: deliverables with at least one unsatisfied dep permanently failed
            stuck_ids: set[str] = set()
            for d in remaining:
                if d.status not in {DeliverableStatus.PLANNED, DeliverableStatus.PENDING}:
                    continue
                for dep_id in d.depends_on or []:
                    if dep_id not in satisfied and dep_id in permanently_failed:
                        stuck_ids.add(str(d.id))
                        break
            # BFS for transitive dependents of stuck deliverables
            if stuck_ids:
                bfs_frontier = list(stuck_ids)
                while bfs_frontier:
                    current = bfs_frontier.pop()
                    for d in remaining:
                        d_id = str(d.id)
                        if d_id in stuck_ids:
                            continue
                        if d.status in {
                            DeliverableStatus.PLANNED,
                            DeliverableStatus.PENDING,
                        } and current in (d.depends_on or []):
                            stuck_ids.add(d_id)
                            bfs_frontier.append(d_id)

                for d in remaining:
                    if str(d.id) in stuck_ids:
                        d.status = DeliverableStatus.SKIPPED
                        d.updated_at = datetime.now(UTC)
                await db.commit()
                logger.info(
                    "Marked %d blocked deliverables as SKIPPED for project %s",
                    len(stuck_ids),
                    str(project_id)[:8],
                )

    return {
        "batch_count": batch_count,
        "deliverables_completed": total_completed,
        "deliverables_failed": total_failed,
        "cost_exceeded": cost_exceeded,
        "threshold_exceeded": threshold_exceeded,
        "pause_requested": pause_requested,
    }


# ---------------------------------------------------------------------------
# Stage loop execution
# ---------------------------------------------------------------------------


async def _execute_stage_loop(
    project_id: uuid.UUID,
    workflow_id: uuid.UUID,
    manifest: WorkflowManifest,
    db_session_factory: async_sessionmaker[AsyncSession],
    publisher: EventPublisher,
    cost_ceiling: float,
    runner: object,
    session_id: str,
    adk_session_id: str,
    redis: ArqRedis | None = None,
    retry_limit: int = 2,
) -> dict[str, object]:
    """Execute the stage -> taskgroup -> batch loop for a project.

    Returns summary dict with stages_completed, total_deliverables_completed,
    total_deliverables_failed, and project_completed flag.
    """
    stages = manifest.stages
    if not stages:
        return {
            "stages_completed": 0,
            "total_deliverables_completed": 0,
            "total_deliverables_failed": 0,
            "project_completed": True,
        }

    stages_completed = 0
    total_completed = 0
    total_failed = 0
    taskgroup_counter = 0

    for stage_idx, stage_def in enumerate(stages):
        # Create or resume StageExecution record
        async with db_session_factory() as db:
            existing_stmt = (
                select(StageExecution)
                .where(StageExecution.project_id == project_id)
                .where(StageExecution.stage_name == stage_def.name)
            )
            existing_se = (await db.execute(existing_stmt)).scalar_one_or_none()

            if existing_se is not None:
                if existing_se.status == StageStatus.COMPLETED:
                    stages_completed += 1
                    continue
                stage_execution_id = existing_se.id
                existing_se.status = StageStatus.ACTIVE
                existing_se.started_at = existing_se.started_at or datetime.now(UTC)
                await db.commit()
            else:
                se = StageExecution(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    stage_name=stage_def.name,
                    stage_index=stage_idx,
                    status=StageStatus.ACTIVE,
                    started_at=datetime.now(UTC),
                )
                db.add(se)
                await db.commit()
                await db.refresh(se)
                stage_execution_id = se.id

        # Update project current_stage
        async with db_session_factory() as db:
            proj_stmt = select(Project).where(Project.id == project_id)
            proj = (await db.execute(proj_stmt)).scalar_one_or_none()
            if proj is not None:
                proj.current_stage = stage_def.name
                await db.commit()

        # Publish stage started event
        await publisher.publish_lifecycle(
            workflow_id=str(workflow_id),
            event_type=PipelineEventType.STAGE_STARTED,
            metadata={
                "stage_name": stage_def.name,
                "stage_index": stage_idx,
            },
        )

        # Create TaskGroup for this stage (Phase 8a: one TaskGroup per stage)
        taskgroup_counter += 1
        async with db_session_factory() as db:
            tge = TaskGroupExecution(
                stage_execution_id=stage_execution_id,
                project_id=project_id,
                taskgroup_number=taskgroup_counter,
                status=StageStatus.ACTIVE,
                started_at=datetime.now(UTC),
            )
            db.add(tge)
            await db.commit()
            await db.refresh(tge)
            taskgroup_execution_id = tge.id

        # Update project current_taskgroup_id
        async with db_session_factory() as db:
            proj_stmt = select(Project).where(Project.id == project_id)
            proj = (await db.execute(proj_stmt)).scalar_one_or_none()
            if proj is not None:
                proj.current_taskgroup_id = taskgroup_execution_id
                await db.commit()

        # Execute batch loop within this TaskGroup
        batch_result = await _execute_batch_loop(
            project_id=project_id,
            workflow_id=workflow_id,
            manifest=manifest,
            stage_execution_id=stage_execution_id,
            taskgroup_execution_id=taskgroup_execution_id,
            db_session_factory=db_session_factory,
            publisher=publisher,
            cost_ceiling=cost_ceiling,
            runner=runner,
            session_id=session_id,
            adk_session_id=adk_session_id,
            redis=redis,
            retry_limit=retry_limit,
        )
        _batch_completed = batch_result.get("deliverables_completed", 0)
        _batch_failed = batch_result.get("deliverables_failed", 0)
        total_completed += int(_batch_completed) if isinstance(_batch_completed, int) else 0
        total_failed += int(_batch_failed) if isinstance(_batch_failed, int) else 0

        # Tier 2 checkpoint at TaskGroup boundary (always — even on interruption)
        from app.agents.supervision import checkpoint_taskgroup

        # Read actual accumulated cost from project record for checkpoint
        _tg_cost: float = 0.0
        async with db_session_factory() as db:
            _tg_proj = (
                await db.execute(select(Project).where(Project.id == project_id))
            ).scalar_one_or_none()
            if _tg_proj is not None:
                _tg_cost = float(_tg_proj.accumulated_cost)

        # Include deliverable statuses from DB for checkpoint completeness
        _tg_deliv_statuses: dict[str, object] = {}
        async with db_session_factory() as db:
            _tg_delivs = list(
                (await db.execute(select(Deliverable).where(Deliverable.project_id == project_id)))
                .scalars()
                .all()
            )
            for _d in _tg_delivs:
                _tg_deliv_statuses[f"{DELIVERABLE_STATUS_PREFIX}{_d.id}"] = _d.status

        tg_checkpoint_state: dict[str, object] = {
            "pm:total_cost": _tg_cost,
            "workflow_id": str(workflow_id),
            "pm:stages_completed": [s.name for s in stages[:stage_idx]],
            **_tg_deliv_statuses,
        }
        await checkpoint_taskgroup(
            db_session_factory=db_session_factory,
            taskgroup_execution_id=taskgroup_execution_id,
            state=tg_checkpoint_state,
            publisher=publisher,
            workflow_id=str(workflow_id),
        )

        # Check for interruptions BEFORE TaskGroup close gate and completion
        # (pause, cost ceiling, threshold exceeded). TaskGroup stays ACTIVE for resume.
        if batch_result.get("cost_exceeded"):
            logger.warning(
                "Stage %s aborted: cost ceiling exceeded",
                stage_def.name,
            )
            break

        if batch_result.get("threshold_exceeded"):
            logger.warning(
                "Stage %s aborted: batch failure threshold exceeded",
                stage_def.name,
            )
            break

        if batch_result.get("pause_requested"):
            logger.info(
                "Stage %s paused: pause requested for project %s",
                stage_def.name,
                str(project_id)[:8],
            )
            break

        # TaskGroup close gate: verify completion before marking done (FR-8a.70)
        from app.workflows.validators import verify_taskgroup_completion

        tg_gate_state: dict[str, object] = {
            "deliverable_statuses": {},
            "pm:current_stage": stage_def.name,
            "pm:pending_escalations": 0,
        }
        # Populate deliverable statuses from DB
        async with db_session_factory() as db:
            deliv_stmt = select(Deliverable).where(Deliverable.project_id == project_id)
            delivs = list((await db.execute(deliv_stmt)).scalars().all())
            tg_gate_state["deliverable_statuses"] = {str(d.id): d.status for d in delivs}
            # Check unresolved escalations from DB
            esc_stmt = (
                select(func.count())
                .select_from(DirectorQueueItem)
                .where(
                    DirectorQueueItem.source_project_id == project_id,
                    DirectorQueueItem.status == DirectorQueueStatus.PENDING,
                )
            )
            pending_esc_count = (await db.execute(esc_stmt)).scalar_one()
            tg_gate_state["pm:pending_escalations"] = pending_esc_count

        tg_validator_results_raw = await _run_scheduled_validators(
            manifest=manifest,
            schedule=ValidatorSchedule.PER_TASKGROUP,
            state=tg_gate_state,
            workflow_id=workflow_id,
            stage_execution_id=stage_execution_id,
            db_session_factory=db_session_factory,
        )
        from app.workflows.manifest import ValidatorResult as ValidatorResultDTO

        tg_validator_results = [
            r for r in tg_validator_results_raw if isinstance(r, ValidatorResultDTO)
        ]
        tg_gate_passed, tg_gate_failures = verify_taskgroup_completion(
            tg_gate_state, manifest, tg_validator_results
        )
        if not tg_gate_passed:
            # FR-8a.70: Hard gate — TaskGroup cannot close with outstanding deliverables,
            # failing validators, or unresolved escalations. Log and skip completion.
            logger.warning(
                "TaskGroup close gate BLOCKED for stage %s: %s",
                stage_def.name,
                "; ".join(tg_gate_failures),
            )
            break

        # TaskGroup completion report (only reached when close gate passes)
        from app.workflows.completion import (
            CompletionReportBuilder,
            store_taskgroup_report,
        )

        report_builder = CompletionReportBuilder(db_session_factory)
        tg_report = await report_builder.build_taskgroup_report(
            taskgroup_execution_id=taskgroup_execution_id,
            workflow_id=workflow_id,
            stage_execution_id=stage_execution_id,
        )
        await store_taskgroup_report(db_session_factory, taskgroup_execution_id, tg_report)

        # Store TaskGroup completion report as artifact
        import json as _json

        from app.agents.artifacts import ArtifactStore

        # Use artifacts_root from tool context if set (tests inject tmp_path)
        _art_root = get_tool_context(session_id).artifacts_root
        artifact_store = (
            ArtifactStore(db_session_factory=db_session_factory, artifacts_root=_art_root)
            if _art_root is not None
            else ArtifactStore(db_session_factory=db_session_factory)
        )
        await artifact_store.save(
            entity_type=ARTIFACT_ENTITY_TASKGROUP,
            entity_id=taskgroup_execution_id,
            filename="completion_report.json",
            content=_json.dumps(tg_report, default=str).encode(),
            content_type="application/json",
            project_id=project_id,
        )

        # Mark TaskGroup as completed (only reached when close gate passes)
        async with db_session_factory() as db:
            tge_stmt = select(TaskGroupExecution).where(
                TaskGroupExecution.id == taskgroup_execution_id
            )
            tge_row = (await db.execute(tge_stmt)).scalar_one_or_none()
            if tge_row is not None:
                tge_row.status = StageStatus.COMPLETED
                tge_row.completed_at = datetime.now(UTC)
                await db.commit()

        # Run PER_STAGE validators
        stage_state: dict[str, object] = {
            "pm:current_stage": stage_def.name,
            "deliverable_statuses": {},
        }
        # Populate deliverable statuses from DB for stage verification
        async with db_session_factory() as db:
            deliv_stmt = select(Deliverable).where(Deliverable.project_id == project_id)
            delivs = list((await db.execute(deliv_stmt)).scalars().all())
            stage_state["deliverable_statuses"] = {str(d.id): d.status for d in delivs}

        stage_validator_results_raw = await _run_scheduled_validators(
            manifest=manifest,
            schedule=ValidatorSchedule.PER_STAGE,
            state=stage_state,
            workflow_id=workflow_id,
            stage_execution_id=stage_execution_id,
            db_session_factory=db_session_factory,
        )

        # Verify stage completion gate before advancing
        from app.workflows.validators import verify_stage_completion

        stage_val_results = [
            r for r in stage_validator_results_raw if isinstance(r, ValidatorResultDTO)
        ]
        stage_gate_passed, stage_gate_failures = verify_stage_completion(
            stage_state, manifest, stage_val_results
        )
        if not stage_gate_passed:
            logger.warning(
                "Stage completion gate failed for %s: %s",
                stage_def.name,
                "; ".join(stage_gate_failures),
            )

        # Stage completion report
        from app.workflows.completion import store_stage_report

        stage_report = await report_builder.build_stage_report(
            stage_execution_id=stage_execution_id,
            workflow_id=workflow_id,
        )
        await store_stage_report(db_session_factory, stage_execution_id, stage_report)

        # Store stage completion report as artifact
        await artifact_store.save(
            entity_type=ARTIFACT_ENTITY_STAGE,
            entity_id=stage_execution_id,
            filename="completion_report.json",
            content=_json.dumps(stage_report, default=str).encode(),
            content_type="application/json",
            project_id=project_id,
        )

        # Mark stage as completed
        async with db_session_factory() as db:
            se_stmt = select(StageExecution).where(StageExecution.id == stage_execution_id)
            se_row = (await db.execute(se_stmt)).scalar_one_or_none()
            if se_row is not None:
                se_row.status = StageStatus.COMPLETED
                se_row.completed_at = datetime.now(UTC)
                await db.commit()

        stages_completed += 1

        # Publish stage completed event (D14: STAGE_COMPLETED with project_id)
        await publisher.publish_stage_completed(
            workflow_id=str(workflow_id),
            project_id=str(project_id),
            stage_name=stage_def.name,
        )

    project_completed = stages_completed == len(stages)

    # Mark project as completed if all stages done
    if project_completed:
        old_project_status: ProjectStatus = ProjectStatus.ACTIVE
        async with db_session_factory() as db:
            proj_stmt = select(Project).where(Project.id == project_id)
            proj = (await db.execute(proj_stmt)).scalar_one_or_none()
            if proj is not None:
                old_project_status = proj.status
                proj.status = ProjectStatus.COMPLETED
                proj.completed_at = datetime.now(UTC)
                await db.commit()

        # D14: PROJECT_STATUS_CHANGED on completion
        await publisher.publish_project_status_changed(
            workflow_id=str(workflow_id),
            project_id=str(project_id),
            old_status=old_project_status,
            new_status=ProjectStatus.COMPLETED,
        )

    return {
        "stages_completed": stages_completed,
        "total_deliverables_completed": total_completed,
        "total_deliverables_failed": total_failed,
        "project_completed": project_completed,
    }


async def _detect_cross_project_patterns(
    db_session_factory: async_sessionmaker[AsyncSession],
    window_hours: float = 1.0,
) -> list[dict[str, object]]:
    """Detect when 2+ projects escalate the same failure type within a time window.

    Queries PENDING DirectorQueueItems grouped by escalation type, filtering to
    those created within ``window_hours`` of now. Returns a list of pattern dicts
    when 2+ distinct projects share the same escalation type.
    """
    async with db_session_factory() as db:
        cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
        stmt = (
            select(
                DirectorQueueItem.type,
                func.count(func.distinct(DirectorQueueItem.source_project_id)).label(
                    "project_count"
                ),
                func.array_agg(func.distinct(DirectorQueueItem.source_project_id)).label(
                    "project_ids"
                ),
            )
            .where(DirectorQueueItem.created_at >= cutoff)
            .where(DirectorQueueItem.status == DirectorQueueStatus.PENDING)
            .where(DirectorQueueItem.source_project_id.is_not(None))
            .group_by(DirectorQueueItem.type)
            .having(func.count(func.distinct(DirectorQueueItem.source_project_id)) >= 2)
        )
        result = await db.execute(stmt)
        patterns: list[dict[str, object]] = []
        for row in result:
            patterns.append(
                {
                    "type": str(row.type.value),  # type: ignore[union-attr]
                    "project_count": int(row.project_count),  # type: ignore[arg-type]
                    "project_ids": [str(pid) for pid in row.project_ids if pid],  # type: ignore[union-attr]
                }
            )
        return patterns


async def _create_pattern_alert(
    db_session_factory: async_sessionmaker[AsyncSession],
    pattern: dict[str, object],
) -> None:
    """Create a CeoQueueItem NOTIFICATION for a detected cross-project pattern.

    Skips creation if an identical alert (same type + projects) already exists
    in PENDING state to avoid flooding.
    """
    async with db_session_factory() as db:
        # De-duplicate: check for existing PENDING alert with same pattern type
        existing_stmt = (
            select(func.count())
            .select_from(CeoQueueItem)
            .where(CeoQueueItem.type == CeoItemType.NOTIFICATION)
            .where(CeoQueueItem.status == CeoQueueStatus.PENDING)
            .where(CeoQueueItem.title.like(f"Cross-project pattern: {pattern['type']}%"))
        )
        count_result = await db.execute(existing_stmt)
        if count_result.scalar_one() > 0:
            logger.debug(
                "Skipping duplicate pattern alert for type %s",
                pattern["type"],
            )
            return

        ceo_item = CeoQueueItem(
            type=CeoItemType.NOTIFICATION,
            priority=EscalationPriority.HIGH,
            title=f"Cross-project pattern: {pattern['type']} ({pattern['project_count']} projects)",
            source_agent="director",
            metadata_={
                "pattern_type": pattern["type"],
                "project_count": pattern["project_count"],
                "project_ids": pattern["project_ids"],
            },
        )
        db.add(ceo_item)
        await db.commit()
        logger.info(
            "Created CEO queue alert for cross-project pattern: %s (%d projects)",
            pattern["type"],
            pattern["project_count"],
        )


async def create_edit_taskgroup(
    project_id: uuid.UUID,
    edit_operation: str,
    description: str,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    """Create a new TaskGroup for an edit operation within an existing project.

    Called by the Director when the CEO requests an edit. The new TaskGroup is
    incorporated by the PM via select_ready_batch without interrupting current
    deliverables. Edit work follows the same execution loop with the same
    validation, checkpointing, and reporting as original work.

    Projects in any state (SHAPING, ACTIVE, PAUSED, SUSPENDED, COMPLETED) accept
    edit TaskGroups — they represent new work injected into an existing project.

    Args:
        project_id: UUID of the project to edit.
        edit_operation: Name of the edit operation (e.g. 'fix_bug', 'add_feature').
        description: Human-readable description of the edit request.
        db_session_factory: Async session factory for DB access.

    Returns:
        UUID of the newly created TaskGroupExecution.

    Raises:
        ValueError: If the project does not exist.
    """
    async with db_session_factory() as db:
        # Verify project exists
        project_row = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if project_row is None:
            raise ValueError(f"Project {project_id} not found")

        # Find the most recent StageExecution for this project to attach to
        stage_exec = (
            (
                await db.execute(
                    select(StageExecution)
                    .where(StageExecution.project_id == project_id)
                    .order_by(StageExecution.created_at.desc())
                )
            )
            .scalars()
            .first()
        )

        if stage_exec is None:
            # No existing stage execution — need a workflow to create one.
            # Look up the project's workflow via workflow_type.
            workflow_row = (
                (
                    await db.execute(
                        select(Workflow)
                        .where(Workflow.workflow_type == project_row.workflow_type)
                        .order_by(Workflow.created_at.desc())
                    )
                )
                .scalars()
                .first()
            )

            workflow_id = workflow_row.id if workflow_row is not None else uuid.uuid4()

            stage_exec = StageExecution(
                workflow_id=workflow_id,
                project_id=project_id,
                stage_name=DEFAULT_EDIT_STAGE_NAME,
                stage_index=0,
                status=StageStatus.PENDING,
            )
            db.add(stage_exec)
            await db.flush()

        # Determine next taskgroup_number for this project
        count_result = await db.execute(
            select(func.count())
            .select_from(TaskGroupExecution)
            .where(TaskGroupExecution.project_id == project_id)
        )
        next_number = (count_result.scalar_one() or 0) + 1

        taskgroup = TaskGroupExecution(
            stage_execution_id=stage_exec.id,
            project_id=project_id,
            taskgroup_number=next_number,
            status=StageStatus.PENDING,
            checkpoint_data={
                "edit_operation": edit_operation,
                "edit_description": description,
            },
        )
        db.add(taskgroup)
        await db.commit()
        await db.refresh(taskgroup)

        logger.info(
            "Created edit TaskGroup %s for project %s (operation=%s)",
            taskgroup.id,
            project_id,
            edit_operation,
        )
        return taskgroup.id


async def create_batch_edit_taskgroups(
    project_id: uuid.UUID,
    edits: list[dict[str, str]],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> list[uuid.UUID]:
    """Create ordered TaskGroups for a batch of edit operations.

    TaskGroups are created in order, respecting inter-edit dependencies.
    Each edit gets its own TaskGroup with sequential numbering.

    Args:
        project_id: UUID of the project to edit.
        edits: List of edit dicts, each with "operation" and optional "description".
        db_session_factory: Async session factory for DB access.

    Returns:
        List of TaskGroupExecution UUIDs in creation order.

    Raises:
        ValueError: If the project does not exist.
    """
    taskgroup_ids: list[uuid.UUID] = []
    for edit in edits:
        tg_id = await create_edit_taskgroup(
            project_id=project_id,
            edit_operation=edit["operation"],
            description=edit.get("description", ""),
            db_session_factory=db_session_factory,
        )
        taskgroup_ids.append(tg_id)
    return taskgroup_ids


async def apply_resolution(
    ctx: dict[str, object], *, project_id: str, resolution: str
) -> dict[str, str | list[str]]:
    """ARQ task: apply a CEO escalation resolution to a project.

    Delegates to lifecycle.apply_resolution_to_project which handles
    SUSPENDED->ACTIVE transition and failed deliverable retry.
    """
    from app.workers.lifecycle import apply_resolution_to_project

    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    pid = uuid.UUID(project_id)
    return await apply_resolution_to_project(
        project_id=pid,
        resolution=resolution,
        db_session_factory=db_session_factory,
        redis=redis,
    )


async def test_task(ctx: dict[str, object], payload: str) -> dict[str, str]:
    """Minimal ARQ job for gateway-to-worker round-trip validation."""
    logger.info("Processing test_task", extra={"payload": payload})
    return {"status": "completed", "payload": payload}


async def heartbeat(ctx: dict[str, object]) -> None:
    """Cron job: logs 'worker alive' every 60 seconds."""
    logger.info("worker alive")


async def run_workflow(ctx: dict[str, object], workflow_id: str) -> dict[str, str]:
    """Execute a workflow via ADK pipeline."""

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)

    try:
        # Read workflow record and extract params in a single query
        workflow_params: dict[str, object] = {}
        async with factory() as db_session:
            result = await db_session.execute(
                select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                raise NotFoundError(message=f"Workflow {workflow_id} not found")

            # Update status to RUNNING
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(UTC)
            if workflow.params is not None:
                workflow_params = dict(workflow.params)
            await db_session.commit()

        # Publish WORKFLOW_STARTED
        await publisher.publish_lifecycle(workflow_id, PipelineEventType.WORKFLOW_STARTED)

        pipeline_type = str(workflow_params.get("pipeline_type", "echo"))

        if pipeline_type == "deliverable":
            from app.agents.assembler import InstructionContext
            from app.agents.context_monitor import ContextRecreationRequired

            instruction_ctx = InstructionContext(
                project_config=str(workflow_params["project_config"])
                if "project_config" in workflow_params
                else None,
                task_context=str(workflow_params["task_context"])
                if "task_context" in workflow_params
                else None,
                agent_name="pipeline",
            )

            workflow_name = str(workflow_params.get("workflow_name", DEFAULT_WORKFLOW_NAME))

            # Register ToolExecutionContext so pipeline tools can access DB/ARQ
            wf_workflow_registry = _build_workflow_registry(ctx)
            _wf_art_root: Path | None = ctx.get("artifacts_root")  # type: ignore[assignment]
            wf_tool_ctx = _make_tool_execution_context(
                factory, redis, publisher, wf_workflow_registry, artifacts_root=_wf_art_root
            )
            register_tool_context(workflow_id, wf_tool_ctx)

            try:
                pipeline = await create_workflow_pipeline(workflow_name, ctx, instruction_ctx)
                app_container = create_app_container(root_agent=pipeline)
                runner = create_runner(app_container, session_service)

                # Create or resume session with _session_id for tool context lookup
                session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=workflow_id
                )
                if session is None:
                    session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                        app_name=APP_NAME,
                        user_id=SYSTEM_USER_ID,
                        session_id=workflow_id,
                        state={SESSION_ID_KEY: workflow_id},
                    )
                else:
                    # Ensure _session_id for resumed sessions
                    _wf_raw_obj: object = getattr(session, "state", None)
                    _wf_raw = (
                        cast("dict[str, object]", _wf_raw_obj)
                        if isinstance(_wf_raw_obj, dict)
                        else {}
                    )
                    if _wf_raw.get(SESSION_ID_KEY) != workflow_id:
                        _wf_merged = dict(_wf_raw)
                        _wf_merged[SESSION_ID_KEY] = workflow_id
                        session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                            app_name=APP_NAME,
                            user_id=SYSTEM_USER_ID,
                            session_id=workflow_id,
                            state=_wf_merged,
                        )

                prompt_text = str(workflow_params.get("prompt", "Execute deliverable pipeline"))
                message = Content(parts=[Part(text=prompt_text)])

                async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
                    user_id=SYSTEM_USER_ID,
                    session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                    new_message=message,
                ):
                    translated = publisher.translate(event, workflow_id)
                    if translated is not None:
                        await publisher.publish(translated)
                await publisher.flush_violations()

            except ContextRecreationRequired as e:
                await publisher.flush_violations()
                logger.warning(
                    "Context recreation required for workflow %s: %.1f%% usage (threshold %.1f%%)",
                    workflow_id,
                    e.usage_pct,
                    e.threshold_pct,
                )
                from app.agents.context_recreation import recreate_context

                # Resolve workflow-specific stages for recreation
                _stages, _stage_keys = _resolve_workflow_stages(workflow_name)

                recreation_result = await recreate_context(
                    session_service=session_service,
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    old_session_id=workflow_id,
                    publisher=publisher,
                    memory_service=None,
                    stages=_stages,
                    stage_completion_keys=_stage_keys,
                )
                logger.info(
                    "Context recreation completed for workflow %s: "
                    "new_session=%s, remaining=%d stages",
                    workflow_id,
                    recreation_result.new_session_id,
                    len(recreation_result.remaining_stages),
                )
            finally:
                unregister_tool_context(workflow_id)

        else:
            # Existing echo pipeline logic
            callback = create_model_override_callback(router)
            echo_agent = create_echo_agent(
                model=router.select_model(ModelRole.FAST),
                before_model_callback=callback,
            )
            app_container = create_app_container(root_agent=echo_agent)
            runner = create_runner(app_container, session_service)

            # Create or resume session
            session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=workflow_id
            )
            if session is None:
                session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    session_id=workflow_id,
                )

            # Construct the prompt from workflow params
            prompt_text = str(workflow_params.get("prompt", "Hello, echo agent!"))
            message = Content(parts=[Part(text=prompt_text)])

            # Execute and stream events
            async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
                user_id=SYSTEM_USER_ID,
                session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                new_message=message,
            ):
                translated = publisher.translate(event, workflow_id)
                if translated is not None:
                    await publisher.publish(translated)
            await publisher.flush_violations()

        # Update status to COMPLETED
        async with factory() as db_session:
            result = await db_session.execute(
                select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
            )
            workflow = result.scalar_one_or_none()
            if workflow is not None:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now(UTC)
                await db_session.commit()

        await publisher.publish_lifecycle(workflow_id, PipelineEventType.WORKFLOW_COMPLETED)

        logger.info("Workflow completed", extra={"workflow_id": workflow_id})
        return {"status": "completed", "workflow_id": workflow_id}

    except NotFoundError:
        raise
    except Exception as exc:
        logger.error(
            "Workflow failed",
            extra={"workflow_id": workflow_id},
            exc_info=True,
        )
        # Update status to FAILED
        try:
            async with factory() as db_session:
                result = await db_session.execute(
                    select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
                )
                workflow = result.scalar_one_or_none()
                if workflow is not None:
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now(UTC)
                    workflow.error_message = str(exc)
                    await db_session.commit()
        except Exception:
            logger.error("Failed to update workflow status", exc_info=True)

        try:
            await publisher.publish_lifecycle(
                workflow_id,
                PipelineEventType.WORKFLOW_FAILED,
                metadata={"error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish WORKFLOW_FAILED event", exc_info=True)
        raise


async def process_director_queue(ctx: dict[str, object]) -> None:
    """ARQ cron: scan for pending Director Queue items in idle projects.

    1. Checks Director pause flag -- skips all processing if paused.
    2. Detects cross-project patterns and creates CEO queue alerts.
    3. Enqueues run_director_turn for projects with pending items
       and no active work session.
    """
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    # Check Director pause flag -- skip all processing when paused
    if await redis.exists(DIRECTOR_PAUSED_KEY):
        logger.info("Director is paused -- skipping queue processing")
        return

    # Cross-project pattern detection: alert CEO when 2+ projects
    # escalate the same type within the configurable window
    try:
        patterns = await _detect_cross_project_patterns(factory)
        for pattern in patterns:
            await _create_pattern_alert(factory, pattern)
    except Exception:
        logger.error("Cross-project pattern detection failed", exc_info=True)

    async with factory() as db_session:
        stmt = (
            select(DirectorQueueItem.source_project_id)
            .where(DirectorQueueItem.status == DirectorQueueStatus.PENDING)
            .where(DirectorQueueItem.source_project_id.is_not(None))
            .group_by(DirectorQueueItem.source_project_id)
        )
        result = await db_session.execute(stmt)
        project_ids: list[uuid.UUID] = [
            row[0]
            for row in result.all()  # type: ignore[misc]
        ]

    if not project_ids:
        return

    for project_id in project_ids:
        key = f"{_WORK_SESSION_KEY_PREFIX}{project_id}"
        active = await redis.exists(key)
        if active:
            logger.debug(
                "Skipping project %s — active work session",
                project_id,
            )
            continue

        await redis.enqueue_job(
            "run_director_turn",
            project_id=str(project_id),
            _queue_name="arq:queue",
        )
        logger.info(
            "Enqueued director queue evaluation for idle project %s",
            project_id,
        )


async def run_director_turn(
    ctx: dict[str, object],
    chat_id: str | None = None,
    message_id: str | None = None,
    *,
    project_id: str | None = None,
    brief: str | None = None,
) -> dict[str, str]:
    """Run a single Director turn.

    Three invocation modes:
    - **Chat mode** (chat_id + message_id): CEO sends a message through chat.
      Director processes the message and persists a response ChatMessage.
    - **Queue mode** (project_id): Cron triggers Director to evaluate pending
      Director Queue items for an idle project. Director runs with a synthetic
      prompt summarizing the pending items. No ChatMessage persistence.
    - **Brief mode** (brief): Gateway enqueues project creation from a brief.
      Director processes the brief and creates a project. No ChatMessage persistence.

    For SETTINGS chats, injects formation or evolution instructions based on
    formation status. For DIRECTOR/PROJECT chats, runs standard Director.

    Registers a ToolExecutionContext so Director management tools (create_project,
    delegate_to_pm, escalate_to_ceo, etc.) can access DB and ARQ infrastructure.
    """
    from pathlib import Path

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionAssembler, InstructionContext
    from app.agents.formation import (
        EVOLUTION_INSTRUCTION,
        FORMATION_INSTRUCTION,
        ensure_formation_state,
    )
    from app.models.enums import ChatType, DefinitionScope, FormationStatus
    from app.tools._toolset import GlobalToolset

    # Validate invocation mode
    chat_mode = chat_id is not None and message_id is not None
    queue_mode = project_id is not None
    brief_mode = brief is not None
    if not chat_mode and not queue_mode and not brief_mode:
        raise ValueError("run_director_turn requires (chat_id + message_id), project_id, or brief")

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)
    if chat_id is not None:
        adk_session_id: str = chat_id
    elif project_id is not None:
        adk_session_id = f"director_queue_{project_id}"
    else:
        adk_session_id = f"director_brief_{uuid.uuid4()}"

    # Register tool execution context so Director tools can access DB/ARQ
    workflow_registry = _build_workflow_registry(ctx)
    _dir_art_root: Path | None = ctx.get("artifacts_root")  # type: ignore[assignment]
    tool_exec_ctx = _make_tool_execution_context(
        factory,
        redis,
        publisher,
        workflow_registry,
        artifacts_root=_dir_art_root,
    )
    register_tool_context(adk_session_id, tool_exec_ctx)

    try:
        # 1. Resolve prompt and session context based on mode
        prompt_text: str
        chat_type: object = None  # ChatType or None for queue mode

        if chat_mode:
            assert chat_id is not None
            assert message_id is not None
            async with factory() as db_session:
                msg_result = await db_session.execute(
                    select(ChatMessage).where(
                        ChatMessage.id == message_id  # type: ignore[reportArgumentType]
                    )
                )
                user_message = msg_result.scalar_one_or_none()
                if user_message is None:
                    raise NotFoundError(message=f"ChatMessage {message_id} not found")
                prompt_text = user_message.content

                chat_result = await db_session.execute(
                    select(Chat).where(
                        Chat.id == chat_id  # type: ignore[reportArgumentType]
                    )
                )
                chat = chat_result.scalar_one_or_none()
                if chat is None:
                    raise NotFoundError(message=f"Chat {chat_id} not found")
                adk_session_id = chat.session_id
                chat_type = chat.type

                # Re-register under the resolved session_id (chat.session_id)
                unregister_tool_context(chat_id)
                register_tool_context(adk_session_id, tool_exec_ctx)
        elif brief_mode:
            # Brief mode: project creation from gateway POST /projects
            assert brief is not None
            prompt_text = (
                f"A user has submitted a new project brief. "
                f"Validate the brief, create the project, check resources, "
                f"and delegate to PM if everything checks out.\n\n"
                f"Brief:\n{brief}"
            )
        else:
            # Queue mode: build prompt from pending Director Queue items
            assert project_id is not None
            async with factory() as db_session:
                stmt = (
                    select(DirectorQueueItem)
                    .where(DirectorQueueItem.status == DirectorQueueStatus.PENDING)
                    .where(
                        DirectorQueueItem.source_project_id == uuid.UUID(project_id)  # type: ignore[reportArgumentType]
                    )
                    .order_by(DirectorQueueItem.priority.desc(), DirectorQueueItem.created_at)
                )
                result = await db_session.execute(stmt)
                items = list(result.scalars().all())

            if not items:
                logger.info(
                    "No pending queue items for project %s, skipping",
                    project_id,
                )
                return {"status": "skipped", "project_id": project_id}

            item_summaries = [
                f"- [{item.priority.value}] {item.title}: {item.context}" for item in items
            ]
            prompt_text = (
                f"You have {len(items)} pending escalation(s) from PM "
                f"for project {project_id}. Evaluate each and decide whether "
                f"to resolve locally or forward to the CEO queue.\n\n" + "\n".join(item_summaries)
            )

        # 2. Determine formation state and task context
        formation_status = await ensure_formation_state(session_service, SYSTEM_USER_ID)  # type: ignore[reportArgumentType]

        task_context: str | None = None
        if chat_type == ChatType.SETTINGS:
            if formation_status != FormationStatus.COMPLETE:
                task_context = FORMATION_INSTRUCTION
            else:
                task_context = EVOLUTION_INSTRUCTION

        instruction_ctx = InstructionContext(
            task_context=task_context,
            agent_name="director",
        )

        # 3. Build Director from AgentRegistry (no sub_agents for chat/queue)
        assembler = InstructionAssembler()
        toolset = GlobalToolset()
        registry = AgentRegistry(
            assembler=assembler,
            router=router,
            toolset=toolset,
        )
        global_agents_dir = Path(__file__).resolve().parent.parent / "agents"
        registry.scan((global_agents_dir, DefinitionScope.GLOBAL))

        # Resolve Director skills at build time (FR-6.46, FR-6.49)
        skill_library: SkillLibrary | None = ctx.get("skill_library")  # type: ignore[assignment]
        director = build_chat_session_agent(registry, instruction_ctx, skill_library=skill_library)
        app_container = create_app_container(root_agent=director)
        runner = create_runner(app_container, session_service)

        # 4. Create or resume ADK session with _session_id in state
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id=adk_session_id,
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=adk_session_id,
                state={SESSION_ID_KEY: adk_session_id},
            )
        else:
            # Ensure _session_id exists for resumed sessions (tools depend on it)
            raw_state_obj: object = getattr(session, "state", None)
            raw_state = (
                cast("dict[str, object]", raw_state_obj) if isinstance(raw_state_obj, dict) else {}
            )
            if raw_state.get(SESSION_ID_KEY) != adk_session_id:
                merged = dict(raw_state)
                merged[SESSION_ID_KEY] = adk_session_id
                session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    session_id=adk_session_id,
                    state=merged,
                )

        # 5. Run single Director turn
        message = Content(parts=[Part(text=prompt_text)])
        response_text = ""
        async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
            user_id=SYSTEM_USER_ID,
            session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            new_message=message,
        ):
            content = getattr(event, "content", None)
            if content is not None:
                content_parts = getattr(content, "parts", None)
                if content_parts is not None:
                    for part in content_parts:
                        text = getattr(part, "text", None)
                        if text:
                            response_text += text

        # 6. Persist Director response (chat mode only)
        if chat_mode:
            if not response_text:
                response_text = "(No response from Director)"

            assert chat_id is not None
            async with factory() as db_session:
                director_message = ChatMessage(
                    chat_id=uuid.UUID(chat_id),
                    role=ChatMessageRole.DIRECTOR,
                    content=response_text,
                )
                db_session.add(director_message)
                await db_session.commit()

        # 7. Publish audit event
        mode_label = "chat" if chat_mode else ("brief" if brief_mode else "queue")
        await publisher.publish_lifecycle(
            adk_session_id,
            PipelineEventType.AGENT_COMPLETED,
            metadata={
                "agent": "director",
                "mode": mode_label,
                "chat_type": str(chat_type) if chat_type else None,
            },
        )

        log_id = chat_id if chat_mode else (project_id or adk_session_id)
        logger.info("Director turn completed", extra={"id": log_id})
        return {"status": "completed", "id": str(log_id)}

    except NotFoundError:
        raise
    except Exception as exc:
        log_id = chat_id if chat_mode else (project_id or adk_session_id)
        logger.error(
            "Director turn failed",
            extra={"id": log_id},
            exc_info=True,
        )

        # Persist error as Director message (chat mode only)
        if chat_mode and chat_id is not None:
            try:
                async with factory() as db_session:
                    error_message = ChatMessage(
                        chat_id=uuid.UUID(chat_id),
                        role=ChatMessageRole.DIRECTOR,
                        content=f"(Director error: {exc})",
                    )
                    db_session.add(error_message)
                    await db_session.commit()
            except Exception:
                logger.error("Failed to persist error message", exc_info=True)

        # Publish error event (FR-5b.33)
        try:
            await publisher.publish_lifecycle(
                adk_session_id,
                PipelineEventType.ERROR,
                metadata={"agent": "director", "error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish director error event", exc_info=True)

        raise
    finally:
        unregister_tool_context(adk_session_id)


_WORK_SESSION_KEY_PREFIX = "director:work_session:"
# TTL must exceed maximum expected work session duration. Stage loops with
# multiple deliverables can run for hours. 24 hours provides safe headroom.
# The key is explicitly deleted on completion or failure.
_WORK_SESSION_TTL = 86400  # 24 hours


async def run_work_session(
    ctx: dict[str, object],
    project_id: str,
    params: dict[str, object] | None = None,
) -> dict[str, str]:
    """Execute a work session: Director delegates to PM for autonomous execution.

    Director is root_agent with PM as sub_agent. PM runs deliverable pipelines.
    Hard limits (retry_budget, cost_ceiling) loaded from project_configs table.
    """
    from pathlib import Path

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionAssembler, InstructionContext
    from app.agents.context_monitor import ContextRecreationRequired
    from app.agents.formation import ensure_formation_state
    from app.config import get_settings
    from app.models.enums import DefinitionScope
    from app.tools._toolset import GlobalToolset

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)
    settings = get_settings()
    session_id = f"work_session_{project_id}"
    redis_key = f"{_WORK_SESSION_KEY_PREFIX}{project_id}"

    # Register tool execution context so tools can access DB/ARQ
    workflow_registry = _build_workflow_registry(ctx)
    _art_root: Path | None = ctx.get("artifacts_root")  # type: ignore[assignment]
    tool_exec_ctx = _make_tool_execution_context(
        factory,
        redis,
        publisher,
        workflow_registry,
        artifacts_root=_art_root,
    )
    register_tool_context(session_id, tool_exec_ctx)

    try:
        # 1. Load project config from DB (or use defaults)
        retry_budget = settings.default_retry_budget
        cost_ceiling = settings.default_cost_ceiling
        deliverable_retry_limit = DEFAULT_DELIVERABLE_RETRY_LIMIT
        project_uuid: uuid.UUID | None = None
        workflow_uuid: uuid.UUID | None = None

        # Try to parse project_id as UUID for FK-based lookup
        import contextlib

        with contextlib.suppress(ValueError):
            project_uuid = uuid.UUID(project_id)

        # Load config: prefer project_id FK, fall back to project_name string match
        async with factory() as db_session:
            if project_uuid is not None:
                result = await db_session.execute(
                    select(ProjectConfig).where(ProjectConfig.project_id == project_uuid)
                )
                project_config = result.scalar_one_or_none()
                # Fall back to name-based lookup if FK match fails
                if project_config is None:
                    result = await db_session.execute(
                        select(ProjectConfig).where(
                            ProjectConfig.project_name == project_id  # type: ignore[reportArgumentType]
                        )
                    )
                    project_config = result.scalar_one_or_none()
            else:
                result = await db_session.execute(
                    select(ProjectConfig).where(
                        ProjectConfig.project_name == project_id  # type: ignore[reportArgumentType]
                    )
                )
                project_config = result.scalar_one_or_none()

            if project_config is not None:
                config_dict: dict[str, object] = dict(project_config.config)
                raw_budget = config_dict.get("retry_budget")
                if isinstance(raw_budget, int):
                    retry_budget = raw_budget
                raw_ceiling = config_dict.get("cost_ceiling")
                if isinstance(raw_ceiling, (int, float)):
                    cost_ceiling = float(raw_ceiling)
                raw_retry_limit = config_dict.get("deliverable_retry_limit")
                if isinstance(raw_retry_limit, int):
                    deliverable_retry_limit = raw_retry_limit

        # Load project record if UUID provided
        if project_uuid is not None:
            async with factory() as db_session:
                proj_result = await db_session.execute(
                    select(Project).where(Project.id == project_uuid)
                )
                project_record = proj_result.scalar_one_or_none()
                if project_record is not None and project_record.status == ProjectStatus.SHAPING:
                    project_record.status = ProjectStatus.ACTIVE
                    project_record.started_at = datetime.now(UTC)
                    await db_session.commit()
                    # D14: PROJECT_STATUS_CHANGED on SHAPING -> ACTIVE
                    await publisher.publish_project_status_changed(
                        workflow_id=session_id,
                        project_id=project_id,
                        old_status=ProjectStatus.SHAPING,
                        new_status=ProjectStatus.ACTIVE,
                    )

        # 2. Ensure formation state for the system user
        await ensure_formation_state(session_service, SYSTEM_USER_ID)  # type: ignore[reportArgumentType]

        # 3. Create instruction context
        resolved_params = params or {}
        instruction_ctx = InstructionContext(
            project_config=str(resolved_params["project_config"])
            if "project_config" in resolved_params
            else None,
            task_context=str(resolved_params["task_context"])
            if "task_context" in resolved_params
            else None,
            agent_name="director",
        )

        # 4. Build agent tree (Director + PM with supervision callbacks)
        assembler = InstructionAssembler()
        toolset = GlobalToolset()
        registry = AgentRegistry(
            assembler=assembler,
            router=router,
            toolset=toolset,
        )
        global_agents_dir = Path(__file__).resolve().parent.parent / "agents"
        registry.scan((global_agents_dir, DefinitionScope.GLOBAL))

        # Create pipeline callbacks (model routing, budget monitor, system reminders)
        from app.workers.adk import create_pipeline_callbacks

        pipeline_callbacks = create_pipeline_callbacks(
            router, float(settings.context_budget_threshold)
        )

        # Resolve Director + PM skills at build time (FR-6.46, FR-6.47, FR-6.48)
        work_skill_library: SkillLibrary | None = ctx.get("skill_library")  # type: ignore[assignment]
        work_workflow_registry: WorkflowRegistry | None = ctx.get("workflow_registry")  # type: ignore[assignment]
        director = await build_work_session_agents(
            registry=registry,
            ctx=instruction_ctx,
            project_id=project_id,
            publisher=publisher,
            skill_library=work_skill_library,
            before_model_callback=pipeline_callbacks,
            workflow_registry=work_workflow_registry,
            db_session_factory=factory,
        )

        # 4b. Load workflow manifest for stage loop
        workflow_name = str(resolved_params.get("workflow_name", DEFAULT_WORKFLOW_NAME))
        manifest = workflow_registry.get_manifest(workflow_name)

        # 5. Create App container and Runner
        app_container = create_app_container(root_agent=director)
        runner = create_runner(app_container, session_service)

        # 6. Create or resume ADK session with hard limits in state
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=session_id
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=session_id,
                state={
                    "project_config": {
                        "retry_budget": retry_budget,
                        "cost_ceiling": cost_ceiling,
                    },
                    "workflow_id": session_id,
                    SESSION_ID_KEY: session_id,
                    "pm:project_id": project_id,
                },
            )
        else:
            # Ensure _session_id exists for resumed sessions (tools depend on it)
            raw_resumed_obj: object = getattr(session, "state", None)
            raw_resumed = (
                cast("dict[str, object]", raw_resumed_obj)
                if isinstance(raw_resumed_obj, dict)
                else {}
            )
            if raw_resumed.get(SESSION_ID_KEY) != session_id:
                merged_resumed = dict(raw_resumed)
                merged_resumed[SESSION_ID_KEY] = session_id
                session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    session_id=session_id,
                    state=merged_resumed,
                )

        # 6b. Write approval resolution to session state if resuming from approval.
        # Must recreate session with merged state — in-memory dict mutation does not
        # persist in DatabaseSessionService.
        approval_item_id = resolved_params.get("approval_item_id")
        approval_resolution = resolved_params.get("approval_resolution")
        if isinstance(approval_item_id, str) and isinstance(approval_resolution, str):
            approval_key = f"{APPROVAL_RESOLUTION_PREFIX}{approval_item_id}"
            existing_state: dict[str, object] = {}
            raw_state: object = getattr(session, "state", None)
            if isinstance(raw_state, dict):
                existing_state = dict(raw_state)  # type: ignore[arg-type]
            existing_state[approval_key] = approval_resolution
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=session_id,
                state=existing_state,
            )
            logger.info(
                "Wrote approval resolution to session state: %s",
                approval_key,
            )

        # 7. Set active work session Redis key with TTL
        await redis.set(redis_key, session_id, ex=_WORK_SESSION_TTL)

        # 8. Publish session started
        await publisher.publish_lifecycle(session_id, PipelineEventType.WORKFLOW_STARTED)

        # 9. Run the ADK session (Director -> PM -> Pipeline)
        prompt_text = str(resolved_params.get("prompt", "Begin work session."))
        message = Content(parts=[Part(text=prompt_text)])

        try:
            async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
                user_id=SYSTEM_USER_ID,
                session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                new_message=message,
            ):
                translated = publisher.translate(event, session_id)
                if translated is not None:
                    await publisher.publish(translated)
            await publisher.flush_violations()
        except ContextRecreationRequired as e:
            await publisher.flush_violations()
            logger.warning(
                "Context recreation required for work session %s: %.1f%% usage (threshold %.1f%%)",
                project_id,
                e.usage_pct,
                e.threshold_pct,
            )
            from app.agents.context_recreation import recreate_context_at_taskgroup
            from app.agents.supervision import checkpoint_taskgroup

            # Resolve workflow-specific stages from the work session's workflow
            _ws_wf_name = str(resolved_params.get("workflow_name", DEFAULT_WORKFLOW_NAME))
            _ws_stages, _ws_stage_keys = _resolve_workflow_stages(_ws_wf_name)

            # Load current TaskGroup ID from project record
            _current_tg_id: uuid.UUID | None = None
            if project_uuid is not None:
                async with factory() as _db:
                    _proj = (
                        await _db.execute(select(Project).where(Project.id == project_uuid))
                    ).scalar_one_or_none()
                    if _proj is not None:
                        _current_tg_id = _proj.current_taskgroup_id

            # Tier 2 checkpoint before recreation (save state at TaskGroup boundary)
            if _current_tg_id is not None:
                old_session_obj = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=session_id
                )
                old_state: dict[str, object] = {}
                if old_session_obj is not None:
                    raw_st: object = getattr(old_session_obj, "state", None)
                    if isinstance(raw_st, dict):
                        old_state = dict(raw_st)  # type: ignore[arg-type]
                await checkpoint_taskgroup(
                    db_session_factory=factory,
                    taskgroup_execution_id=_current_tg_id,
                    state=old_state,
                    publisher=publisher,
                    workflow_id=session_id,
                )

            # Load old session for TaskGroup-aware recreation
            old_session_for_recreation = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=session_id
            )

            if old_session_for_recreation is not None:
                recreation_result = await recreate_context_at_taskgroup(
                    session_service=session_service,
                    old_session=old_session_for_recreation,
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    db_session_factory=factory,
                    current_taskgroup_id=_current_tg_id,
                    publisher=publisher,
                    workflow_id=session_id,
                    stages=_ws_stages,
                    stage_completion_keys=_ws_stage_keys,
                )
            else:
                # Fallback: no old session available (shouldn't happen in practice)
                from app.agents.context_recreation import recreate_context

                recreation_result = await recreate_context(
                    session_service=session_service,
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    old_session_id=session_id,
                    publisher=publisher,
                    memory_service=None,
                    stages=_ws_stages,
                    stage_completion_keys=_ws_stage_keys,
                )

            old_session_id = session_id
            # Update session_id so cleanup uses the fresh session
            session_id = recreation_result.new_session_id

            # Re-register ToolExecutionContext with the new session_id
            unregister_tool_context(old_session_id)
            register_tool_context(session_id, tool_exec_ctx)

            logger.info(
                "Context recreation completed for %s: new_session=%s, remaining=%d stages",
                project_id,
                recreation_result.new_session_id,
                len(recreation_result.remaining_stages),
            )

        # 9b. Execute autonomous stage loop if project has a UUID and manifest has stages
        if project_uuid is not None and manifest.stages:
            # Create a Workflow record to anchor StageExecution/ValidatorResult
            async with factory() as db_session:
                wf_record = Workflow(
                    workflow_type=workflow_name,
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    params={"project_id": project_id, "workflow_name": workflow_name},
                )
                db_session.add(wf_record)
                await db_session.commit()
                await db_session.refresh(wf_record)
                workflow_uuid = wf_record.id

            stage_result = await _execute_stage_loop(
                project_id=project_uuid,
                workflow_id=workflow_uuid,
                manifest=manifest,
                db_session_factory=factory,
                publisher=publisher,
                cost_ceiling=cost_ceiling,
                runner=runner,
                session_id=session_id,
                adk_session_id=session_id,
                redis=redis,
                retry_limit=deliverable_retry_limit,
            )
            logger.info(
                "Stage loop completed for project %s: %s",
                project_id,
                stage_result,
            )

        # 10. Clean up Redis key and publish completion
        await redis.delete(redis_key)
        await publisher.publish_lifecycle(session_id, PipelineEventType.WORKFLOW_COMPLETED)

        logger.info("Work session completed", extra={"project_id": project_id})
        return {"status": "completed", "project_id": project_id}

    except Exception as exc:
        logger.error(
            "Work session failed",
            extra={"project_id": project_id},
            exc_info=True,
        )

        # Clean up Redis key on failure
        try:
            await redis.delete(redis_key)
        except Exception:
            logger.error("Failed to clean up work session Redis key", exc_info=True)

        # Publish failure event
        try:
            await publisher.publish_lifecycle(
                session_id,
                PipelineEventType.WORKFLOW_FAILED,
                metadata={"error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish WORKFLOW_FAILED event", exc_info=True)

        # Create CEO queue item for failure escalation
        try:
            async with factory() as db_session:
                # Attempt to parse project_id as UUID for traceability
                try:
                    source_pid = uuid.UUID(project_id)
                except ValueError:
                    source_pid = None
                ceo_item = CeoQueueItem(
                    type=CeoItemType.ESCALATION,
                    priority=EscalationPriority.HIGH,
                    title=f"Work session failed: {project_id}",
                    source_project_id=source_pid,
                    source_agent="director",
                    metadata_={"error": str(exc), "project_id": project_id},
                    session_id=session_id,
                )
                db_session.add(ceo_item)
                await db_session.commit()
        except Exception:
            logger.error("Failed to create CEO queue item", exc_info=True)

        raise
    finally:
        unregister_tool_context(session_id)
