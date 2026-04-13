"""Lifecycle operations -- pause, resume, abort for projects and Director.

All operations are ARQ tasks enqueued by gateway routes. They execute
asynchronously and publish lifecycle events.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db.models import Deliverable, Project
from app.events.publisher import EventPublisher
from app.models.enums import DeliverableStatus, PipelineEventType, ProjectStatus

if TYPE_CHECKING:
    from arq.connections import ArqRedis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# Redis key for Director pause flag
DIRECTOR_PAUSED_KEY = "director:paused"


async def pause_project(
    ctx: dict[str, object], *, project_id: str, reason: str | None = None
) -> dict[str, str]:
    """Pause a single project -- finish current deliverable, checkpoint, stop.

    Sets project status to PAUSED and sets a Redis key that the PM batch loop
    checks between deliverables.
    """
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    pid = uuid.UUID(project_id)
    async with db_session_factory() as db:
        project = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not project:
            return {"status": "error", "message": f"Project {project_id} not found"}
        if project.status != ProjectStatus.ACTIVE:
            return {
                "status": "error",
                "message": f"Cannot pause: status is {project.status.value}",
            }

        project.status = ProjectStatus.PAUSED
        wf_type = project.workflow_type
        await db.commit()

    # Set Redis flag for PM to observe between deliverables
    await redis.set(f"project:pause_requested:{project_id}", reason or "user_initiated", ex=86400)

    # Publish lifecycle event (D14: PROJECT_STATUS_CHANGED)
    publisher = EventPublisher(redis)
    await publisher.publish_project_status_changed(
        workflow_id=project_id,
        project_id=project_id,
        old_status=ProjectStatus.ACTIVE,
        new_status=ProjectStatus.PAUSED,
        actor="user",
        scope="project",
        workflow_type=wf_type,
    )

    logger.info("Project %s paused: %s", project_id, reason or "no reason")
    return {"status": "ok", "project_id": project_id, "new_status": "PAUSED"}


async def resume_project(
    ctx: dict[str, object], *, project_id: str, resolution: str | None = None
) -> dict[str, str]:
    """Resume a paused project -- load state, enqueue work session from checkpoint.

    Args:
        ctx: Worker context with db_session_factory and redis.
        project_id: UUID string of the project to resume.
        resolution: Optional resolution context from CEO escalation.
    """
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    pid = uuid.UUID(project_id)
    async with db_session_factory() as db:
        project = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not project:
            return {"status": "error", "message": f"Project {project_id} not found"}
        if project.status != ProjectStatus.PAUSED:
            return {
                "status": "error",
                "message": f"Cannot resume: status is {project.status.value}",
            }

        project.status = ProjectStatus.ACTIVE
        wf_type = project.workflow_type
        await db.commit()

    # Clear pause flag
    await redis.delete(f"project:pause_requested:{project_id}")

    # Enqueue work session to resume from checkpoint, with resolution context if provided
    if resolution:
        await redis.enqueue_job(
            "run_work_session",
            project_id=project_id,
            params={"resume_resolution": resolution},
        )
    else:
        await redis.enqueue_job("run_work_session", project_id=project_id)

    # Publish lifecycle event (D14: PROJECT_STATUS_CHANGED)
    publisher = EventPublisher(redis)
    await publisher.publish_project_status_changed(
        workflow_id=project_id,
        project_id=project_id,
        old_status=ProjectStatus.PAUSED,
        new_status=ProjectStatus.ACTIVE,
        actor="user",
        scope="project",
        workflow_type=wf_type,
    )

    logger.info("Project %s resumed", project_id)
    return {"status": "ok", "project_id": project_id, "new_status": "ACTIVE"}


async def abort_project(ctx: dict[str, object], *, project_id: str, reason: str) -> dict[str, str]:
    """Abort a project -- terminate, preserve completed work, record reason."""
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    pid = uuid.UUID(project_id)
    old_status: ProjectStatus = ProjectStatus.ACTIVE  # fallback; overwritten below
    async with db_session_factory() as db:
        project = (await db.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
        if not project:
            return {"status": "error", "message": f"Project {project_id} not found"}

        old_status = project.status
        terminal_statuses = {ProjectStatus.COMPLETED, ProjectStatus.ABORTED}
        if old_status in terminal_statuses:
            return {
                "status": "error",
                "message": f"Cannot abort: status is {old_status.value}",
            }

        project.status = ProjectStatus.ABORTED
        project.error_message = reason
        project.completed_at = datetime.now(UTC)
        wf_type = project.workflow_type
        await db.commit()

    # Publish lifecycle event (D14: PROJECT_STATUS_CHANGED)
    publisher = EventPublisher(redis)
    await publisher.publish_project_status_changed(
        workflow_id=project_id,
        project_id=project_id,
        old_status=old_status,
        new_status=ProjectStatus.ABORTED,
        actor="user",
        scope="project",
        workflow_type=wf_type,
    )

    logger.info("Project %s aborted: %s", project_id, reason)
    return {"status": "ok", "project_id": project_id, "new_status": "ABORTED"}


async def pause_director(ctx: dict[str, object], *, reason: str | None = None) -> dict[str, object]:
    """Pause Director -- stop backlog processing, cascade to active projects.

    Sets Redis pause flags for each active project. Does NOT directly change
    project status -- the PM batch loop checks the flag and gracefully pauses
    at the next checkpoint (between batches).
    """
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    # Set Director paused flag
    await redis.set(DIRECTOR_PAUSED_KEY, reason or "user_initiated", ex=86400)

    # Set pause flags for each active project -- PM observes these at next checkpoint
    async with db_session_factory() as db:
        stmt = select(Project).where(Project.status == ProjectStatus.ACTIVE)
        projects = list((await db.execute(stmt)).scalars().all())
        flagged_ids = [str(p.id) for p in projects]

    for pid in flagged_ids:
        await redis.set(f"project:pause_requested:{pid}", "director_pause", ex=86400)

    # Publish Director-level lifecycle event (flag-only -- project DB status unchanged).
    # Per-project status change events are NOT published here because DB status is
    # still ACTIVE. The PM batch loop will publish PROJECT_STATUS_CHANGED when it
    # observes the flag and transitions to PAUSED at the next checkpoint.
    publisher = EventPublisher(redis)
    await publisher.publish_lifecycle(
        workflow_id="director",
        event_type=PipelineEventType.STATE_UPDATED,
        metadata={
            "lifecycle_action": "DIRECTOR_PAUSED",
            "reason": reason,
            "flagged_projects": flagged_ids,
            "actor": "director",
            "scope": "system",
        },
    )

    logger.info("Director paused. Flagged %d active projects for graceful pause", len(flagged_ids))
    return {"status": "ok", "paused_projects": flagged_ids}


async def resume_director(ctx: dict[str, object]) -> dict[str, object]:
    """Resume Director -- clear pause flag, resume only Director-paused projects.

    Only resumes projects whose Redis pause flag is ``director_pause``.
    Projects individually paused by users retain their PAUSED status.
    """
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    # Clear Director paused flag
    await redis.delete(DIRECTOR_PAUSED_KEY)

    # Only resume projects that were paused by the Director cascade (flag == "director_pause"),
    # not projects paused individually by users.
    async with db_session_factory() as db:
        stmt = (
            select(Project)
            .where(Project.status == ProjectStatus.PAUSED)
            .order_by(Project.created_at)
        )
        projects = list((await db.execute(stmt)).scalars().all())

        resumed_ids: list[str] = []
        wf_types: dict[str, str] = {}
        for project in projects:
            pid = str(project.id)
            flag = await redis.get(f"project:pause_requested:{pid}")
            if flag == b"director_pause":
                project.status = ProjectStatus.ACTIVE
                resumed_ids.append(pid)
                wf_types[pid] = project.workflow_type
        await db.commit()

    # Clear pause flags for resumed projects and enqueue work sessions
    for pid in resumed_ids:
        await redis.delete(f"project:pause_requested:{pid}")
        await redis.enqueue_job("run_work_session", project_id=pid)

    # Also clear stale director_pause flags for ACTIVE projects that haven't
    # yet observed the flag. Without this, the PM would pause these projects
    # at their next checkpoint even though the Director has already resumed.
    async with db_session_factory() as db:
        active_stmt = select(Project).where(Project.status == ProjectStatus.ACTIVE)
        active_projects = list((await db.execute(active_stmt)).scalars().all())
    for p in active_projects:
        pid = str(p.id)
        flag = await redis.get(f"project:pause_requested:{pid}")
        if flag == b"director_pause":
            await redis.delete(f"project:pause_requested:{pid}")

    # Publish per-project lifecycle events
    publisher = EventPublisher(redis)
    for pid in resumed_ids:
        await publisher.publish_project_status_changed(
            workflow_id=pid,
            project_id=pid,
            old_status=ProjectStatus.PAUSED,
            new_status=ProjectStatus.ACTIVE,
            actor="director",
            scope="system",
            workflow_type=wf_types.get(pid),
        )

    # Publish Director-level lifecycle event
    await publisher.publish_lifecycle(
        workflow_id="director",
        event_type=PipelineEventType.STATE_UPDATED,
        metadata={
            "lifecycle_action": "DIRECTOR_RESUMED",
            "resumed_projects": resumed_ids,
            "actor": "director",
            "scope": "system",
        },
    )

    logger.info("Director resumed. Resumed %d projects", len(resumed_ids))
    return {"status": "ok", "resumed_projects": resumed_ids}


async def pause_all_projects(
    ctx: dict[str, object], *, reason: str | None = None
) -> dict[str, object]:
    """System-wide pause -- pause every active project individually."""
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    async with db_session_factory() as db:
        stmt = select(Project).where(Project.status == ProjectStatus.ACTIVE)
        projects = list((await db.execute(stmt)).scalars().all())
        for project in projects:
            project.status = ProjectStatus.PAUSED
        await db.commit()
        paused_ids = [str(p.id) for p in projects]
        wf_types = {str(p.id): p.workflow_type for p in projects}

    for pid in paused_ids:
        await redis.set(f"project:pause_requested:{pid}", reason or "system_pause", ex=86400)

    # Publish per-project lifecycle events
    publisher = EventPublisher(redis)
    for pid in paused_ids:
        await publisher.publish_project_status_changed(
            workflow_id=pid,
            project_id=pid,
            old_status=ProjectStatus.ACTIVE,
            new_status=ProjectStatus.PAUSED,
            actor="system",
            scope="system",
            workflow_type=wf_types.get(pid),
        )

    # Publish system-level lifecycle event
    await publisher.publish_lifecycle(
        workflow_id="system",
        event_type=PipelineEventType.STATE_UPDATED,
        metadata={
            "lifecycle_action": "SYSTEM_PAUSE",
            "reason": reason,
            "paused_projects": paused_ids,
            "actor": "system",
            "scope": "system",
        },
    )

    logger.info("System-wide pause. Paused %d projects", len(paused_ids))
    return {"status": "ok", "paused_projects": paused_ids}


async def resume_all_projects(ctx: dict[str, object]) -> dict[str, object]:
    """System-wide resume -- resume each paused project individually."""
    db_session_factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    async with db_session_factory() as db:
        stmt = select(Project).where(Project.status == ProjectStatus.PAUSED)
        projects = list((await db.execute(stmt)).scalars().all())
        for project in projects:
            project.status = ProjectStatus.ACTIVE
        await db.commit()
        resumed_ids = [str(p.id) for p in projects]
        wf_types = {str(p.id): p.workflow_type for p in projects}

    for pid in resumed_ids:
        await redis.delete(f"project:pause_requested:{pid}")
        await redis.enqueue_job("run_work_session", project_id=pid)

    # Publish per-project lifecycle events
    publisher = EventPublisher(redis)
    for pid in resumed_ids:
        await publisher.publish_project_status_changed(
            workflow_id=pid,
            project_id=pid,
            old_status=ProjectStatus.PAUSED,
            new_status=ProjectStatus.ACTIVE,
            actor="system",
            scope="system",
            workflow_type=wf_types.get(pid),
        )

    # Publish system-level lifecycle event
    await publisher.publish_lifecycle(
        workflow_id="system",
        event_type=PipelineEventType.STATE_UPDATED,
        metadata={
            "lifecycle_action": "SYSTEM_RESUME",
            "resumed_projects": resumed_ids,
            "actor": "system",
            "scope": "system",
        },
    )

    logger.info("System-wide resume. Resumed %d projects", len(resumed_ids))
    return {"status": "ok", "resumed_projects": resumed_ids}


async def apply_resolution_to_project(
    project_id: uuid.UUID,
    resolution: str,
    db_session_factory: async_sessionmaker[AsyncSession],
    redis: ArqRedis,
) -> dict[str, str | list[str]]:
    """Apply a CEO escalation resolution back to the project.

    - If project is SUSPENDED: transition to ACTIVE, clear error
    - Failed deliverables that were escalated: mark for retry (reset to PENDING)
    - Enqueue a work session to resume execution

    Args:
        project_id: UUID of the project.
        resolution: CEO resolution text.
        db_session_factory: Async session factory for DB access.
        redis: ArqRedis for job enqueue.

    Returns:
        Dict with status and list of retried deliverable IDs.
    """
    was_suspended = False
    async with db_session_factory() as db:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if not project:
            return {"status": "error", "message": "Project not found"}

        wf_type = project.workflow_type
        if project.status == ProjectStatus.SUSPENDED:
            was_suspended = True
            project.status = ProjectStatus.ACTIVE
            project.error_message = None

        # Mark failed deliverables for retry (reset status to PENDING)
        failed_deliverables = list(
            (
                await db.execute(
                    select(Deliverable).where(
                        Deliverable.project_id == project_id,
                        Deliverable.status == DeliverableStatus.FAILED,
                    )
                )
            )
            .scalars()
            .all()
        )

        retried_ids: list[str] = []
        for d in failed_deliverables:
            d.status = DeliverableStatus.PENDING
            d.retry_count = 0
            retried_ids.append(str(d.id))
        await db.commit()

    # Publish lifecycle event for SUSPENDED->ACTIVE transition
    if was_suspended:
        publisher = EventPublisher(redis)
        await publisher.publish_project_status_changed(
            workflow_id=str(project_id),
            project_id=str(project_id),
            old_status=ProjectStatus.SUSPENDED,
            new_status=ProjectStatus.ACTIVE,
            actor="ceo",
            scope="project",
            workflow_type=wf_type,
        )

    # Enqueue work session to resume
    await redis.enqueue_job("run_work_session", project_id=str(project_id))

    logger.info(
        "Applied resolution to project %s: %d deliverables retried",
        str(project_id)[:8],
        len(retried_ids),
    )
    return {"status": "ok", "retried_deliverables": retried_ids}
