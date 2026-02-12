# AutoBuilder Tech Stack

## Overview

AutoBuilder is a Python-first autonomous agentic workflow system with a TypeScript web dashboard. The core engine handles all orchestration, agent coordination, state management, and tool execution in Python. While auto-code is the first workflow, the system is designed to support any workflow type (auto-design, auto-research, auto-market, etc.). TypeScript is used exclusively for the dashboard/web UI layer, which is a pure consumer of the engine's API.

This document is the definitive tech stack reference. Every technology choice is listed with rationale.

---

## 1. Python Engine

### 1.1 Python Runtime: 3.11+

**Choice**: Python 3.11+ with asyncio

**Rationale**:
- Agent ecosystem is Python-first; Google ADK, Pydantic AI, LangChain, CrewAI are all Python-native
- Strong async support via `asyncio` for concurrent agent execution
- Google ADK requires Python 3.11+
- Type hints + pyright provide TypeScript-like type safety

**Alternatives Considered**:

| Language | Why Not |
|----------|---------|
| TypeScript/Node | Weaker agent framework ecosystem; ADK is Python-only |
| Go | Smaller agent ecosystem, more boilerplate, no ADK support |
| Rust | Overkill for orchestration, no ADK support |

### 1.2 Core Framework: Google ADK

**Choice**: Google Agent Development Kit (ADK) v1.14.0+

**Rationale**: AutoBuilder needs two fundamentally different types of tool execution: LLM-discretionary ("use search if you need info") and deterministic ("run validator, run tests, check constraints"). ADK is the only evaluated framework where deterministic tools are first-class citizens via `CustomAgent` (inheriting `BaseAgent`). They participate in the same state system as LLM agents, appear in the same event stream for observability, cannot be skipped by LLM judgment, and compose naturally with LLM agents in Sequential/Parallel/Loop workflows.

AutoBuilder is fundamentally an orchestration problem where LLM agents are one component alongside deterministic tooling. This applies whether the output is code, research, design assets, or marketing content. ADK treats this as the core design principle.

ADK is used behind an **anti-corruption layer** to isolate the rest of the system from framework-specific APIs, ensuring the framework can be replaced or upgraded without cascading changes.

**Alternatives Evaluated**:

| Framework | Why Not |
|-----------|---------|
| Pydantic AI | All tools are LLM-discretionary; deterministic steps exist in a "shadow world" outside the framework, invisible to tracing and state management |
| Claude Agent SDK | Single-agent harness, not a workflow orchestrator; Claude-only, TypeScript-only |
| Custom framework | Both ADK and PAI handle multi-model natively; building our own provider abstraction is unnecessary |

**ADK Primitives Used**:

| Primitive | Role in AutoBuilder |
|-----------|-------------------|
| `LlmAgent` | Planning, execution, reviewing -- probabilistic steps |
| `CustomAgent` (BaseAgent) | Validators, test runners, formatters, skill loader, outer loop orchestrator -- deterministic steps (workflow-specific) |
| `SequentialAgent` | Inner deliverable pipeline (plan, execute, validate, verify, review) |
| `ParallelAgent` | Concurrent deliverable execution within a batch |
| `LoopAgent` | Review/fix cycles with max iteration bounds |
| `Session State` | Inter-agent communication (4 scopes: session/user/app/temp) |
| `Event Stream` | Unified observability for all agent types |
| `FunctionTool` | Wrap Python functions as LLM-callable tools (auto-schema from type hints) |
| `InstructionProvider` | Dynamic context/knowledge loading per invocation |
| `before_model_callback` | Context injection, token budget monitoring |
| `BaseToolset` | Dynamic tool selection based on deliverable type |
| `DatabaseSessionService` | State persistence to PostgreSQL |

**Acknowledged Tradeoffs**:

| Weakness | Severity | Mitigation |
|----------|----------|------------|
| Gemini-first bias | Medium | LiteLLM wrapper for Claude; test thoroughly in prototyping |
| No Temporal-style durability | Medium-Low | Native Resume feature (v1.16+) covers most crash scenarios; evaluate Temporal only if insufficient |
| Google ecosystem gravity | Medium | Discipline: local PostgreSQL only; skip all Vertex AI services; anti-corruption layer |
| Documentation accuracy issues | Low | Test everything empirically |
| Type safety less emphasized | Low | Use Pydantic models for structured outputs within ADK agents |
| No context-window usage awareness | Low | `before_model_callback` token-count implementation (~50 lines) |

### 1.3 LLM Integration: LiteLLM

**Choice**: LiteLLM for multi-model support

**Rationale**: AutoBuilder routes different tasks to different LLM providers based on capability, cost, and speed. LiteLLM provides a unified interface across providers (Anthropic, OpenAI, Google, etc.) without requiring separate SDK integrations for each. It also handles provider fallback chains -- if a primary model is unavailable or rate-limited, the system falls back gracefully.

**Why not direct SDKs**: Using the Anthropic SDK directly would lock all tasks to a single provider. Using multiple SDKs (anthropic, openai, google-generativeai) would require maintaining separate integration code for each. LiteLLM provides a single interface that ADK consumes via its LiteLLM wrapper class.

### 1.4 Primary LLM: Anthropic Claude

**Choice**: Anthropic Claude as the primary model family

**Rationale**: Best-in-class for code generation, instruction following, and agentic workflows. Large context window (200K tokens) supports the long autonomous runs AutoBuilder requires.

**Model Tiers and Routing**:

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| Planning | `anthropic/claude-opus-4-6` | Complex reasoning and decomposition |
| Implementation (standard) | `anthropic/claude-sonnet-4-5-20250929` | Strong execution, good cost/quality balance |
| Implementation (complex) | `anthropic/claude-opus-4-6` | Maximum capability for difficult tasks |
| Review | `anthropic/claude-sonnet-4-5-20250929` | Good judgment, reasonable cost |
| Classification / summarization | `anthropic/claude-haiku-4-5-20251001` | Fast, cheap, sufficient for simple tasks |
| Context compression (summarizer) | `anthropic/claude-haiku-4-5-20251001` | Fast summaries without burning expensive tokens |

**Routing Configuration**:

```yaml
routing_rules:
  - task_type: implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: implementation
    complexity: complex
    model: "anthropic/claude-opus-4-6"
  - task_type: planning
    model: "anthropic/claude-opus-4-6"
  - task_type: review
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - task_type: summarization
    model: "anthropic/claude-haiku-4-5-20251001"

fallback_chains:
  anthropic/claude-opus-4-6: ["anthropic/claude-sonnet-4-5-20250929"]
  anthropic/claude-sonnet-4-5-20250929: ["anthropic/claude-haiku-4-5-20251001"]
```

Phase 1 implements static routing (task_type to model lookup table). Adaptive routing with cost tracking and latency monitoring deferred to Phase 2.

### 1.5 Gateway API: FastAPI

**Choice**: FastAPI for the gateway API server

**Rationale**: FastAPI provides a high-performance async Python web framework that natively supports REST endpoints and SSE (Server-Sent Events) streaming. It auto-generates an OpenAPI spec from Pydantic models, which is the foundation of the end-to-end type safety chain (see Section 6). FastAPI is the gateway between the dashboard and the engine -- all commands, queries, and real-time event streams flow through it.

**Key capabilities**:
- REST endpoints for commands and queries
- SSE endpoints for real-time agent event streaming
- Auto-generated OpenAPI specification from Pydantic type annotations
- Native async/await support matching the rest of the engine
- Dependency injection for session management, auth, etc.

### 1.6 ORM: SQLAlchemy 2.0 Async

**Choice**: SQLAlchemy 2.0 with async engine

**Rationale**: A single database backs all persistence in AutoBuilder -- session state, workflow metadata, task queues, and any future domain tables. SQLAlchemy 2.0 provides a mature async ORM with full type annotation support. Its declarative model definitions feed directly into Pydantic models, maintaining the type safety chain.

**Key points**:
- Single database for all persistence (no split databases; see Architecture Decisions)
- Async engine via `asyncpg`
- Declarative models as the database source of truth

### 1.7 Database Migrations: Alembic

**Choice**: Alembic for schema migrations

**Rationale**: Alembic is the standard migration tool for SQLAlchemy. It provides auto-generated migrations from model changes, versioned migration history, and both upgrade and downgrade paths. Required for any production deployment where schema evolves over time.

### 1.8 Data Validation: Pydantic

**Choice**: Pydantic v2 for data validation, API models, and structured outputs

**Rationale**: Pydantic is the **single source of truth for types** across the entire system. It serves multiple roles:
- Structured output schemas for LLM agents (ADK `output_schema`)
- Request/response models for FastAPI endpoints
- Settings management via `pydantic-settings`
- Configuration validation
- The bridge between SQLAlchemy models and the API layer

The type safety chain flows: `SQLAlchemy model -> Pydantic model -> OpenAPI spec -> Generated TS types`.

Shared domain definitions live in `app/models/`:
- `enums.py` -- domain enums used across all layers (agent types, workflow states, deliverable statuses)
- `constants.py` -- shared constants (default values, limits, configuration keys)
- `base.py` -- base Pydantic models inherited by all domain-specific models

### 1.9 Task Queue: ARQ

**Choice**: ARQ (async Redis queue) for background task execution

**Rationale**: ADK is 100% async Python. Celery is sync-first with poor asyncio bridging -- it requires thread pool executors and `sync_to_async` wrappers that add complexity and defeat the purpose of native async. ARQ runs async tasks natively on the same event loop, includes built-in cron scheduling, and depends only on Redis.

**Key capabilities**:
- Native asyncio task execution (no sync/async bridging)
- Built-in cron scheduler (replaces need for a separate scheduler like APScheduler)
- Single Redis dependency (shared with event bus and cache)
- Job result storage and retry logic

**Decision: ARQ over Celery**:

| Concern | Celery | ARQ |
|---------|--------|-----|
| Async support | Sync-first, requires `sync_to_async` wrappers | Native asyncio |
| Dependencies | RabbitMQ or Redis + multiple packages | Redis only |
| Cron | Celery Beat (separate process) | Built-in, same worker |
| Complexity | Heavy, many configuration options | Lightweight, minimal config |
| Ecosystem maturity | Battle-tested at scale | Smaller community, sufficient for AutoBuilder's scale |

### 1.10 Async HTTP Client: httpx

**Choice**: httpx for outbound HTTP calls

**Rationale**: httpx provides a modern async HTTP client for webhook dispatch, external API calls, and any outbound HTTP communication. It supports async/await natively, connection pooling, and has an API similar to `requests` for familiarity.

### 1.11 CLI Framework: typer

**Choice**: typer for the command-line interface

**Rationale**: The CLI is the primary user interface for Phase 1 (web dashboard is Phase 3). typer provides a modern, type-hint-driven CLI framework built on top of click. It auto-generates help text from type annotations and supports subcommands, options, and arguments with minimal boilerplate.

**CLI requirements**:
- Start/stop autonomous runs
- Specify workflow + spec file
- Configure model routing
- Monitor progress
- Human-in-the-loop intervention points

### 1.12 Memory: PostgreSQL tsvector + pgvector

**Choice**: Custom `BaseMemoryService` implementation backed by PostgreSQL tsvector (full-text) and pgvector (semantic search)

**Rationale**: ADK's `MemoryService` interface (`BaseMemoryService`) has two methods: `add_session_to_memory()` and `search_memory()`. The only production-ready built-in implementation is `VertexAiMemoryBankService` (GCP-only, which we are avoiding). `InMemoryMemoryService` is keyword-only and non-persistent.

AutoBuilder needs local, persistent, searchable cross-session memory so that deliverable 47 can know what patterns deliverables 1-10 established. PostgreSQL is already the database. `tsvector` provides full-text search built into PostgreSQL. `pgvector` provides vector search as a column type -- no separate service needed. Single database principle maintained.

**Implementation scope**: ~200-500 lines for `PostgresMemoryService` implementing `BaseMemoryService`. Uses tsvector for keyword search, pgvector available for semantic search when needed.

---

## 2. Dashboard (TypeScript)

### 2.1 UI Framework: React 19

**Choice**: React 19

**Rationale**: Industry-standard component library with the largest ecosystem. React 19 brings server components and improved concurrent rendering. The dashboard is a pure consumer of the FastAPI gateway -- it has no database, no server-side logic beyond what the API provides.

### 2.2 Build Tool: Vite

**Choice**: Vite

**Rationale**: Fast dev server with HMR (Hot Module Replacement), optimized production builds via Rollup, and first-class TypeScript support. The standard choice for modern React applications.

### 2.3 Server State: TanStack Query

**Choice**: TanStack Query (React Query) for server state management

**Rationale**: TanStack Query handles all server-derived state -- API data fetching, caching, background refetching, pagination, and cache invalidation. It eliminates the need to hand-roll cache management in a client-side store.

**Decision: TanStack Query + Zustand over Zustand alone**: Without TanStack Query, all API caching, refetching, stale-while-revalidate, and invalidation logic would need to be hand-built in Zustand. TanStack Query handles server state as a dedicated concern. Zustand handles client-only state. Clear separation of responsibilities.

### 2.4 Client State: Zustand

**Choice**: Zustand for client-side state management

**Rationale**: Lightweight, minimal-boilerplate state management for UI-only state: theme preferences, sidebar collapse state, SSE stream buffer, modal visibility, and other ephemeral client concerns. Does not duplicate server state -- that belongs to TanStack Query.

### 2.5 Styling: Tailwind v4

**Choice**: Tailwind CSS v4

**Rationale**: Utility-first CSS framework with CSS-first `@theme` configuration in v4. Provides a 100% tokenized design system where all colors, spacing, typography, and sizing are defined as design tokens. No custom CSS files, no naming conventions to enforce -- the design system is the utility classes.

### 2.6 API Client Codegen: hey-api

**Choice**: hey-api for OpenAPI to TypeScript client generation

**Rationale**: hey-api generates typed TypeScript clients and TanStack Query hooks directly from the FastAPI-generated OpenAPI specification. This is the final link in the type safety chain: changes to Pydantic models automatically propagate to TypeScript types at build time.

**Decision: hey-api over orval**:

| Concern | orval | hey-api |
|---------|-------|---------|
| Output quality | Verbose, sometimes messy | Clean, readable generated code |
| TanStack Query v5 | Supported but integration less polished | First-class TanStack Query v5 integration |
| HTTP client dependency | Requires axios | Standalone clients, no axios dependency |
| Maintenance | Active | Active |

---

## 3. Infrastructure

### 3.1 Redis

**Choice**: Redis (single instance) serving multiple roles

**Roles**:
- **Task queue backend** for ARQ workers
- **Event bus** via Redis Streams (persistent, replayable event distribution)
- **Cron store** for ARQ's built-in cron scheduler
- **Cache** for ephemeral data (rate limit counters, session caches, etc.)

**Decision: Redis Streams over Pub/Sub**:

| Concern | Redis Pub/Sub | Redis Streams |
|---------|---------------|---------------|
| Persistence | Fire-and-forget, messages lost if no subscriber | Persistent, messages stored until trimmed |
| Replay | No replay capability | Full replay from any position via message IDs |
| SSE reconnection | Lost events during disconnect | Client reconnects and replays from last known ID |
| Consumer groups | Not supported | Multiple independent consumers on same stream |
| Backpressure | None | Consumer groups track acknowledgment |

Redis Streams enable reliable SSE: when a dashboard client disconnects and reconnects, it provides its last received event ID and the server replays all missed events from that position. No data loss during network interruptions.

### 3.2 Database: PostgreSQL + pgvector

**Choice**: PostgreSQL for all environments (dev via Docker, production native)

**Rationale**: Gateway + ARQ workers are separate processes. SQLite serializes writes -- concurrent workers would hit SQLITE_BUSY. PostgreSQL handles concurrent access natively. pgvector provides vector search without a separate service. Docker makes local PostgreSQL trivial -- and Redis already requires Docker/install.

**Single database** -- the gateway API is THE system. The dashboard is a pure consumer via the API. There is no reason for separate databases per concern. All persistence (sessions, workflow state, task results, metadata) lives in one database accessed through SQLAlchemy.

**Async driver**: `asyncpg`

**Note**: Docker required for local dev (PostgreSQL + Redis)

### 3.3 Observability: OpenTelemetry + Langfuse

**OpenTelemetry**: ADK has native OpenTelemetry integration for distributed tracing. All agent executions, tool calls, and state transitions are traced automatically.

**Langfuse** (Phase 2): Open-source, self-hosted LLM observability platform. Provides token usage tracking, cost monitoring, prompt versioning, and evaluation metrics specific to LLM workloads. Complements OpenTelemetry's general tracing with LLM-specific insights.

---

## 4. Dev Tools

| Tool | Purpose | Rationale |
|------|---------|-----------|
| `uv` | Package management | Fast Rust-based package manager; drop-in pip + venv replacement; deterministic `uv.lock` |
| `ruff` | Linting + formatting | Replaces black, isort, flake8 in a single Rust-based tool; fast |
| `pyright` | Type checking (strict mode) | TypeScript-like type safety for Python; catches bugs before runtime |
| `pytest` | Testing | Industry standard; excellent plugin ecosystem |
| `pytest-asyncio` | Async test support | Required for testing ADK async agent execution |
| `pre-commit` | Git hooks | Enforces lint/type/format checks before commits |

---

## 5. Transport Decisions

### REST for Commands and Queries

Standard HTTP REST endpoints for all command (write) and query (read) operations. Battle-tested, zero infrastructure tax, excellent tooling support, universal client compatibility.

### SSE for Real-Time Streaming

Server-Sent Events for real-time agent event streaming (agent progress, log output, state changes). SSE is browser-native, HTTP-native, and unidirectional (server to client) -- which matches the use case exactly. The dashboard observes; it does not send real-time data upstream.

SSE reconnection is backed by Redis Streams: clients provide their last event ID on reconnect, and the server replays missed events.

### What We Are NOT Using

| Transport | Status | Rationale |
|-----------|--------|-----------|
| GraphQL | Not using | Complexity doesn't pay when you control both client and server. REST + codegen provides equivalent type safety with less overhead. |
| gRPC (at gateway) | Not using | Browser-incompatible without grpc-web proxy. Revisit only if internal service mesh emerges later. |
| WebSockets | Not using | Bidirectional not needed; SSE is simpler for unidirectional server-to-client streaming. |
| WebRTC | Reserved | Future consideration for voice communication features only. |

---

## 6. Type Safety Chain

The end-to-end type safety chain ensures that a type change in a Python model automatically propagates to the TypeScript dashboard at build time, with no manual synchronization:

```
SQLAlchemy model -> Pydantic model -> OpenAPI spec -> Generated TS types + hooks
```

**How it works**:
1. **SQLAlchemy models** define database schema
2. **Pydantic models** are the single source of truth for API types, derived from / aligned with SQLAlchemy models
3. **FastAPI** auto-generates an **OpenAPI specification** from Pydantic model annotations
4. **hey-api** generates typed **TypeScript clients** and **TanStack Query hooks** from the OpenAPI spec at dashboard build time
5. **Build fails if types drift** -- the generated client won't compile if the API contract changes without updating consumers

**Key architecture decisions supporting type safety**:
- **Pydantic is the single source of truth** -- not SQLAlchemy, not TypeScript interfaces
- **No Drizzle/Prisma needed** -- the dashboard has no database; type safety comes from OpenAPI codegen
- **Single database** -- one set of models, one API, one OpenAPI spec

---

## 7. Architecture Decisions Summary

Key decisions with rationale, collected for reference:

| Decision | Choice | Over | Rationale |
|----------|--------|------|-----------|
| Task queue | ARQ | Celery | ADK is 100% async; Celery is sync-first with poor asyncio bridging; ARQ runs natively async with built-in cron and single Redis dependency |
| Event distribution | Redis Streams | Redis Pub/Sub | Streams are persistent and replayable; SSE reconnection replays missed events; consumer groups allow multiple independent consumers |
| API client codegen | hey-api | orval | Cleaner output, better TanStack Query v5 integration, standalone clients without axios dependency |
| Server state | TanStack Query + Zustand | Zustand alone | TanStack Query handles server state (caching, refetching, invalidation); Zustand handles client-only state; avoids hand-rolling cache management |
| Database topology | Single database | Split databases | Gateway API is THE system; dashboard is a pure consumer; no reason for interfaces to have their own persistence |
| Dashboard ORM | None (codegen) | Drizzle / Prisma | Dashboard has no database; type safety comes from OpenAPI codegen, not an ORM |
| ADK integration | Anti-corruption layer | Direct coupling | Isolates framework-specific APIs; enables framework replacement without cascading changes |
| Database engine | PostgreSQL + pgvector | SQLite (dev) + PostgreSQL (prod) | Concurrent worker access, vector search built-in, eliminates dev/prod divergence, Docker already required for Redis |

---

## 8. Dependencies

### pyproject.toml Skeleton

```toml
[project]
name = "autobuilder"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Core Framework
    "google-adk>=1.14.0",

    # LLM Integration
    "litellm>=1.0.0",

    # API Server
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",

    # ORM & Database
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pgvector>=0.3.0",

    # Task Queue
    "arq>=0.26.0",

    # Data Validation & Settings
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",

    # HTTP Client
    "httpx>=0.27.0",

    # CLI
    "typer>=0.12.0",

    # Utilities
    "pyyaml>=6.0.0",

    # Redis
    "redis[hiredis]>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.4.0",
    "pyright>=1.1.0",
    "pre-commit>=3.5.0",
]

observability = [
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "langfuse>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "SIM", "TCH"]

[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "strict"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Key Dependency Rationale

| Dependency | Why Included |
|------------|-------------|
| `google-adk` | Core framework: agent composition, state management, event stream, session services |
| `litellm` | Multi-model LLM routing without separate SDKs per provider |
| `fastapi` + `uvicorn` | Gateway API server: REST + SSE, OpenAPI spec generation |
| `sqlalchemy[asyncio]` | Async ORM for all database persistence |
| `alembic` | Database schema migrations |
| `asyncpg` | Async PostgreSQL driver for all environments |
| `pgvector` | Vector search extension for semantic memory |
| `arq` | Async task queue with built-in cron |
| `redis[hiredis]` | Task queue backend, event bus (Streams), cache |
| `pydantic` | Single source of truth for types; structured outputs; validation; settings |
| `httpx` | Async HTTP client for webhooks and external API calls |
| `typer` | CLI framework for Phase 1 user interface |
| `pyyaml` | Skill frontmatter parsing; workflow manifest parsing; routing config |

### What Is NOT Included

| Dependency | Why Excluded |
|------------|-------------|
| `anthropic` SDK | LiteLLM handles Anthropic API calls; direct SDK adds redundancy |
| `openai` SDK | Same -- LiteLLM abstracts provider SDKs |
| `langchain` | ADK provides its own composition primitives; LangChain would be redundant |
| `chromadb` / `faiss` | Separate vector database; pgvector provides vector search in PostgreSQL; no separate service needed |
| `sqlite` / `aiosqlite` | PostgreSQL used for all environments; eliminates dev/prod divergence |
| `celery` | Sync-first; poor asyncio bridging; ARQ is the async-native choice |
| Any GCP SDK | Avoiding Google ecosystem gravity; local PostgreSQL only |
| `drizzle` / `prisma` | Dashboard has no database; type safety from OpenAPI codegen |
| `axios` | hey-api generates standalone clients without axios dependency |

---

*Document Version: 2.0*
*Last Updated: 2026-02-11*
