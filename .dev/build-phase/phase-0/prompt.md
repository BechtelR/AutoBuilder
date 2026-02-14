# Context
Read these files before starting:
- `CLAUDE.md` — project rules (loaded automatically)
- `.dev/03-STRUCTURE.md` — file placement truth
- `.dev/build-phase/phase-0/spec.md` — full spec (read Overview, Design Decisions, and all Deliverables)
- `.dev/10-DEV_SETUP.md` — environment variables (section 3), dependencies (section 7)
- `.dev/04-TECH_STACK.md` — tech decisions and rationale (reference only if questions arise)

# Task
Implement **Phase 0: Project Scaffold & Dev Environment**.

Set up a working empty project that builds, lints, type-checks, and tests clean. This includes Python packaging via uv, Docker infrastructure (PostgreSQL + Redis), Alembic migration config, the full directory scaffold from `03-STRUCTURE.md`, shared domain models, Pydantic-based configuration, pre-commit hooks, and a `.env.example` template.

# Success Criteria
- [ ] `docker compose -f docker/docker-compose.yml up -d` starts PostgreSQL and Redis (verify: `docker compose -f docker/docker-compose.yml ps`)
- [ ] `uv sync && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest` all pass (verify: run the full command)
- [ ] Directory structure matches `.dev/03-STRUCTURE.md` (verify: `uv run python -c "import app; import app.models; import app.config; import app.gateway; import app.workers; import app.db"`)
- [ ] Configuration loads from environment variables with sensible defaults (verify: `uv run python -c "from app.config import get_settings; s = get_settings(); print(s.db_url, s.redis_url, s.log_level)"`)
- [ ] Shared enums and base models importable from `app.models` (verify: `uv run python -c "from app.models import WorkflowStatus, DeliverableStatus, AgentRole; assert WorkflowStatus.RUNNING.value == 'RUNNING'; print('OK')"`)

# Scope
## Files to Create/Modify
- `pyproject.toml` — project metadata, all deps, ruff/pyright/pytest config
- `.gitignore` — comprehensive ignores (Python, Node, IDE, env, Docker, OS)
- `docker/docker-compose.yml` — PostgreSQL 16 (pgvector) + Redis 7 services
- `alembic.ini` — Alembic config pointing to `app/db/migrations/`
- `app/db/migrations/env.py` — async migration runner using `AsyncEngine`
- `app/db/migrations/script.py.mako` — Alembic template
- `app/__init__.py`, `app/__main__.py` — package root and CLI entry stub
- All `app/` subdirectories per `03-STRUCTURE.md` with `__init__.py` files
- `app/config/settings.py` — Pydantic Settings with all env vars from CLAUDE.md table
- `app/models/enums.py` — `WorkflowStatus`, `DeliverableStatus`, `AgentRole`
- `app/models/constants.py` — `APP_NAME` constant
- `app/models/base.py` — shared `BaseModel` with `from_attributes=True`
- `app/models/__init__.py` — re-exports key types
- `.pre-commit-config.yaml` — ruff lint, ruff format, pyright hooks via `uv run`
- `.env.example` — all env vars from DEV_SETUP.md section 3 with placeholders
- `tests/conftest.py` — minimal test config skeleton
- Test subdirectories: `tests/gateway/`, `tests/workers/`, `tests/agents/`

## Out of Scope
- FastAPI app, routes, or middleware (Phase 2)
- ARQ worker implementation (Phase 2)
- Database ORM models or migrations (Phase 2)
- ADK integration (Phase 1/3)
- Dashboard code (Phase 12)
- Any actual business logic

# Work Breakdown
1. **Batch 1** — `pyproject.toml` (P0.D1), `.gitignore` (P0.D2), `docker/docker-compose.yml` (P0.D3), directory scaffold (P0.D5), `.env.example` (P0.D9)
   - These have no dependencies on each other
   - `pyproject.toml`: all core + dev deps, ruff (line-length=100, double quotes, isort with known-first-party=["app"]), pyright (strict, py311), pytest (asyncio_mode="auto")
   - Docker: PostgreSQL 16 with pgvector extension + Redis 7, health checks, named volumes, `autobuilder` credentials
   - Scaffold: every directory from `03-STRUCTURE.md` with `__init__.py`; `dashboard/`, `docs/`, `scripts/` with `.gitkeep`; `tests/conftest.py`

2. **Batch 2** — `app/config/settings.py` (P0.D6), `app/models/` (P0.D7), `.pre-commit-config.yaml` (P0.D8)
   - Depends on Batch 1 (deps installed, dirs exist)
   - Settings: `pydantic_settings.BaseSettings`, fields for `AUTOBUILDER_DB_URL`, `AUTOBUILDER_REDIS_URL`, `AUTOBUILDER_LOG_LEVEL` with defaults from CLAUDE.md; `get_settings()` with `@lru_cache`
   - Models: enums as `str, enum.Enum` with values = names (SCREAMING_SNAKE); `BaseModel(ConfigDict(from_attributes=True))`; `__init__.py` re-exports
   - Pre-commit: local hooks using `uv run` for ruff check, ruff format --check, pyright

3. **Batch 3** — Alembic configuration (P0.D4)
   - Depends on D1 + D6 (alembic installed, config module exists for DB URL)
   - `alembic.ini` with `script_location = app/db/migrations`
   - `env.py` with async pattern: `create_async_engine` → `run_sync(do_run_migrations)`
   - DB URL loaded from `app.config.get_settings()`, not hardcoded

4. **Batch 4** — Quality gate verification (P0.D10)
   - Run: `uv sync && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
   - Fix ALL errors until clean

# Constraints
- Follow enum convention: values MUST match names (`RUNNING = "RUNNING"`, not `"running"`)
- Python 3.11+ — use `datetime.now(timezone.utc)`, not `utcnow()`
- No `Any` types — use explicit types throughout
- Double quotes (ruff default, Q12 decided)
- Line length: 100 (ruff enforced)
- Alembic `env.py` must use async pattern with `AsyncEngine`
- Config must NOT hardcode DB URL in `alembic.ini` — load from settings
- `pydantic-settings` is a separate package from `pydantic` v2
- All `__init__.py` files should be minimal (empty or re-exports only)
- `app/__main__.py` should be minimal: `print("AutoBuilder CLI — not yet implemented")`
- `tests/conftest.py` can be empty or have a docstring only

# Verification
Before marking complete:
1. All success criteria checked
2. `uv run ruff check .` passes
3. `uv run ruff format --check .` passes
4. `uv run pyright` passes (strict mode, 0 errors)
5. `uv run pytest` runs (0 tests collected, 0 errors)
6. `docker compose -f docker/docker-compose.yml up -d` starts PostgreSQL + Redis
7. `uv run python -c "from app.config import get_settings; s = get_settings(); print(s.db_url, s.redis_url, s.log_level)"`
8. `uv run python -c "from app.models import WorkflowStatus, DeliverableStatus, AgentRole; assert WorkflowStatus.RUNNING.value == 'RUNNING'"`
