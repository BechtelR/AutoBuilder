"""Director queue API contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import model_validator

from app.models.base import BaseModel
from app.models.enums import (
    DirectorQueueAction,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
)


class DirectorQueueItemResponse(BaseModel):
    """Response model for a Director queue item."""

    id: UUID
    type: EscalationRequestType
    priority: EscalationPriority
    status: DirectorQueueStatus
    title: str
    source_project_id: UUID | None
    source_agent: str | None
    context: str
    metadata: dict[str, object]
    resolution: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime
    updated_at: datetime


class ResolveDirectorQueueItemRequest(BaseModel):
    """Request to resolve or forward a Director queue item."""

    action: DirectorQueueAction
    resolution: str | None = None
    rationale: str | None = None

    @model_validator(mode="after")
    def _validate_action_fields(self) -> "ResolveDirectorQueueItemRequest":
        if self.action == DirectorQueueAction.RESOLVE and not self.resolution:
            msg = "resolution is required when action is RESOLVE"
            raise ValueError(msg)
        if self.action == DirectorQueueAction.FORWARD_TO_CEO and not self.rationale:
            msg = "rationale is required when action is FORWARD_TO_CEO"
            raise ValueError(msg)
        return self
