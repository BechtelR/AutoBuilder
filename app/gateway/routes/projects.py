"""Project routes — creation, listing, detail, and pause/resume lifecycle."""

from typing import Annotated
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Deliverable, Project
from app.gateway.deps import get_arq_pool, get_db_session
from app.gateway.models.projects import (
    ProjectAbortRequest,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
)
from app.lib import ConflictError, NotFoundError
from app.models.enums import DeliverableStatus, ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


@router.post("", status_code=202)
async def create_project(
    request: ProjectCreateRequest,
    arq: ArqPool,
) -> dict[str, str]:
    """Enqueue a Director turn to create a project from a brief."""
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "run_director_turn",
        brief=request.brief,
        workflow_type=request.workflow_type,
        name=request.name,
        _job_id=None,
    )
    return {"message": "Project creation enqueued"}


@router.get("")
async def list_projects(
    db: DbSession,
    status: ProjectStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ProjectResponse]:
    """List projects with optional status filter."""
    stmt = select(Project).order_by(Project.created_at.desc())
    if status is not None:
        stmt = stmt.where(Project.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return [_project_to_response(p) for p in projects]


@router.get("/{project_id}")
async def get_project(
    project_id: UUID,
    db: DbSession,
) -> ProjectDetailResponse:
    """Get project detail with deliverable counts."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=f"Project '{project_id}' not found")

    # Count deliverables by status
    count_stmt = select(
        func.count().label("total"),
        func.count().filter(Deliverable.status == DeliverableStatus.COMPLETED).label("completed"),
        func.count().filter(Deliverable.status == DeliverableStatus.FAILED).label("failed"),
        func.count()
        .filter(Deliverable.status == DeliverableStatus.IN_PROGRESS)
        .label("in_progress"),
        func.count().filter(Deliverable.status == DeliverableStatus.PENDING).label("pending"),
    ).where(Deliverable.project_id == project_id)

    counts = (await db.execute(count_stmt)).one()

    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        workflow_type=project.workflow_type,
        brief=project.brief,
        status=project.status,
        current_stage=project.current_stage,
        accumulated_cost=project.accumulated_cost,
        created_at=project.created_at,
        updated_at=project.updated_at,
        started_at=project.started_at,
        completed_at=project.completed_at,
        error_message=project.error_message,
        deliverable_total=counts.total,
        deliverable_completed=counts.completed,
        deliverable_failed=counts.failed,
        deliverable_in_progress=counts.in_progress,
        deliverable_pending=counts.pending,
    )


@router.post("/{project_id}/abort", status_code=202)
async def abort_project(
    project_id: UUID,
    request: ProjectAbortRequest,
    db: DbSession,
    arq: ArqPool,
) -> dict[str, str]:
    """Abort a project. Returns 202 -- actual abort happens in worker."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=f"Project '{project_id}' not found")
    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.ABORTED):
        raise ConflictError(
            message=f"Cannot abort project in {project.status.value} state",
        )
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "abort_project",
        project_id=str(project_id),
        reason=request.reason,
    )
    return {"status": "accepted", "message": f"Abort requested for project {project_id}"}


@router.post("/pause", status_code=202)
async def pause_all(
    arq: ArqPool,
    reason: str | None = None,
) -> dict[str, str]:
    """System-wide pause -- enqueues pause_all_projects ARQ job."""
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "pause_all_projects",
        reason=reason,
    )
    return {"status": "accepted", "message": "System-wide pause requested"}


@router.post("/resume", status_code=202)
async def resume_all(
    arq: ArqPool,
) -> dict[str, str]:
    """System-wide resume -- enqueues resume_all_projects ARQ job."""
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "resume_all_projects",
    )
    return {"status": "accepted", "message": "System-wide resume requested"}


@router.post("/{project_id}/pause", status_code=202)
async def pause_project(
    project_id: UUID,
    db: DbSession,
    arq: ArqPool,
    reason: str | None = None,
) -> dict[str, str]:
    """Pause a project. Returns 202 — actual pause happens in worker."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=f"Project '{project_id}' not found")
    if project.status != ProjectStatus.ACTIVE:
        raise ConflictError(message=f"Cannot pause project in {project.status.value} state")
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "pause_project",
        project_id=str(project_id),
        reason=reason,
    )
    return {"status": "accepted", "message": f"Pause requested for project {project_id}"}


@router.post("/{project_id}/resume", status_code=202)
async def resume_project(
    project_id: UUID,
    db: DbSession,
    arq: ArqPool,
) -> dict[str, str]:
    """Resume a paused project. Returns 202 — actual resume happens in worker."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=f"Project '{project_id}' not found")
    if project.status != ProjectStatus.PAUSED:
        raise ConflictError(message=f"Cannot resume project in {project.status.value} state")
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "resume_project",
        project_id=str(project_id),
    )
    return {"status": "accepted", "message": f"Resume requested for project {project_id}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_to_response(project: Project) -> ProjectResponse:
    """Convert a Project ORM model to response."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        workflow_type=project.workflow_type,
        brief=project.brief,
        status=project.status,
        current_stage=project.current_stage,
        accumulated_cost=project.accumulated_cost,
        created_at=project.created_at,
        updated_at=project.updated_at,
        started_at=project.started_at,
        completed_at=project.completed_at,
        error_message=project.error_message,
    )
