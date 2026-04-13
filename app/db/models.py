"""SQLAlchemy ORM models for AutoBuilder."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    ChatMessageRole,
    ChatStatus,
    ChatType,
    DeliverableStatus,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
    ProjectStatus,
    SpecificationStatus,
    StageStatus,
    TaskStatus,
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
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, default=None, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[DeliverableStatus] = mapped_column(
        SqlEnum(DeliverableStatus, native_enum=False),
        default=DeliverableStatus.PENDING,
    )
    depends_on: Mapped[list[str]] = mapped_column(JSONB, default=list)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True, default=None)
    retry_count: Mapped[int] = mapped_column(default=0)
    execution_order: Mapped[int | None] = mapped_column(nullable=True, default=None)

    workflow: Mapped[Workflow] = relationship(back_populates="deliverables", lazy="raise")


class Project(TimestampMixin, Base):
    """A first-order project entity tracking autonomous execution lifecycle."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    workflow_type: Mapped[str] = mapped_column(String(100))
    brief: Mapped[str] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        SqlEnum(ProjectStatus, native_enum=False),
        default=ProjectStatus.SHAPING,
    )
    current_stage: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    current_taskgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "taskgroup_executions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_projects_current_taskgroup",
        ),
        nullable=True,
        default=None,
    )
    accumulated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


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


class CeoQueueItem(TimestampMixin, Base):
    """An item in the CEO escalation queue."""

    __tablename__ = "ceo_queue"

    type: Mapped[CeoItemType] = mapped_column(
        SqlEnum(CeoItemType, native_enum=False),
    )
    priority: Mapped[EscalationPriority] = mapped_column(
        SqlEnum(EscalationPriority, native_enum=False),
        default=EscalationPriority.NORMAL,
    )
    status: Mapped[CeoQueueStatus] = mapped_column(
        SqlEnum(CeoQueueStatus, native_enum=False),
        default=CeoQueueStatus.PENDING,
    )
    title: Mapped[str] = mapped_column(String(255))
    source_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, default=None, index=True
    )
    source_agent: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, server_default="{}", default=dict
    )
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class DirectorQueueItem(TimestampMixin, Base):
    """An item in the Director escalation queue."""

    __tablename__ = "director_queue"

    type: Mapped[EscalationRequestType] = mapped_column(
        SqlEnum(EscalationRequestType, native_enum=False),
    )
    priority: Mapped[EscalationPriority] = mapped_column(
        SqlEnum(EscalationPriority, native_enum=False),
        default=EscalationPriority.NORMAL,
    )
    status: Mapped[DirectorQueueStatus] = mapped_column(
        SqlEnum(DirectorQueueStatus, native_enum=False),
        default=DirectorQueueStatus.PENDING,
    )
    title: Mapped[str] = mapped_column(String(255))
    source_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, default=None, index=True
    )
    source_agent: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    context: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, server_default="{}", default=dict
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class ProjectConfig(TimestampMixin, Base):
    """Per-project configuration stored in the database."""

    __tablename__ = "project_configs"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, default=None, index=True
    )
    project_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    config: Mapped[dict[str, object]] = mapped_column(JSONB, server_default="{}", default=dict)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), default=True)


class StageExecution(TimestampMixin, Base):
    """Tracks stage lifecycle within a workflow execution."""

    __tablename__ = "stage_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, default=None, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(255), index=True)
    stage_index: Mapped[int]
    status: Mapped[StageStatus] = mapped_column(
        SqlEnum(StageStatus, native_enum=False),
        default=StageStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completion_report: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    workflow: Mapped[Workflow] = relationship(lazy="raise")
    taskgroups: Mapped[list["TaskGroupExecution"]] = relationship(
        back_populates="stage_execution", lazy="raise"
    )
    validator_results: Mapped[list["ValidatorResult"]] = relationship(
        back_populates="stage_execution", lazy="raise"
    )


class TaskGroupExecution(TimestampMixin, Base):
    """PM TaskGroup tracking -- runtime planning units within a stage."""

    __tablename__ = "taskgroup_executions"

    stage_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stage_executions.id"), index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, default=None, index=True
    )
    taskgroup_number: Mapped[int]
    status: Mapped[StageStatus] = mapped_column(
        SqlEnum(StageStatus, native_enum=False),
        default=StageStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    deliverable_count: Mapped[int] = mapped_column(default=0)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    checkpoint_data: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )
    completion_report: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    stage_execution: Mapped[StageExecution] = relationship(
        back_populates="taskgroups", lazy="raise"
    )


class ValidatorResult(TimestampMixin, Base):
    """Validator evidence persistence."""

    __tablename__ = "validator_results"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    stage_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stage_executions.id"), nullable=True, default=None, index=True
    )
    validator_name: Mapped[str] = mapped_column(String(255), index=True)
    passed: Mapped[bool]
    evidence: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True, default=None)
    message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workflow: Mapped[Workflow] = relationship(lazy="raise")
    stage_execution: Mapped[StageExecution | None] = relationship(
        back_populates="validator_results", lazy="raise"
    )


class ProjectTask(TimestampMixin, Base):
    """Cross-session task visible to all agents in a project."""

    __tablename__ = "project_tasks"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, default=None, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(TaskStatus, native_enum=False),
        default=TaskStatus.OPEN,
    )
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)


class Artifact(TimestampMixin, Base):
    """Persistent artifact storage — polymorphic entity association."""

    __tablename__ = "artifacts"

    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column(index=True)
    path: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int]
