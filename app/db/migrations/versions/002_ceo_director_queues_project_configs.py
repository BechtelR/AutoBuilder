"""CEO queue, Director queue, and project configs tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ceo_queue, director_queue, and project_configs tables."""
    # --- ceo_queue ---
    op.create_table(
        "ceo_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_project_id", sa.Uuid(), nullable=True),
        sa.Column("source_agent", sa.String(length=255), nullable=True),
        sa.Column("metadata", JSONB(), server_default="{}", nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ceo_queue_source_project_id", "ceo_queue", ["source_project_id"])

    # --- director_queue ---
    op.create_table(
        "director_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_project_id", sa.Uuid(), nullable=True),
        sa.Column("source_agent", sa.String(length=255), nullable=True),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB(), server_default="{}", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_director_queue_source_project_id", "director_queue", ["source_project_id"])

    # --- project_configs ---
    op.create_table(
        "project_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("config", JSONB(), server_default="{}", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_configs_project_name", "project_configs", ["project_name"], unique=True
    )


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_table("project_configs")
    op.drop_table("director_queue")
    op.drop_table("ceo_queue")
