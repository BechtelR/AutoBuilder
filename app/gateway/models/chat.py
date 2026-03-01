"""Chat API contract models."""

import uuid
from datetime import datetime

from pydantic import Field

from app.models.base import BaseModel
from app.models.enums import ChatMessageRole, ChatStatus, ChatType


class CreateChatRequest(BaseModel):
    """Request to create a new chat session."""

    type: ChatType = ChatType.DIRECTOR
    title: str | None = None
    project_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    """Chat session summary."""

    id: str
    session_id: str
    type: ChatType
    status: ChatStatus
    title: str | None
    project_id: str | None
    created_at: datetime
    updated_at: datetime


class SendChatMessageRequest(BaseModel):
    """Request to send a message in a chat session."""

    content: str = Field(min_length=1, max_length=100_000)


class ChatMessageResponse(BaseModel):
    """A single chat message."""

    id: str
    chat_id: str
    role: ChatMessageRole
    content: str
    created_at: datetime
