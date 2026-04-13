"""Project API contract models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.base import BaseModel
from app.models.enums import ProjectStatus


class ProjectCreateRequest(BaseModel):
    """Request to create a project via Director."""

    brief: str
    workflow_type: str | None = None
    name: str | None = None


class ProjectAbortRequest(BaseModel):
    """Request to abort a project."""

    reason: str


class ProjectResponse(BaseModel):
    """Response model for a project."""

    id: UUID
    name: str
    workflow_type: str
    brief: str
    status: ProjectStatus
    current_stage: str | None
    accumulated_cost: Decimal
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class ProjectDetailResponse(ProjectResponse):
    """Detailed project response with deliverable counts."""

    deliverable_total: int
    deliverable_completed: int
    deliverable_failed: int
    deliverable_in_progress: int
    deliverable_pending: int
