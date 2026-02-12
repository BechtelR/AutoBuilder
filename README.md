# AutoBuilder

Autonomous agentic workflow system that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines.

## Overview

AutoBuilder takes a specification and runs it through pluggable workflows (auto-code, auto-design, auto-research) using LLM agents for judgment tasks and deterministic agents for guaranteed steps, producing verified output with optional human-in-the-loop intervention. The system exposes an API-first FastAPI gateway with out-of-process worker execution via ARQ and Redis.

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Docker](https://docs.docker.com/get-docker/) (PostgreSQL + Redis)

### Installation
```bash
# Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# Install dependencies
uv sync

# Apply database migrations
uv run alembic upgrade head
```

### Development
```bash
# Start the gateway server
uv run uvicorn app.gateway.main:app --reload

# Start an ARQ worker (separate terminal)
uv run arq app.workers.settings.WorkerSettings

# Use the CLI
uv run python -m app --help
```

## Features

- **Autonomous execution**: Runs from spec to verified output without constant human steering
- **Pluggable workflows**: auto-code, auto-design, auto-research -- each with own pipeline, agents, and quality gates
- **Multi-model routing**: LiteLLM routes tasks to optimal models (Claude, GPT, Gemini) by capability
- **Deterministic quality gates**: Linting, testing, and validation are guaranteed pipeline steps, not LLM suggestions
- **Real-time observability**: SSE event streaming from Redis Streams for live pipeline monitoring
- **Skill-based knowledge injection**: Progressive context loading -- agents get task-appropriate knowledge, not everything
- **Git worktree isolation**: True filesystem isolation for parallel execution

## Architecture

**Type**: Autonomous workflow orchestrator
**Engine**: Python 3.11+ / Google ADK / FastAPI / ARQ / Redis
**Dashboard**: React 19 + Vite (Phase 3)

```
Clients (CLI / Dashboard)
         |
    REST + SSE
         |
  FastAPI Gateway -----> SQLAlchemy DB
         |
    enqueue jobs
         |
    ARQ Workers -------> Redis Streams --> SSE / Webhooks / Audit
         |
    ADK Runner
    (internal)
```

See **[.dev/02-ARCHITECTURE.md](./.dev/02-ARCHITECTURE.md)** for detailed architecture.

## Project Structure

```
AutoBuilder/
├── app/                # Python engine (gateway, workers, agents, tools, workflows)
├── dashboard/          # React 19 + Vite SPA (Phase 3)
├── tests/              # Test suite (mirrors app/ structure)
├── docs/               # User-facing documentation (future)
├── .dev/               # Architecture docs and planning (not shipped)
├── AGENTS.md           # AI agent guidance
├── pyproject.toml      # Project config (uv, ruff, pyright)
└── alembic.ini         # Alembic configuration
```

See [.dev/03-STRUCTURE.md](./.dev/03-STRUCTURE.md) for the full project scaffold.

## Configuration

### Environment Variables
```bash
AUTOBUILDER_DB_URL=postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder  # Database
AUTOBUILDER_REDIS_URL=redis://localhost:6379                # Redis
AUTOBUILDER_LOG_LEVEL=INFO                                  # Log level
ANTHROPIC_API_KEY=                                          # Claude models
OPENAI_API_KEY=                                             # OpenAI models
GOOGLE_API_KEY=                                             # Gemini models
```

## Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run pyright
```

## Troubleshooting

### Common Issues

**Redis not running**: Gateway and workers require Redis to be running.
- **Solution**: `redis-server` or check your system service: `redis-cli ping`

**PostgreSQL not running**: Database requires Docker.
- **Solution**: `docker compose up -d`

**Migration errors**: Database schema out of sync.
- **Solution**: `uv run alembic upgrade head`

**Type errors**: Pyright strict mode catches everything.
- **Solution**: `uv run pyright` -- fix before committing

### Debug Commands
```bash
docker compose ps  # Check infrastructure
redis-cli ping                        # Verify Redis
uv run alembic current                # Check migration state
uv run adk web app/app.py             # ADK Dev UI (local debugging only)
```

## Contributing

See [AGENTS.md](./AGENTS.md) for development guidelines and coding standards.

## Documentation

- **[AGENTS.md](./AGENTS.md)**: Development workflow and coding standards
- **[.dev/02-ARCHITECTURE.md](./.dev/02-ARCHITECTURE.md)**: Technical architecture and design
- **[.dev/03-STRUCTURE.md](./.dev/03-STRUCTURE.md)**: Project scaffold (single source of truth)
- **[.dev/04-TECH_STACK.md](./.dev/04-TECH_STACK.md)**: Tech stack decisions and rationale
- **[.dev/01-ROADMAP.md](./.dev/01-ROADMAP.md)**: Project roadmap

---

*Part of the [AutoBuilder](./README.md) platform*
