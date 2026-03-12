---
name: database-migration
description: This skill provides patterns for creating Alembic database migrations in AutoBuilder, including naming conventions, revision IDs, and safe migration practices.
triggers:
  - deliverable_type: migration
  - file_pattern: "*/migrations/*.py"
tags: [database, migration, alembic]
applies_to: [coder]
priority: 10
---

# Database Migration Patterns

This skill covers the conventions for creating Alembic migrations in AutoBuilder. Migrations are versioned, sequential, and must be safe to run forward and roll back.

## Naming Convention

All migrations use sequential numeric IDs — never Alembic's default hash-based IDs.

```
NNN_description_in_snake_case.py
```

Examples:
- `001_initial_schema.py`
- `002_add_deliverable_status.py`
- `015_add_project_archived_at.py`

Always pass `--rev-id NNN` when creating a migration:

```bash
uv run alembic revision --autogenerate -m "add_deliverable_status" --rev-id 002
```

Check the current highest ID before creating:

```bash
uv run alembic history --verbose | head -5
```

## Migration File Structure

Generated migrations require review before use. Alembic's autogenerate misses: column type changes without explicit comparison, index renames, custom constraints.

Always verify the generated `upgrade()` and `downgrade()` match the intended schema change.

```python
"""add deliverable status column.

Revision ID: 002
Revises: 001
Create Date: 2026-03-11 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "deliverables",
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
    )
    op.create_index("ix_deliverables_status", "deliverables", ["status"])


def downgrade() -> None:
    op.drop_index("ix_deliverables_status", table_name="deliverables")
    op.drop_column("deliverables", "status")
```

## Safe Migration Practices

**Nullable before non-nullable.** When adding a non-nullable column to a populated table, use a two-step migration:

1. Add as nullable, populate data
2. Alter to non-nullable

```python
# Step 1 — migration 010
op.add_column("projects", sa.Column("owner_id", sa.String(36), nullable=True))

# Step 2 — migration 011 (after data backfill in 010)
op.alter_column("projects", "owner_id", existing_type=sa.String(36), nullable=False)
```

**Index creation.** Always create indexes on foreign key columns and columns used in WHERE clauses:

```python
op.create_index("ix_deliverables_project_id", "deliverables", ["project_id"])
```

**Never rename** — drop and recreate. Renaming columns or tables can fail in production depending on database vendor and locks.

**Server defaults for new non-nullable columns.** When backfilling existing rows isn't practical, use `server_default` temporarily:

```python
op.add_column(
    "projects",
    sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
)
```

Remove `server_default` in a follow-up migration after backfill if the application manages this field.

## Apply and Verify

Apply pending migrations:

```bash
uv run alembic upgrade head
```

Check current migration state:

```bash
uv run alembic current
```

Verify the database schema matches models after migration. Run the test suite — tests use real PostgreSQL and will catch schema drift.

## Checklist

- Migration file named `NNN_description.py` with sequential ID
- `--rev-id NNN` used when generating
- `upgrade()` and `downgrade()` both implemented
- Non-nullable columns on existing tables added in two steps
- Foreign key columns have indexes
- `server_default` removed in follow-up when not needed permanently
- Migration tested against real PostgreSQL (not mocked)
