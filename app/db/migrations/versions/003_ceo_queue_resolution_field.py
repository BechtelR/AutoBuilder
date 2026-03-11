"""Add resolution text field to ceo_queue table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add resolution column to ceo_queue."""
    op.add_column("ceo_queue", sa.Column("resolution", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove resolution column from ceo_queue."""
    op.drop_column("ceo_queue", "resolution")
