"""Deliverable API contract models."""

from datetime import datetime
from uuid import UUID

from app.models.base import BaseModel
from app.models.enums import DeliverableStatus


class DeliverableResponse(BaseModel):
    """Response model for a deliverable."""

    id: UUID
    name: str
    description: str | None
    status: DeliverableStatus
    project_id: UUID | None
    workflow_id: UUID
    retry_count: int
    execution_order: int | None
    depends_on: list[str]
    created_at: datetime
    updated_at: datetime


class ValidatorResultResponse(BaseModel):
    """Compact validator result returned inside deliverable detail."""

    id: UUID
    validator_name: str
    passed: bool
    message: str | None
    evidence: dict[str, object] | None
    evaluated_at: datetime


class DeliverableDetailResponse(DeliverableResponse):
    """Detailed deliverable with result, artifacts, and validator evidence."""

    result: dict[str, object] | None
    artifacts: list[dict[str, object]]
    validator_results: list[ValidatorResultResponse]
