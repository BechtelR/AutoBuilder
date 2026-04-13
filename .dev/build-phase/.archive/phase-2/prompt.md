# Context
Read these files before starting:
- `CLAUDE.md` — project rules (loaded automatically)
- `.dev/03-STRUCTURE.md` — file placement truth
- `.dev/build-phase/phase-2/spec.md` — full spec (read Overview, Design Decisions, and all Deliverables)
- `.dev/02-ARCHITECTURE.md` — sections 4 (Gateway Layer), 5 (Worker Architecture), 7 (Data Layer), 10 (Infrastructure)
- `.dev/04-TECH_STACK.md` — sections 1.5 (FastAPI), 1.6 (SQLAlchemy), 1.9 (ARQ), 3.1 (Redis), 3.2 (PostgreSQL)
- `app/config/settings.py` — existing config module
- `app/models/enums.py` — existing enums
- `app/models/base.py` — existing Pydantic base model
- `app/db/migrations/env.py` — existing Alembic env (needs update)

# Task
Implement **Phase 2: Gateway + Infrastructure**.

Build the production-grade FastAPI gateway, Redis infrastructure, database layer with initial schema, and ARQ workers. This phase creates the complete server-side foundation with structured logging, error handling, and dependency injection. No ADK code — that comes in Phase 3.

# Success Criteria
- [ ] `uv run uvicorn app.gateway.main:app` starts and serves `/health` (verify: `curl localhost:8000/health`)
- [ ] `uv run arq app.workers.settings.WorkerSettings` starts worker (verify: worker process starts, heartbeat cron fires)
- [ ] `uv run alembic upgrade head` creates tables (verify: tables exist in PostgreSQL)
- [ ] Redis `PING` succeeds (verify: health endpoint reports redis: "ok")
- [ ] Gateway can enqueue a test job, worker can dequeue and process it (verify: integration test passes)
- [ ] All quality gates pass (verify: `uv run ruff check . && uv run pyright && uv run pytest`)

# Scope
## Files to Create/Modify
- `app/lib/logging.py` — structured JSON logging with `app.*` hierarchy
- `app/lib/exceptions.py` — custom exception hierarchy (`AutoBuilderError` + subclasses)
- `app/lib/__init__.py` — exports
- `app/models/enums.py` — add `SpecificationStatus`, `ErrorCode` enums
- `app/models/__init__.py` — export new enums
- `app/db/engine.py` — `AsyncEngine` + `async_sessionmaker` factory
- `app/db/models.py` — SQLAlchemy mapped models: `Specification`, `Workflow`, `Deliverable`
- `app/db/__init__.py` — exports
- `app/db/migrations/env.py` — update to use `Base.metadata`
- `app/db/migrations/versions/` — generated initial migration
- `app/workers/settings.py` — ARQ `WorkerSettings` with Redis config, cron skeleton
- `app/workers/tasks.py` — `test_task` job function
- `app/workers/__init__.py` — exports
- `app/gateway/models/common.py` — `ErrorResponse`, `ErrorDetail` Pydantic models
- `app/gateway/models/health.py` — `HealthResponse` Pydantic model
- `app/gateway/models/__init__.py` — exports
- `app/gateway/main.py` — app factory with lifespan (DB engine + Redis client)
- `app/gateway/deps.py` — DI: `get_db_session()`, `get_redis()`
- `app/gateway/routes/health.py` — `GET /health` with DB + Redis checks
- `app/gateway/routes/__init__.py` — router aggregation
- `app/gateway/middleware/errors.py` — exception → HTTP response mapping
- `docker/Dockerfile` — production multi-stage image
- `docker/Dockerfile.dev` — dev image with hot-reload
- `docker/docker-compose.yml` — add gateway + worker services
- `tests/conftest.py` — async DB session, Redis, FastAPI test client fixtures
- `tests/lib/test_logging.py` — logging setup tests
- `tests/lib/test_exceptions.py` — exception hierarchy tests
- `tests/db/test_engine.py` — engine creation tests
- `tests/gateway/test_health.py` — health endpoint tests
- `tests/workers/test_tasks.py` — worker task + round-trip tests

## Out of Scope
- ADK integration (Phase 3)
- Agent definitions (Phase 5)
- Event system / Redis Streams (Phase 10)
- SSE endpoint (Phase 10)
- CLI (Phase 10)
- Workflow CRUD routes (Phase 7a+)
- Auth middleware (Phase 11)
- OpenTelemetry / Langfuse (Phase 11)

# Work Breakdown
Follow the Build Order from spec.md:

1. **Batch 1** — P2.D1 + P2.D2: Shared libraries (logging + exceptions in `app/lib/`) and enum additions (`app/models/enums.py`). These are leaf dependencies with no prerequisites.

2. **Batch 2** — P2.D3 + P2.D5 + P2.D6: Database engine + ORM models (`app/db/engine.py`, `app/db/models.py`), Redis/ARQ workers (`app/workers/`), gateway Pydantic models (`app/gateway/models/`). These depend on Batch 1.

3. **Batch 3** — P2.D4 + P2.D7: Alembic migration setup + initial migration, and FastAPI app factory with routes + middleware + DI. D4 depends on D3; D7 depends on D1, D3, D5, D6.

4. **Batch 4** — P2.D8: Docker app containers. Production Dockerfile (multi-stage, uv), dev Dockerfile, updated docker-compose with gateway + worker services.

5. **Batch 5** — P2.D9: Test suite. Fixtures in `conftest.py`, unit tests for lib/db/gateway/workers, integration test for gateway→worker round-trip.

6. Run `uv run ruff check app/ tests/ && uv run pyright app/ && uv run pytest` — fix all errors.

# Constraints
- **Async everywhere**: All I/O operations must be async (SQLAlchemy async, redis.asyncio, httpx async)
- **No `Any` type**: Use explicit types, `TypedDict`, or `object`. Exceptions per `common-errors.md` allowed list only.
- **Pydantic v2 at boundaries**: All API request/response models use Pydantic. DB models use SQLAlchemy `Mapped[]`.
- **Enum values = names**: `RUNNING = "RUNNING"` not `RUNNING = "running"` (see common-errors.md)
- **Domain enums in `app/models/enums.py`**: Never define enums inline
- **`datetime.now(timezone.utc)`**: Never `utcnow()`
- **Structured logging only**: Use `logger.debug/info/warning/error`, never `print()`. No debug logging in committed code.
- **FastAPI lifespan pattern**: Use `lifespan` context manager, not deprecated `on_startup`/`on_shutdown`
- **Single database**: All models in `app/db/models.py`, all accessed via gateway or workers
- **Error response envelope**: `{"error": {"code": "...", "message": "...", "details": {}}}` — see DD-1 in spec
- **UUID primary keys**: All tables use UUID PKs with server-generated defaults
- **Follow existing patterns**: See `app/config/settings.py` for Pydantic Settings pattern, `app/models/enums.py` for enum style

# Verification
Before marking complete:
1. All success criteria checked
2. `uv run ruff check .` passes
3. `uv run pyright` passes (strict mode)
4. `uv run pytest` passes
5. `docker compose -f docker/docker-compose.yml up -d` starts all services
6. `curl localhost:8000/health` returns 200 with DB + Redis status
