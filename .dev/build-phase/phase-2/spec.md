# Phase 2 Spec: Gateway + Infrastructure
*Generated: 2026-02-12*

## Overview

Production-grade FastAPI gateway, Redis infrastructure, database layer, and ARQ workers — the foundation everything else sits on. This phase builds the complete server-side infrastructure with no ADK dependency. After this phase, we have a running gateway that can enqueue jobs, workers that can process them, a database with initial tables, and structured logging/error handling throughout.

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 0: Project Scaffold | Effectively complete | pyproject.toml, docker-compose.yml, directory scaffold, config module, enums, base models all exist |
| Phase 1: ADK Validation | Bypassed | Phase 2 is pure infrastructure; ADK sits on top in Phase 3. Decision #12 commits to ADK. |

## Design Decisions

### DD-1: Error Response Schema
All error responses follow a consistent envelope:
```json
{"error": {"code": "NOT_FOUND", "message": "Human-readable description", "details": {}}}
```
The `code` field uses an `ErrorCode` string enum. The `details` field is optional and typed as `dict[str, object]`.

### DD-2: Exception Hierarchy
```
AutoBuilderError (base — all app exceptions inherit)
├── NotFoundError          — resource lookup failures
├── ConflictError          — state conflicts (duplicate, already running)
├── ValidationError        — business logic validation (not Pydantic parse errors)
├── ConfigurationError     — missing/invalid config at startup
└── WorkerError            — worker-side execution failures
```
Each exception carries `code: ErrorCode` and optional `details`. The error middleware maps exceptions to HTTP status codes.

### DD-3: Database Models (Phase 2 Scope)
Three core tables for Phase 2. Minimal columns — enough to demonstrate the gateway→worker round-trip. Additional columns added in future phases as needed.

**`specifications`**: `id` (UUID PK), `name`, `content` (text), `status` (enum), `created_at`, `updated_at`

**`workflows`**: `id` (UUID PK), `specification_id` (FK nullable), `workflow_type` (str), `status` (enum), `params` (JSONB), `started_at`, `completed_at`, `created_at`, `updated_at`

**`deliverables`**: `id` (UUID PK), `workflow_id` (FK), `name`, `description`, `status` (enum), `depends_on` (JSONB array of UUIDs), `result` (JSONB nullable), `created_at`, `updated_at`

All tables use UUID primary keys (server-generated), `timezone.utc` timestamps, and optimistic locking isn't needed yet.

### DD-4: Structured Logging Format
JSON structured logging via stdlib `logging` with a custom JSON formatter. Fields: `timestamp` (ISO 8601), `level`, `logger`, `message`, plus arbitrary extras. Uses the `app.*` logger hierarchy. No third-party logging libraries.

### DD-5: Redis Client Management
A single `redis.asyncio.Redis` instance created at app startup (in lifespan), injected via FastAPI dependency injection. The same Redis URL serves ARQ (task queue) and future event streams. Connection verified with `PING` during lifespan startup.

### DD-6: ARQ Worker Test Task
Phase 2 includes a minimal `test_task` ARQ job to validate the gateway→worker→result round-trip. The gateway enqueues, the worker processes, the result is verifiable. This proves the infrastructure works before Phase 3 adds real ADK pipelines.

### DD-7: Lifespan Resource Management
FastAPI lifespan context manager owns startup/shutdown of:
1. Database engine (create → dispose)
2. Redis client (connect → close)
3. Health check verification (DB + Redis reachable)

Resources stored in `app.state` and accessed via `deps.py` dependency functions.

### DD-8: SQLAlchemy Base Class
A single declarative `Base` class in `app/db/models.py` with common column mixins:
- `id`: UUID primary key with `uuid4` server default
- `created_at` / `updated_at`: timezone-aware timestamps with server defaults

All ORM models inherit from this Base. The Alembic env.py references `Base.metadata` for autogenerate.

### DD-9: Additional Enums
Phase 2 adds to `app/models/enums.py`:
- `SpecificationStatus`: PENDING, PROCESSING, COMPLETED, FAILED
- `ErrorCode`: NOT_FOUND, CONFLICT, VALIDATION_ERROR, CONFIGURATION_ERROR, WORKER_ERROR, INTERNAL_ERROR

### DD-10: Docker Strategy
- **Production image** (`Dockerfile`): Multi-stage build, uv for dependency install, single image runs both gateway (uvicorn) and worker (arq) via entrypoint argument
- **Dev image** (`Dockerfile.dev`): Extends production, adds dev deps, mounts source for hot-reload
- **docker-compose.yml**: Add `gateway` and `worker` services alongside existing `postgres` and `redis`

## Deliverables

### P2.D1: Shared Libraries — Logging + Exceptions
**Files:** `app/lib/logging.py`, `app/lib/exceptions.py`, `app/lib/__init__.py`
**Depends on:** —
**Description:** Structured JSON logging setup with `app.*` logger hierarchy and custom JSON formatter. Custom exception hierarchy rooted at `AutoBuilderError` with subclasses for common error categories, each carrying an `ErrorCode`.
**Acceptance criteria:**
- [ ] `setup_logging()` configures root logger with JSON formatter
- [ ] `get_logger(name)` returns a logger under `app.*` hierarchy
- [ ] All exception classes carry `code: ErrorCode` and `message: str`
- [ ] Exception classes are importable from `app.lib`
**Validation:** `uv run pyright app/lib/ && uv run pytest tests/lib/`

### P2.D2: Domain Enum Additions
**Files:** `app/models/enums.py`, `app/models/__init__.py`
**Depends on:** —
**Description:** Add `SpecificationStatus` and `ErrorCode` enums needed by database models and exception hierarchy.
**Acceptance criteria:**
- [ ] `SpecificationStatus` has members: PENDING, PROCESSING, COMPLETED, FAILED
- [ ] `ErrorCode` has members: NOT_FOUND, CONFLICT, VALIDATION_ERROR, CONFIGURATION_ERROR, WORKER_ERROR, INTERNAL_ERROR
- [ ] All new enums exported from `app.models`
**Validation:** `uv run pyright app/models/`

### P2.D3: Database Engine + ORM Models
**Files:** `app/db/engine.py`, `app/db/models.py`, `app/db/__init__.py`
**Depends on:** P2.D1, P2.D2
**Description:** Async SQLAlchemy engine factory and session factory. Declarative Base with UUID/timestamp mixins. Three ORM models: Specification, Workflow, Deliverable with relationships and proper typing.
**Acceptance criteria:**
- [ ] `create_engine(url)` returns `AsyncEngine`
- [ ] `async_session_factory(engine)` returns `async_sessionmaker[AsyncSession]`
- [ ] `Base` class provides `id`, `created_at`, `updated_at` columns
- [ ] `Specification`, `Workflow`, `Deliverable` models defined with correct columns, types, and FK relationships
- [ ] All models use domain enums for status columns (not raw strings)
- [ ] Models importable from `app.db`
**Validation:** `uv run pyright app/db/`

### P2.D4: Alembic Migration Configuration + Initial Migration
**Files:** `app/db/migrations/env.py` (update), `app/db/migrations/versions/*.py` (generated)
**Depends on:** P2.D3
**Description:** Update Alembic env.py to reference `Base.metadata` for autogenerate support. Generate and verify the initial migration creating specifications, workflows, and deliverables tables.
**Acceptance criteria:**
- [ ] `env.py` imports `Base` from `app.db.models` and sets `target_metadata = Base.metadata`
- [ ] Initial migration file exists and creates all three tables
- [ ] `uv run alembic upgrade head` succeeds against a running PostgreSQL
- [ ] `uv run alembic downgrade base` reverses cleanly
**Validation:** `docker compose -f docker/docker-compose.yml up -d postgres && uv run alembic upgrade head`

### P2.D5: Redis Client + ARQ Worker Settings
**Files:** `app/workers/settings.py`, `app/workers/tasks.py`, `app/workers/__init__.py`
**Depends on:** P2.D1
**Description:** ARQ `WorkerSettings` class with Redis URL from config. A minimal `test_task` job function that accepts input, processes it, and returns a result. Worker entry point runnable via `uv run arq`.
**Acceptance criteria:**
- [ ] `WorkerSettings` class defines `redis_settings` from `AUTOBUILDER_REDIS_URL`
- [ ] `WorkerSettings.functions` includes `test_task`
- [ ] `test_task(ctx, payload)` is async, logs execution, returns a result dict
- [ ] `uv run arq app.workers.settings.WorkerSettings` starts without error
- [ ] ARQ cron skeleton with a `heartbeat` job (logs "worker alive" every 60s)
**Validation:** `uv run arq app.workers.settings.WorkerSettings` (starts and runs heartbeat)

### P2.D6: Gateway Pydantic Models
**Files:** `app/gateway/models/common.py`, `app/gateway/models/health.py`, `app/gateway/models/__init__.py`
**Depends on:** P2.D2
**Description:** API contract models for error responses and health endpoint. `ErrorResponse` envelope matching DD-1. `HealthResponse` with service status details (db, redis).
**Acceptance criteria:**
- [ ] `ErrorResponse` has nested `ErrorDetail` with `code`, `message`, `details` fields
- [ ] `HealthResponse` includes `status: str`, `version: str`, `services: dict[str, str]`
- [ ] All models inherit from `app.models.base.BaseModel`
- [ ] Models importable from `app.gateway.models`
**Validation:** `uv run pyright app/gateway/models/`

### P2.D7: FastAPI App Factory + Routes + DI + Middleware
**Files:** `app/gateway/main.py`, `app/gateway/deps.py`, `app/gateway/routes/health.py`, `app/gateway/middleware/errors.py`, `app/gateway/routes/__init__.py`
**Depends on:** P2.D1, P2.D3, P2.D5, P2.D6
**Description:** FastAPI app factory with lifespan managing DB engine + Redis client. Dependency injection for `AsyncSession` and `Redis` client. Health endpoint checking DB + Redis connectivity. Error handling middleware mapping `AutoBuilderError` subclasses to HTTP responses. CORS middleware configured for local development.
**Acceptance criteria:**
- [ ] `create_app()` returns a configured `FastAPI` instance
- [ ] Lifespan creates/disposes DB engine and Redis client
- [ ] `GET /health` returns 200 with DB and Redis status
- [ ] `GET /health` returns 503 if DB or Redis unreachable
- [ ] `get_db_session()` dependency yields `AsyncSession`
- [ ] `get_redis()` dependency returns `Redis` client
- [ ] Unhandled `AutoBuilderError` returns structured JSON error response
- [ ] CORS allows `localhost:*` origins
**Validation:** `uv run uvicorn app.gateway.main:app --port 8000` then `curl localhost:8000/health`

### P2.D8: Docker App Containers
**Files:** `docker/Dockerfile`, `docker/Dockerfile.dev`, `docker/docker-compose.yml` (update)
**Depends on:** P2.D7
**Description:** Production Dockerfile (multi-stage, uv-based, runs gateway or worker via entrypoint arg). Dev Dockerfile with hot-reload. Update docker-compose to add gateway and worker services with depends_on for postgres and redis. Worker service volume-mounts the project directory.
**Acceptance criteria:**
- [ ] `docker compose -f docker/docker-compose.yml up` starts all 4 services (postgres, redis, gateway, worker)
- [ ] Gateway container responds to `GET /health`
- [ ] Worker container starts ARQ and runs heartbeat cron
- [ ] Dev compose profile supports hot-reload via source mount
**Validation:** `docker compose -f docker/docker-compose.yml up -d && curl localhost:8000/health`

### P2.D9: Test Suite
**Files:** `tests/conftest.py` (update), `tests/lib/test_logging.py`, `tests/lib/test_exceptions.py`, `tests/db/test_engine.py`, `tests/gateway/test_health.py`, `tests/workers/test_tasks.py`
**Depends on:** P2.D7, P2.D5
**Description:** Test fixtures for async DB sessions (test database), Redis mock/instance, and FastAPI test client. Unit tests for logging, exceptions, DB engine creation, and health endpoint. Integration test demonstrating gateway enqueue → worker dequeue round-trip.
**Acceptance criteria:**
- [ ] `conftest.py` provides `async_session`, `redis_client`, `test_client` fixtures
- [ ] Health endpoint test verifies 200 response with correct schema
- [ ] Exception tests verify correct `code` and `message` attributes
- [ ] Worker test verifies `test_task` processes and returns expected result
- [ ] All tests pass: `uv run pytest`
**Validation:** `uv run pytest --cov=app`

## Build Order

```
Batch 1 (parallel): P2.D1, P2.D2
  D1: Logging + Exceptions (app/lib/)
  D2: Enum additions (app/models/enums.py)

Batch 2 (parallel): P2.D3, P2.D5, P2.D6
  D3: Database engine + ORM models (app/db/) — depends on D1, D2
  D5: Redis + ARQ workers (app/workers/) — depends on D1
  D6: Gateway Pydantic models (app/gateway/models/) — depends on D2

Batch 3 (parallel): P2.D4, P2.D7
  D4: Alembic migration (app/db/migrations/) — depends on D3
  D7: FastAPI app factory + routes + middleware (app/gateway/) — depends on D1, D3, D5, D6

Batch 4 (sequential): P2.D8
  D8: Docker containers (docker/) — depends on D7

Batch 5 (sequential): P2.D9
  D9: Test suite (tests/) — depends on D7, D5
```

## Completion Contract Traceability

| Completion Contract Item | Covered By | Validation |
|---|---|---|
| `uv run uvicorn app.gateway.main:app` starts and serves `/health` | P2.D7 | `curl localhost:8000/health` returns 200 |
| `uv run arq app.workers.settings.WorkerSettings` starts worker | P2.D5 | Worker process starts, heartbeat cron fires |
| `uv run alembic upgrade head` creates tables | P2.D4 | Migration creates specifications, workflows, deliverables tables |
| Redis `PING` succeeds | P2.D7 (lifespan), P2.D5 | Health endpoint reports redis: "ok" |
| Gateway can enqueue a test job, worker can dequeue and process it | P2.D9 | Integration test in `tests/workers/test_tasks.py` |
| All quality gates pass (ruff, pyright, pytest) | P2.D9 | `uv run ruff check . && uv run pyright && uv run pytest` |

## Research Notes

### ARQ WorkerSettings Pattern
ARQ requires a `WorkerSettings` class (not instance) with class-level attributes. The entry point is `arq <module.path.WorkerSettings>`. Key attributes:
- `functions`: list of task functions
- `redis_settings`: `RedisSettings` object (host, port, database)
- `cron_jobs`: list of `cron()` jobs for scheduled tasks
- `on_startup` / `on_shutdown`: async lifecycle hooks

### FastAPI Lifespan Pattern
FastAPI's `lifespan` context manager replaces the deprecated `on_startup`/`on_shutdown` events. Resources created in the `async with` block are available for the app's lifetime and cleaned up on shutdown. Store resources on `app.state`.

### SQLAlchemy 2.0 Async Pattern
Use `create_async_engine()` with `asyncpg` URL scheme. Session factory via `async_sessionmaker(engine, class_=AsyncSession)`. All queries use `await session.execute(select(...))` style. The `Mapped[]` type annotation system provides full pyright compatibility.

### Docker Multi-Stage Build
Stage 1: Install dependencies with uv into a venv. Stage 2: Copy venv + app source. Entrypoint accepts `gateway` or `worker` argument to run the appropriate process. This keeps image size small and avoids installing build tools in production.
