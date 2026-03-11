"""CEO queue API contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.models.base import BaseModel
from app.models.enums import (
    CeoItemType,
    CeoQueueAction,
    CeoQueueStatus,
    EscalationPriority,
)


class CeoQueueItemResponse(BaseModel):
    """CEO queue item returned from API."""

    id: UUID
    type: CeoItemType
    priority: EscalationPriority
    status: CeoQueueStatus
    title: str
    source_project_id: UUID | None
    source_agent: str | None
    metadata: dict[str, object]
    session_id: str | None
    resolution: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime
    updated_at: datetime


class ResolveCeoQueueItemRequest(BaseModel):
    """Request to resolve or dismiss a CEO queue item."""

    action: CeoQueueAction = Field(description="RESOLVE or DISMISS")
    resolution: str | None = Field(
        default=None,
        description="Resolution text (required for RESOLVE, ignored for DISMISS)",
    )
    resolver: str = Field(description="Resolver identity")

    @model_validator(mode="after")
    def _resolution_required_for_resolve(self) -> "ResolveCeoQueueItemRequest":
        if self.action == CeoQueueAction.RESOLVE and not self.resolution:
            msg = "resolution is required when action is RESOLVE"
            raise ValueError(msg)
        return self
