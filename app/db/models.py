"""SQLAlchemy ORM models for AutoBuilder."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.enums import DeliverableStatus, SpecificationStatus, WorkflowStatus


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
