# Phase 3 Spec: ADK Engine Integration
*Generated: 2026-02-14 | Updated: 2026-02-18 | Status: **DONE** — 116 tests pass (incl. 4 LLM integration tests), all quality gates clean*

## Overview

Phase 3 wires Google ADK into the production infrastructure built in Phase 2. After this phase, the system can receive a workflow execution request through the gateway, enqueue it to an ARQ worker, execute an ADK agent pipeline with Claude via LiteLLM, persist session state to PostgreSQL via DatabaseSessionService, translate ADK events into gateway-native event objects, and publish them to Redis Streams. This is the critical integration layer between the API-first gateway and the ADK orchestration engine.

This phase directly advances four core vision differentiators: **Multi-model orchestration** (#5) — the LLM Router selects models by task type and complexity, with 3-step fallback chain resolution and runtime model override via `before_model_callback`. **API-first architecture** (#7) — the anti-corruption layer ensures ADK types never leak through the gateway API. **Out-of-process execution** (#8) — workflow pipelines run in ARQ workers, triggered by gateway job enqueueing. **Autonomous completion** (#1) — session state persistence with 4-scope state system enables workflows to maintain context across invocations, the foundation for the autonomous "run until done" loop.

Key constraints: ADK types never appear in gateway API models or route handlers. All ADK interaction happens inside worker processes. The anti-corruption layer translates in both directions: gateway commands → ADK Runner calls (inbound), ADK Events → Redis Stream messages (outbound). Phase 3 uses a minimal test agent (`EchoAgent` — an `LlmAgent` with simple instructions) to validate the full stack; real agent definitions come in Phase 5.

## Features

- **LLM Router** — Static routing mapping task type × complexity to LiteLLM model strings, with 3-step fallback chain resolution and `before_model_callback` for runtime model override
- **ADK App container + Runner factory** — App class with EventsCompactionConfig, ResumabilityConfig, ContextCacheConfig, and LoggingPlugin; Runner creation with DatabaseSessionService for PostgreSQL-backed session persistence
- **Anti-corruption layer** — Bidirectional translation: gateway commands → ADK Runner calls (inbound), ADK events → gateway PipelineEvent objects (outbound)
- **Worker pipeline bridge** — `run_workflow` ARQ task with session creation/resumption, event streaming, and workflow status tracking
- **4-scope state system** — `temp:`, session, `user:`, `app:` scopes operational via DatabaseSessionService with `app:` scope initialization
- **Redis infrastructure** — Cache helpers and Stream publishing helpers for event distribution
- **Gateway workflow endpoint** — `POST /workflows/run` enqueues workflow execution jobs via ArqRedis, returns 202 Accepted
- **Context compression** — Sliding window summarization via EventsCompactionConfig + LlmEventSummarizer

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 2: Gateway + Infrastructure | MET | 51 tests pass; `ruff check .`, `pyright`, `pytest` all clean; gateway serves `/health`; ARQ worker runs with heartbeat; Alembic migration creates core tables; commit `2a7f732` |

## Design Decisions

### DD-1: Test Pipeline for Phase 3 Validation
Phase 3 validates ADK infrastructure integration, not full agent pipelines (those come in Phase 5). A minimal `EchoAgent` — an `LlmAgent` with simple instructions — serves as the test pipeline. It receives a prompt, calls Claude via LiteLLM, writes the response to state via `output_key`, and emits events into the ADK event stream. This proves the full stack (gateway → ARQ → ADK Runner → LiteLLM → Claude → state persistence → event translation → Redis Streams) without depending on complex agent definitions. The EchoAgent is defined in `app/workers/adk.py` as test infrastructure, not in `app/agents/`.

### DD-2: ADK App Container — Created Per Execution
The ADK `App` container is created per workflow execution in `run_workflow`, not at worker startup. Reason: the App takes a `root_agent` which varies by workflow type (auto-code, auto-research, etc.). In Phase 3, the root agent is always EchoAgent. In later phases, it is constructed dynamically per workflow type.

Shared resources (DatabaseSessionService, LlmRouter) are created during worker `on_startup` and stored in the worker context (`ctx`). These are reused across executions. The App is passed to `Runner(app=app_instance, session_service=...)` which extracts compaction and resumability configs from the App.

```python
# Per execution
app = create_app_container(root_agent=echo_agent)
runner = Runner(app=app, session_service=ctx["session_service"])

# App provides: EventsCompactionConfig, ResumabilityConfig, ContextCacheConfig, plugins
# Runner provides: session management, event streaming
```

Phase 3 uses EchoAgent as root_agent for infrastructure validation. In production, Director (LlmAgent, opus) becomes the root_agent with PM sub_agents via `sub_agents` + `transfer_to_agent`. Director is a stateless config object recreated per invocation -- all persistent state lives in DatabaseSessionService, formation artifacts (identity, CEO profile, operating contract) in `user:` scope. The `create_app_container(root_agent)` factory pattern supports this transition -- only the caller changes.

### DD-3: DatabaseSessionService — ADK-Managed Tables
ADK's `DatabaseSessionService` is configured with the same PostgreSQL URL as AutoBuilder (`AUTOBUILDER_DB_URL`). ADK creates and manages its own tables via a separate SQLAlchemy metadata (not AutoBuilder's `Base`):

| ADK Table | Purpose |
|-----------|---------|
| `adk_internal_metadata` | Schema versioning |
| `sessions` | Session records (app_name, user_id, session_id, state) |
| `events` | Event history per session |
| `app_states` | App-scoped state (cross-user, cross-session) |
| `user_states` | User-scoped state (cross-session) |

Tables are auto-created lazily on first operation via `metadata.create_all()`. No Alembic migration needed — ADK handles its own schema. AutoBuilder-owned tables and ADK tables coexist in the same database.

The session service is initialized during worker `on_startup` and stored in `ctx["session_service"]`.

### DD-4: Session Identity — Workflow ID as Session ID
Each workflow execution maps 1:1 to an ADK session: `app_name="autobuilder"`, `user_id="system"`, `session_id=str(workflow.id)`. No additional columns on the `workflows` table. Re-running a workflow resumes the existing session, enabling state continuity. This directly supports the completion contract requirement "session state persists across worker invocations."

### DD-5: LLM Router — Configuration via Settings + Runtime Override
The router loads defaults from `app/config/settings.py` via `AUTOBUILDER_DEFAULT_*_MODEL` env vars (code, plan, review, fast). Fallback chains are defined in code — they change rarely and benefit from type safety. The router is a stateless lookup with no I/O.

Runtime model override: `create_model_override_callback(router)` returns a `before_model_callback` function that maps agent names to ModelRoles and overrides `llm_request.model` via the router. This callback is set on the EchoAgent in Phase 3; in Phase 5, it's registered as a plugin on the App for all agents. The callback reads the agent name from `callback_context.agent_name` and an optional user override from `callback_context.state.get("user:model_override")`.

```python
router = LlmRouter.from_settings(get_settings())
model = router.select_model(ModelRole.CODE)  # → "anthropic/claude-sonnet-4-6"
model = router.select_model(ModelRole.PLAN, user_override="openai/gpt-5")  # → user override wins

# before_model_callback wires the router into ADK
callback = create_model_override_callback(router)
agent = LlmAgent(..., before_model_callback=callback)
```

Adaptive routing with cost/latency tracking deferred to Phase 11.

### DD-6: Gateway Event Schema
Gateway events are ADK-agnostic Pydantic models. ADK event internals are mapped to a simplified `PipelineEventType` enum. The translator inspects ADK Event fields (author, content, actions) to determine the gateway event type:

| ADK Signal | Maps To |
|-----------|---------|
| First event for an agent author | `AGENT_STARTED` |
| `event.content.parts[0].function_call` | `TOOL_CALLED` |
| `event.content.parts[0].function_response` | `TOOL_RESULT` |
| `event.actions.state_delta` present | `STATE_UPDATED` |
| `event.is_final_response()` for agent | `AGENT_COMPLETED` |
| `event.error_code` present | `ERROR` |
| Synthetic (published by worker) | `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED` |

Event payload:
```python
class PipelineEvent(BaseModel):
    event_type: PipelineEventType
    workflow_id: str
    timestamp: datetime
    agent_name: str | None = None
    content: str | None = None
    metadata: dict[str, object] = {}
```

### DD-7: Redis Stream Key Pattern
Events are published to per-workflow streams: `workflow:{workflow_id}:events`. Stream entry IDs are auto-generated by Redis (timestamp-based), mapping naturally to SSE event IDs for replay support (Phase 10). One stream per workflow provides isolation and simplifies cleanup of completed workflows. The naming convention is enforced via the `stream_key()` helper function in the stream helpers module.

### DD-8: Gateway Job Enqueueing via ArqRedis
The gateway lifespan creates an `ArqRedis` pool (via `arq.connections.create_pool()`) for job enqueueing. `ArqRedis` extends `redis.asyncio.Redis`, so it supports both job enqueueing and general Redis operations. Stored on `app.state.arq_pool`. A new dependency `get_arq_pool()` provides FastAPI injection.

The existing `app.state.redis` client is **replaced** by `app.state.arq_pool` since ArqRedis is a Redis superset — no need for two separate clients. The `get_redis()` dependency returns the ArqRedis instance (type-compatible with Redis). Health checks use the same pool.

### DD-9: Redis Cache + Stream Helpers
Two small utility modules (~100 LOC each) provide the foundation for Redis-based infrastructure:

- **Cache helpers** (`app/lib/cache.py`): `cache_get`, `cache_set`, `cache_delete` with TTL support. Used by LLM Router (routing config cache), Skill Library (Phase 6), and Workflow Registry (Phase 7).
- **Stream helpers** (`app/events/streams.py`): `stream_publish`, `stream_read_range` wrapping `XADD`/`XRANGE` with the naming convention `workflow:{id}:events`. Used by EventPublisher and future SSE consumers.

These are thin wrappers — no abstraction beyond type safety and naming convention enforcement.

### DD-10: LoggingPlugin
A `BasePlugin` subclass that emits structured log entries for agent and tool lifecycle events. Logs `agent_started`, `agent_completed`, `tool_called`, `tool_result` via the existing `get_logger()` infrastructure. Minimal implementation: only `before_agent_callback`, `after_agent_callback`, `before_tool_callback`, `after_tool_callback` methods. Registered on the App container. ~50 LOC.

### DD-11: Job Metadata Tracking
The existing `Workflow` model (`app/db/models.py`) serves as the job metadata table for ARQ tracking. It already has `status`, `started_at`, `completed_at`, `params`. Phase 3 adds an `error_message: str | None` column via Alembic migration to persist the last error without requiring event stream reads. No separate job metadata table is needed — the Workflow table IS the AutoBuilder status table for ARQ job tracking.

### DD-12: App Scope Initialization
Worker startup initializes `app:`-scoped state keys as scaffolding for later phases. In Phase 3, this means writing placeholder values: `app:skill_index` (empty dict), `app:workflow_registry` (empty dict). These keys are written via `session_service` on first startup and skipped if already present (idempotent). This validates the `app:` scope persistence mechanism.

## Deliverables

### P3.D1: Configuration Extensions + Domain Enums
**Files:** `app/config/settings.py` (update), `app/models/enums.py` (update), `app/models/__init__.py` (update)
**Depends on:** —
**BOM Components:**
- [x] `R02` — Routing rules (static config — settings fields for default models per task type)
**Description:** Add LLM model default settings for each task type and new domain enums for LLM routing and event classification. Settings fields use `AUTOBUILDER_DEFAULT_*_MODEL` env vars with defaults pointing to Anthropic models per `06-PROVIDERS.md`.
**Requirements:**
- [x] `Settings` has `default_code_model: str` defaulting to `"anthropic/claude-sonnet-4-6"`
- [x] `Settings` has `default_plan_model: str` defaulting to `"anthropic/claude-opus-4-6"`
- [x] `Settings` has `default_review_model: str` defaulting to `"anthropic/claude-sonnet-4-6"`
- [x] `Settings` has `default_fast_model: str` defaulting to `"anthropic/claude-haiku-4-5-20251001"`
- [x] `ModelRole` enum (StrEnum): `CODE`, `PLAN`, `REVIEW`, `FAST` — values match names
- [x] `PipelineEventType` enum (StrEnum): `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `AGENT_STARTED`, `AGENT_COMPLETED`, `TOOL_CALLED`, `TOOL_RESULT`, `STATE_UPDATED`, `ERROR` — values match names
- [x] Both enums exported from `app.models`
- [x] Settings fields loadable from env vars with `AUTOBUILDER_` prefix
**Validation:**
- `uv run pyright app/config/ app/models/`

> **Delta note (2026-02-27):** `parse_redis_settings()` was consolidated to `app/config/settings.py` and exported from `app.config` during Phase 3. The function originated as a private `_parse_redis_settings()` in `app/workers/settings.py` (Phase 2); Phase 3's DD-8 ArqRedis gateway integration required the gateway to also parse Redis URLs, so it was made public and moved to shared config. Not listed in P3.D1's requirements. Note: `search_provider` field in Settings was added by Phase 4 (Phase 4 spec P4.D2), not Phase 3.

---

### P3.D2: LLM Router + Model Override Callback
**Files:** `app/router/router.py`, `app/router/__init__.py` (update)
**Depends on:** P3.D1
**BOM Components:**
- [x] `R01` — `LlmRouter` module
- [x] `R03` — Fallback chain resolution (3-step)
- [x] `R04` — `before_model_callback` model override
- [x] `A44` — `before_model_callback` LLM Router override
- [x] `M22` — Routing config cache (long TTL)
**Description:** `LlmRouter` class that maps `ModelRole` to LiteLLM model strings using configuration from Settings. Implements 3-step fallback chain resolution: user override → fallback chain → default. Also provides `create_model_override_callback()` — a factory that returns a `before_model_callback` function for ADK agents, enabling runtime model selection via the router. Includes `to_dict()` / `cache_to_redis()` for caching the routing config in Redis with long TTL.
**Requirements:**
- [x] `LlmRouter.select_model(task_type: ModelRole, user_override: str | None = None) -> str` returns model string matching Settings defaults: `CODE`→`"anthropic/claude-sonnet-4-6"`, `PLAN`→`"anthropic/claude-opus-4-6"`, `REVIEW`→`"anthropic/claude-sonnet-4-6"`, `FAST`→`"anthropic/claude-haiku-4-5-20251001"`
- [x] When `user_override` is a non-None string, `select_model()` returns that string regardless of task_type
- [x] Default models per ModelRole sourced from Settings fields (not hardcoded)
- [x] Fallback chains: opus→`["anthropic/claude-sonnet-4-6", "anthropic/claude-haiku-4-5-20251001"]`, sonnet→`["anthropic/claude-haiku-4-5-20251001"]`, haiku→`[]` (empty, no fallback)
- [x] `LlmRouter.get_fallbacks(model: str) -> list[str]` returns the ordered fallback list for a model string; returns `[]` for unknown models
- [x] `LlmRouter.from_settings(settings: Settings) -> LlmRouter` creates router from settings defaults
- [x] `LlmRouter.to_dict() -> dict[str, object]` serializes routing table for caching
- [x] `LlmRouter.cache_to_redis(redis: Redis) -> None` (async) stores routing config in Redis with 1-hour TTL via `cache_set` from `app.lib.cache`
- [x] `create_model_override_callback(router: LlmRouter) -> Callable` returns a `before_model_callback`-compatible function that: reads `callback_context.agent_name`, maps agent name → `ModelRole` via `AGENT_MODEL_ROLES` dict, calls `router.select_model()` with optional `user:model_override` from state, sets `llm_request.model` to result, returns `None`
- [x] `AGENT_MODEL_ROLES: dict[str, ModelRole]` mapping at module level (initially: `echo_agent` → `FAST`)
- [x] All `select_model` / `get_fallbacks` / `from_settings` methods synchronous (pure lookup, no I/O)
- [x] Importable as `from app.router import LlmRouter, create_model_override_callback`
**Validation:**
- `uv run pyright app/router/`

---

### P3.D3: Redis Cache + Stream Helpers
**Files:** `app/lib/cache.py`, `app/events/streams.py`, `app/events/__init__.py` (update), `app/lib/__init__.py` (update if needed)
**Depends on:** —
**BOM Components:**
- [x] `M25` — Redis cache helpers (~100 LOC)
- [x] `M26` — Redis Stream publishers (~100 LOC)
- [x] `V02` — Redis Stream naming convention
**Description:** Two small utility modules providing Redis infrastructure foundations. Cache helpers: `cache_get`, `cache_set`, `cache_delete` with typed JSON serialization and TTL support. Stream helpers: `stream_publish`, `stream_read_range` wrapping XADD/XRANGE with enforced naming convention (`workflow:{id}:events`). Both modules use `redis.asyncio.Redis` as the client type. The stream naming convention is defined as a constant function `stream_key(workflow_id: str) -> str`.
**Requirements:**
- [x] `cache_get(redis: Redis, key: str) -> str | None` retrieves a cached value; returns `None` on miss
- [x] `cache_set(redis: Redis, key: str, value: str, ttl: int = 3600) -> None` stores a value with TTL in seconds
- [x] `cache_delete(redis: Redis, key: str) -> None` removes a cached value
- [x] `stream_key(workflow_id: str) -> str` returns `f"workflow:{workflow_id}:events"` (naming convention)
- [x] `stream_publish(redis: Redis, workflow_id: str, data: str) -> str` calls `XADD` on the workflow stream, returns the stream entry ID
- [x] `stream_read_range(redis: Redis, workflow_id: str, start: str = "-", end: str = "+", count: int | None = None) -> list[tuple[str, dict[str, str]]]` calls `XRANGE` on the workflow stream
- [x] Both modules use `redis.asyncio.Redis` type (compatible with `ArqRedis`)
- [x] All functions async
- [x] `app/lib/cache.py` importable as `from app.lib.cache import cache_get, cache_set, cache_delete`
- [x] `app/events/streams.py` importable as `from app.events.streams import stream_key, stream_publish, stream_read_range`
**Validation:**
- `uv run pyright app/lib/cache.py app/events/streams.py`

---

### P3.D4: Gateway Event Schema + Event Translation
**Files:** `app/gateway/models/events.py`, `app/events/publisher.py`, `app/events/__init__.py` (update), `app/gateway/models/__init__.py` (update)
**Depends on:** P3.D1, P3.D3
**BOM Components:**
- [x] `G21` — Anti-corruption translation layer (outbound: ADK events → gateway events)
- [x] `V01` — Per-workflow Redis Stream publishing
- [x] `W06` — `translate_event()`
- [x] `W07` — `publish_to_stream()`
**Description:** `PipelineEvent` Pydantic model defining the gateway-native event payload — ADK-agnostic, suitable for SSE and webhook consumers. `EventPublisher` class that translates ADK Event objects into PipelineEvent instances and publishes them to per-workflow Redis Streams using stream helpers from D3. The translator inspects ADK Event fields (`author`, `content`, `actions`, `error_code`) to determine the appropriate `PipelineEventType`. Stream key pattern enforced via `stream_key()` from `app.events.streams`.
**Requirements:**
- [x] `PipelineEvent` model has fields: `event_type: PipelineEventType`, `workflow_id: str`, `timestamp: datetime`, `agent_name: str | None`, `content: str | None`, `metadata: dict[str, object]`
- [x] `PipelineEvent` inherits from `app.models.base.BaseModel`
- [x] `EventPublisher.__init__(redis: Redis)` accepts a Redis client instance
- [x] `EventPublisher.translate(adk_event: object, workflow_id: str) -> PipelineEvent | None` converts ADK Event to gateway event, returns `None` for unclassified events (skipped) — `adk_event` typed as `object` at the module boundary (ADK types never in gateway model signatures)
- [x] Translation maps per DD-6: `error_code` present→`ERROR`, `function_call` in content→`TOOL_CALLED`, `function_response`→`TOOL_RESULT`, `state_delta` present→`STATE_UPDATED`, final response→`AGENT_COMPLETED`, first event for author→`AGENT_STARTED`, all others→`None` (skip)
- [x] `EventPublisher.publish(event: PipelineEvent) -> None` publishes via `stream_publish()` from `app.events.streams`
- [x] `EventPublisher.publish_lifecycle(workflow_id: str, event_type: PipelineEventType) -> None` publishes synthetic lifecycle events (STARTED, COMPLETED, FAILED)
- [x] Published events are JSON-serialized with `model_dump_json()`
- [x] `app/events/publisher.py` has zero `google.adk` imports — translation uses `getattr()` / `hasattr()` only (ACL boundary)
**Validation:**
- `uv run pyright app/events/ app/gateway/models/`

---

### P3.D5: ADK Engine — App Container + Session Service + Plugins
**Files:** `app/workers/adk.py`
**Depends on:** P3.D1, P3.D2
**BOM Components:**
- [x] `E01` — `App` container (`autobuilder`)
- [x] `E04` — `EventsCompactionConfig`
- [x] `E05` — `LlmEventSummarizer` (haiku model)
- [x] `E06` — `ResumabilityConfig`
- [x] `E07` — `context_cache_config`
- [x] `E09` — `LoggingPlugin`
- [x] `E12` — `DatabaseSessionService` integration
- [x] `D04` — `sessions` table (ADK auto-created)
- [x] `W04` — `create_adk_runner()` factory
- [x] `O04` — Context compression (sliding window summarization)
**Description:** Factory functions for ADK infrastructure. `create_session_service()` initializes DatabaseSessionService with the PostgreSQL URL (triggers lazy table creation for D04). `create_app_container()` builds an ADK App with EventsCompactionConfig (using LlmEventSummarizer for context compression, O04), ResumabilityConfig, ContextCacheConfig, and LoggingPlugin. `create_runner()` wraps the App in a Runner. Also defines the minimal `EchoAgent` with `before_model_callback` wired to the LLM Router, and `LoggingPlugin` as a `BasePlugin` subclass.
**Requirements:**
- [x] `create_session_service(db_url: str) -> DatabaseSessionService` creates a session service connected to PostgreSQL (ADK uses `create_async_engine` internally — `postgresql+asyncpg://` URLs from `Settings.db_url` work directly)
- [x] `create_app_container(root_agent: BaseAgent, plugins: list[BasePlugin] | None = None) -> App` creates App with `name="autobuilder"`, `EventsCompactionConfig(compaction_interval=5, overlap_size=1, summarizer=LlmEventSummarizer(...))`, `ResumabilityConfig(is_resumable=True)`, and `ContextCacheConfig(min_tokens=1000, ttl_seconds=300, cache_intervals=5)`
- [x] `LlmEventSummarizer` initialized with `LiteLlm(model="anthropic/claude-haiku-4-5-20251001")`
- [x] Default `plugins` list includes `LoggingPlugin()` if no plugins argument provided
- [x] `create_runner(app: App, session_service: DatabaseSessionService) -> Runner` creates a Runner from the App with `auto_create_session=False` (sessions managed explicitly)
- [x] `create_echo_agent(model: str, before_model_callback: Callable | None = None) -> LlmAgent` creates a test agent with `name="echo_agent"`, `output_key="agent_response"`, simple instructions, and optional `before_model_callback`
- [x] Echo agent uses `LiteLlm(model=model)` for the LLM backend
- [x] `LoggingPlugin` extends `BasePlugin` with `before_agent_callback` (logs agent start) and `after_agent_callback` (logs agent completion) using `get_logger("engine.plugins")`
- [x] All factory functions have explicit return type annotations
- [x] Module imports only from `google.adk.*`, `app.config`, `app.router`, `app.lib`, and stdlib — never from `app.gateway` (ACL boundary)
**Validation:**
- `uv run pyright app/workers/adk.py`

---

### P3.D6: Worker Pipeline Bridge — run_workflow + Lifecycle
**Files:** `app/workers/tasks.py` (update), `app/workers/settings.py` (update), `app/workers/__init__.py` (update)
**Depends on:** P3.D3, P3.D4, P3.D5
**BOM Components:**
- [x] `W03` — `run_workflow()` ARQ job function
- [x] `W05` — `create_or_resume_session()`
- [x] `W08` — `update_workflow_state()`
- [x] `D11` — Job metadata table (ARQ tracking — via existing Workflow model)
- [x] `E13` — 4-scope state system (operational via DatabaseSessionService)
- [x] `E14` — `app:` scope initialization (skill index, workflow registry)
- [x] `E15` — App lifecycle hooks (`on_startup` / `on_shutdown`)
- [x] `A71` — Work session model (long-running ARQ job)
- [x] `G21` — Anti-corruption translation layer (inbound: gateway commands → ADK Runner)
- [x] `M01` — `temp:` scope handling
- [x] `M02` — `user:` scope handling
- [x] `M03` — `app:` scope handling
- [x] `M04` — Session (no prefix) scope handling
**Description:** ARQ task function `run_workflow` that orchestrates the full execution cycle — the inbound anti-corruption layer (gateway commands → ADK). On invocation: reads the workflow record (D11 job metadata), updates status to RUNNING, creates or resumes an ADK session (W05, A71 work session model), instantiates App container + Runner with EchoAgent, iterates the ADK event stream translating and publishing events, and updates workflow status (W08). Worker `on_startup` (E15) initializes shared resources (DatabaseSessionService, LlmRouter) in context, caches routing config in Redis (M22), and initializes `app:` scope state (E14). The 4-scope state system (E13, M01-M04) is operational through DatabaseSessionService — all four prefix scopes are available to agents.

Also adds `error_message` column to the Workflow model (D11) via Alembic migration.
**Requirements:**
- [x] `run_workflow(ctx: dict[str, object], workflow_id: str) -> dict[str, str]` is async and registered in `WorkerSettings.functions`
- [x] Task reads workflow record from database; raises `NotFoundError(message=f"Workflow {workflow_id} not found")` if not found
- [x] Task updates workflow `status` to `RUNNING` (with `started_at` timestamp) before pipeline execution
- [x] Task creates or resumes ADK session using `app_name="autobuilder"`, `user_id="system"`, `session_id=workflow_id`
  > **Delta note (2026-02-27):** Actual implementation uses `APP_NAME` and `SYSTEM_USER_ID` constants from `app.models.constants` instead of string literals. `INIT_SESSION_ID = "__init__"` was also added to constants.py — used for the `app:` scope initialization session (DD-12), not for workflow sessions which still use `session_id=workflow_id`.
- [x] Task creates App container with EchoAgent (model from LlmRouter, `before_model_callback` from `create_model_override_callback`) and Runner with DatabaseSessionService
- [x] ADK events are translated via `EventPublisher.translate()` and published to Redis Stream
- [x] `WORKFLOW_STARTED` event published before pipeline execution; `WORKFLOW_COMPLETED` or `WORKFLOW_FAILED` published after
- [x] On success: workflow `status` updated to `COMPLETED` with `completed_at` timestamp
- [x] On error: workflow `status` updated to `FAILED`, `error_message` set on workflow record, `WORKFLOW_FAILED` event published with error message in `metadata`, exception logged at `ERROR` level with `workflow_id` and stack trace
- [x] Worker `on_startup` initializes `DatabaseSessionService` and `LlmRouter` in worker context (`ctx`)
- [x] Worker `on_startup` calls `router.cache_to_redis()` to cache routing config
  > **Delta note (2026-02-27):** Worker `on_startup` also creates `db_engine` and `db_session_factory` (SQLAlchemy) and stores them in worker context for `run_workflow` to use when reading/writing Workflow records. These are not listed in the spec's worker startup requirements above but are present in the actual implementation.
- [x] Worker `on_startup` initializes `app:` scope state: `app:skill_index` = `{}`, `app:workflow_registry` = `{}` (idempotent — skip if keys already exist)
- [x] Worker `on_shutdown` disposes of session service resources
- [x] Existing tasks (`test_task`, `heartbeat`) remain functional and registered
- [x] Workflow model has `error_message: Mapped[str | None]` column with Alembic migration
**Validation:**
- `uv run pyright app/workers/`
- `uv run alembic upgrade head`

---

### P3.D7: Gateway Workflow Route + Job Enqueueing
**Files:** `app/gateway/routes/workflows.py`, `app/gateway/models/workflows.py`, `app/gateway/deps.py` (update), `app/gateway/main.py` (update)
**Depends on:** P3.D1
**Description:** Minimal workflow API endpoint: `POST /workflows/run` accepts a workflow type and optional params, creates a workflow record in the database with status PENDING, enqueues an ARQ `run_workflow` job, and returns 202 Accepted. Gateway lifespan updated to create an ArqRedis pool (replacing the separate Redis client per DD-8). New dependency `get_arq_pool()` provides FastAPI injection.
**Requirements:**
- [x] `WorkflowRunRequest` model has `workflow_type: str` and `params: dict[str, object] | None = None`
- [x] `WorkflowRunResponse` model has `workflow_id: str` and `status: WorkflowStatus`
- [x] `POST /workflows/run` creates a `Workflow` record with `status=PENDING` in the database
- [x] Endpoint enqueues `run_workflow` ARQ job with the workflow ID as argument
- [x] Endpoint returns 202 Accepted with `WorkflowRunResponse`
- [x] Gateway lifespan creates `ArqRedis` pool via `arq.connections.create_pool()`, stored on `app.state.arq_pool`
- [x] `ArqRedis` pool replaces the separate `app.state.redis` client (ArqRedis is a Redis superset)
- [x] `get_arq_pool()` dependency returns ArqRedis from `app.state`
- [x] Existing `get_redis()` dependency updated to return from `app.state.arq_pool` (type-compatible)
- [x] Workflow router registered on FastAPI app in `create_app()`
- [x] Health endpoint continues to work (uses ArqRedis for Redis health check)
- [x] No ADK imports anywhere in gateway code
**Validation:**
- `uv run pyright app/gateway/`
- `curl -X POST localhost:8000/workflows/run -H "Content-Type: application/json" -d '{"workflow_type": "echo"}'`

---

### P3.D8: Test Suite
**Files:** `tests/router/__init__.py`, `tests/router/test_router.py`, `tests/events/__init__.py`, `tests/events/test_publisher.py`, `tests/events/test_streams.py`, `tests/lib/test_cache.py`, `tests/lib/__init__.py`, `tests/workers/test_tasks.py` (update), `tests/workers/test_adk.py`, `tests/gateway/test_workflows.py`, `tests/conftest.py` (update)
**Depends on:** P3.D6, P3.D7
**Description:** Tests covering all Phase 3 deliverables. Tests use real infrastructure (PostgreSQL, Redis) per project testing standards — skip when unavailable. Tests requiring LLM calls (ADK pipeline execution, session persistence, 4-scope state) use real LLM APIs — skip when `ANTHROPIC_API_KEY` is not set (same `require_*` marker pattern as `require_postgres`/`require_redis`). No mocking of local infrastructure or LLM calls. The `before_model_callback` tests construct real `CallbackContext`/`LlmRequest` objects (no mocks) — these are pure in-process logic tests, no LLM call needed. Event publisher `translate()` tests construct ADK Event-like objects with the expected attributes (not mocks — real `object` instances with `getattr`-accessible fields).
**Requirements:**
- [x] `require_llm` marker added to `conftest.py`: skips test if `ANTHROPIC_API_KEY` env var is not set
- [x] **Router tests** (no infra needed — pure logic): `select_model(ModelRole.CODE)` returns `"anthropic/claude-sonnet-4-6"`; `select_model(ModelRole.PLAN)` returns `"anthropic/claude-opus-4-6"`; `select_model(ModelRole.CODE, user_override="openai/gpt-5")` returns `"openai/gpt-5"`; `get_fallbacks("anthropic/claude-opus-4-6")` returns list of 2 models
- [x] **before_model_callback tests** (no infra needed — pure logic): callback reads agent name from `callback_context.agent_name`; maps `echo_agent` to `ModelRole.FAST`; sets `llm_request.model` to router result; returns `None`; respects `user:model_override` from state
- [x] **Cache helper tests** (`require_redis`): `cache_set` + `cache_get` round-trips a value; `cache_get` returns `None` on miss; `cache_delete` removes the value; TTL expiry works
- [x] **Stream helper tests** (`require_redis`): `stream_key("abc")` returns `"workflow:abc:events"`; `stream_publish` calls XADD and returns stream ID; `stream_read_range` reads published events
- [x] **Event publisher tests** (`require_redis`): `translate()` maps an ADK Event-like object with `function_call` content to `PipelineEventType.TOOL_CALLED`; `publish()` publishes to correct stream via `stream_publish`; `publish_lifecycle()` publishes event with `WORKFLOW_STARTED` type
- [x] **ADK engine tests** (no infra needed — construction only): `create_echo_agent("anthropic/claude-haiku-4-5-20251001")` returns `LlmAgent` with `name="echo_agent"` and `output_key="agent_response"`; `create_app_container(agent)` returns `App` with `name="autobuilder"`, non-None `events_compaction_config`, non-None `context_cache_config`, non-None `resumability_config`; LoggingPlugin is in default plugins list
- [x] **ADK engine tests** (`require_postgres`): `create_session_service()` returns `DatabaseSessionService` instance that can create a session
- [x] **Worker task tests** (`require_infra`, `require_llm`): `run_workflow` with valid workflow_id updates status to `RUNNING` then `COMPLETED`; with invalid workflow_id raises `NotFoundError`; events appear in Redis Stream `workflow:{id}:events`; error case sets `error_message` on workflow record
- [x] **Gateway route tests** (`require_infra`): `POST /workflows/run` with `{"workflow_type": "echo"}` returns 202 with `workflow_id` in response; request missing `workflow_type` field returns 422
- [x] **Session persistence test** (`require_postgres`, `require_llm`): First invocation writes `agent_response` to session state; second invocation on same `(app_name, user_id, session_id)` tuple retrieves session with `agent_response` in state
- [x] **4-scope state tests** (`require_postgres`, `require_llm`): `temp:` key set in one invocation is NOT present in next invocation; session key (no prefix) persists across invocations; `app:` scope key is accessible; `user:` scope key is accessible across sessions with same user_id
- [x] **App scope initialization test** (`require_postgres`): After worker startup, `app:skill_index` and `app:workflow_registry` exist in `app:` scope state
- [x] All Phase 2 tests continue to pass (no regressions): `uv run pytest tests/ --ignore=tests/phase1`
- [x] All quality gates exit 0: `uv run ruff check .`, `uv run pyright`, `uv run pytest`
**Validation:**
- `uv run pytest tests/ --ignore=tests/phase1 --cov=app -v`

---

## Build Order

```
Batch 1 (parallel): P3.D1, P3.D3
  D1: Config + enums — app/config/settings.py, app/models/enums.py
  D3: Redis cache + stream helpers — app/lib/cache.py, app/events/streams.py

Batch 2 (parallel): P3.D2, P3.D7
  D2: LLM Router + callback — app/router/router.py (depends D1)
  D7: Gateway workflow route — app/gateway/routes/workflows.py, app/gateway/deps.py (depends D1)

Batch 3 (parallel): P3.D4, P3.D5
  D4: Event schema + publisher — app/gateway/models/events.py, app/events/publisher.py (depends D1, D3)
  D5: ADK engine setup — app/workers/adk.py (depends D1, D2)

Batch 4: P3.D6
  D6: Worker pipeline bridge + migration — app/workers/tasks.py, app/workers/settings.py, app/db/models.py (depends D3, D4, D5)

Batch 5: P3.D8
  D8: Test suite — tests/ (depends D6, D7)
```

## Completion Contract Traceability

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | Can enqueue a workflow job from gateway, have worker execute an ADK pipeline | P3.D6, P3.D7, P3.D8 | `POST /workflows/run` returns 202; worker processes job; workflow status updates to COMPLETED |
| 2 | LLM Router selects correct model per task type | P3.D2, P3.D8 | Router unit tests verify correct model for each ModelRole; fallback chains resolve correctly; `before_model_callback` overrides model at runtime |
| 3 | Claude responds reliably via LiteLLM through ADK | P3.D5, P3.D6, P3.D8 | EchoAgent receives prompt, produces response via LiteLLM; `agent_response` key in session state |
| 4 | Session state persists across worker invocations | P3.D5, P3.D6, P3.D8 | Integration test: first invocation writes state via output_key; second invocation reads persisted state from DatabaseSessionService |
| 5 | ADK events translate to gateway events in Redis Streams | P3.D4, P3.D6, P3.D8 | Events appear in Redis Stream `workflow:{id}:events` with PipelineEventType enum values; no ADK types in published events |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| G21 | Anti-corruption translation layer | P3.D4 (outbound), P3.D6 (inbound) |
| D04 | `sessions` table (ADK) | P3.D5 |
| D11 | Job metadata table (ARQ tracking) | P3.D6 |
| E01 | `App` container (`autobuilder`) | P3.D5 |
| E04 | `EventsCompactionConfig` | P3.D5 |
| E05 | `LlmEventSummarizer` (haiku model) | P3.D5 |
| E06 | `ResumabilityConfig` | P3.D5 |
| E07 | `context_cache_config` | P3.D5 |
| E09 | `LoggingPlugin` | P3.D5 |
| E12 | `DatabaseSessionService` integration | P3.D5 |
| E13 | 4-scope state system | P3.D6, P3.D8 |
| E14 | `app:` scope initialization | P3.D6 |
| E15 | App lifecycle hooks (`on_startup`/`on_shutdown`) | P3.D6 |
| W03 | `run_workflow()` ARQ job function | P3.D6 |
| W04 | `create_adk_runner()` factory | P3.D5 |
| W05 | `create_or_resume_session()` | P3.D6 |
| W06 | `translate_event()` | P3.D4 |
| W07 | `publish_to_stream()` | P3.D4 |
| W08 | `update_workflow_state()` | P3.D6 |
| V01 | Per-workflow Redis Stream publishing | P3.D4 |
| V02 | Redis Stream naming convention | P3.D3 |
| R01 | `LlmRouter` module | P3.D2 |
| R02 | Routing rules (static config) | P3.D1, P3.D2 |
| R03 | Fallback chain resolution (3-step) | P3.D2 |
| R04 | `before_model_callback` model override | P3.D2 |
| A44 | `before_model_callback` LLM Router override | P3.D2 |
| A71 | Work session model (long-running ARQ job) | P3.D6 |
| M01 | `temp:` scope handling | P3.D6, P3.D8 |
| M02 | `user:` scope handling | P3.D6, P3.D8 |
| M03 | `app:` scope handling | P3.D6, P3.D8 |
| M04 | Session (no prefix) scope handling | P3.D6, P3.D8 |
| M22 | Routing config cache (long TTL) | P3.D2, P3.D6 |
| M25 | Redis cache helpers (~100 LOC) | P3.D3 |
| M26 | Redis Stream publishers (~100 LOC) | P3.D3 |
| O04 | Context compression (sliding window summarization) | P3.D5 |

*All 35 BOM components assigned to Phase 3 in `07-COMPONENTS.md` are mapped above. Zero unmapped.*

## Research Notes

### ADK Import Paths (Verified against installed package)
```python
# Agents
from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent, ParallelAgent, LoopAgent

# LiteLLM model wrapper
from google.adk.models.lite_llm import LiteLlm

# Events and State
from google.adk.events import Event, EventActions

# Tools
from google.adk.tools.function_tool import FunctionTool

# Session Services
from google.adk.sessions import DatabaseSessionService, InMemorySessionService

# Runner
from google.adk.runners import Runner, InMemoryRunner

# App Container and Configs
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

# Context Cache Config
from google.adk.agents.context_cache_config import ContextCacheConfig

# Plugins
from google.adk.plugins.base_plugin import BasePlugin

# Callbacks
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

# Content types (for messages)
from google.genai.types import Content, Part
```

### Verified API Signatures (from installed package)

**Runner constructor:**
```python
Runner(
    *,
    app: Optional[App] = None,
    app_name: Optional[str] = None,
    agent: Optional[BaseAgent] = None,
    plugins: Optional[List[BasePlugin]] = None,
    artifact_service: Optional[BaseArtifactService] = None,
    session_service: BaseSessionService,
    memory_service: Optional[BaseMemoryService] = None,
    credential_service: Optional[BaseCredentialService] = None,
    plugin_close_timeout: float = 5.0,
    auto_create_session: bool = False,
)
```

**App fields:** `name`, `root_agent`, `plugins`, `events_compaction_config`, `context_cache_config`, `resumability_config`

**EventsCompactionConfig fields:** `summarizer`, `compaction_interval`, `overlap_size`, `token_threshold`, `event_retention_size`

**ResumabilityConfig fields:** `is_resumable`

**ContextCacheConfig fields:** `cache_intervals`, `ttl_seconds`, `min_tokens`

**LlmEventSummarizer constructor:** `LlmEventSummarizer(llm: BaseLlm, prompt_template: Optional[str] = None)`

**DatabaseSessionService constructor:** `DatabaseSessionService(db_url: str)`

**before_model_callback signature:**
```python
def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    # Return None → proceed normally
    # Return LlmResponse → skip LLM call
```

**CallbackContext attributes:** `agent_name`, `state`, `session`, `user_content`, `invocation_id`, `run_config`, `user_id`

**LlmRequest fields (mutable):** `model`, `contents`, `config`, `tools_dict`, `cache_config`, `cache_metadata`

### Critical ADK Patterns (Phase 1 Findings)
1. **State writes**: Only `Event(actions=EventActions(state_delta={...}))` persists state. Direct `ctx.session.state["key"] = val` does NOT persist.
2. **State reads**: `ctx.session.state.get("key")` works within the same execution.
3. **InMemoryRunner quirk**: `runner.auto_create_session = True` must be set after construction. Runner with `auto_create_session=False` (default) requires explicit session creation.
4. **BaseAgent override**: `_run_async_impl` needs `# type: ignore[override]` for pyright strict.
5. **FunctionTool import**: `from google.adk.tools.function_tool import FunctionTool` (not `from google.adk.tools`).

### Hierarchical Supervision
Phase 3 validates ADK infrastructure with EchoAgent. The production architecture uses a three-tier hierarchy:
- **Director** (LlmAgent, opus) -- stateless config object, recreated per invocation; formation artifacts in `user:` scope; delegates to PMs via `sub_agents` + `transfer_to_agent`
- **PM** (LlmAgent, sonnet) -- per-project manager, IS the outer loop via tools (`select_ready_batch`), `after_agent_callback` (`verify_batch_completion`), `checkpoint_project` (`after_agent_callback` on DeliverablePipeline, persists state via `CallbackContext`), and `run_regression_tests` (`RegressionTestAgent` CustomAgent in pipeline after each batch, reads PM regression policy from session state); stateless config object same as Director
- **Workers** (LlmAgent + CustomAgent) -- deliverable execution

Multi-session architecture: chat sessions for CEO interaction, work sessions per project for autonomous oversight. Cross-session bridge via `app:`/`user:` state + MemoryService + Redis Streams.

Project config is a DB entity -- no new ADK scope. Existing 4 ADK scopes are sufficient: `app:` = global, `user:` = CEO prefs + Director formation artifacts (identity, CEO profile, operating contract), session = per-session, `temp:` = scratch.

The `create_app_container(root_agent)` factory in Phase 3 accommodates this -- Phase 5 passes Director instead of EchoAgent. See `.discussion/260214_hierarchical-supervision.md`, `.discussion/260216_terminology-skills-pm.md`.

### Runner Execution Pattern
```python
from google.genai.types import Content, Part

# Create shared resources (worker startup)
session_service = DatabaseSessionService(db_url=settings.db_url)
router = LlmRouter.from_settings(settings)

# Per-execution (in run_workflow)
callback = create_model_override_callback(router)
echo_agent = create_echo_agent(model=router.select_model(ModelRole.FAST), before_model_callback=callback)
app = create_app_container(root_agent=echo_agent)
runner = Runner(app=app, session_service=session_service)

# Create or resume session
session = await session_service.get_session(
    app_name="autobuilder", user_id="system", session_id=workflow_id
)
if session is None:
    session = await session_service.create_session(
        app_name="autobuilder", user_id="system", session_id=workflow_id
    )

# Execute and stream events
message = Content(parts=[Part(text="Execute the workflow")])
async for event in runner.run_async(
    user_id="system", session_id=session.id, new_message=message
):
    translated = publisher.translate(event, workflow_id)
    if translated is not None:
        await publisher.publish(translated)
```

### DatabaseSessionService Tables (Auto-Created)
ADK creates 5 tables with its own SQLAlchemy metadata (separate from AutoBuilder's `Base`):
- `adk_internal_metadata` — schema version tracking
- `sessions` — session records (app_name + user_id + id composite PK, state as JSON)
- `events` — event history per session (event_data as JSON)
- `app_states` — app-scoped state (cross-user, cross-session)
- `user_states` — user-scoped state (cross-session per user)

Tables are created lazily on first operation. No Alembic migration needed.

### ARQ Worker Context Pattern
```python
async def startup(ctx: dict[str, object]) -> None:
    """Worker on_startup — initialize shared ADK resources."""
    setup_logging(get_settings().log_level)
    settings = get_settings()
    ctx["session_service"] = DatabaseSessionService(db_url=settings.db_url)
    router = LlmRouter.from_settings(settings)
    ctx["llm_router"] = router
    # Cache routing config (M22)
    redis = cast(ArqRedis, ctx["redis"])
    await router.cache_to_redis(redis)
    # Initialize app: scope (E14) — idempotent
    session_service = cast(DatabaseSessionService, ctx["session_service"])
    # ... initialize app:skill_index, app:workflow_registry if not present

async def shutdown(ctx: dict[str, object]) -> None:
    """Worker on_shutdown — cleanup."""
    pass  # session_service cleanup if needed

async def run_workflow(ctx: dict[str, object], workflow_id: str) -> dict[str, str]:
    session_service = cast(DatabaseSessionService, ctx["session_service"])
    router = cast(LlmRouter, ctx["llm_router"])
    redis = cast(ArqRedis, ctx["redis"])  # Provided by ARQ automatically
    publisher = EventPublisher(redis)
    # ... create agent, app, runner, execute
```

### ArqRedis in Gateway
```python
from arq.connections import create_pool, RedisSettings, ArqRedis

# In lifespan startup
arq_pool = await create_pool(RedisSettings(host=..., port=...))
app.state.arq_pool = arq_pool

# In lifespan shutdown
await arq_pool.aclose()

# In route handler
await arq_pool.enqueue_job("run_workflow", workflow_id=str(workflow.id))
```

### Existing Patterns to Follow
- **Enums**: `enum.StrEnum` with values matching names (`app/models/enums.py`)
- **BaseModel**: Inherit from `app.models.base.BaseModel` (has `from_attributes=True`, `strict=True`)
- **Settings**: Access via `get_settings()` singleton from `app.config`
- **Logging**: `get_logger("module.name")` from `app.lib.logging`
- **Exceptions**: Raise `AutoBuilderError` subclasses from `app.lib.exceptions`
- **DB Sessions**: Use `async with session_factory() as session` pattern
- **Dependency Injection**: FastAPI `Depends()` via `app.state`
- **Error Handling**: Middleware catches `AutoBuilderError` → structured JSON response
