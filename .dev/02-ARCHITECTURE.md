# AutoBuilder Architecture

## 1. System Overview

AutoBuilder is an autonomous agentic workflow system that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. The system exposes an API-first FastAPI gateway that owns the external contract. Google ADK runs behind an anti-corruption layer as the internal orchestration engine -- clients never interact with ADK directly. Workflow execution is out-of-process: the gateway enqueues work via ARQ, Redis-backed workers execute pipelines, and Redis Streams distribute events to consumers (SSE endpoints, webhook dispatchers, audit loggers).

The architecture is organized around five layers:

1. **Interface layer** -- CLI (typer) and web dashboard (React SPA), both pure API consumers
2. **Gateway layer** -- FastAPI REST + SSE, AutoBuilder-owned routes/models/contract
3. **Worker layer** -- ARQ async workers executing ADK pipelines out-of-process
4. **Engine layer** -- ADK orchestration (batch scheduling, pipelines, agents, tools, state)
5. **Infrastructure layer** -- Redis (queue + events + cache + cron), database (SQLAlchemy + Alembic), filesystem

All agent types -- LLM and deterministic -- participate in the same ADK event stream, state system, and observability infrastructure. While auto-code is the first workflow, the architecture is workflow-agnostic -- pipeline stages, quality gates, and artifact types are defined per workflow, not hardcoded.

---

## 2. System Architecture Diagram

```mermaid
flowchart TB
    subgraph INTERFACE["INTERFACE LAYER"]
        CLI["CLI (typer)\n- Launch workflows\n- Check status\n- Intervene\n- Scripting/automation"]
        Dashboard["Web Dashboard (React 19 SPA)\n- Rich observability\n- Pipeline visualization\n- Real-time event stream\n- Static build (Vite)"]
    end

    subgraph GATEWAY["GATEWAY LAYER"]
        FastAPI["FastAPI Gateway\n\nRoutes:\n- POST /workflows/{id}/run\n- GET /workflows/{id}/status\n- POST /workflows/{id}/intervene\n- GET /events/stream\n- GET /deliverables\n- POST /specs\n\nModels: Pydantic (auto-generates OpenAPI)\nAuth: TBD (Phase 2)"]
        ARQ[("ARQ Queue\n(Redis)")]
        DB[("SQLAlchemy 2.0 async\n(via gateway only)")]
    end

    subgraph WORKER["WORKER LAYER"]
        subgraph ARQWorkers["ARQ Workers (async, out-of-process)"]
            ACL["Anti-Corruption Layer\n- Translates gateway commands to ADK Runner calls\n- Translates ADK events to Redis Stream messages\n- ADK is an internal implementation detail"]
            ADK["ADK Engine\n- App container (context compression, resumability)\n- BatchOrchestrator (outer loop)\n- DeliverablePipeline (inner sequential agent)\n- LLM agents + deterministic agents\n- LLM Router (LiteLLM)"]
            ACL --> ADK
        end
        Streams[("Redis Streams")]
        Database[("Database\n(SQLAlchemy)")]
        Filesystem[("Filesystem\n(artifacts, git worktrees)")]
    end

    subgraph EVENTS["EVENT DISTRIBUTION LAYER"]
        SSE["SSE Endpoint Consumer\nGateway reads stream,\npushes to connected clients"]
        Webhook["Webhook Dispatcher Consumer\nReads events, dispatches via\nhttpx to registered listeners"]
        Audit["Audit Logger Consumer\nReads events, writes to DB\nfor compliance and debugging"]
    end

    CLI & Dashboard -->|"REST + SSE (HTTP)"| FastAPI
    FastAPI -->|enqueue| ARQ
    FastAPI -->|query| DB
    ARQ --> ARQWorkers
    ADK -->|publish events| Streams
    ADK -->|read/write state| Database
    ADK -->|read/write| Filesystem
    Streams --> SSE & Webhook & Audit
```

---

## 3. Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant Redis/ARQ
    participant Worker
    participant Redis Streams

    Client->>Gateway: POST /workflows/run
    Gateway->>Redis/ARQ: enqueue job
    Gateway-->>Client: 202 Accepted
    Redis/ARQ->>Worker: dequeue + execute

    Client->>Gateway: GET /events/stream
    Worker->>Redis Streams: publish events
    Gateway->>Redis Streams: read stream
    Gateway-->>Client: SSE: event data
    Worker->>Redis Streams: publish events
    Gateway-->>Client: SSE: event data

    Client->>Gateway: GET /workflows/status
    Note right of Gateway: query DB
    Gateway-->>Client: 200 { status }
```

**SSE reconnection**: Clients send `Last-Event-ID` header on reconnect. The SSE endpoint replays missed events from the Redis Stream starting from that ID, then resumes live streaming. No events are lost.

---

## 4. Gateway Layer

### Anti-Corruption Pattern

The gateway owns the external API contract. ADK is an internal implementation detail:

- **Gateway models**: Pydantic models define the API contract (request/response schemas)
- **ADK models**: Internal to workers; never exposed to clients
- **Translation**: The anti-corruption layer in workers translates between gateway commands and ADK Runner/SessionService calls
- **Swappable**: ADK could be replaced with another orchestration engine without changing the client-facing API

`get_fast_api_app()` and `adk web` are local development tools only. They are not part of the production architecture.

### Route Structure

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/specs` | Submit a specification for decomposition |
| `POST` | `/workflows/{id}/run` | Enqueue workflow execution |
| `GET` | `/workflows/{id}/status` | Query workflow state |
| `POST` | `/workflows/{id}/intervene` | Human-in-the-loop intervention |
| `GET` | `/deliverables` | Query deliverables (filter by workflow, status) |
| `GET` | `/deliverables/{id}` | Get deliverable detail |
| `GET` | `/events/stream` | SSE endpoint for real-time events |

### Transport

- **REST** for commands and queries (standard request/response)
- **SSE** for real-time event streaming (server-push, reconnectable)
- **No GraphQL** -- REST is sufficient; GraphQL adds complexity without benefit for this use case
- **No gRPC** at gateway layer -- internal service communication is in-process or via Redis
- **WebRTC** reserved for future voice interface

### Type Safety Chain

```mermaid
flowchart TB
    Pydantic["Pydantic models (Python)"]
    OpenAPI["OpenAPI spec (JSON)"]
    HeyAPI["hey-api"]
    TSClient["Typed TypeScript client"]
    TanStack["TanStack Query hooks (generated)"]
    React["React Dashboard\n(fully typed, no manual API layer)"]

    Pydantic -->|"auto-generated by FastAPI"| OpenAPI
    OpenAPI -->|"build-time codegen"| HeyAPI
    HeyAPI --> TSClient
    HeyAPI --> TanStack
    TSClient --> React
    TanStack --> React
```

Build-time type safety from Python models to TypeScript UI without maintaining a separate TS ORM or manual API client.

---

## 5. Worker Architecture

### ARQ Workers

Workers execute workflow pipelines out-of-process. The gateway never runs ADK directly.

| Concern | Implementation |
|---------|---------------|
| Worker framework | **ARQ** (native asyncio, Redis-backed) |
| Why not Celery | Celery is sync-first; ARQ is native asyncio, simpler, fits the stack |
| Execution model | Gateway enqueues a job (workflow ID + params) -> ARQ worker picks up -> runs ADK pipeline -> publishes events to Redis Streams |
| Concurrency | Multiple workers can run in parallel; each worker runs one pipeline at a time |
| Cron jobs | **ARQ cron** for scheduled tasks (cleanup, health checks, scheduled workflows) |
| Idempotency | Workers must handle re-delivery; ADK resume helps with crash recovery |

### Worker Lifecycle

```python
# Simplified worker structure
async def run_workflow(ctx: dict, workflow_id: str, params: dict) -> None:
    """ARQ job function -- runs in worker process."""
    # Anti-corruption layer: translate gateway params -> ADK
    runner = create_adk_runner(workflow_id, params)
    session = await create_or_resume_session(workflow_id)

    async for event in runner.run_async(session):
        # Translate ADK event -> gateway event schema
        gateway_event = translate_event(event)
        # Publish to Redis Streams
        await publish_to_stream(workflow_id, gateway_event)
        # Update database state
        await update_workflow_state(workflow_id, event)
```

---

## 6. Event System

### Redis Streams

Redis Streams serve as the persistent, replayable event bus. All pipeline events flow through streams.

| Feature | Implementation |
|---------|---------------|
| Publish | Workers publish translated ADK events to a per-workflow stream |
| Persistence | Events are stored in Redis with configurable retention |
| Replay | Consumers can read from any point in the stream (by ID) |
| Consumer groups | Multiple independent consumers process the same stream |
| Delivery guarantees | At-least-once via consumer group acknowledgment |

### Consumers

| Consumer | Purpose | Mechanism |
|----------|---------|-----------|
| **SSE endpoint** | Push real-time events to connected clients | Gateway reads stream, pushes via SSE |
| **Webhook dispatcher** | Notify external systems | Reads events, dispatches via httpx to registered listeners (stored in DB) |
| **Audit logger** | Compliance and debugging | Reads events, writes to database |

### SSE Reconnection

```
1. Client connects:   GET /events/stream
2. Server streams:    event: pipeline.step.completed (id: 1707-001)
3. Connection drops
4. Client reconnects: GET /events/stream  (Last-Event-ID: 1707-001)
5. Server replays:    all events after 1707-001 from Redis Stream
6. Server resumes:    live streaming from current position
```

No events are lost. Redis Stream IDs map directly to SSE event IDs.

### Event Listeners (Webhooks)

- Registered hooks stored in database (URL, event filter, secret)
- Redis Stream consumer reads matching events
- Dispatches via httpx with HMAC signature
- Retry with exponential backoff on failure

---

## 7. Data Layer

### Single Database

All persistent data lives in one database, accessed only through the gateway (and workers via shared SQLAlchemy models).

| Concern | Implementation |
|---------|---------------|
| ORM | **SQLAlchemy 2.0 async** (native async sessions, modern 2.0-style queries) |
| Migrations | **Alembic** (version-controlled schema evolution) |
| Driver | `asyncpg` (PostgreSQL) or `aiosqlite` (SQLite for dev) |
| Access pattern | Gateway and workers share the same SQLAlchemy models |

No separate dashboard database. No separate session database. One schema, one migration history.

### Key Tables (Conceptual)

| Table | Purpose |
|-------|---------|
| `specifications` | Submitted specs and their decomposition status |
| `workflows` | Workflow execution records (status, params, timestamps) |
| `deliverables` | Individual deliverable records within a workflow |
| `sessions` | ADK session state (persisted via DatabaseSessionService adapter) |
| `events` | Audit log (subset of events written by audit consumer) |
| `webhook_listeners` | Registered webhook endpoints and filters |
| `skills` | Skill index and metadata |

---

## 8. ADK Engine (Internal)

ADK runs inside workers, behind the anti-corruption layer. This section documents the internal orchestration engine.

### ADK Mapping

| ADK Primitive | Role in AutoBuilder |
|---------------|-------------------|
| `LlmAgent` | Planning, coding, reviewing -- probabilistic steps requiring LLM judgment |
| `CustomAgent` (BaseAgent) | Linter, test runner, formatter, skill loader, orchestrator -- deterministic steps |
| `SequentialAgent` | Inner deliverable pipeline (plan, code, lint, test, review) |
| `ParallelAgent` | Concurrent deliverable execution within a batch |
| `LoopAgent` | Review/fix cycles with max iteration bounds |
| `Session State` | Inter-agent communication (4 scopes: session, user, app, temp) |
| `Event Stream` | Unified observability for all agent types (translated to Redis Streams at boundary) |
| `FunctionTool` | Wrap Python functions as LLM-callable tools (auto-schema from type hints) |
| `InstructionProvider` | Dynamic context/knowledge loading per invocation |
| `before_model_callback` | Context injection, token budget monitoring |
| `DatabaseSessionService` | State persistence (adapter bridges to shared database) |

### Multi-Model via LiteLLM

LiteLLM provides the model abstraction layer. Model strings use the LiteLLM format (e.g., `anthropic/claude-sonnet-4-5-20250929`). The LLM Router selects models per task based on routing configuration.

### Architecture Diagram (Engine Internal)

```mermaid
flowchart TB
    subgraph APP["ADK APP CONTAINER"]
        direction TB
        AppConfig["Context compression (EventsCompactionConfig)\nResumability (ResumabilityConfig)\nPlugins (TokenTracking, Logging)\nLifecycle hooks (on_startup, on_shutdown)"]
    end

    subgraph ORCH["ORCHESTRATION LAYER"]
        BatchOrch["BatchOrchestrator (CustomAgent)\n- Dynamic ParallelAgent batch construction\n- Dependency-aware deliverable selection\n- Checkpoint/resume\n- Regression test orchestration"]
        Batch1["Batch_001\nParallelAgent"]
        Batch2["Batch_002\nParallelAgent"]
        BatchN["Batch_N\nParallelAgent"]
        BatchOrch --> Batch1 & Batch2 & BatchN
    end

    subgraph PIPELINE["PIPELINE LAYER (per deliverable)"]
        FP["DeliverablePipeline (SequentialAgent)"]
        S1["1. SkillLoaderAgent -- Deterministic"]
        S2["2. plan_agent -- LLM"]
        S3["3. code_agent -- LLM"]
        S4["4. LinterAgent -- Deterministic"]
        S5["5. TestRunnerAgent -- Deterministic"]
        subgraph ReviewCycle["6. ReviewCycle (LoopAgent, max=3)"]
            R1["a. review_agent -- LLM"]
            R2["b. fix_agent -- LLM"]
            R3["c. LinterAgent -- Deterministic"]
            R4["d. TestRunnerAgent -- Deterministic"]
            R1 --> R2 --> R3 --> R4
        end
        FP --> S1 --> S2 --> S3 --> S4 --> S5 --> ReviewCycle
    end

    subgraph INFRA["SHARED ENGINE INFRASTRUCTURE"]
        Tools["Tool Registry (FunctionTools)\nfile_read, file_write, file_edit\nbash_exec, git_*, web_*, todo_*"]
        Skills["Skill Library\n(Global + Project-local)\nMarkdown + YAML frontmatter\nDeterministic matching"]
        Router["LLM Router\n(task_type to model)\nplanning: opus\ncoding: sonnet\nreview: sonnet\nclassification: haiku\nFallback chains"]
        Models["Models (Shared Domain)\nenums.py, constants.py\nbase.py (Pydantic base models)"]
        State["State System (4 scopes)\nsession, user:, app:, temp:"]
        Memory["Memory Service (SQLite FTS5)\nCross-session learnings\nSearchable archive"]
        Observability["Observability\nADK Event stream\nOpenTelemetry native\nPython logging\nPlugin system"]
    end

    APP --> ORCH
    Batch1 & Batch2 & BatchN --> PIPELINE
    PIPELINE --> INFRA
```

### Inner Pipeline Composition

```python
# Inner deliverable pipeline -- declarative composition
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # Deterministic
        plan_agent,                                # LLM
        code_agent,                                # LLM
        LinterAgent(name="Lint"),                  # Deterministic
        TestRunnerAgent(name="Test"),               # Deterministic
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM
                fix_agent,                         # LLM
                LinterAgent(name="ReLint"),        # Deterministic
                TestRunnerAgent(name="ReTest"),     # Deterministic
            ]
        )
    ]
)
```

```python
# Outer loop -- dynamic orchestrator
class BatchOrchestrator(BaseAgent):
    """Dynamically constructs ParallelAgent batches per iteration."""
    async def _run_async_impl(self, ctx):
        while incomplete_deliverables_exist(ctx):
            batch = select_next_batch(ctx)  # Dependency-aware, respects concurrency
            parallel = ParallelAgent(
                name=f"Batch_{batch.id}",
                sub_agents=[create_pipeline(d) for d in batch.deliverables]
            )
            async for event in parallel.run_async(ctx):
                yield event
            await run_regression_tests(ctx)
            await checkpoint(ctx)
```

---

## 9. The Autonomous Execution Loop

```
1. Client submits spec via POST /specs
2. Gateway enqueues decomposition job -> ARQ worker decomposes -> deliverables in DB
3. Client triggers POST /workflows/{id}/run
4. Gateway enqueues execution job -> ARQ worker picks up
5. Worker runs ADK pipeline:
   a. Load spec -> resolve dependencies (topological sort)
   b. While incomplete deliverables exist:
      i.   Select next batch (respecting deps + concurrency limits)
      ii.  For each deliverable in batch (parallel):
           - Load relevant skills (deterministic: SkillLoaderAgent)
           - Plan implementation (LLM: plan_agent)
           - Execute plan (LLM: execute_agent)
           - Validate output (deterministic: workflow-specific ValidatorAgent)
           - Verify output (deterministic: workflow-specific VerifyAgent)
           - Review quality (LLM: review_agent)
           - Loop execute-validate-verify-review if review fails (max N)
      iii. Merge completed deliverables
      iv.  Run regression checks
      v.   Publish batch completion event -> Redis Streams
      vi.  Optional: pause for human review (intervention via API)
6. Worker publishes completion event
7. Client receives completion via SSE stream (or polls status endpoint)
```

The loop runs autonomously until all deliverables are complete. No human prompting is required between iterations. Optional human-in-the-loop intervention points can be configured at the batch boundary (step 5b.vi), triggered via the intervention API endpoint.

Note: The specific deterministic agents in validation/verification steps vary by workflow. For auto-code: LinterAgent + TestRunnerAgent. For auto-research: SourceVerifierAgent + CitationCheckerAgent. The *pattern* (deterministic validation is mandatory) is universal; the *implementation* is workflow-specific.

---

## 10. Infrastructure

### Redis Roles

Redis serves four distinct roles from day one. This is fundamental infrastructure, not a Phase 2 optimization.

| Role | Mechanism | Purpose |
|------|-----------|---------|
| **Task queue** | ARQ (Redis lists) | Enqueue and dequeue workflow execution jobs |
| **Event bus** | Redis Streams | Persistent, replayable pipeline event distribution |
| **Cron store** | ARQ cron | Scheduled job definitions and execution tracking |
| **Cache** | Redis key/value | LLM response caching, skill index caching, session state caching |

### Database

| Concern | Choice |
|---------|--------|
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Production | PostgreSQL (asyncpg) |
| Development | SQLite (aiosqlite) |
| Access | Gateway + workers (shared models, single schema) |

### Filesystem

| Concern | Purpose |
|---------|---------|
| Git worktrees | Filesystem isolation for parallel code generation |
| Artifacts | Large data (generated code, reports, files) |
| Skills | Markdown + YAML frontmatter files |

---

## 11. CLI Architecture

The CLI is a thin API client built with **typer**. It has no database, no direct ADK access, and no business logic beyond argument parsing and API calls.

| Command | API Call | Purpose |
|---------|----------|---------|
| `autobuilder run <spec>` | `POST /specs` + `POST /workflows/{id}/run` | Submit and launch |
| `autobuilder status <id>` | `GET /workflows/{id}/status` | Check progress |
| `autobuilder intervene <id>` | `POST /workflows/{id}/intervene` | Human-in-the-loop |
| `autobuilder list` | `GET /workflows` | List workflows |
| `autobuilder logs <id>` | `GET /events/stream` (SSE) | Stream events to terminal |

The CLI connects to the gateway via REST + SSE. It can be used for scripting, CI/CD integration, and headless operation.

---

## 12. Dashboard Architecture

The web dashboard is a **React 19 SPA** (static build via Vite). It consumes the gateway API exclusively -- no backend, no database of its own.

### Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | React 19 | UI components |
| Build | Vite | Fast dev server + static production build |
| Server state | TanStack Query | Generated from OpenAPI via hey-api; caching, refetching, optimistic updates |
| Client state | Zustand | SSE event buffer, UI preferences, transient state |
| Styling | Tailwind v4 | CSS-first @theme, fully tokenized design system |
| API client | hey-api generated | Typed client + TanStack Query hooks from OpenAPI spec |

### Data Flow

```mermaid
flowchart TB
    FastAPI["FastAPI (Pydantic models)"]
    OpenAPI["OpenAPI spec"]
    Generated["Typed TS client + TanStack Query hooks"]
    React["React components"]
    TQ["TanStack Query\nREST queries (deliverables, status, specs)"]
    Zustand["Zustand store\nSSE event buffer (real-time pipeline events)"]

    FastAPI -->|"auto-generated"| OpenAPI
    OpenAPI -->|"hey-api codegen at build time"| Generated
    Generated -->|"consumed by"| React
    React --> TQ
    React --> Zustand
```

The dashboard is a static asset. It can be served from any CDN, file server, or embedded in the gateway's static files.

---

## 13. State Architecture

Agents communicate via session state, not direct message passing. All state updates happen through `Event.actions.state_delta`, making every change auditable in the event stream.

| Scope | Prefix | Contents | Persistence |
|-------|--------|----------|-------------|
| **Session** | *(none)* | Current batch, deliverable statuses, loaded skills, validation results, verification results | Per-run (persistent via database) |
| **User** | `user:` | Preferences, model selections, intervention settings | Cross-session per user |
| **App** | `app:` | Project config, global conventions, skill index | Cross-user, cross-session |
| **Temp** | `temp:` | Intermediate LLM outputs, scratch data | Discarded after invocation |
| **Memory** | `MemoryService` | Cross-session learnings, past decisions, discovered patterns | Persistent, searchable archive |

State values are injectable into agent instructions via `{key}` templating. For example: `"Implement the deliverable: {current_deliverable_spec}"` auto-resolves from `session.state['current_deliverable_spec']`. Use `{key?}` for optional keys that may not exist.

---

## 14. Multi-Agent Communication

Agents communicate via four mechanisms, all operating through session state:

| # | Mechanism | How It Works |
|---|-----------|-------------|
| 1 | `output_key` | Agent writes its result to a named state key |
| 2 | `{key}` templates | Agent reads from state via template injection in instructions |
| 3 | `InstructionProvider` | Dynamic function reads state and constructs context-appropriate instructions at invocation time |
| 4 | `before_model_callback` | Injects additional context (file contents, test results) right before LLM call |

No agent calls another agent directly. All coordination flows through the shared state system, making data flow explicit and debuggable.

---

## 15. Observability

### Phased Approach

| Phase | Tool | Purpose |
|-------|------|---------|
| Phase 1 | **OpenTelemetry** | ADK-native tracing (auto-traces agents, tools, runner) |
| Phase 1 | **Python logging** | Structured logs under `app.*` hierarchy |
| Phase 1 | **Redis Streams** | Pipeline events (also serves as operational observability) |
| Phase 2 | **Langfuse** | LLM-specific tracing (token usage, latency, quality) |
| Phase 3 | **Custom dashboard** | Integrated observability views in the web dashboard |

### Event Stream

Every agent (LLM or deterministic) emits `Event` objects into ADK's unified chronological stream. The anti-corruption layer translates these to gateway events and publishes to Redis Streams. This provides full pipeline visibility from plan to execution to validation to review.

`adk web` remains available as a local development tool for detailed ADK-level debugging, but is not part of the production observability stack.

---

## 16. Context Window Management

ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt. Two built-in mechanisms manage growth:

- **Context compression** -- sliding window summarization of older events (config-driven, interval + overlap)
- **Context caching** -- caches static prompt parts server-side (system instructions, knowledge bases)

**Gap identified**: ADK has no built-in context-window usage metric. Agents cannot reactively respond to "you are at 80% capacity."

**Solution**: A `before_model_callback` that token-counts the assembled `LlmRequest`, writes percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). Approximately 50 lines of code.

**Implication for pipeline design**: For longer pipelines, agents should not rely on reading raw event history from prior steps. Better to use SkillLoaderAgent + explicit state writes so each agent gets precisely the context it needs, not the full event log.

---

## 17. Dynamic Context & Knowledge Loading

ADK provides injection hooks but no built-in knowledge management system. AutoBuilder's knowledge loading is layered:

| Layer | Mechanism | What It Loads |
|-------|-----------|---------------|
| 1 | Static instruction string | Base agent personality/role |
| 2 | `InstructionProvider` function | Project conventions, patterns, deliverable spec (at invocation time) |
| 3 | `before_model_callback` | File context, codebase analysis, test results (right before LLM call) |
| 4 | `BaseToolset.get_tools()` | Different tools per deliverable type |
| 5 | Artifacts (`save_artifact`/`load_artifact`) | Large data (full file contents, generated code) |
| 6 | Context compression | Sliding window summarization for long autonomous runs |

No built-in RAG or vector store. For AutoBuilder, knowledge is deterministic lookup -- conventions from files, codebase via tools, specs via state, patterns from local directory. `InstructionProvider` + callbacks are sufficient.

---

## 18. App Container Configuration

ADK's `App` class is the top-level container for the agent workflow, instantiated inside workers.

### What App Provides

| Feature | Purpose | AutoBuilder Use |
|---------|---------|----------------|
| `root_agent` | The top-level agent tree | `BatchOrchestrator` (CustomAgent) |
| `events_compaction_config` | Context compression (sliding window summarization) | Keep long autonomous runs within context limits |
| `resumability_config` | Workflow resume after interruption | Pick up where we left off after crash/power loss |
| `plugins` | Global lifecycle hooks (logging, metrics, guardrails) | Token tracking, cost monitoring, security guardrails |
| `context_cache_config` | Cache static prompt parts server-side | Cache system instructions and skill content |
| Lifecycle hooks | `on_startup` / `on_shutdown` | Initialize connections, tool registry, skill library |
| State scope boundary | `app:*` prefix for app-level state | Project config, global conventions, workflow registry |

### App Structure

```python
from google.adk.apps import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

summarizer = LlmEventSummarizer(
    llm=LiteLlm(model="anthropic/claude-haiku-4-5-20251001")
)

app = App(
    name="autobuilder",
    root_agent=batch_orchestrator,

    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,
        overlap_size=1,
        summarizer=summarizer,
    ),

    resumability_config=ResumabilityConfig(
        is_resumable=True,
    ),

    plugins=[
        TokenTrackingPlugin(),
        LoggingPlugin(),
    ],
)
```

### Resumability for CustomAgents

ADK's Resume feature (v1.16+) tracks workflow execution and allows picking up after unexpected interruption:

- Resume is not automatic for CustomAgents -- we must implement `BaseAgentState` subclass and define checkpoint steps in `BatchOrchestrator`
- Tools may run more than once on resume -- git, file write, and bash tools must be idempotent or include duplicate-run protection
- The system reinstates results from successfully completed tools and re-runs from the point of failure

---

*Document Version: 2.0*
*Last Updated: February 2026*
