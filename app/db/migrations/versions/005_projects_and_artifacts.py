"""Add projects table, artifacts table, and Phase 8a column extensions.

Revision ID: 005
Revises: 004
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

_project_status_values = ("SHAPING", "ACTIVE", "PAUSED", "SUSPENDED", "COMPLETED", "ABORTED")

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create projects/artifacts tables and extend existing tables for Phase 8a."""
    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("workflow_type", sa.String(length=100), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*_project_status_values, native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("current_stage", sa.String(length=255), nullable=True),
        sa.Column("current_taskgroup_id", sa.Uuid(), nullable=True),
        sa.Column("accumulated_cost", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    # Deferred FK: current_taskgroup_id -> taskgroup_executions.id
    op.create_foreign_key(
        "fk_projects_current_taskgroup",
        "projects",
        "taskgroup_executions",
        ["current_taskgroup_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- artifacts ---
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_entity_id", "artifacts", ["entity_id"])

    # --- Add columns to deliverables ---
    op.add_column("deliverables", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column(
        "deliverables",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("deliverables", sa.Column("execution_order", sa.Integer(), nullable=True))
    op.create_index("ix_deliverables_project_id", "deliverables", ["project_id"])
    op.create_foreign_key(
        "fk_deliverables_project", "deliverables", "projects", ["project_id"], ["id"]
    )

    # --- Add columns to stage_executions ---
    op.add_column("stage_executions", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_index("ix_stage_executions_project_id", "stage_executions", ["project_id"])
    op.create_foreign_key(
        "fk_stage_executions_project", "stage_executions", "projects", ["project_id"], ["id"]
    )

    # --- Add columns to taskgroup_executions ---
    op.add_column("taskgroup_executions", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.add_column("taskgroup_executions", sa.Column("checkpoint_data", JSONB(), nullable=True))
    op.add_column("taskgroup_executions", sa.Column("completion_report", JSONB(), nullable=True))
    op.create_index("ix_taskgroup_executions_project_id", "taskgroup_executions", ["project_id"])
    op.create_foreign_key(
        "fk_taskgroup_executions_project",
        "taskgroup_executions",
        "projects",
        ["project_id"],
        ["id"],
    )

    # --- Add columns to project_configs ---
    op.add_column("project_configs", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_index("ix_project_configs_project_id", "project_configs", ["project_id"])
    op.create_foreign_key(
        "fk_project_configs_project", "project_configs", "projects", ["project_id"], ["id"]
    )

    # --- Add resolution to director_queue ---
    op.add_column("director_queue", sa.Column("resolution", sa.Text(), nullable=True))

    # --- Add FK constraints on existing source_project_id columns ---
    op.execute("UPDATE ceo_queue SET source_project_id = NULL WHERE source_project_id IS NOT NULL")
    op.execute(
        "UPDATE director_queue SET source_project_id = NULL WHERE source_project_id IS NOT NULL"
    )
    op.create_foreign_key(
        "fk_ceo_queue_project",
        "ceo_queue",
        "projects",
        ["source_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_director_queue_project",
        "director_queue",
        "projects",
        ["source_project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Reverse all Phase 8a schema changes."""
    # Drop FK constraints on source_project_id
    op.drop_constraint("fk_director_queue_project", "director_queue", type_="foreignkey")
    op.drop_constraint("fk_ceo_queue_project", "ceo_queue", type_="foreignkey")

    # Drop resolution from director_queue
    op.drop_column("director_queue", "resolution")

    # Drop project_id from project_configs
    op.drop_constraint("fk_project_configs_project", "project_configs", type_="foreignkey")
    op.drop_index("ix_project_configs_project_id", table_name="project_configs")
    op.drop_column("project_configs", "project_id")

    # Drop columns from taskgroup_executions
    op.drop_constraint(
        "fk_taskgroup_executions_project", "taskgroup_executions", type_="foreignkey"
    )
    op.drop_index("ix_taskgroup_executions_project_id", table_name="taskgroup_executions")
    op.drop_column("taskgroup_executions", "completion_report")
    op.drop_column("taskgroup_executions", "checkpoint_data")
    op.drop_column("taskgroup_executions", "project_id")

    # Drop project_id from stage_executions
    op.drop_constraint("fk_stage_executions_project", "stage_executions", type_="foreignkey")
    op.drop_index("ix_stage_executions_project_id", table_name="stage_executions")
    op.drop_column("stage_executions", "project_id")

    # Drop columns from deliverables
    op.drop_constraint("fk_deliverables_project", "deliverables", type_="foreignkey")
    op.drop_index("ix_deliverables_project_id", table_name="deliverables")
    op.drop_column("deliverables", "execution_order")
    op.drop_column("deliverables", "retry_count")
    op.drop_column("deliverables", "project_id")

    # Drop tables
    op.drop_index("ix_artifacts_entity_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_constraint("fk_projects_current_taskgroup", "projects", type_="foreignkey")
    op.drop_table("projects")
