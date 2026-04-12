"""Add stage_executions, taskgroup_executions, and validator_results tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

_stage_status_values = ("PENDING", "ACTIVE", "COMPLETED", "FAILED")

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workflow composition tables."""
    # --- stage_executions ---
    op.create_table(
        "stage_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("stage_name", sa.String(length=255), nullable=False),
        sa.Column("stage_index", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*_stage_status_values, native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_report", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stage_executions_workflow_id", "stage_executions", ["workflow_id"])
    op.create_index("ix_stage_executions_stage_name", "stage_executions", ["stage_name"])

    # --- taskgroup_executions ---
    op.create_table(
        "taskgroup_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stage_execution_id", sa.Uuid(), nullable=False),
        sa.Column("taskgroup_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*_stage_status_values, native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deliverable_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["stage_execution_id"], ["stage_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_taskgroup_executions_stage_execution_id",
        "taskgroup_executions",
        ["stage_execution_id"],
    )

    # --- validator_results ---
    op.create_table(
        "validator_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("stage_execution_id", sa.Uuid(), nullable=True),
        sa.Column("validator_name", sa.String(length=255), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.ForeignKeyConstraint(["stage_execution_id"], ["stage_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validator_results_workflow_id", "validator_results", ["workflow_id"])
    op.create_index(
        "ix_validator_results_stage_execution_id",
        "validator_results",
        ["stage_execution_id"],
    )
    op.create_index(
        "ix_validator_results_validator_name",
        "validator_results",
        ["validator_name"],
    )


def downgrade() -> None:
    """Drop workflow composition tables in reverse dependency order."""
    op.drop_table("validator_results")
    op.drop_table("taskgroup_executions")
    op.drop_table("stage_executions")
