# Phase 3 Spec: ADK Engine Integration
*Generated: 2026-02-14*

## Overview

Phase 3 wires Google ADK into the production infrastructure built in Phase 2. After this phase, the system can receive a workflow execution request through the gateway, enqueue it to an ARQ worker, execute an ADK agent pipeline with Claude via LiteLLM, persist session state to PostgreSQL via DatabaseSessionService, translate ADK events into gateway-native event objects, and publish them to Redis Streams. This is the critical integration layer between the API-first gateway and the ADK orchestration engine.

This phase directly advances four core vision differentiators: **Multi-model orchestration** (#4) — the LLM Router selects models by task type and complexity, with cross-provider fallback chains. **API-first architecture** (#6) — the anti-corruption layer ensures ADK types never leak through the gateway API. **Out-of-process execution** (#7) — workflow pipelines run in ARQ workers, triggered by gateway job enqueueing. **Autonomous completion** (#1) — session state persistence enables workflows to maintain context across invocations, the foundation for the autonomous "run until done" loop.

Key constraints: ADK types never appear in gateway API models or route handlers. All ADK interaction happens inside worker processes. The anti-corruption layer translates in both directions: gateway commands → ADK Runner calls (inbound), ADK Events → Redis Stream messages (outbound). Phase 3 uses a minimal test agent (`EchoAgent` — an `LlmAgent` with simple instructions) to validate the full stack; real agent definitions come in Phase 5.

## Features

- **LLM Router** — Static routing mapping task type × complexity to LiteLLM model strings, with 3-step fallback chain resolution (user override → chain → default)
- **ADK App container + Runner factory** — App class with EventsCompactionConfig and ResumabilityConfig; Runner creation with DatabaseSessionService for PostgreSQL-backed session persistence
- **Anti-corruption layer (inbound)** — Gateway workflow commands translate to ADK Runner calls inside worker tasks
- **Anti-corruption layer (outbound)** — ADK events translate to gateway-native PipelineEvent objects, published to per-workflow Redis Streams
- **Worker pipeline bridge** — `run_workflow` ARQ task that creates/resumes ADK sessions, runs pipelines, publishes translated events, and updates workflow status in the database
- **Gateway workflow endpoint** — `POST /workflows/run` enqueues workflow execution jobs via ArqRedis, returns 202 Accepted
- **Event infrastructure** — PipelineEvent schema and Redis Stream publisher for event distribution
- **Session state persistence** — ADK 4-scope state operational via DatabaseSessionService; state writes persist to PostgreSQL across invocations

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

# App provides: EventsCompactionConfig, ResumabilityConfig
# Runner provides: session management, event streaming
```

Phase 3 uses EchoAgent as root_agent for infrastructure validation. In production, Director (LlmAgent, opus) becomes the root_agent with PM sub_agents via `sub_agents` + `transfer_to_agent`. Director is a stateless config object recreated per invocation -- all persistent state lives in DatabaseSessionService, personality in `user:` scope. The `create_app_container(root_agent)` factory pattern supports this transition -- only the caller changes.

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

### DD-5: LLM Router — Configuration via Settings
The router loads defaults from `app/config/settings.py` via `AUTOBUILDER_DEFAULT_*_MODEL` env vars (code, plan, review, fast). Fallback chains are defined in code — they change rarely and benefit from type safety. The router is a stateless lookup with no I/O.

Phase 3 implements static routing only. The `before_model_callback` integration pattern (runtime model override) is deferred to Phase 5 when real agents exist — EchoAgent uses a fixed model. Adaptive routing with cost/latency tracking deferred to Phase 11.

```python
router = LlmRouter.from_settings(get_settings())
model = router.select_model(TaskType.CODE)  # → "anthropic/claude-sonnet-4-5-20250929"
model = router.select_model(TaskType.PLAN, user_override="openai/gpt-5")  # → user override wins
```

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
Events are published to per-workflow streams: `workflow:{workflow_id}:events`. Stream entry IDs are auto-generated by Redis (timestamp-based), mapping naturally to SSE event IDs for replay support (Phase 10). One stream per workflow provides isolation and simplifies cleanup of completed workflows.

### DD-8: Gateway Job Enqueueing via ArqRedis
The gateway lifespan creates an `ArqRedis` pool (via `arq.connections.create_pool()`) for job enqueueing. `ArqRedis` extends `redis.asyncio.Redis`, so it supports both job enqueueing and general Redis operations. Stored on `app.state.arq_pool`. A new dependency `get_arq_pool()` provides FastAPI injection.

The existing `app.state.redis` client is **replaced** by `app.state.arq_pool` since ArqRedis is a Redis superset — no need for two separate clients. The `get_redis()` dependency returns the ArqRedis instance (type-compatible with Redis). Health checks use the same pool.

## Deliverables

### P3.D1: Configuration Extensions + Domain Enums
**Files:** `app/config/settings.py` (update), `app/models/enums.py` (update), `app/models/__init__.py` (update)
**Depends on:** —
**Description:** Add LLM model default settings for each task type and new domain enums for LLM routing and event classification. Settings fields use `AUTOBUILDER_DEFAULT_*_MODEL` env vars with defaults pointing to Anthropic models per `06-PROVIDERS.md`.
**Requirements:**
- [ ] `Settings` has `default_code_model: str` defaulting to `"anthropic/claude-sonnet-4-5-20250929"`
- [ ] `Settings` has `default_plan_model: str` defaulting to `"anthropic/claude-opus-4-6"`
- [ ] `Settings` has `default_review_model: str` defaulting to `"anthropic/claude-sonnet-4-5-20250929"`
- [ ] `Settings` has `default_fast_model: str` defaulting to `"anthropic/claude-haiku-4-5-20251001"`
- [ ] `TaskType` enum (StrEnum): `CODE`, `PLAN`, `REVIEW`, `FAST` — values match names
- [ ] `PipelineEventType` enum (StrEnum): `WORKFLOW_STARTED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `AGENT_STARTED`, `AGENT_COMPLETED`, `TOOL_CALLED`, `TOOL_RESULT`, `STATE_UPDATED`, `ERROR` — values match names
- [ ] Both enums exported from `app.models`
- [ ] Settings fields loadable from env vars with `AUTOBUILDER_` prefix
**Validation:**
- `uv run pyright app/config/ app/models/`

---

### P3.D2: LLM Router — Static Routing + Fallback Chains
**Files:** `app/router/router.py`, `app/router/__init__.py` (update)
**Depends on:** P3.D1
**Description:** `LlmRouter` class that maps `TaskType` to LiteLLM model strings using configuration from Settings. Implements 3-step fallback chain resolution: user override → fallback chain → default. Phase 3 fallback chains define Anthropic-tier degradation paths (opus → sonnet → haiku). Cross-provider fallbacks (Anthropic → OpenAI → Google per `06-PROVIDERS.md`) deferred to Phase 11 (adaptive routing). A `from_settings()` class method creates the router from application settings. The router is a stateless, synchronous lookup — no API calls, no I/O.
**Requirements:**
- [ ] `LlmRouter.select_model(task_type: TaskType, user_override: str | None = None) -> str` returns model string matching Settings defaults: `CODE`→`"anthropic/claude-sonnet-4-5-20250929"`, `PLAN`→`"anthropic/claude-opus-4-6"`, `REVIEW`→`"anthropic/claude-sonnet-4-5-20250929"`, `FAST`→`"anthropic/claude-haiku-4-5-20251001"`
- [ ] When `user_override` is a non-None string, `select_model()` returns that string regardless of task_type
- [ ] Default models per TaskType sourced from Settings fields (not hardcoded)
- [ ] Fallback chains: opus→`["anthropic/claude-sonnet-4-5-20250929", "anthropic/claude-haiku-4-5-20251001"]`, sonnet→`["anthropic/claude-haiku-4-5-20251001"]`, haiku→`[]` (empty, no fallback)
- [ ] `LlmRouter.get_fallbacks(model: str) -> list[str]` returns the ordered fallback list for a model string; returns `[]` for unknown models
- [ ] `LlmRouter.from_settings(settings: Settings) -> LlmRouter` creates router from settings defaults
- [ ] All methods synchronous (pure lookup, no I/O)
- [ ] Importable as `from app.router import LlmRouter`
**Validation:**
- `uv run pyright app/router/`

---

### P3.D3: Gateway Event Schema + Redis Stream Publisher
**Files:** `app/gateway/models/events.py`, `app/events/publisher.py`, `app/events/__init__.py` (update), `app/gateway/models/__init__.py` (update)
**Depends on:** P3.D1
**Description:** `PipelineEvent` Pydantic model defining the gateway-native event payload — ADK-agnostic, suitable for SSE and webhook consumers. `EventPublisher` class that translates ADK Event objects into PipelineEvent instances and publishes them to per-workflow Redis Streams. The translator inspects ADK Event fields (`author`, `content`, `actions`, `error_code`) to determine the appropriate `PipelineEventType`. Stream key pattern: `workflow:{workflow_id}:events`.
**Requirements:**
- [ ] `PipelineEvent` model has fields: `event_type: PipelineEventType`, `workflow_id: str`, `timestamp: datetime`, `agent_name: str | None`, `content: str | None`, `metadata: dict[str, object]`
- [ ] `PipelineEvent` inherits from `app.models.base.BaseModel`
- [ ] `EventPublisher.__init__(redis: Redis)` accepts a Redis client instance
- [ ] `EventPublisher.translate(adk_event: object, workflow_id: str) -> PipelineEvent | None` converts ADK Event to gateway event, returns `None` for unclassified events (skipped) — `adk_event` typed as `object` at the module boundary (ADK types never in gateway model signatures)
- [ ] Translation maps per DD-6: `error_code` present→`ERROR`, `function_call` in content→`TOOL_CALLED`, `function_response`→`TOOL_RESULT`, `state_delta` present→`STATE_UPDATED`, final response→`AGENT_COMPLETED`, first event for author→`AGENT_STARTED`, all others→`None` (skip)
- [ ] `EventPublisher.publish(event: PipelineEvent) -> None` publishes to Redis Stream `workflow:{event.workflow_id}:events` via `XADD`
- [ ] `EventPublisher.publish_lifecycle(workflow_id: str, event_type: PipelineEventType) -> None` publishes synthetic lifecycle events (STARTED, COMPLETED, FAILED)
- [ ] Published events are JSON-serialized with `model_dump_json()`
- [ ] `app/events/publisher.py` has zero `google.adk` imports — translation uses `getattr()` / `hasattr()` only (ACL boundary)
**Validation:**
- `uv run pyright app/events/ app/gateway/models/`

---

### P3.D4: ADK Engine Setup — App Container + Session Service + Runner
**Files:** `app/workers/adk.py`
**Depends on:** P3.D1, P3.D2
**Description:** Factory functions for ADK infrastructure. `create_session_service()` initializes DatabaseSessionService with the PostgreSQL URL. `create_app_container()` builds an ADK App with EventsCompactionConfig and ResumabilityConfig. `create_runner()` wraps the App in a Runner with a session service for programmatic execution. Also defines the minimal `EchoAgent` — an LlmAgent used for Phase 3 validation that responds to prompts and writes to state via `output_key`.
**Requirements:**
- [ ] `create_session_service(db_url: str) -> DatabaseSessionService` creates a session service connected to PostgreSQL (ADK uses `create_async_engine` internally — `postgresql+asyncpg://` URLs from `Settings.db_url` work directly)
- [ ] `create_app_container(root_agent: BaseAgent) -> App` creates App with `name="autobuilder"`, `EventsCompactionConfig(compaction_interval=5, overlap_size=1)` and `ResumabilityConfig(is_resumable=True)`
- [ ] App container uses `LlmEventSummarizer` with haiku model for context compression
- [ ] `create_runner(app: App, session_service: DatabaseSessionService) -> Runner` creates a Runner from the App
- [ ] `create_echo_agent(model: str) -> LlmAgent` creates a test agent with `name="echo_agent"`, `output_key="agent_response"`, and a simple instruction string
- [ ] Echo agent uses `LiteLlm(model=model)` for the LLM backend
- [ ] `create_session_service` returns `DatabaseSessionService`, `create_app_container` returns `App`, `create_runner` returns `Runner`, `create_echo_agent` returns `LlmAgent` — all with explicit return type annotations
- [ ] Module imports only from `google.adk.*`, `app.config`, `app.router`, and stdlib — never from `app.gateway` (ACL boundary)
**Validation:**
- `uv run pyright app/workers/adk.py`

---

### P3.D5: Worker Pipeline Bridge — run_workflow Task
**Files:** `app/workers/tasks.py` (update), `app/workers/settings.py` (update), `app/workers/__init__.py` (update)
**Depends on:** P3.D3, P3.D4
**Description:** ARQ task function `run_workflow` that orchestrates the full execution cycle. On invocation: reads the workflow record from the database, updates status to RUNNING, creates or resumes an ADK session (using `workflow.id` as `session_id`), instantiates an App container + Runner with the EchoAgent, iterates the ADK event stream translating and publishing each event to Redis Streams, and updates the workflow status to COMPLETED or FAILED on conclusion. Worker startup (`on_startup`) initializes shared resources (DatabaseSessionService, LlmRouter) stored in the worker context.
**Requirements:**
- [ ] `run_workflow(ctx: dict[str, object], workflow_id: str) -> dict[str, str]` is async and registered in `WorkerSettings.functions`
- [ ] Task reads workflow record from database; raises `NotFoundError(message=f"Workflow {workflow_id} not found")` if not found
- [ ] Task updates workflow `status` to `RUNNING` (with `started_at` timestamp) before pipeline execution
- [ ] Task creates or resumes ADK session using `app_name="autobuilder"`, `user_id="system"`, `session_id=workflow_id`
- [ ] Task creates App container with EchoAgent (model from LlmRouter) and Runner with DatabaseSessionService
- [ ] ADK events are translated via `EventPublisher.translate()` and published to Redis Stream
- [ ] `WORKFLOW_STARTED` event published before pipeline execution; `WORKFLOW_COMPLETED` or `WORKFLOW_FAILED` published after
- [ ] On success: workflow `status` updated to `COMPLETED` with `completed_at` timestamp
- [ ] On error: workflow `status` updated to `FAILED`, `WORKFLOW_FAILED` event published with error message in `metadata`, exception logged at `ERROR` level with `workflow_id` and stack trace
- [ ] Worker `on_startup` initializes `DatabaseSessionService` and `LlmRouter` in worker context (`ctx`)
- [ ] Worker `on_shutdown` disposes of session service resources
- [ ] Existing tasks (`test_task`, `heartbeat`) remain functional and registered
**Validation:**
- `uv run pyright app/workers/`

---

### P3.D6: Gateway Workflow Route + Job Enqueueing
**Files:** `app/gateway/routes/workflows.py`, `app/gateway/models/workflows.py`, `app/gateway/deps.py` (update), `app/gateway/main.py` (update)
**Depends on:** P3.D1
**Description:** Minimal workflow API endpoint: `POST /workflows/run` accepts a workflow type and optional params, creates a workflow record in the database with status PENDING, enqueues an ARQ `run_workflow` job, and returns 202 Accepted. Gateway lifespan updated to create an ArqRedis pool (replacing the separate Redis client per DD-8). New dependency `get_arq_pool()` provides FastAPI injection.
**Requirements:**
- [ ] `WorkflowRunRequest` model has `workflow_type: str` and `params: dict[str, object] | None = None`
- [ ] `WorkflowRunResponse` model has `workflow_id: str` and `status: WorkflowStatus`
- [ ] `POST /workflows/run` creates a `Workflow` record with `status=PENDING` in the database
- [ ] Endpoint enqueues `run_workflow` ARQ job with the workflow ID as argument
- [ ] Endpoint returns 202 Accepted with `WorkflowRunResponse`
- [ ] Gateway lifespan creates `ArqRedis` pool via `arq.connections.create_pool()`, stored on `app.state.arq_pool`
- [ ] `ArqRedis` pool replaces the separate `app.state.redis` client (ArqRedis is a Redis superset)
- [ ] `get_arq_pool()` dependency returns ArqRedis from `app.state`
- [ ] Existing `get_redis()` dependency updated to return from `app.state.arq_pool` (type-compatible)
- [ ] Workflow router registered on FastAPI app in `create_app()`
- [ ] Health endpoint continues to work (uses ArqRedis for Redis health check)
- [ ] No ADK imports anywhere in gateway code
**Validation:**
- `uv run pyright app/gateway/`
- `curl -X POST localhost:8000/workflows/run -H "Content-Type: application/json" -d '{"workflow_type": "echo"}'`

---

### P3.D7: Test Suite
**Files:** `tests/router/__init__.py`, `tests/router/test_router.py`, `tests/events/__init__.py`, `tests/events/test_publisher.py`, `tests/workers/test_tasks.py` (update), `tests/gateway/test_workflows.py`, `tests/conftest.py` (update)
**Depends on:** P3.D5, P3.D6
**Description:** Unit and integration tests covering all Phase 3 deliverables. LLM calls are mocked in unit tests — no live API keys required for CI. Redis Stream operations tested with a real or mocked Redis client. Database operations use the existing test fixtures from Phase 2. Tests verify the full request flow: gateway enqueue → worker execution → event publication → status update.
**Requirements:**
- [ ] **Router tests**: `select_model(TaskType.CODE)` returns `"anthropic/claude-sonnet-4-5-20250929"`; `select_model(TaskType.PLAN)` returns `"anthropic/claude-opus-4-6"`; `select_model(TaskType.CODE, user_override="openai/gpt-5")` returns `"openai/gpt-5"`; `get_fallbacks("anthropic/claude-opus-4-6")` returns list of 2 models
- [ ] **Event publisher tests**: `translate()` maps a mock ADK event with `function_call` content to `PipelineEventType.TOOL_CALLED`; `publish()` calls `XADD` on stream key `workflow:{id}:events`; `publish_lifecycle()` publishes event with `WORKFLOW_STARTED` type
- [ ] **Worker task tests**: `run_workflow` with valid workflow_id updates status to `RUNNING` then `COMPLETED`; with invalid workflow_id raises `NotFoundError`; events appear in Redis Stream `workflow:{id}:events`
- [ ] **Gateway route tests**: `POST /workflows/run` with `{"workflow_type": "echo"}` returns 202 with `workflow_id` in response; request missing `workflow_type` field returns 422
- [ ] **ADK engine tests**: `create_session_service()` returns `DatabaseSessionService` instance; `create_echo_agent("anthropic/claude-haiku-4-5-20251001")` returns `LlmAgent` with `name="echo_agent"` and `output_key="agent_response"`; `create_app_container(agent)` returns `App` with `name="autobuilder"` and non-None `events_compaction_config`
- [ ] **Session persistence test**: First invocation writes `agent_response` to session state; second invocation on same `(app_name, user_id, session_id)` tuple retrieves session with `agent_response` in state
- [ ] All Phase 2 tests continue to pass (no regressions): `uv run pytest tests/ --ignore=tests/phase1`
- [ ] All quality gates exit 0: `uv run ruff check .`, `uv run pyright`, `uv run pytest`
**Validation:**
- `uv run pytest tests/ --ignore=tests/phase1 --cov=app -v`

---

## Build Order

```
Batch 1: P3.D1
  D1: Config + enums — app/config/settings.py, app/models/enums.py

Batch 2 (parallel): P3.D2, P3.D3, P3.D6
  D2: LLM Router — app/router/router.py (depends D1)
  D3: Event schema + publisher — app/gateway/models/events.py, app/events/publisher.py (depends D1)
  D6: Gateway workflow route — app/gateway/routes/workflows.py, app/gateway/deps.py (depends D1)

Batch 3: P3.D4
  D4: ADK engine setup — app/workers/adk.py (depends D1, D2)

Batch 4: P3.D5
  D5: Worker pipeline bridge — app/workers/tasks.py, app/workers/settings.py (depends D3, D4)

Batch 5: P3.D7
  D7: Test suite — tests/ (depends D5, D6)
```

## Completion Contract Traceability

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | Can enqueue a workflow job from gateway, have worker execute an ADK pipeline | P3.D5, P3.D6, P3.D7 | `POST /workflows/run` returns 202; worker processes job; workflow status updates to COMPLETED |
| 2 | LLM Router selects correct model per task type | P3.D2, P3.D7 | Router unit tests verify correct model for each TaskType; fallback chains resolve correctly |
| 3 | Claude responds reliably via LiteLLM through ADK | P3.D4, P3.D5, P3.D7 | EchoAgent receives prompt, produces response via LiteLLM; `agent_response` key in session state |
| 4 | Session state persists across worker invocations | P3.D4, P3.D5, P3.D7 | Integration test: first invocation writes state via output_key; second invocation reads persisted state from DatabaseSessionService |
| 5 | ADK events translate to gateway events in Redis Streams | P3.D3, P3.D5, P3.D7 | Events appear in Redis Stream `workflow:{id}:events` with PipelineEventType enum values; no ADK types in published events |

## Research Notes

### ADK Import Paths (Verified)
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

# Content types (for messages)
from google.genai.types import Content, Part
```

### Critical ADK Patterns (Phase 1 Findings)
1. **State writes**: Only `Event(actions=EventActions(state_delta={...}))` persists state. Direct `ctx.session.state["key"] = val` does NOT persist.
2. **State reads**: `ctx.session.state.get("key")` works within the same execution.
3. **InMemoryRunner quirk**: `runner.auto_create_session = True` must be set after construction. Verify if this applies to Runner with DatabaseSessionService.
4. **BaseAgent override**: `_run_async_impl` needs `# type: ignore[override]` for pyright strict.
5. **FunctionTool import**: `from google.adk.tools.function_tool import FunctionTool` (not `from google.adk.tools`).

### Hierarchical Supervision
Phase 3 validates ADK infrastructure with EchoAgent. The production architecture uses a three-tier hierarchy:
- **Director** (LlmAgent, opus) -- stateless config object, recreated per invocation; personality in `user:` scope, seeded from config on first login; delegates to PMs via `sub_agents` + `transfer_to_agent`
- **PM** (LlmAgent, sonnet) -- per-project manager, IS the outer loop via tools (`select_ready_batch`), `after_agent_callback` (`verify_batch_completion`), `checkpoint_project` (`after_agent_callback` on DeliverablePipeline, persists state via `CallbackContext`), and `run_regression_tests` (`RegressionTestAgent` CustomAgent in pipeline after each batch, reads PM regression policy from session state); stateless config object same as Director
- **Workers** (LlmAgent + CustomAgent) -- deliverable execution

Multi-session architecture: chat sessions for CEO interaction, work sessions per project for autonomous oversight. Cross-session bridge via `app:`/`user:` state + MemoryService + Redis Streams.

Project config is a DB entity -- no new ADK scope. Existing 4 ADK scopes are sufficient: `app:` = global, `user:` = CEO prefs + Director personality, session = per-session, `temp:` = scratch.

`AutoBuilderToolset(BaseToolset)` for per-role tool vending via ADK-native `get_tools(readonly_context)`. Tools organized by function type in `app/tools/`. Cascading permission config CEO->Director->PM->Worker.

The `create_app_container(root_agent)` factory in Phase 3 accommodates this -- Phase 5 passes Director instead of EchoAgent. See `.discussion/260214_hierarchical-supervision.md`, `.discussion/260216_terminology-skills-pm.md`.

### Runner Execution Pattern
```python
from google.genai.types import Content, Part

# Create shared resources (worker startup)
session_service = DatabaseSessionService(db_url=settings.db_url)
router = LlmRouter.from_settings(settings)

# Per-execution (in run_workflow)
echo_agent = create_echo_agent(model=router.select_model(TaskType.FAST))
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
    await publisher.publish(translated)
```

### Runner Constructor
```python
# Runner accepts app= parameter, extracts configs from App
runner = Runner(
    app=app_instance,              # Gets root_agent, compaction, resumability from App
    session_service=session_svc,   # PostgreSQL-backed session persistence
)

# Or without App (no compaction/resumability)
runner = Runner(
    agent=my_agent,
    app_name="autobuilder",
    session_service=session_svc,
)
```

### ADK Event Object Structure
```python
class Event:
    id: str                          # Unique event ID
    author: str                      # 'user' or agent name
    invocation_id: str               # Tracks full interaction cycle
    timestamp: float                 # POSIX timestamp
    content: Content | None          # Text, function calls, or results
    partial: bool | None             # Streaming incomplete
    turn_complete: bool | None       # LLM turn complete
    actions: EventActions            # Side effects (state_delta, etc.)
    usage_metadata: UsageMetadata | None  # Token counts
    error_code: str | None
    error_message: str | None

class EventActions:
    state_delta: dict[str, object]   # State updates
    artifact_delta: dict[str, int]   # Artifact changes
    transfer_to_agent: str | None    # Agent transfer
    escalate: bool | None            # Escalation flag

# Useful method
event.is_final_response()  # True if this is the agent's final output
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
    ctx["llm_router"] = LlmRouter.from_settings(settings)

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

### Redis Streams Commands
```python
# Publish event
await redis.xadd(
    f"workflow:{workflow_id}:events",
    {"data": event.model_dump_json()},
)

# Read events (for future SSE/consumer use)
events = await redis.xrange(
    f"workflow:{workflow_id}:events",
    min=last_event_id or "-",
    max="+",
)
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
