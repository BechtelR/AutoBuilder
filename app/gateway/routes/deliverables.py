"""Deliverable routes — listing and detail views."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact, Deliverable, ValidatorResult
from app.gateway.deps import get_db_session
from app.gateway.models.deliverables import (
    DeliverableDetailResponse,
    DeliverableResponse,
    ValidatorResultResponse,
)
from app.lib import NotFoundError
from app.models.constants import ARTIFACT_ENTITY_DELIVERABLE
from app.models.enums import DeliverableStatus

router = APIRouter(prefix="/deliverables", tags=["deliverables"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("")
async def list_deliverables(
    db: DbSession,
    project_id: UUID | None = None,
    status: DeliverableStatus | None = None,
    stage: str | None = Query(
        default=None,
        description=(
            "Filter by project current_stage. Deliverables lack a direct stage column, "
            "so this filters via the parent project's current_stage."
        ),
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[DeliverableResponse]:
    """List deliverables with optional filters."""
    stmt = select(Deliverable).order_by(Deliverable.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(Deliverable.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Deliverable.status == status)
    # NOTE: Deliverables have no direct `stage` column. Filter through the parent
    # Project's current_stage. This means the filter returns deliverables whose
    # project is *currently* in the given stage, not deliverables that were produced
    # during that stage. A per-deliverable stage column would require a schema change.
    if stage is not None:
        from app.db.models import Project

        stmt = stmt.join(Project, Deliverable.project_id == Project.id).where(
            Project.current_stage == stage
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    deliverables = result.scalars().all()
    return [_deliverable_to_response(d) for d in deliverables]


@router.get("/{deliverable_id}")
async def get_deliverable(
    deliverable_id: UUID,
    db: DbSession,
) -> DeliverableDetailResponse:
    """Get deliverable detail with artifacts."""
    result = await db.execute(select(Deliverable).where(Deliverable.id == deliverable_id))
    deliverable = result.scalar_one_or_none()
    if deliverable is None:
        raise NotFoundError(message=f"Deliverable '{deliverable_id}' not found")

    # Load associated artifacts
    artifact_stmt = select(Artifact).where(
        Artifact.entity_type == ARTIFACT_ENTITY_DELIVERABLE,
        Artifact.entity_id == deliverable_id,
    )
    artifact_result = await db.execute(artifact_stmt)
    artifacts = artifact_result.scalars().all()

    artifact_dicts: list[dict[str, object]] = [
        {
            "id": str(a.id),
            "path": a.path,
            "content_type": a.content_type,
            "size_bytes": a.size_bytes,
            "created_at": a.created_at.isoformat(),
        }
        for a in artifacts
    ]

    # Load validator results for this deliverable's workflow.
    # NOTE: No direct FK from Deliverable to ValidatorResult. Joined via shared
    # workflow_id. Returns all validator results for the workflow, which is correct
    # for single-deliverable workflows. Multi-deliverable workflows will show all
    # results for all deliverables — a per-deliverable FK would require a migration.
    vr_stmt = (
        select(ValidatorResult)
        .where(ValidatorResult.workflow_id == deliverable.workflow_id)
        .order_by(ValidatorResult.evaluated_at.desc())
    )
    vr_result = await db.execute(vr_stmt)
    validator_rows = vr_result.scalars().all()

    validator_dtos = [
        ValidatorResultResponse(
            id=vr.id,
            validator_name=vr.validator_name,
            passed=vr.passed,
            message=vr.message,
            evidence=vr.evidence,
            evaluated_at=vr.evaluated_at,
        )
        for vr in validator_rows
    ]

    return DeliverableDetailResponse(
        id=deliverable.id,
        name=deliverable.name,
        description=deliverable.description,
        status=deliverable.status,
        project_id=deliverable.project_id,
        workflow_id=deliverable.workflow_id,
        retry_count=deliverable.retry_count,
        execution_order=deliverable.execution_order,
        depends_on=deliverable.depends_on,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at,
        result=deliverable.result,
        artifacts=artifact_dicts,
        validator_results=validator_dtos,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deliverable_to_response(deliverable: Deliverable) -> DeliverableResponse:
    """Convert a Deliverable ORM model to response."""
    return DeliverableResponse(
        id=deliverable.id,
        name=deliverable.name,
        description=deliverable.description,
        status=deliverable.status,
        project_id=deliverable.project_id,
        workflow_id=deliverable.workflow_id,
        retry_count=deliverable.retry_count,
        execution_order=deliverable.execution_order,
        depends_on=deliverable.depends_on,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at,
    )
