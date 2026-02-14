# Phase 2 Spec: Gateway + Infrastructure
*Generated: 2026-02-14*

## Overview

Phase 2 builds the production-grade server infrastructure that everything else sits on: FastAPI gateway, async database layer, Redis-backed ARQ workers, structured logging, and Docker containerization. After this phase, the system has a running HTTP gateway serving health checks, workers processing queued jobs, a PostgreSQL database with initial tables, and structured error handling throughout — all with zero ADK dependency. ADK integration arrives in Phase 3 on top of this foundation.

This phase directly enables two core vision differentiators: **API-first architecture** (the gateway owns the external contract — ADK is never exposed) and **out-of-process execution** (the gateway enqueues work, ARQ workers execute it). It also establishes the infrastructure patterns that solve **Problem #2** (intelligent orchestration infrastructure) and **Problem #3** (self-hosted, cost-effective alternative to $10k+ platforms).

Key constraints: no ADK imports anywhere in Phase 2 code (clean separation), all I/O async, all types strict (pyright), all enums follow the established `StrEnum` pattern with values matching names.

## Features

- **Structured logging and exception hierarchy** — JSON-formatted logging with `app.*` hierarchy; custom exceptions with error codes mapping to HTTP statuses
- **Domain enum additions** — `SpecificationStatus` and `ErrorCode` enums for database models and error handling
- **Async database layer** — `AsyncEngine` + `AsyncSession` factory, SQLAlchemy 2.0 declarative models for specifications, workflows, and deliverables
- **Alembic migration** — Autogenerate-enabled migration environment with initial schema migration
- **Redis + ARQ worker infrastructure** — Async Redis client, ARQ `WorkerSettings` with task queue and cron heartbeat
- **FastAPI gateway** — App factory with lifespan management, health endpoint, dependency injection, CORS, error handling middleware, request logging
- **Gateway Pydantic models** — API contract models for error responses and health checks
- **Production Dockerfile** — Multi-stage build for deployment and CI
- **Test suite** — Unit and integration tests covering logging, exceptions, database, gateway, and worker round-trip

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 0: Project Scaffold | MET | `uv sync && uv run ruff check . && uv run pyright && uv run pytest` all pass; directory structure matches `03-STRUCTURE.md` |
| Phase 1: ADK Validation | MET | 17/17 tests pass (`tests/phase1/`); go/no-go decision documented at `.dev/.discussion/phase1-decision.md`; commit `ecdc5dc` |

## Design Decisions

### DD-1: Error Response Schema
All error responses follow a consistent JSON envelope:
```json
{"error": {"code": "NOT_FOUND", "message": "Human-readable description", "details": {}}}
```
The `code` field uses an `ErrorCode` string enum (see DD-9). The `details` field is optional, typed as `dict[str, object]`. This gives clients a machine-readable code for programmatic handling and a human-readable message for display.

### DD-2: Exception Hierarchy
```
AutoBuilderError (base — all app exceptions inherit)
├── NotFoundError          — resource lookup failures (404)
├── ConflictError          — state conflicts: duplicate, already running (409)
├── ValidationError        — business logic validation, not Pydantic parse errors (422)
├── ConfigurationError     — missing/invalid config at startup (500)
└── WorkerError            — worker-side execution failures (500)
```
Each exception carries `code: ErrorCode`, `message: str`, and optional `details: dict[str, object]`. The error middleware maps exception types to HTTP status codes. Pydantic `RequestValidationError` is handled separately by FastAPI's built-in handler.

### DD-3: Database Models (Phase 2 Scope)
Three core tables — minimal columns sufficient to demonstrate the gateway→worker round-trip and establish the ORM pattern. Additional columns added in future phases.

**`specifications`**: `id` (UUID PK), `name` (str), `content` (text), `status` (SpecificationStatus enum), `created_at`, `updated_at`

**`workflows`**: `id` (UUID PK), `specification_id` (FK → specifications, nullable), `workflow_type` (str), `status` (WorkflowStatus enum), `params` (JSONB, nullable), `started_at` (nullable), `completed_at` (nullable), `created_at`, `updated_at`

**`deliverables`**: `id` (UUID PK), `workflow_id` (FK → workflows), `name` (str), `description` (text, nullable), `status` (DeliverableStatus enum), `depends_on` (JSONB array of UUID strings, default `[]`), `result` (JSONB, nullable), `created_at`, `updated_at`

All tables use UUID primary keys (`uuid4` server default), timezone-aware UTC timestamps, and proper foreign key constraints.

### DD-4: Structured Logging Format
JSON structured logging via stdlib `logging` with a custom `JsonFormatter`. Fields: `timestamp` (ISO 8601 UTC), `level`, `logger`, `message`, plus arbitrary extras passed via `logger.info("msg", extra={...})`. Uses the `app.*` logger hierarchy. No third-party logging libraries — stdlib is sufficient.

### DD-5: Redis Client Management
A single `redis.asyncio.Redis` instance created at gateway startup (in lifespan), injected via FastAPI dependency injection. The same `AUTOBUILDER_REDIS_URL` serves both the gateway's Redis client and ARQ workers. Connection verified with `PING` during lifespan startup.

### DD-6: ARQ Worker Test Task
Phase 2 includes a minimal `test_task` ARQ job to validate the gateway→Redis→worker round-trip. The gateway enqueues the job (via `arq.connections.ArqRedis`), the worker processes it, and the result is verifiable. This proves the infrastructure works end-to-end before Phase 3 adds real ADK pipelines.

### DD-7: Lifespan Resource Management
FastAPI lifespan context manager owns startup/shutdown of:
1. Database engine (`create_async_engine` → `engine.dispose()`)
2. Redis client (`Redis.from_url()` → `redis.aclose()`)
3. Health check verification (DB `SELECT 1` + Redis `PING` at startup)

Resources stored on `app.state` and accessed via dependency functions in `deps.py`.

### DD-8: SQLAlchemy Declarative Base
A single declarative `Base` class in `app/db/models.py` using `DeclarativeBase` (SQLAlchemy 2.0 style). Common columns defined via a mixin:
- `id`: `Mapped[uuid.UUID]` primary key with `uuid4` default
- `created_at`: `Mapped[datetime]` with server-side UTC default
- `updated_at`: `Mapped[datetime]` with server-side UTC default, auto-updates on change

All ORM models inherit from `Base`. Alembic's `env.py` references `Base.metadata` for autogenerate.

### DD-9: Additional Enums
Phase 2 adds to `app/models/enums.py` using the established `enum.StrEnum` pattern (values match names):
- `SpecificationStatus`: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`
- `ErrorCode`: `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR`, `CONFIGURATION_ERROR`, `WORKER_ERROR`, `INTERNAL_ERROR`

### DD-10: Docker Strategy
- **Development**: `docker compose up -d` runs infrastructure only (postgres + redis). Gateway, worker, tests, lint, and typecheck all run locally via `uv run`. This gives direct access to all dev tooling without Docker indirection.
- **Production image** (`Dockerfile`): Multi-stage build using `uv` for dependency install. Single image runs both gateway (`uvicorn`) and worker (`arq`) via entrypoint argument. Stage 1 installs deps into venv; Stage 2 copies venv + source. Used for production deployment and CI.
- **docker-compose.yml** remains infra-only (postgres + redis). No gateway/worker services — those run locally during dev.

## Deliverables

### P2.D1: Shared Libraries — Logging + Exceptions
**Files:** `app/lib/logging.py`, `app/lib/exceptions.py`, `app/lib/__init__.py` (update)
**Depends on:** —
**Description:** Structured JSON logging setup with `app.*` logger hierarchy and a custom `JsonFormatter` that outputs one JSON object per log line. Custom exception hierarchy rooted at `AutoBuilderError` with subclasses for common error categories, each carrying an `ErrorCode` enum value and optional details dict.
**Requirements:**
- [ ] `setup_logging(level: str)` configures the root `app` logger with JSON formatter and the specified level
- [ ] `get_logger(name: str)` returns a `logging.Logger` under the `app.*` hierarchy (e.g., `get_logger("gateway")` → `app.gateway`)
- [ ] `JsonFormatter` outputs `{"timestamp": "...", "level": "...", "logger": "...", "message": "...", ...extras}` per line
- [ ] `AutoBuilderError` base class has `code: ErrorCode`, `message: str`, `details: dict[str, object]`
- [ ] Subclasses: `NotFoundError`, `ConflictError`, `ValidationError`, `ConfigurationError`, `WorkerError` — each with appropriate default `ErrorCode`
- [ ] All classes importable from `app.lib`
- [ ] Both files pass pyright strict mode
**Validation:**
- `uv run pyright app/lib/`

---

### P2.D2: Domain Enum Additions
**Files:** `app/models/enums.py` (update), `app/models/__init__.py` (update)
**Depends on:** —
**Description:** Add `SpecificationStatus` and `ErrorCode` enums to the existing enums module, following the established `enum.StrEnum` pattern where values match names. Update `__init__.py` exports.
**Requirements:**
- [ ] `SpecificationStatus` has members: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` (all `StrEnum`, values match names)
- [ ] `ErrorCode` has members: `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR`, `CONFIGURATION_ERROR`, `WORKER_ERROR`, `INTERNAL_ERROR` (all `StrEnum`, values match names)
- [ ] Both enums exported from `app.models`
- [ ] Existing enums (`WorkflowStatus`, `DeliverableStatus`, `AgentRole`) unchanged
**Validation:**
- `uv run pyright app/models/`

---

### P2.D3: Database Engine + ORM Models
**Files:** `app/db/engine.py`, `app/db/models.py`, `app/db/__init__.py` (update)
**Depends on:** P2.D1, P2.D2
**Description:** Async SQLAlchemy 2.0 engine factory and session factory. Declarative `Base` class with UUID primary key and timestamp mixins. Three ORM models (`Specification`, `Workflow`, `Deliverable`) with proper column types, foreign key relationships, and domain enum usage. All typed with `Mapped[]` annotations for pyright strict compatibility.
**Requirements:**
- [ ] `create_engine(url: str) -> AsyncEngine` creates an async engine with `asyncpg` driver
- [ ] `async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]` returns a configured session factory
- [ ] `Base` class (via `DeclarativeBase`) provides `id` (UUID PK with `uuid4` default), `created_at`, `updated_at` (timezone-aware UTC timestamps)
- [ ] `Specification` model has columns: `name` (str), `content` (text), `status` (`SpecificationStatus` enum)
- [ ] `Workflow` model has columns: `specification_id` (FK nullable), `workflow_type` (str), `status` (`WorkflowStatus` enum), `params` (JSONB nullable), `started_at` (nullable), `completed_at` (nullable)
- [ ] `Deliverable` model has columns: `workflow_id` (FK), `name` (str), `description` (text nullable), `status` (`DeliverableStatus` enum), `depends_on` (JSONB default `[]`), `result` (JSONB nullable)
- [ ] Foreign key relationships: `Workflow.specification_id → Specification.id`, `Deliverable.workflow_id → Workflow.id`
- [ ] All models use domain enums for status columns (not raw strings)
- [ ] `Base`, `Specification`, `Workflow`, `Deliverable`, `create_engine`, `async_session_factory` importable from `app.db`
**Validation:**
- `uv run pyright app/db/`

---

### P2.D4: Alembic Migration + Initial Schema
**Files:** `app/db/migrations/env.py` (update), `app/db/migrations/versions/*.py` (generated)
**Depends on:** P2.D3
**Description:** Update the existing Alembic `env.py` to import `Base` from `app.db.models` and set `target_metadata = Base.metadata` (the commented-out import is already there). Generate the initial migration creating `specifications`, `workflows`, and `deliverables` tables. Verify upgrade and downgrade both succeed.
**Requirements:**
- [ ] `env.py` imports `Base` from `app.db.models` and sets `target_metadata = Base.metadata`
- [ ] Initial migration file exists in `app/db/migrations/versions/` and creates all three tables
- [ ] `uv run alembic upgrade head` succeeds against a running PostgreSQL instance
- [ ] `uv run alembic downgrade base` reverses cleanly (drops all three tables)
- [ ] Tables have correct column types, constraints, and foreign keys
**Validation:**
- `docker compose up -d postgres && uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head`

---

### P2.D5: Redis Client + ARQ Worker Settings
**Files:** `app/workers/settings.py`, `app/workers/tasks.py`, `app/workers/__init__.py` (update)
**Depends on:** P2.D1
**Description:** ARQ `WorkerSettings` class with Redis connection from `AUTOBUILDER_REDIS_URL`. A minimal `test_task` job function for round-trip validation. Worker entry point runnable via `uv run arq`. Cron skeleton with heartbeat job. Worker `on_startup` initializes structured logging.
**Requirements:**
- [ ] `WorkerSettings` class defines `redis_settings` parsed from `AUTOBUILDER_REDIS_URL` (default `redis://localhost:6379`)
- [ ] `WorkerSettings.functions` list includes `test_task`
- [ ] `test_task(ctx: dict[str, object], payload: str) -> dict[str, str]` is async, logs execution via structured logger, returns `{"status": "completed", "payload": payload}`
- [ ] `WorkerSettings.cron_jobs` includes a `heartbeat` job that logs "worker alive" every 60 seconds
- [ ] `WorkerSettings.on_startup` calls `setup_logging()` from `app.lib`
- [ ] `uv run arq app.workers.settings.WorkerSettings` starts the worker process without error
**Validation:**
- `uv run arq app.workers.settings.WorkerSettings` (starts, runs heartbeat, Ctrl+C to stop)

---

### P2.D6: Gateway Pydantic Models
**Files:** `app/gateway/models/common.py`, `app/gateway/models/health.py`, `app/gateway/models/__init__.py` (update)
**Depends on:** P2.D2
**Description:** API contract models for error responses and the health endpoint. `ErrorResponse` envelope per DD-1. `HealthResponse` with service status details. All models inherit from the project's `app.models.base.BaseModel` (which has `from_attributes=True`, `strict=True`).
**Requirements:**
- [ ] `ErrorDetail` model has `code: ErrorCode`, `message: str`, `details: dict[str, object]` (details defaults to `{}`)
- [ ] `ErrorResponse` model has `error: ErrorDetail`
- [ ] `HealthResponse` model has `status: str`, `version: str`, `services: dict[str, str]` (service names as keys, `"ok"` / `"unavailable"` as values)
- [ ] All models inherit from `app.models.base.BaseModel`
- [ ] Models importable from `app.gateway.models`
**Validation:**
- `uv run pyright app/gateway/models/`

---

### P2.D7: FastAPI App Factory + Health Route + DI + Middleware
**Files:** `app/gateway/main.py`, `app/gateway/deps.py`, `app/gateway/routes/health.py`, `app/gateway/routes/__init__.py` (update), `app/gateway/middleware/errors.py`, `app/gateway/middleware/logging.py`
**Depends on:** P2.D1, P2.D3, P2.D5, P2.D6
**Description:** FastAPI app factory with lifespan managing DB engine + Redis client lifecycle. Dependency injection functions for `AsyncSession` and `Redis` client. Health endpoint checking DB + Redis connectivity. Error handling middleware mapping `AutoBuilderError` subclasses to HTTP status codes and structured JSON error responses. CORS middleware for local development. Request logging middleware that logs method, path, status code, and duration for every request.
**Requirements:**
- [ ] `create_app() -> FastAPI` returns a configured FastAPI instance with lifespan, middleware, and routes
- [ ] Lifespan creates `AsyncEngine` and `Redis` client on startup, disposes on shutdown
- [ ] Lifespan verifies DB connectivity (`SELECT 1`) and Redis connectivity (`PING`) at startup — logs warning on failure but does not crash
- [ ] `GET /health` returns `200` with `HealthResponse` showing service statuses when DB and Redis are reachable
- [ ] `GET /health` returns `503` with degraded status if DB or Redis is unreachable
- [ ] `get_db_session()` dependency yields an `AsyncSession` from the engine's session factory
- [ ] `get_redis()` dependency returns the `Redis` client from `app.state`
- [ ] Error middleware catches `AutoBuilderError` subclasses and returns `ErrorResponse` JSON with correct HTTP status codes (404, 409, 422, 500)
- [ ] Unhandled exceptions return 500 with generic `INTERNAL_ERROR` response (no stack trace in response body)
- [ ] CORS middleware allows `localhost:*` and `127.0.0.1:*` origins
- [ ] Request logging middleware logs `{"method": "...", "path": "...", "status": ..., "duration_ms": ...}` for every request
- [ ] Application importable as `app.gateway.main:app` for uvicorn
**Validation:**
- `uv run uvicorn app.gateway.main:app --port 8000` then `curl -s localhost:8000/health | python -m json.tool`

---

### P2.D8: Production Dockerfile
**Files:** `Dockerfile`
**Depends on:** P2.D7
**Description:** Production Dockerfile using multi-stage build with `uv` for dependency installation. Single image runs either gateway or worker based on command argument. Used for production deployment and CI — not for daily development (dev runs locally via `uv run`).
**Requirements:**
- [ ] `Dockerfile` uses multi-stage build: Stage 1 installs deps with `uv`, Stage 2 copies venv + source
- [ ] Image runs gateway by default: `uvicorn app.gateway.main:app --host 0.0.0.0 --port 8000`
- [ ] Image can run worker via command override: `arq app.workers.settings.WorkerSettings`
- [ ] `docker build -t autobuilder .` succeeds
- [ ] `docker run --rm autobuilder` starts the gateway process
**Validation:**
- `docker build -t autobuilder . && docker run --rm --name ab-test -d autobuilder && sleep 2 && docker logs ab-test && docker stop ab-test`

---

### P2.D9: Test Suite
**Files:** `tests/conftest.py` (update), `tests/lib/__init__.py`, `tests/lib/test_logging.py`, `tests/lib/test_exceptions.py`, `tests/db/__init__.py`, `tests/db/test_engine.py`, `tests/gateway/test_health.py`, `tests/workers/__init__.py`, `tests/workers/test_tasks.py`
**Depends on:** P2.D7, P2.D5
**Description:** Test fixtures for async DB sessions (using a separate `autobuilder_test` PostgreSQL database for isolation), Redis mock, and FastAPI test client via `httpx.AsyncClient`. Unit tests for logging setup, exception hierarchy, DB engine/session creation, and health endpoint responses. Integration test demonstrating gateway enqueue → worker dequeue round-trip with `test_task`.
**Requirements:**
- [ ] `conftest.py` provides `async_session` fixture (async DB session for testing)
- [ ] `conftest.py` provides `test_client` fixture (`httpx.AsyncClient` with FastAPI test app)
- [ ] Logging tests verify `setup_logging()` configures JSON output and `get_logger()` returns correctly-named loggers
- [ ] Exception tests verify each subclass has correct `code: ErrorCode` and `message` attributes
- [ ] DB engine test verifies `create_engine()` returns `AsyncEngine` and sessions can execute queries
- [ ] Health endpoint test verifies `GET /health` returns 200 with correct `HealthResponse` schema
- [ ] Health endpoint test verifies 503 response when services are degraded
- [ ] Worker test verifies `test_task` processes payload and returns expected result dict
- [ ] Error middleware test verifies `AutoBuilderError` subclasses map to correct HTTP status codes
- [ ] All tests pass: `uv run pytest tests/ --ignore=tests/phase1`
- [ ] All quality gates pass: `uv run ruff check . && uv run pyright && uv run pytest`
**Validation:**
- `uv run pytest tests/ --ignore=tests/phase1 --cov=app -v`

---

## Build Order

```
Batch 1 (parallel): P2.D1, P2.D2
  D1: Logging + Exceptions — app/lib/logging.py, app/lib/exceptions.py
  D2: Enum additions — app/models/enums.py (update)

Batch 2 (parallel): P2.D3, P2.D5, P2.D6
  D3: Database engine + ORM models — app/db/engine.py, app/db/models.py (depends D1, D2)
  D5: Redis + ARQ workers — app/workers/settings.py, app/workers/tasks.py (depends D1)
  D6: Gateway Pydantic models — app/gateway/models/ (depends D2)

Batch 3 (parallel): P2.D4, P2.D7
  D4: Alembic migration — app/db/migrations/ (depends D3)
  D7: FastAPI app factory + routes + middleware — app/gateway/ (depends D1, D3, D5, D6)

Batch 4 (parallel): P2.D8, P2.D9
  D8: Production Dockerfile — Dockerfile (depends D7)
  D9: Test suite — tests/ (depends D7, D5)
```

## Completion Contract Traceability

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | `uv run uvicorn app.gateway.main:app` starts and serves `/health` | P2.D7 | `curl -s localhost:8000/health` returns 200 with JSON |
| 2 | `uv run arq app.workers.settings.WorkerSettings` starts worker | P2.D5 | Worker process starts, heartbeat cron fires every 60s |
| 3 | `uv run alembic upgrade head` creates tables | P2.D4 | Migration creates `specifications`, `workflows`, `deliverables` tables |
| 4 | Redis `PING` succeeds | P2.D7 (lifespan health check), P2.D5 (ARQ connects) | Health endpoint reports `redis: "ok"` |
| 5 | Gateway can enqueue a test job, worker can dequeue and process it | P2.D5, P2.D9 | Integration test in `tests/workers/test_tasks.py` |
| 6 | All quality gates pass (ruff, pyright, pytest) | P2.D9 | `uv run ruff check . && uv run pyright && uv run pytest` |

## Research Notes

### Existing Code Patterns (Phase 0/1 established)

**Enum pattern** — `enum.StrEnum` with values matching names:
```python
class WorkflowStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
```

**BaseModel** — all Pydantic models inherit from:
```python
class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)
```

**Settings** — singleton via `lru_cache`:
```python
from app.config import get_settings
settings = get_settings()  # settings.db_url, settings.redis_url, settings.log_level
```

**Alembic env.py** — already configured for async migrations with `asyncpg`. Only change needed: uncomment `from app.db.models import Base` and set `target_metadata = Base.metadata` (lines 20-22 have the commented-out import ready).

### ARQ WorkerSettings Pattern
```python
from arq import cron
from arq.connections import RedisSettings

class WorkerSettings:
    functions = [test_task]  # list of async job functions
    redis_settings = RedisSettings(host="localhost", port=6379)
    cron_jobs = [cron(heartbeat, second=0)]  # runs every minute at :00
    on_startup = startup  # async def startup(ctx: dict) -> None
    on_shutdown = shutdown  # async def shutdown(ctx: dict) -> None
```

Entry point: `uv run arq app.workers.settings.WorkerSettings`

ARQ `RedisSettings` can be constructed from a URL via:
```python
from urllib.parse import urlparse
parsed = urlparse(settings.redis_url)
redis_settings = RedisSettings(host=parsed.hostname or "localhost", port=parsed.port or 6379)
```

### FastAPI Lifespan Pattern
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    engine = create_engine(settings.db_url)
    redis = Redis.from_url(settings.redis_url)
    app.state.engine = engine
    app.state.redis = redis
    app.state.session_factory = async_session_factory(engine)
    yield
    # Shutdown
    await redis.aclose()
    await engine.dispose()
```

### SQLAlchemy 2.0 Async Patterns
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, MappedAsDataclass
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

Use `Mapped[T]` annotations for full pyright strict compatibility. Use `mapped_column()` for column configuration. Enum columns: `mapped_column(SqlEnum(MyEnum, native_enum=False))` to store as VARCHAR.

### Production Dockerfile Pattern (Multi-Stage with uv)
```dockerfile
# Stage 1: Build — install deps into venv
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Runtime — copy venv + source only
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
ENV PATH="/app/.venv/bin:$PATH"

# Default: run gateway. Override CMD for worker.
CMD ["uvicorn", "app.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Worker override: docker run autobuilder arq app.workers.settings.WorkerSettings
```

### Dev Workflow
```bash
docker compose up -d                            # postgres + redis (background)
uv run uvicorn app.gateway.main:app --reload    # gateway with hot-reload
uv run arq app.workers.settings.WorkerSettings  # worker (separate terminal)
uv run pytest                                   # tests
uv run ruff check . && uv run pyright           # lint + typecheck
```

### Key Import Paths
```python
# Database
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, Enum as SqlEnum, func
from sqlalchemy.dialects.postgresql import JSONB

# Redis
from redis.asyncio import Redis

# ARQ
from arq import cron
from arq.connections import RedisSettings, ArqRedis, create_pool

# FastAPI
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Testing
from httpx import AsyncClient, ASGITransport
```

### Test Database Strategy
For unit tests, use a separate test database (`autobuilder_test`) or override the engine with a test-scoped async engine. The `conftest.py` should create tables directly via `Base.metadata.create_all()` (wrapped in `run_sync`) rather than running Alembic migrations in tests. This keeps tests fast and isolated from migration state.

```python
@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder_test")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```
