"""Workflow API contract models."""

from pydantic import Field

from app.models.base import BaseModel
from app.models.enums import WorkflowStatus


class WorkflowRunRequest(BaseModel):
    """Request to execute a workflow."""

    workflow_type: str = Field(min_length=1, max_length=100)
    params: dict[str, object] | None = None


class WorkflowRunResponse(BaseModel):
    """Response after enqueueing a workflow execution."""

    workflow_id: str
    status: WorkflowStatus
