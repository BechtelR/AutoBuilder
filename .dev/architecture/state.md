[← Architecture Overview](../02-ARCHITECTURE.md)

# AutoBuilder State & Memory Architecture

## Overview

AutoBuilder uses ADK's three-tier context management system -- Session, State, and Memory -- to provide six levels of progressively broader context to agents. All persistence flows through a single database (SQLAlchemy 2.0 async + Alembic), with Redis providing a caching layer and event distribution. This document covers what ADK provides natively, where the gaps are, and how AutoBuilder fills them.

---

## 1. What ADK Provides Natively

### 1.1 Session

A single conversation thread. Contains a chronological `Event` history and a `state` dict. Identified by the tuple `(app_name, user_id, session_id)`. Managed by a `SessionService`.

Every agent (LLM or deterministic) emits `Event` objects into the session's event stream. ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt.

### 1.2 State (4-Scope System)

Key-value scratchpad within a session, with four prefix-scoped tiers:

| Prefix | Scope | Lifetime | AutoBuilder Use |
|--------|-------|----------|----------------|
| *(none)* | This session only | Persists with session (via `DatabaseSessionService`) | Current batch, deliverable statuses, loaded skills, validation/verification results, intermediate pipeline data |
| `user:` | All sessions for this user (within same app) | Persistent | Director personality, user preferences, model selections, intervention settings, notification preferences |
| `app:` | All users and sessions for this app | Persistent | Skill index, workflow registry, shared templates, runtime agent coordination |
| `temp:` | Current invocation only | Discarded after invocation completes | Intermediate LLM outputs, scratch calculations, data passed between tool calls within one invocation |

Key characteristics:

- **Event-sourced updates.** State changes happen via `Event.actions.state_delta` -- never direct mutation. All state changes are auditable in the event stream.
- **Serializable values only.** Strings, numbers, booleans, simple lists/dicts. No complex objects.
- **Template injection.** State values are injectable into agent instructions via `{key}` templating: `"Implement the deliverable: {current_deliverable_spec}"` auto-resolves from `session.state['current_deliverable_spec']`. Use `{key?}` for optional keys that may not exist.

> **Director personality:** The Director's personality profile lives in `user:` scope. Different CEO logins get different Director personalities. Seeded from a config file on first login, then evolvable via `state_delta` over time. This means personality follows the user across all sessions and projects.

> **Project config as DB entity:** Project-specific configuration (conventions, architecture decisions, tech stack settings) is a **database entity** (project table with CRUD, permissions, versioning) -- NOT stored in `app:` state. Agents load project config at session start via a tool or init callback. ADK state scopes remain exclusively for runtime agent communication. This keeps `app:` scope lightweight and avoids persisting large structured data in the key-value state system.

> **Multi-session model:** Director operates via multiple concurrent sessions: **chat sessions** for interactive CEO conversation and **work sessions** (one per project) for background autonomous oversight. Same agent definition, different session IDs. ADK `Runner.run_async()` supports concurrent calls with different session IDs natively. The `user:` scoped Director personality is shared across all of these sessions automatically.

### 1.3 State Scope per Tier

The 6-level memory architecture applies at each tier's scope:

| Level | Director Scope | PM Scope | Worker Scope |
|-------|---------------|----------|--------------|
| Invocation (`temp:`) | Current decision cycle (chat or work session) | Current batch management cycle | Current deliverable execution |
| Pipeline (`session`) | Chat: conversation state. Work: cross-project governance state. | Project execution state | Deliverable pipeline state |
| Project (DB entity + Skills) | All `project_configs` (DB). Global conventions. | Project config (DB). Project conventions, skills. | Deliverable-specific skills |
| User (`user:`) | CEO preferences, Director personality | Inherits from Director | Inherits from PM |
| Cross-session (`MemoryService`) | Historical decisions, pattern library | Project history, past batch outcomes | Past deliverable patterns |
| Business (Skills) | Global skills, governance rules | Project skills, workflow skills | Task-specific skills |

Hard limits cascade through the hierarchy: CEO sets globals -> Director enforces per-project limits -> PM enforces per-worker constraints.

### 1.4 Memory (MemoryService)

Searchable cross-session knowledge archive. Two operations:

- `add_session_to_memory(session)` -- ingests a completed session
- `search_memory(app_name, user_id, query)` -- retrieves relevant past context

Built-in tools for agent access:

| Tool | Behavior |
|------|----------|
| `PreloadMemoryTool` | Auto-loads relevant memories every turn |
| `LoadMemory` | Agent-decided retrieval (on-demand) |
| `tool.Context.search_memory()` | Programmatic search from within custom tools |

### 1.5 Session Rewind (v1.17+)

Revert to any previous invocation point. Session-level state and artifacts are restored. `app:` and `user:` state are NOT restored (by design -- those are cross-session). External systems (filesystem, git) are not managed by rewind -- AutoBuilder handles that via git worktree isolation.

### 1.6 Session Migration

CLI tool for `DatabaseSessionService` schema upgrades (v0 pickle to v1 JSON). Important for production maintenance when upgrading ADK versions.

---

## 2. Persistence Architecture

### 2.1 Single Database

All persistence flows through one database, managed by SQLAlchemy 2.0 async with Alembic migrations.

| Data | Table/Store | Access Pattern |
|------|------------|----------------|
| Sessions + state | ADK `DatabaseSessionService` tables | Read/write from workers during pipeline execution; read from gateway for status queries |
| Event listeners/hooks | AutoBuilder-owned table | Registered via gateway API; matched against Redis Stream events by consumers |
| Job metadata | ARQ-managed (Redis) + AutoBuilder status table | Gateway writes job records; workers update status; gateway reads for API responses |
| Memory | `PostgresMemoryService` tables (tsvector + pgvector) | Workers write after session completion; workers read during skill/memory loading |
| Alembic migrations | `alembic_version` table | Schema versioning for upgrades |

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Single engine shared across the application
engine = create_async_engine(
    settings.database_url,  # "postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder"
    echo=settings.debug,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)
```

Both the gateway and workers connect to the same database. The gateway handles API-facing queries (workflow status, event listener registration). Workers handle pipeline-facing operations (session state, memory ingestion).

### 2.2 Redis Layer

Redis serves four roles in AutoBuilder:

| Role | Mechanism | Description |
|------|-----------|-------------|
| **Task queue** | ARQ | Async job enqueueing and worker dispatch |
| **Event bus** | Redis Streams | Persistent, replayable event distribution |
| **Cache** | Redis key-value | Frequently accessed state, skill index, routing config |
| **Cron** | ARQ cron | Scheduled jobs (heartbeats, cleanup, maintenance) |

Redis is not the source of truth for any persistent data. The database is always authoritative. Redis provides performance (caching), distribution (event bus), and coordination (task queue).

```python
from arq import create_pool
from arq.connections import RedisSettings

redis_pool = await create_pool(RedisSettings(
    host=settings.redis_host,
    port=settings.redis_port,
))
```

### 2.3 State Access Patterns

| Component | Database | Redis | Filesystem |
|-----------|----------|-------|------------|
| Gateway | Session status queries, event listener CRUD, job metadata | Enqueue jobs, read cached state, SSE via Streams | None |
| Worker | Session state R/W, memory ingestion, job status updates | Publish events to Streams, read cached config | Git worktrees, tool execution |
| ARQ cron | Stale job cleanup, health checks | Heartbeat writes | None |

---

## 3. SessionService Options

| Service | Persistence | Use Case |
|---------|------------|----------|
| `InMemorySessionService` | None (lost on restart) | Dev/testing only |
| **`DatabaseSessionService`** | **PostgreSQL** | **AutoBuilder production choice -- local, no GCP dependency** |
| `VertexAiSessionService` | Vertex AI managed | Skipping -- GCP dependency |

`DatabaseSessionService` requires the `asyncpg` async driver for PostgreSQL.

```python
from google.adk.sessions import DatabaseSessionService

# AutoBuilder production configuration
session_service = DatabaseSessionService(
    db_url="postgresql+asyncpg://autobuilder:autobuilder@localhost:5432/autobuilder"
)
```

---

## 4. MemoryService Options

| Service | Search | Persistence | Limitations |
|---------|--------|-------------|-------------|
| `InMemoryMemoryService` | Basic keyword matching | None | Dev/testing only |
| `VertexAiMemoryBankService` | Semantic (LLM-powered extraction + search) | Managed by Vertex AI | GCP-only -- we are avoiding this |

ADK's `MemoryService` is an interface (`BaseMemoryService`) with two methods: `add_session_to_memory()` and `search_memory()`. The only production-ready implementation is `VertexAiMemoryBankService` (GCP-only). `InMemoryMemoryService` is keyword-only and non-persistent.

This is the primary gap AutoBuilder must fill.

---

## 5. Memory Service: PostgreSQL tsvector + pgvector

AutoBuilder needs a local, persistent, searchable memory service. PostgreSQL provides both capabilities in the existing database:

### Full-Text Search: tsvector

PostgreSQL's built-in `tsvector` provides full-text search with ranking, stemming, and phrase matching. Sufficient for keyword-based queries like "what patterns did we establish in deliverables 1-10?"

### Semantic Search: pgvector

The `pgvector` extension adds vector column types and similarity search operators to PostgreSQL. When semantic search is needed (Phase 9+), embeddings are stored alongside text in the same table -- no separate vector database required.

### Embedding Model

pgvector stores and indexes vectors; an embedding model produces them. Embeddings are routed through **LiteLLM** (`litellm.embedding()`) -- same provider-agnostic abstraction used for LLM calls. The model is a configuration value, not a hardcoded dependency.

| Option | Dims | Notes |
|--------|------|-------|
| `text-embedding-3-small` (OpenAI) | 1536 | Low cost (~$0.02/1M tokens) |
| `text-embedding-004` (Gemini) | 768 | Free tier available |
| `all-MiniLM-L6-v2` (local) | 384 | No API cost, ~80MB, sufficient for session similarity |

Default: whichever provider the project already has an API key for. Swappable via config without code changes.

### Implementation: `PostgresMemoryService`

Custom `BaseMemoryService` implementation (~200-500 LOC):
- `add_session_to_memory(session)` -- ingests completed session text + optional embeddings
- `search_memory(app_name, user_id, query)` -- tsvector keyword search (Phase 1), pgvector semantic search (Phase 9+)
- Single table in the shared PostgreSQL database
- Same SQLAlchemy models, same Alembic migrations, same connection pool

**Why not a separate vector database?** ChromaDB, Qdrant, Pinecone, etc. add another service to operate. pgvector keeps everything in PostgreSQL -- one database, one backup strategy, one connection pool. The single-database architecture principle is preserved.

---

## 6. AutoBuilder's Multi-Level Memory Architecture

Mapping the original "multi-level memory" requirement (Problem #7 from plan-shaping) to ADK's native primitives:

| Memory Level | ADK Mechanism | What It Stores | Loaded How |
|---|---|---|---|
| **Invocation context** | `temp:` state | Scratch data for current tool chain | Auto-available, discarded after |
| **Pipeline context** | Session state (no prefix) | Deliverable spec, plan, execution output, validation results, verification results | Written by agents via `state_delta`, read via `{key}` templates |
| **Project conventions** | Database entity (project table) + Skills | Standards, architecture decisions, workflow patterns, tech stack settings | Loaded at session start via tool/init callback; Skills via SkillLoaderAgent |
| **Director personality + user preferences** | `user:` state | Director personality profile, model preferences, notification settings, review strictness | Auto-merged into session at load; personality seeded from config on first login |
| **Cross-session learnings** | `MemoryService` | Patterns discovered, mistakes made, architectural decisions from past runs | `PreloadMemoryTool` or `LoadMemory` tool |
| **Business knowledge** | Skills files (global + project-local) | Domain rules, compliance requirements, workflow conventions | SkillLoaderAgent (deterministic matching) |

This is six levels of progressively broader context, all using ADK-native mechanisms. No custom memory framework needed -- just proper use of state scopes + MemoryService + Skills.

---

## 7. How Memory Flows Through the Pipeline

All pipeline execution happens inside worker processes. Workers access state through the database and publish events to Redis Streams.

```
Client request --> Gateway (enqueue job) --> Redis (ARQ queue) --> Worker picks up job

Worker execution:
  Session loads via DatabaseSessionService (database)
    --> app:* state available (skill index, workflow registry, runtime coordination)
    --> user:* state available (Director personality, preferences, settings)
    --> Project config loaded from DB via tool/init callback
    --> session state available (deliverable list, batch status from last run)
    |
    v
  SkillLoaderAgent
    --> loads relevant skills into session state (deterministic matching)
    |
    v
  PreloadMemoryTool
    --> searches MemoryService for relevant cross-session context
    |
    v
  plan_agent reads:
    {current_deliverable_spec}, {loaded_skills}, {memory_context}, {project_config}
    |
    v
  code_agent reads:
    {implementation_plan}, {loaded_skills}, {project_config}
    |
    v
  LinterAgent writes: lint_results to session state
  TestRunnerAgent writes: test_results to session state
    |
    v
  review_agent reads:
    {code_output}, {lint_results}, {test_results}, {loaded_skills}
    |
    v
  Session complete
    --> add_session_to_memory() ingests learnings for future runs (database)
    --> Publish completion event to Redis Streams
    --> Gateway SSE consumers push update to clients
```

Each step reads from and writes to session state. Agents communicate via state, not direct message passing. The event stream captures every state mutation for observability and rewind support.

---

## 8. Multi-Agent Communication

Agents communicate via four mechanisms, all operating through session state:

| # | Mechanism | How It Works |
|---|-----------|-------------|
| 1 | `output_key` | Agent writes its result to a named state key |
| 2 | `{key}` templates | Agent reads from state via template injection in instructions |
| 3 | `InstructionProvider` | Dynamic function reads state and constructs context-appropriate instructions at invocation time |
| 4 | `before_model_callback` | Injects additional context (file contents, test results) right before LLM call |

Within a pipeline tier, no agent calls another agent directly. All coordination flows through the shared state system, making data flow explicit and debuggable.

### Hierarchical Communication

Between tiers, agents communicate via ADK's delegation primitives:

| Pattern | Mechanism | Example |
|---------|-----------|---------|
| Director -> PM delegation | `sub_agents` + `transfer_to_agent` | Director declares PMs as sub_agents, delegates via transfer_to_agent |
| PM -> Worker orchestration | `sub_agents` tree | PM constructs DeliverablePipeline workers per batch |
| Worker -> PM escalation | State write + event | Worker writes failure to state; PM reads and decides |
| PM -> Director escalation | State write + event + CEO queue | PM writes unresolvable issue; enqueues escalation to CEO queue |
| Director observation | `before_agent_callback` / `after_agent_callback` | Director monitors PM events via supervision hooks |
| Cross-project state | `app:` scope prefix | Visible to Director and all PMs |
| Cross-session bridge | `app:`/`user:` state + `MemoryService` + Redis Streams | Chat sessions observe/influence work sessions |

---

## 9. Key Implementation Details

### 9.1 State Updates Are Event-Sourced

Never mutate `session.state` directly. Always write via `EventActions(state_delta={...})`. This ensures all changes are captured in the event stream and are rewind-safe.

```python
from google.adk.events import Event, EventActions

yield Event(
    author=self.name,
    actions=EventActions(state_delta={
        "lint_results": {"passed": True, "warnings": 3, "errors": 0},
        "lint_status": "passed",
    })
)
```

> **VERIFIED (Phase 1):** Direct `ctx.session.state["key"] = value` writes inside `_run_async_impl` do NOT persist to the session service. Only `state_delta` on yielded Events persists state. Direct reads from `ctx.session.state` still work within the same execution because ADK applies incoming `state_delta` from sub-agent events. See `.knowledge/adk/ERRATA.md` #1.

### 9.2 Memory Ingestion Is Explicit

Call `memory_service.add_session_to_memory(session)` at appropriate points -- after deliverable completion, after batch completion, at session end. Not every invocation needs to be ingested.

The ingestion strategy (after each deliverable, each batch, or session end) is an open design question. See consolidated planning doc, Open Questions #10.

### 9.3 Rewind Limitations

Session rewind restores session-level state and artifacts but NOT `app:` or `user:` state. Since AutoBuilder's project conventions live in the database (project config entity) and skills, and Director personality lives in `user:` state, a rewind does not accidentally erase global learnings or personality. This is the right behavior for our use case.

External filesystem state is not managed by rewind. AutoBuilder handles this via git worktree isolation -- each parallel deliverable executes in its own worktree, so rewind within a deliverable pipeline does not affect other deliverables.

### 9.4 Multiple Memory Services

ADK allows agents to access more than one `MemoryService`. This could be useful if AutoBuilder later needs separate stores for different knowledge types (e.g., code patterns vs. project decisions). Phase 1 uses a single `PostgresMemoryService`.

### 9.5 Redis Cache Strategy

Frequently accessed read-heavy data is cached in Redis to reduce database load:

| Cached Data | TTL | Invalidation |
|------------|-----|-------------|
| Skill index | Long (hours) | Invalidated on skill file change |
| Routing config | Long (hours) | Invalidated on config update |
| Active session state snapshots | Short (seconds) | Invalidated on state mutation |
| Workflow registry | Long (hours) | Invalidated on registry scan |

Cache reads are opportunistic -- a cache miss falls through to the database. Cache writes happen on database reads (write-through for hot data).

### 9.6 Context Window Management

ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt. Two built-in mechanisms manage growth:

- **Context compression** -- sliding window summarization of older events (config-driven, interval + overlap)
- **Context caching** -- caches static prompt parts server-side (system instructions, knowledge bases)

**Gap identified:** ADK has no built-in context-window usage metric. Agents cannot reactively respond to "you are at 90% capacity." Solution: `before_model_callback` that token-counts the assembled `LlmRequest`, writes percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). Approximately 50 lines of code.

**Pipeline design implication:** For longer pipelines, agents should not rely on reading raw event history from prior steps. Better to use SkillLoaderAgent + explicit state writes so each agent gets precisely the context it needs, not the full event log.

---

## 10. Gateway API for State & Memory (Phase 2)

Phase 2 introduces gateway endpoints for state and memory inspection:

| Endpoint | Purpose |
|----------|---------|
| `GET /sessions/{id}/state` | Inspect session state (loaded skills, deliverable status, etc.) |
| `GET /memory/search?q=...` | Search cross-session memory |
| `GET /metrics/tokens` | Token usage across sessions |
| `GET /costs` | Cost breakdown per agent, per model, per run |

These endpoints read from the database. They do not interact with ADK directly -- they query the same tables that workers write to.

---

## 11. Scope Estimate

**`PostgresMemoryService`**: ~200-500 lines implementing `BaseMemoryService` with PostgreSQL tsvector backing (pgvector for semantic search in Phase 9+).

**Database models + Alembic migrations**: ~200 lines for AutoBuilder-owned tables (event listeners, job metadata). ADK's `DatabaseSessionService` manages its own tables.

**Redis integration**: ~100 lines for cache helpers and Stream publishers.

The rest of the state and memory architecture (state scopes, session management, event-sourced updates, template injection, context compression) is native ADK. AutoBuilder uses it correctly rather than rebuilding it.

---

## See Also

- [Agents](./agents.md) -- agent composition, custom agents, supervision hierarchy
- [Skills](./skills.md) -- skill-based knowledge injection, SkillLoaderAgent
- [Tools](./tools.md) -- FunctionTools, GlobalToolset, tool authorization
- [Architecture Overview](../02-ARCHITECTURE.md) -- system-level architecture
- [Roadmap](../08-ROADMAP.md) -- delivery plan
- ADK Sessions & Memory overview: https://google.github.io/adk-docs/sessions/
- ADK State management: https://google.github.io/adk-docs/sessions/state/
- ADK Memory service: https://google.github.io/adk-docs/sessions/memory/
- ADK Session rewind: https://google.github.io/adk-docs/sessions/session/rewind/

---

*Document Version: 3.0*
*Last Updated: 2026-02-17*
