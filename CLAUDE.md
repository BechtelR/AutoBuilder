# AGENTS.md - AutoBuilder

## Preferences
- Brief and concise explanations; time is precious
- Think outside the box, create innovation
- Pragmatic simplicity over architectural complexity
- Question assumptions -- challenge requirements if they don't make sense
- Your role is the expert engineer with the voice of Truth
- System security and privacy are non-negotiable
- Performance matters -- measure with evidence, don't guess
- Developer experience should be delightful

## Tech Stack
- Language: Python 3.11+, asyncio throughout
- Framework: Google ADK (behind anti-corruption layer)
- Gateway: FastAPI (REST + SSE)
- ORM: SQLAlchemy 2.0 async + Alembic migrations
- Task Queue: ARQ (Redis-backed, native asyncio)
- Event Bus: Redis Streams (persistent, replayable)
- Infrastructure: Redis (queue + events + cron + cache)
- Multi-model: LiteLLM (provider-agnostic routing)
- CLI: typer (pure API client)
- Dashboard: React 19 + Vite + TanStack Query + Zustand + Tailwind v4
- Type Codegen: hey-api (OpenAPI to TypeScript)
- Observability: OpenTelemetry + Langfuse (Phase 2)
- Package Manager: uv

## Workspace Commands
```bash
# Dev (hot-reload — docker-compose.override.yml auto-loaded)
docker compose up -d                  # All services, gateway reloads on app/ changes
docker compose run --rm migrate       # Apply migrations (first time / schema changes)

# Prod (-f skips override: no hot-reload, no bind mounts)
docker compose -f docker-compose.yml up -d --build

# Development (local gateway + worker, Docker infra)
docker compose up -d postgres redis   # Infrastructure only
uv run uvicorn app.gateway.main:app --reload  # Dev server (hot-reload)
uv run arq app.workers.settings.WorkerSettings  # ARQ worker

# Database
uv run alembic upgrade head           # Apply migrations (local dev)
uv run alembic revision --autogenerate -m "description"  # New migration

# Testing & Quality
uv run pytest                         # Run tests
uv run pytest --cov=app               # With coverage
uv run ruff check .                   # Lint
uv run ruff format .                  # Format
uv run pyright                        # Type check (strict)

# CLI
uv run python -m app --help           # CLI entry point

# Dashboard (from dashboard/)
npm run generate                      # Regen TS client from OpenAPI
npm run dev                           # Vite dev server
```

## Architecture Rules
- API-first: gateway owns all routes/models; ADK is an internal engine, never exposed
- Out-of-process execution: gateway enqueues jobs, ARQ workers execute pipelines
- Single database: all persistence through gateway API, no direct DB access from clients
- Type safety chain: SQLAlchemy -> Pydantic -> OpenAPI -> generated TS types
- Event-driven: Redis Streams for all event distribution (SSE, webhooks, audit)
- Generic > Specific: registries and pluggable workflows, not hardcoded lists
- Single source of truth for all configuration
- Async by default for all I/O operations
- Max ~500 per module; split if larger

## Code Style
- Python strict typing: full type hints, pyright strict, no `Any`
- Pydantic `BaseModel` for API contracts and LLM structured outputs
- SQLAlchemy mapped classes for DB models
- `Protocol` for interfaces with multiple implementations
- Prefer composition over deep inheritance
- Line length: 100 (ruff)
- Import order: stdlib -> third-party -> local (ruff enforced)
- Naming: `snake_case` functions/files, `PascalCase` classes, `SCREAMING_SNAKE` constants

## Project Structure

See [.dev/03-STRUCTURE.md](./.dev/03-STRUCTURE.md) for the full project scaffold.

## Project Architecture
API-first gateway (FastAPI) enqueues work to ARQ workers via Redis. Workers execute ADK pipelines behind an anti-corruption layer and publish events to Redis Streams. SSE endpoints, webhook dispatchers, and audit loggers consume the stream. Single database (SQLAlchemy 2.0 async) stores all state. CLI and dashboard are pure API consumers. See **[.dev/02-ARCHITECTURE.md](./.dev/02-ARCHITECTURE.md)** for full architecture.

## Critical DOs
- Understand the design or problem BEFORE writing code
- Ask clarifying questions when requirements are ambiguous
- Fail fast and fail loudly with meaningful error messages
- Type-check early and often -- most common build error
- Mock external services in unit tests (LLM calls, Redis, filesystem)
- Use Pydantic models at all API boundaries
- Publish events to Redis Streams for all significant state changes

## Critical DON'Ts
- NEVER MAKE UP NON-EXISTENT FILES, FACTS OR REFERENCES
- NEVER IGNORE EXISTING ERRORS, FIX IMMEDIATELY
- NEVER DEFER ACTIONS OR WORK ITEMS, except in the case of proven blocking dependencies
- Don't use retrospective language, eg. `old version was ABC design, but now it's XYZ design`
- Don't expose ADK types through the gateway API
- Don't bypass type checking with `Any`
- Don't commit secrets or API keys
- Don't access the database directly from CLI or dashboard -- use the gateway API
- Don't run tools in the gateway process -- tools execute in worker context
- Don't assume dependencies already exist -- check imports

## Security
- **Input Validation**: Validate all inputs at gateway boundaries via Pydantic
- **No Secrets in Code**: Use environment variables, never hardcode
- **Secure Defaults**: Fail-safe patterns, explicit security configurations
- **Tool Isolation**: Tools run in worker processes with scoped filesystem access

## Quick Troubleshooting
```bash
redis-cli ping                        # Verify Redis is running
uv run alembic current                # Check migration state
uv run ruff check . --fix             # Auto-fix lint issues
uv run pyright                        # Identify type errors
```

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTOBUILDER_DB_URL` | `postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder` | Database connection |
| `AUTOBUILDER_REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `AUTOBUILDER_LOG_LEVEL` | `INFO` | Log verbosity |
| `AUTOBUILDER_DEFAULT_*_MODEL` | See `.env` | LLM routing: `CODE`, `PLAN`, `REVIEW`, `FAST` |
| `AUTOBUILDER_SEARCH_PROVIDER` | `tavily` | Web search provider (`tavily` or `brave`) |
| `AUTOBUILDER_MAX_CONCURRENCY` | `6` | Max parallel deliverable pipelines (Phase 8a) |
| `AUTOBUILDER_SKILLS_DIR` | `./skills` | Project-local skills directory (Phase 6) |
| `AUTOBUILDER_WORKFLOWS_DIR` | `~/.autobuilder/workflows` | User-level workflows directory (Phase 7a) |
| `ANTHROPIC_API_KEY` | -- | Claude models (primary) |
| `OPENAI_API_KEY` | -- | OpenAI models (fallback) |
| `GOOGLE_API_KEY` | -- | Gemini models (fallback) |

See [.dev/06-PROVIDERS.md](./.dev/06-PROVIDERS.md) for full model reference (strings, pricing, fallback chains).

## Knowledge Base
Before writing ADK code, must read `.dev/.knowledge/adk/README.md` → category file → `ERRATA.md`. Never guess ADK APIs.

## Related Documentation
- **[README.md](./README.md)**: Setup and introduction
- **[.dev/02-ARCHITECTURE.md](./.dev/02-ARCHITECTURE.md)**: Technical architecture and design
- **[.dev/03-STRUCTURE.md](./.dev/03-STRUCTURE.md)**: Project scaffold (single source of truth)
- **[.dev/04-TECH_STACK.md](./.dev/04-TECH_STACK.md)**: Tech stack decisions and rationale
- **[.dev/08-ROADMAP.md](./.dev/08-ROADMAP.md)**: Project roadmap
