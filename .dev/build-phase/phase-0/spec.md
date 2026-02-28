# Phase 0 Spec: Project Scaffold & Dev Environment
*Generated: 2026-02-12*

## Overview

Standing up a working empty project that builds, lints, type-checks, and tests clean. This is the foundation every subsequent phase depends on. Includes Python packaging via uv, Docker infrastructure (PostgreSQL + Redis), Alembic migration config, directory scaffold matching `03-STRUCTURE.md`, shared domain models, and Pydantic-based configuration loading.

## Prerequisites

**None.** Phase 0 is the first phase.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Quote style | Double quotes | Ruff default (Q12 — decided) |
| Docker config | docker-compose with PostgreSQL + Redis | Local infra only (Q14 — decided) |
| Package build backend | `hatchling` | Roadmap specifies it; lightweight, standards-compliant |
| Python version | 3.11+ | Roadmap constraint; `datetime.UTC` alias not used (3.11 compat) |
| Alembic async | `asyncpg` driver with async `run_migrations_online` | Matches tech stack (SQLAlchemy 2.0 async throughout) |
| Initial enums | `WorkflowStatus`, `DeliverableStatus`, `AgentRole` | Roadmap-specified; values = names (SCREAMING_SNAKE per enum convention) |
| Config approach | Single `Settings` class via `pydantic-settings` | Covers all env vars from CLAUDE.md table + DEV_SETUP.md |
| .gitignore scope | Python, Node, IDE, env, Docker, OS artifacts | Roadmap requirement; comprehensive from day one |
| Pre-commit hooks | `ruff check`, `ruff format --check`, `pyright` | Roadmap specifies ruff + pyright hooks |
| Dashboard placeholder | Empty `dashboard/` with `.gitkeep` | Phase 12 deliverable; just reserve the directory now |

## Deliverables

### P0.D1: Create `pyproject.toml` with all tooling config
**Files:** `pyproject.toml`
**Depends on:** —
**Description:** Define project metadata, Python 3.11+ requirement, all core and dev dependencies from the tech stack doc, and tool configuration sections for ruff (line-length=100, double quotes, isort), pyright (strict mode), and pytest (asyncio_mode=auto). Build backend is hatchling.
**Acceptance criteria:**
- [x] `uv sync` installs all dependencies without error
- [x] Contains all core deps: `google-adk`, `litellm`, `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `pgvector`, `arq`, `redis[hiredis]`, `pydantic`, `pydantic-settings`, `httpx`, `typer`, `pyyaml`
- [x] Contains all dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `pyright`
- [x] Ruff configured: line-length=100, target=py311, double quotes, isort with known-first-party=["app"]
- [x] Pyright configured: strict mode, pythonVersion="3.11"
- [x] Pytest configured: asyncio_mode="auto", testpaths=["tests"]
**Validation:** `uv sync && uv run python -c "import fastapi; import sqlalchemy; import arq; print('OK')"`

### P0.D2: Create `.gitignore`
**Files:** `.gitignore`
**Depends on:** —
**Description:** Comprehensive gitignore covering Python artifacts (__pycache__, *.pyc, *.egg-info, dist/, build/, .venv/), Node (node_modules/, dist/), IDE (.vscode/, .idea/), environment (.env, .env.*), Docker volumes, OS files (.DS_Store, Thumbs.db), and project-specific exclusions (*.db, .coverage, htmlcov/).
**Acceptance criteria:**
- [x] Covers Python, Node, IDE, env, Docker, OS artifacts
- [x] `.env` is ignored (secrets protection)
- [x] `__pycache__/` and `.venv/` are ignored
- [x] `node_modules/` is ignored
**Validation:** `git check-ignore .env __pycache__/foo.pyc node_modules/x`

### P0.D3: Create `docker-compose.yml`
**Files:** `docker-compose.yml` (project root)
**Depends on:** —
**Description:** Docker Compose file defining PostgreSQL 16 (with pgvector extension) and Redis 7 services. PostgreSQL configured with `autobuilder` user/password/database matching the default `AUTOBUILDER_DB_URL`. Redis on default port. Both with health checks and named volumes for data persistence.
**Acceptance criteria:**
- [x] `docker compose up -d` starts both services
- [x] PostgreSQL accessible at `localhost:5432` with `autobuilder` credentials
- [x] Redis accessible at `localhost:6379` and responds to PING
- [x] PostgreSQL has pgvector extension available (`CREATE EXTENSION IF NOT EXISTS vector`)
- [x] Health checks defined for both services
- [x] Named volumes for data persistence
**Validation:** `docker compose up -d && docker compose ps && docker exec autobuilder-redis redis-cli ping && docker exec autobuilder-postgres pg_isready -U autobuilder`

### P0.D4: Create Alembic configuration
**Files:** `alembic.ini`, `app/db/__init__.py`, `app/db/migrations/env.py`, `app/db/migrations/script.py.mako`
**Depends on:** P0.D1, P0.D6
**Description:** Alembic configured for async migrations with asyncpg. `alembic.ini` points to `app/db/migrations/` for script location. `env.py` uses `run_async` pattern with `AsyncEngine`. Database URL sourced from app config (not hardcoded in ini). Initial `versions/` directory created empty.
**Acceptance criteria:**
- [x] `alembic.ini` exists with correct script_location
- [x] `env.py` uses async migration pattern (connectable via `AsyncEngine`)
- [x] Database URL loaded from `AUTOBUILDER_DB_URL` env var (not hardcoded)
- [x] `uv run alembic --help` runs without import errors
- [x] `app/db/migrations/versions/` directory exists (empty)
**Validation:** `uv run alembic --help`

### P0.D5: Create directory scaffold with `__init__.py` files
**Files:** All directories per `03-STRUCTURE.md` with `__init__.py`
**Depends on:** —
**Description:** Create the full directory tree from `03-STRUCTURE.md` for the `app/` package. Each Python package directory gets an `__init__.py` (can be empty or with minimal `__all__` exports). Non-package directories (`scripts/`, `dashboard/`, `docs/`, `docker/`) get `.gitkeep` where empty. `tests/` mirrors app structure.
**Acceptance criteria:**
- [x] `app/__init__.py` exists
- [x] `app/__main__.py` exists (minimal: `print("AutoBuilder CLI — not yet implemented")`)
- [x] All `app/` subdirectories from `03-STRUCTURE.md` exist with `__init__.py`: `gateway/`, `gateway/routes/`, `gateway/models/`, `gateway/middleware/`, `workers/`, `events/`, `models/`, `lib/`, `utils/`, `agents/`, `agents/custom/`, `agents/llm/`, `tools/`, `skills/`, `workflows/`, `router/`, `memory/`, `orchestrator/`, `db/`, `config/`
- [x] `tests/conftest.py` exists (empty or minimal docstring)
- [x] `tests/gateway/`, `tests/workers/`, `tests/agents/` exist
- [x] `scripts/` directory exists
- [x] `dashboard/` directory exists with `.gitkeep`
- [x] `docs/` directory exists with `.gitkeep`
- [x] `uv run python -m app` runs without import error
**Validation:** `uv run python -m app && python -c "import app; import app.models; import app.config; import app.gateway; import app.workers; import app.db"`

> **Delta note (2026-02-27):** `03-STRUCTURE.md` was updated to v1.5 (2026-02-18) after this deliverable was built. Two diffs vs. what Phase 0 created: (1) `app/orchestrator/` was removed from the canonical structure — this directory exists in the codebase as an empty placeholder but is now an orphan (no BOM component, no architecture reference). Remediation required: remove `app/orchestrator/`. (2) `app/cli/` was added to the canonical structure — this directory is Phase 10 scope (BOM C01–C06) and will be created when the CLI is built.

### P0.D6: Create configuration module
**Files:** `app/config/__init__.py`, `app/config/settings.py`
**Depends on:** P0.D1
**Description:** Pydantic Settings class loading all environment variables from the CLAUDE.md env table: `AUTOBUILDER_DB_URL`, `AUTOBUILDER_REDIS_URL`, `AUTOBUILDER_LOG_LEVEL`. Include sensible defaults matching the documented values. Settings class uses `model_config` with `env_prefix` or explicit `Field(alias=...)`. Export a `get_settings()` function with `@lru_cache` for singleton access.
**Acceptance criteria:**
- [x] `Settings` class extends `pydantic_settings.BaseSettings`
- [x] All env vars from CLAUDE.md table have fields with correct defaults
- [x] `get_settings()` returns cached singleton
- [x] `from app.config import Settings, get_settings` works
- [x] Settings loads from environment without `.env` file (pure env vars + defaults)
- [x] Pyright passes on this module (strict)
**Validation:** `uv run python -c "from app.config import get_settings; s = get_settings(); print(s.db_url, s.redis_url, s.log_level)"`

### P0.D7: Create shared domain models
**Files:** `app/models/__init__.py`, `app/models/enums.py`, `app/models/constants.py`, `app/models/base.py`
**Depends on:** P0.D1
**Description:** Initial shared domain types. `enums.py`: `WorkflowStatus` (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED), `DeliverableStatus` (PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED), `AgentRole` (PLANNER, CODER, REVIEWER, FIXER). All enums are `str, enum.Enum` with values matching names (SCREAMING_SNAKE). `constants.py`: placeholder with `APP_NAME = "autobuilder"`. `base.py`: `BaseModel` subclass with shared config (e.g., `model_config = ConfigDict(from_attributes=True, strict=True)`). `__init__.py` re-exports key types.
**Acceptance criteria:**
- [x] All three enums defined with values = names (SCREAMING_SNAKE)
- [x] Enums are `str, enum.Enum` subclasses
- [x] `BaseModel` configured with `from_attributes=True`
- [x] `from app.models import WorkflowStatus, DeliverableStatus, AgentRole` works
- [x] `from app.models.base import BaseModel` works
- [x] Pyright passes on all model files (strict)
**Validation:** `uv run python -c "from app.models import WorkflowStatus, DeliverableStatus, AgentRole; assert WorkflowStatus.RUNNING.value == 'RUNNING'; print('OK')"`

### P0.D8: Create pre-commit configuration
**Files:** `.pre-commit-config.yaml`
**Depends on:** P0.D1
**Description:** Pre-commit config with hooks for ruff check (lint), ruff format check (formatting), and pyright (type checking). Uses local hooks pointing to `uv run` commands so they use the project's pinned versions.
**Acceptance criteria:**
- [x] `.pre-commit-config.yaml` exists
- [x] Ruff lint hook configured
- [x] Ruff format hook configured
- [x] Pyright hook configured
- [x] All hooks use `uv run` for consistent tooling versions
**Validation:** `uv run pre-commit run --all-files` (after `uv run pre-commit install`)

### P0.D9: Create `.env.example`
**Files:** `.env.example`
**Depends on:** —
**Description:** Template environment file with all variables from DEV_SETUP.md section 3, with placeholder values and comments. This file IS committed (unlike `.env`).
**Acceptance criteria:**
- [x] Contains all env vars from DEV_SETUP.md section 3
- [x] Placeholder values (not real keys)
- [x] Comments explaining each variable
- [x] `.env.example` is NOT in `.gitignore`
**Validation:** `test -f .env.example && ! git check-ignore .env.example`

> **Delta note (2026-02-27):** Three stale entries identified by delta audit: (1) Line 26 references `.dev/11-PROVIDERS.md` which does not exist — should be `.dev/06-PROVIDERS.md`. (2) Lines 16–19 comment "Phase 1 provider TBD" with `SEARXNG_URL` as an option — Roadmap Q7 was closed (Tavily primary, Brave fallback; SearXNG rejected). (3) Lines 23–24 document `AUTOBUILDER_MAX_CONCURRENCY` and `AUTOBUILDER_SKILLS_DIR` but these have no corresponding fields in `app/config/settings.py`. Remediation required: fix broken reference, update search provider comment, and resolve the Settings gap (remove vars from `.env.example` or add fields to Settings when Phases 6 and 8 implement them respectively).

### P0.D10: Quality gate verification
**Files:** — (validation only)
**Depends on:** P0.D1, P0.D2, P0.D4, P0.D5, P0.D6, P0.D7, P0.D8
**Description:** Run the full quality gate suite to verify everything passes clean: `uv sync`, `ruff check .`, `ruff format --check .`, `pyright`, `pytest`. Fix any issues until all pass.
**Acceptance criteria:**
- [x] `uv sync` succeeds
- [x] `ruff check .` passes with 0 errors
- [x] `ruff format --check .` passes (already formatted)
- [x] `uv run pyright` passes with 0 errors (strict mode)
- [x] `uv run pytest` runs (3 scaffold tests pass)
**Validation:** `uv sync && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`

## Build Order

```
Batch 1 (parallel): P0.D1, P0.D2, P0.D3, P0.D5, P0.D9
  - No dependencies; pyproject.toml, gitignore, docker, dirs, env.example

Batch 2 (parallel): P0.D6, P0.D7, P0.D8
  - Depend on D1 (dependencies installed) and D5 (directories exist)

Batch 3 (sequential): P0.D4
  - Depends on D1 (alembic installed) and D6 (config module for DB URL)

Batch 4 (sequential): P0.D10
  - Depends on all above; final validation sweep
```

## Completion Contract Traceability

| Completion Contract Item | Covered By | Validation |
|--------------------------|------------|------------|
| `docker compose up -d` starts PostgreSQL and Redis | P0.D3 | `docker compose up -d && docker compose ps` |
| `docker compose up -d && uv sync && ruff check && pyright && pytest` all pass | P0.D10 | Full quality gate command |
| Directory structure matches `03-STRUCTURE.md` | P0.D5 | `import app; import app.models; import app.config; ...` |
| Configuration loads from env vars with sensible defaults | P0.D6 | `from app.config import get_settings; s = get_settings()` |
| Shared enums and base models importable from `app.models` | P0.D7 | `from app.models import WorkflowStatus, DeliverableStatus, AgentRole` |

## Research Notes

- **pgvector Docker image**: Use `pgvector/pgvector:pg16` or `ankane/pgvector` image which includes the extension pre-installed, avoiding manual `CREATE EXTENSION` in init scripts. Alternatively, use the standard `postgres:16` image with an init script to install pgvector.
- **Alembic async pattern**: SQLAlchemy 2.0 async migrations require `run_async()` wrapper in `env.py`. The `connectable` must be created via `create_async_engine()` and migrations run inside `async with connectable.connect() as connection: await connection.run_sync(do_run_migrations)`.
- **pydantic-settings**: Separate package from pydantic v2. Must be listed as explicit dependency (`pydantic-settings`).
- **Ruff isort**: Ruff includes isort functionality via `[tool.ruff.lint.isort]` section. No separate isort package needed.
- **pre-commit with uv**: Use `repo: local` hooks with `language: system` and `entry: uv run ruff check` to leverage project-pinned versions.
