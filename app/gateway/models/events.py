"""Pipeline event models — ADK-agnostic event payload for SSE and webhooks."""

from datetime import datetime

from pydantic import Field

from app.models.base import BaseModel
from app.models.enums import PipelineEventType


class PipelineEvent(BaseModel):
    """Gateway-native event emitted during pipeline execution."""

    event_type: PipelineEventType
    workflow_id: str
    timestamp: datetime
    agent_name: str | None = None
    content: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
