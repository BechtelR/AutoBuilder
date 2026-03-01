"""SQLAlchemy ORM models for AutoBuilder."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.enums import (
    ChatMessageRole,
    ChatStatus,
    ChatType,
    DeliverableStatus,
    SpecificationStatus,
    WorkflowStatus,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    """Mixin providing id (UUID PK) and UTC timezone-aware timestamp columns."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Specification(TimestampMixin, Base):
    """A specification document that drives workflow execution."""

    __tablename__ = "specifications"

    name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[SpecificationStatus] = mapped_column(
        SqlEnum(SpecificationStatus, native_enum=False),
        default=SpecificationStatus.PENDING,
    )

    workflows: Mapped[list["Workflow"]] = relationship(back_populates="specification", lazy="raise")


class Workflow(TimestampMixin, Base):
    """A workflow execution triggered from a specification."""

    __tablename__ = "workflows"

    specification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("specifications.id"), nullable=True, default=None, index=True
    )
    workflow_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[WorkflowStatus] = mapped_column(
        SqlEnum(WorkflowStatus, native_enum=False),
        default=WorkflowStatus.PENDING,
    )
    params: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    specification: Mapped[Specification | None] = relationship(
        back_populates="workflows", lazy="raise"
    )
    deliverables: Mapped[list["Deliverable"]] = relationship(
        back_populates="workflow", lazy="raise"
    )


class Deliverable(TimestampMixin, Base):
    """A deliverable produced by a workflow."""

    __tablename__ = "deliverables"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[DeliverableStatus] = mapped_column(
        SqlEnum(DeliverableStatus, native_enum=False),
        default=DeliverableStatus.PENDING,
    )
    depends_on: Mapped[list[str]] = mapped_column(JSONB, default=list)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True, default=None)

    workflow: Mapped[Workflow] = relationship(back_populates="deliverables", lazy="raise")


class Chat(TimestampMixin, Base):
    """A chat session (Director conversation or project-scoped)."""

    __tablename__ = "chats"

    session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[ChatType] = mapped_column(
        SqlEnum(ChatType, native_enum=False),
        default=ChatType.DIRECTOR,
    )
    status: Mapped[ChatStatus] = mapped_column(
        SqlEnum(ChatStatus, native_enum=False),
        default=ChatStatus.ACTIVE,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    project_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, default=None, index=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="chat", lazy="raise", order_by="ChatMessage.created_at"
    )


class ChatMessage(TimestampMixin, Base):
    """A single message within a chat session."""

    __tablename__ = "chat_messages"

    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id"), index=True)
    role: Mapped[ChatMessageRole] = mapped_column(
        SqlEnum(ChatMessageRole, native_enum=False),
    )
    content: Mapped[str] = mapped_column(Text)

    chat: Mapped[Chat] = relationship(back_populates="messages", lazy="raise")
