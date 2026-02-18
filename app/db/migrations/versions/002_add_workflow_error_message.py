"""add_workflow_error_message

Revision ID: 002
Revises: 001
Create Date: 2026-02-17 08:05:18.981895

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflows", "error_message")
