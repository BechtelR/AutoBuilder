# AutoBuilder Component Registry (BOM)
*Version: 2.5.0*

**Single source of truth for all buildable components.** Every item in this registry is derived from the architecture domain files (`architecture/*.md`). Every item maps to exactly one roadmap phase. An unassigned item (`—`) is a gap.

**Pipeline**: Architecture defines → Registry assigns → Phase Spec elaborates → Build implements

---

## How to Use This Document

- **Before building Phase N**: Filter by phase, verify all components are in the phase spec
- **After architecture changes**: Re-derive affected components, update phase assignments
- **Gap detection**: Search for `—` in the Phase column — these are unscheduled components

### Legend

| Symbol | Meaning |
|--------|---------|
| `✓` | Implemented (Phase 0–2) |
| `3`–`14` | Assigned to that phase |
| `DROP` | Dropped — over-engineering or unnecessary |

### Component Types

`route` `endpoint` `db` `migration` `module` `agent` `tool` `callback` `mechanism` `config` `plugin` `skill` `workflow` `cli` `ui`

---

## 1. Gateway

Source: `architecture/gateway.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| G01 | `GET /health` | route | ✓ | gateway.md §Route Structure | — |
| G02 | `POST /specs` (brief submission) | route | 8a | gateway.md §Route Structure | WorkflowRegistry, X01 |
| G03 | `POST /workflows/{id}/run` | route | 8a | gateway.md §Route Structure | ARQ worker, WorkflowRegistry |
| G04 | `GET /workflows/{id}/status` | route | 8a | gateway.md §Route Structure | `workflows` table |
| G05 | `GET /workflows` | route | 10 | gateway.md §Route Structure | WorkflowRegistry |
| G06 | `POST /workflows/{id}/intervene` | route | 8b | gateway.md §Route Structure | ADK session, PM agent, X09 |
| G07 | `GET /deliverables` | route | 8a | gateway.md §Route Structure | `deliverables` table |
| G08 | `GET /deliverables/{id}` | route | 8a | gateway.md §Route Structure | `deliverables` table |
| G09 | `GET /events/stream` | endpoint | 10 | gateway.md §Route Structure | Redis Streams, SSE |
| G10 | `POST /chat/{session_id}/messages` | route | 5b | gateway.md §Route Structure | Director agent, `runner.run_async` |
| G11 | `GET /chat/{session_id}/messages` | route | 5b | gateway.md §Route Structure | ADK session / DB |
| G12 | `GET /ceo/queue` | route | 5b | gateway.md §Route Structure | `ceo_queue` table |
| G13 | `PATCH /ceo/queue/{id}` | route | 5b | gateway.md §Route Structure | `ceo_queue` table, session state writeback |
| G14 | `GET /ceo/queue/stream` | endpoint | 10 | gateway.md §Route Structure | `ceo_queue` table, Redis Streams |
| G15 | `GET /sessions/{id}/state` | endpoint | 11 | state.md §10 | `DatabaseSessionService` |
| G16 | `GET /memory/search` | endpoint | 9 | state.md §10 | `PostgresMemoryService` |
| G17 | `GET /metrics/tokens` | endpoint | 11 | state.md §10 | Token tracking |
| G18 | `GET /costs` | endpoint | 11 | state.md §10 | Token tracking |
| G19 | `GET /workflows/{id}/events` | endpoint | 10 | workflows.md §Workflow Execution Model | Redis Streams, SSE |
| G20 | Gateway Pydantic request/response models | module | ✓ | gateway.md §Anti-Corruption Pattern | — |
| G21 | Anti-corruption translation layer | module | 3 | gateway.md §Anti-Corruption Pattern | Gateway models, ADK models |
| G22 | CORS middleware | module | ✓ | gateway.md §Anti-Corruption Pattern | — |
| G23 | Error handling middleware | module | ✓ | gateway.md §Anti-Corruption Pattern | — |
| G24 | Request logging middleware | module | ✓ | gateway.md §Anti-Corruption Pattern | — |
| G25 | Dependency injection (`deps.py`) | module | ✓ | gateway.md §Anti-Corruption Pattern | DB sessions, Redis client |
| G26 | OpenAPI spec auto-generation | mechanism | ✓ | gateway.md §Type Safety Chain | Gateway Pydantic models |
| G27 | hey-api TypeScript codegen | mechanism | 12 | gateway.md §Type Safety Chain | OpenAPI spec |

---

## 2. Database

Source: `architecture/data.md`, `architecture/state.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| D01 | `specifications` table | db | ✓ | data.md §1 | Alembic |
| D02 | `workflows` table | db | ✓ | data.md §1 | Alembic |
| D03 | `deliverables` table | db | ✓ | data.md §1 | Alembic |
| D04 | `sessions` table (ADK) | db | 3 | data.md §1 | `DatabaseSessionService` |
| D05 | `ceo_queue` table | db | 5a | data.md §1, events.md §Unified CEO Queue | Alembic |
| D06 | `events` table (audit log) | db | 10 | data.md §1 | Audit consumer |
| D07 | `webhook_listeners` table | db | 10 | data.md §1 | Alembic |
| D08 | `project_configs` table | db | 5a | data.md §1, state.md §1.2 | Alembic |
| D09 | `skills` table | db | DROP | data.md §1 | File-based + Redis cache is sufficient per current architecture |
| D10 | `memory` table (tsvector + pgvector) | db | 9 | state.md §5 | pgvector extension |
| D11 | Job metadata table (ARQ tracking) | db | 3 | state.md §2.1 | Alembic, ARQ |
| D12 | SQLAlchemy async engine (shared) | module | ✓ | state.md §2.1 | asyncpg |
| D13 | `async_sessionmaker` factory | module | ✓ | state.md §2.1 | SQLAlchemy async engine |
| D14 | Alembic migration environment | config | ✓ | data.md §1 | — |
| D15 | Initial migration (core tables) | migration | ✓ | data.md §1 | Alembic |
| D16 | CEO queue migration | migration | 5a | events.md §Unified CEO Queue | Alembic |
| D17 | Memory table migration | migration | 9 | state.md §5 | Alembic, pgvector |
| D18 | Events + webhook_listeners migration | migration | 10 | data.md §1 | Alembic |
| D19 | Project configs migration | migration | 5a | data.md §1 | Alembic |

---

## 3. Engine (ADK App Container)

Source: `architecture/engine.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| E01 | `App` container (`autobuilder`) | module | 3 | engine.md §5 | Director agent, plugins, configs |
| E02 | Agent tree construction (via `AgentRegistry.build()`) | module | 5a | engine.md §5, agents.md §Agent Registry | AgentRegistry, InstructionAssembler, project IDs |
| E03 | PM agent construction (via `AgentRegistry.build()`) | module | 5a | engine.md §5, agents.md §Agent Registry | AgentRegistry, project config |
| E04 | `EventsCompactionConfig` | config | 3 | engine.md §5 | `LlmEventSummarizer` |
| E05 | `LlmEventSummarizer` (haiku model) | module | 3 | engine.md §5 | LiteLLM, haiku model |
| E06 | `ResumabilityConfig` | config | 3 | engine.md §5 | — |
| E07 | `context_cache_config` | config | 3 | engine.md §5 | — |
| E08 | `TokenTrackingPlugin` | plugin | 11 | engine.md §5 | App container |
| E09 | `LoggingPlugin` | plugin | 3 | engine.md §5 | App container |
| E10 | `BaseAgentState` subclass (CustomAgent resume) | module | 11 | engine.md §5 | `ResumabilityConfig` |
| E11 | Idempotent tool execution guards | mechanism | 4 | engine.md §5 | Tools, `ResumabilityConfig` |
| E12 | `DatabaseSessionService` integration | module | 3 | engine.md §5, state.md §1.1 | asyncpg, `sessions` table |
| E13 | 4-scope state system (`temp:`, session, `user:`, `app:`) | mechanism | 3 | state.md §1.2 | `DatabaseSessionService` |
| E14 | `app:` scope initialization (skill index, workflow registry) | mechanism | 3 | state.md §1.2, engine.md §5 | `DatabaseSessionService` |
| E15 | App lifecycle hooks (`on_startup` / `on_shutdown`) | mechanism | 3 | engine.md §5 | App container |
| E16 | Security guardrails plugin | plugin | 11 | engine.md §5 | App container |

---

## 4. Workers

Source: `architecture/workers.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| W01 | ARQ WorkerSettings | config | ✓ | workers.md §ARQ Workers | Redis |
| W02 | ARQ worker entry point | module | ✓ | workers.md §ARQ Workers | ARQ WorkerSettings |
| W03 | `run_workflow()` ARQ job function | module | 3 | workers.md §Worker Lifecycle | ADK Runner, session, events |
| W04 | `create_adk_runner()` factory | module | 3 | workers.md §Worker Lifecycle | Anti-corruption layer |
| W05 | `create_or_resume_session()` | module | 3 | workers.md §Worker Lifecycle | `DatabaseSessionService` |
| W06 | `translate_event()` | module | 3 | workers.md §Worker Lifecycle | Gateway event models |
| W07 | `publish_to_stream()` | module | 3 | workers.md §Worker Lifecycle | Redis Streams |
| W08 | `update_workflow_state()` | module | 3 | workers.md §Worker Lifecycle | `workflows` table |
| W09 | ARQ cron jobs (heartbeat, cleanup) | mechanism | ✓ | workers.md §ARQ Workers | ARQ, Redis |
| W10 | Worker re-delivery / idempotency handling | mechanism | 11 | workers.md §ARQ Workers | `create_or_resume_session` |
| W11 | Multi-worker concurrency validation | mechanism | 11 | workers.md §ARQ Workers | ARQ |

---

## 5. Events & CEO Queue

Source: `architecture/events.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| V01 | Per-workflow Redis Stream publishing | mechanism | 3 | events.md §Redis Streams | Redis Streams, `translate_event` |
| V02 | Redis Stream naming convention | config | 3 | events.md §Redis Streams | — |
| V03 | Redis Stream retention config | config | 10 | events.md §Redis Streams | Redis |
| V04 | Redis Stream consumer groups | mechanism | 10 | events.md §Redis Streams | Redis Streams |
| V05 | At-least-once delivery (ACK/NACK) | mechanism | 10 | events.md §Redis Streams | Consumer groups |
| V06 | SSE consumer | module | 10 | events.md §Consumers | Redis Streams, `GET /events/stream` |
| V07 | Webhook dispatcher consumer | module | 10 | events.md §Consumers | `webhook_listeners` table, httpx |
| V08 | Audit logger consumer | module | 10 | events.md §Consumers | `events` table |
| V09 | SSE reconnection (`Last-Event-ID` replay) | mechanism | 10 | events.md §SSE Reconnection | Redis Stream IDs |
| V10 | Webhook HMAC signature | mechanism | 10 | events.md §Event Listeners (Webhooks) | Webhook dispatcher |
| V11 | Webhook retry (exponential backoff) | mechanism | 10 | events.md §Event Listeners (Webhooks) | Webhook dispatcher |
| V12 | Event listener CRUD (register/unregister) | module | 10 | events.md §Event Listeners (Webhooks) | `webhook_listeners` table |
| V13 | CEO queue type enum (`NOTIFICATION`, `APPROVAL`, `ESCALATION`, `TASK`) | config | 5a | events.md §Unified CEO Queue | — |
| V14 | CEO queue priority enum (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`) | config | 5a | events.md §Unified CEO Queue | — |
| V15 | CEO queue status enum (`PENDING`, `SEEN`, `RESOLVED`, `DISMISSED`) | config | 5a | events.md §Unified CEO Queue | — |
| V17 | CEO queue Redis Stream trigger consumer | mechanism | DROP | events.md §Unified CEO Queue | `escalate_to_ceo` FunctionTool is the write path; second write path via stream consumer is over-engineering |
| V18 | CEO resolved approval → session state writeback | mechanism | 5b | events.md §Unified CEO Queue | CEO queue, ADK session |
| V19 | Batch completion event publishing | mechanism | 8a | events.md §Unified CEO Queue | Redis Streams — see also §14.2 |
| V20 | Director queue type enum (`ESCALATION`, `STATUS_REPORT`, `RESOURCE_REQUEST`, `PATTERN_ALERT`) | config | 4 | events.md §Director Queue | — |
| V21 | Director queue priority enum (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`) | config | 4 | events.md §Director Queue | — |
| V22 | Director queue status enum (`PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO`) | config | 4 | events.md §Director Queue | — |
| V23 | `director_queue` table | db | 5a | events.md §Director Queue | Alembic |
| V24 | `director_queue` migration | migration | 5a | events.md §Director Queue | Alembic |

---

## 6. Agents

Source: `architecture/agents.md`, `architecture/execution.md`

### 6.1 Supervision Tier

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A01 | Director agent (LlmAgent, opus) | agent | 5a | agents.md §Director Agent | AgentRegistry, PM agents |
| A02 | PM agent (LlmAgent, sonnet) | agent | 5a | agents.md §PM Agent | AgentRegistry, PM tools |
| A03 | Director agent definition file (`director.md`) | config | 5a | agents.md §Agent Definition Files | AgentRegistry |
| A04 | PM agent definition file (`pm.md`) | config | 5a | agents.md §Agent Definition Files | AgentRegistry |
| A05 | Director → PM delegation (`transfer_to_agent`) | mechanism | 5b | agents.md §PM Agent, §Agent Communication via Session State | ADK primitives |
| A06 | PM → Director escalation (`transfer_to_agent`) | mechanism | 5b | agents.md §PM Agent, §Agent Communication via Session State | ADK primitives |
| A07 | Hard limits cascade (CEO → Director → PM → Workers) | mechanism | 5b | agents.md §PM Agent | `project_configs` |
| A08 | Director formation artifacts (`user:` scope — three structured keys + formation status) | config | 5b | agents.md §Director Agent | `user:` state, Settings conversation |
| A09 | Director formation logic (Settings conversation) | module | 5b | agents.md §Director Agent | A08 |
| A10 | Director tool authoring + CEO approval gate | mechanism | 13+ | agents.md §Director Agent | Tool registry, CEO queue |
| A11 | Director cross-project pattern propagation | mechanism | 14 | agents.md §Director Agent | `MemoryService` |
| A12 | Director governance tools | tool | 13+ | agents.md §Director Agent | `GlobalToolset` |
| A13 | Director "Main" project (permanent chat session) | mechanism | 5b | agents.md §Director Agent | Session model |
| A16 | Director queue consumption (reads pending escalations, resolves or forwards to CEO queue) | mechanism | 5b | agents.md §Director Agent | `director_queue` table, CEO queue |
| A14 | `before_agent_callback` (Director supervision) | callback | 5b | agents.md §PM Agent | Director agent |
| A15 | `after_agent_callback` (Director supervision) | callback | 5b | agents.md §PM Agent | Director agent |

### 6.2 Worker Tier — LLM Agents

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A20 | `planner` (LlmAgent, opus) | agent | 5a | agents.md §Worker-Tier LLM Agents | Read-only tools, skills |
| A21 | `coder` (LlmAgent, sonnet) | agent | 5a | agents.md §Worker-Tier LLM Agents | Full tools, plan output |
| A22 | `reviewer` (LlmAgent, sonnet) | agent | 5a | agents.md §Worker-Tier LLM Agents | Read-only tools, lint/test results |
| A23 | `fixer` (LlmAgent, sonnet) | agent | 5a | agents.md §Worker-Tier LLM Agents | Full tools, review output |

### 6.3 Worker Tier — Custom Agents (Deterministic & Hybrid)

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A30 | `SkillLoaderAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | SkillLibrary |
| A31 | `LinterAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | Filesystem |
| A32 | `TestRunnerAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | Filesystem |
| A33 | `FormatterAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | Filesystem |
| A34 | `DependencyResolverAgent` (hybrid CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | Deliverable deps, LiteLLM |
| A35 | `RegressionTestAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | PM regression policy |
| A36 | `DiagnosticsAgent` (hybrid CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | `lint_results`, `test_results`, LiteLLM |
| A37 | `MemoryLoaderAgent` (CustomAgent) | agent | 5a | agents.md §Worker-Tier Custom Agents | BaseMemoryService (ADK) |

### 6.4 Callbacks & Hooks

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A40 | `verify_batch_completion` (`after_agent_callback`) | callback | 5b | agents.md §PM Agent | PM agent |
| A41 | `checkpoint_project` (`after_agent_callback`) | callback | 5b | agents.md §PM Agent | DeliverablePipeline |
| A43 | `before_model_callback` context injection | callback | 5a | agents.md §Worker-Tier LLM Agents | Session state |
| A44 | `before_model_callback` LLM Router override | callback | 3 | agents.md §LLM Router | LlmRouter |

### 6.5 Agent Communication

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A50 | `output_key` state communication | mechanism | 5a | agents.md §1. output_key | Session state |
| A51 | `{key}` state template injection | mechanism | 5a | agents.md §2. {key} Templates | Session state |
| A52 | `InstructionAssembler` — fragment-based instruction composition | module | 5a | agents.md §Agent Definitions | InstructionFragment, session state |
| A53 | `InstructionFragment` dataclass | module | 5a | agents.md §Agent Definitions | — |
| A54 | `context_from_state` helper | module | 5a | agents.md §Worker-Tier Custom Agents | Session state |
| A55 | Agent definition files (markdown + YAML frontmatter) | config | 5a | agents.md §Agent Definition Files | — |
| A56 | `AgentRegistry` class (scan + build from files) | module | 5a | agents.md §AgentRegistry | InstructionAssembler, GlobalToolset, LlmRouter |
| A57 | Base instruction fragments (6 types: SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL) | config | 5a | agents.md §Agent Definitions | — |
| A58 | System reminder injection (`before_model_callback`) | callback | 5b | agents.md §System Reminders | Session state |
| A59 | Context recreation mechanism | mechanism | 5b | context.md §Context Recreation | InstructionAssembler, SkillLoaderAgent, MemoryService |
| A75 | SAFETY instruction fragment (hardcoded, non-overridable) | config | 5a | agents.md §Instruction Composition | InstructionAssembler |
| A76 | `InstructionContext` container (per-invocation assembly data) | module | 5a | agents.md §Agent Definitions | Project config, session state, loaded skills |
| A77 | Partial override (frontmatter-only definition files inherit parent body) | mechanism | 5a | agents.md §Definition Cascade | AgentRegistry |
| A78a | Project-scope type validation (`type: llm` only from project scope) | mechanism | 5a | agents.md §Project-Scope Restrictions | AgentRegistry |
| A78b | Project-scope `tool_role` ceiling validation (against workflow manifest) | mechanism | 7 | agents.md §Project-Scope Restrictions | AgentRegistry, WORKFLOW.yaml |
| A79 | State key authorization (tier prefixes, EventPublisher ACL) | mechanism | 5b | agents.md §State Key Authorization | EventPublisher |
| A80 | Resolution auditability (`agent_resolution_sources` session state key) | mechanism | 5a | agents.md §AgentRegistry | AgentRegistry, event stream |

### 6.6 Pipelines & Loops

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A60 | `DeliverablePipeline` (SequentialAgent) | workflow | 5a | agents.md §How Workers Compose | All worker agents |
| A61 | `ReviewCycle` (LoopAgent, max=3) | workflow | 5a | agents.md §How Workers Compose | review, fix, lint, test agents |
| A62 | Parallel batch execution (ParallelAgent) | workflow | 8b | execution.md §PM loop | See §14.3 |
| A63 | PM outer loop (sequential batch management) | workflow | 8a | execution.md §PM loop | See §14.2 |

### 6.7 Session Model

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A70 | Chat session model (per-message `runner.run_async`) | mechanism | 5b | execution.md §Multi-Session | Director, `DatabaseSessionService` |
| A71 | Work session model (long-running ARQ job) | mechanism | 3 | execution.md §Multi-Session | ARQ, `DatabaseSessionService` |
| A72 | Cross-session bridge (`app:`/`user:` state + Redis Streams) | mechanism | 3 | execution.md §Multi-Session | Multiple subsystems |
| A73 | Session rewind integration | mechanism | 11 | state.md §1.5 | `DatabaseSessionService` |
| A74 | Session migration CLI tool | tool | 11 | state.md §1.6 | `DatabaseSessionService` |

---

## 7. Tools

Source: `architecture/tools.md`

### 7.1 FunctionTools

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| T01 | `file_read` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T02 | `file_write` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T03 | `file_edit` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T04 | `file_glob` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T04b | `file_grep` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T05 | `directory_list` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T06 | `bash_exec` FunctionTool | tool | 4 | tools.md §3.3 | — |
| T07 | `git_status` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T08 | `git_commit` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T09 | `git_branch` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T10 | `git_diff` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T11 | `web_search` FunctionTool | tool | 4 | tools.md §3.5 | Tavily primary, Brave fallback |
| T12 | `web_fetch` FunctionTool | tool | 4 | tools.md §3.5 | — |
| T13 | `todo_read` FunctionTool | tool | 4 | tools.md §3.6 | Session state |
| T14 | `todo_write` FunctionTool | tool | 4 | tools.md §3.6 | Session state |
| T15 | `todo_list` FunctionTool | tool | 4 | tools.md §3.6 | Session state |
| T16 | `select_ready_batch` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T17 | `escalate_to_ceo` FunctionTool | tool | 4 | tools.md §3.8 | CEO queue |
| T18 | `file_insert` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T19 | `file_multi_edit` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T20 | `file_move` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T21 | `file_delete` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T22 | `code_symbols` FunctionTool | tool | 4 | tools.md §3.2 | tree-sitter |
| T23 | `run_diagnostics` FunctionTool | tool | 4 | tools.md §3.2 | Project config |
| T24 | `http_request` FunctionTool | tool | 4 | tools.md §3.3 | — |
| T25 | `git_log` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T26 | `git_show` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T27 | `git_worktree` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T28 | `git_apply` FunctionTool | tool | 4 | tools.md §3.4 | — |
| T29 | `task_create` FunctionTool | tool | 4 | tools.md §3.6 | Shared task store |
| T30b | `task_update` FunctionTool | tool | 4 | tools.md §3.6 | Shared task store |
| T30c | `task_query` FunctionTool | tool | 4 | tools.md §3.6 | Shared task store |
| T31 | `escalate_to_director` FunctionTool | tool | 4 | tools.md §3.7 | Director queue |
| T32b | `update_deliverable` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T33b | `query_deliverables` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T34b | `reorder_deliverables` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T35b | `manage_dependencies` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T36b | `list_projects` FunctionTool | tool | 4 | tools.md §3.8 | Project state |
| T37b | `query_project_status` FunctionTool | tool | 4 | tools.md §3.8 | Project state |
| T38 | `override_pm` FunctionTool | tool | 4 | tools.md §3.8 | PM agent, event stream |
| T39 | `get_project_context` FunctionTool | tool | 4 | tools.md §3.8 | Filesystem |
| T40 | `query_dependency_graph` FunctionTool | tool | 4 | tools.md §3.8 | Deliverable state |

### 7.2 Tool Modules

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| TM01 | `app/tools/filesystem.py` | module | 4 | tools.md §7.1 | — |
| TM02 | `app/tools/git.py` | module | 4 | tools.md §7.1 | — |
| TM03 | `app/tools/execution.py` | module | 4 | tools.md §7.1 | — |
| TM04 | `app/tools/web.py` | module | 4 | tools.md §7.1 | — |
| TM05 | `app/tools/task.py` | module | 4 | tools.md §7.1 | — |
| TM06 | `app/tools/management.py` | module | 4 | tools.md §7.1 | — |
| TM07 | `app/tools/code.py` | module | 4 | tools.md §7.1 | tree-sitter |

### 7.3 GlobalToolset & Permissions

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| TS01 | `GlobalToolset` (BaseToolset) | module | 4 | tools.md §7.3 | All FunctionTools |
| TS02 | `resolve_role()` (role from ReadonlyContext) | module | 4 | tools.md §7.3 | ADK ReadonlyContext |
| TS03 | Cascading permission config | config | 4 | tools.md §7.4 | — |
| TS04 | Role scoping: `planner` (read-only) | config | 4 | tools.md §7.5 | GlobalToolset |
| TS05 | Role scoping: `coder` (full tools) | config | 4 | tools.md §7.5 | GlobalToolset |
| TS06 | Role scoping: `reviewer` (read-only) | config | 4 | tools.md §7.5 | GlobalToolset |
| TS07 | Role scoping: `fixer` (full FS, limited exec/git) | config | 4 | tools.md §7.5 | GlobalToolset |
| TS08 | Role scoping: PM (batch + shared) | config | 4 | tools.md §7.5 | GlobalToolset |
| TS09 | Role scoping: Director (governance + shared) | config | 4 | tools.md §7.5 | GlobalToolset |

---

## 8. LLM Router

Source: `architecture/agents.md §LLM Router`, `architecture/tools.md §6`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| R01 | `LlmRouter` module | module | 3 | agents.md §LLM Router | LiteLLM |
| R02 | Routing rules (static config) | config | 3 | agents.md §LLM Router | — |
| R03 | Fallback chain resolution (3-step) | mechanism | 3 | agents.md §LLM Router | Provider availability |
| R04 | `before_model_callback` model override | callback | 3 | agents.md §LLM Router | LlmRouter |
| R05 | Adaptive router (cost-aware, latency-aware) | mechanism | 11 | agents.md §LLM Router | Token tracking |

---

## 9. Skills

Source: `architecture/skills.md`

### 9.1 Skills Infrastructure

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| S01 | `SkillEntry` Pydantic model | module | 6 | skills.md §Skill File Format | Pydantic |
| S02 | `SkillLibrary` class | module | 6 | skills.md §Two-Tier Library | SkillEntry, frontmatter parser |
| S03 | Frontmatter parser (YAML from markdown) | module | 6 | skills.md §Skill File Format | — |
| S04 | `deliverable_type` trigger matcher | mechanism | 6 | skills.md §Trigger Matching | — |
| S05 | `file_pattern` trigger matcher (glob) | mechanism | 6 | skills.md §Trigger Matching | — |
| S06 | `tag_match` trigger matcher (set intersection) | mechanism | 6 | skills.md §Trigger Matching | — |
| S07 | `explicit` trigger matcher | mechanism | 6 | skills.md §Trigger Matching | — |
| S08 | `always` trigger matcher | mechanism | 6 | skills.md §Trigger Matching | — |
| S09 | Description keyword fallback (interop) | mechanism | 6 | skills.md §Trigger Matching | — |
| S10 | Two-tier scan (global + project-local override) | mechanism | 6 | skills.md §Two-Tier Library | — |
| S11 | Three-tier merge (+ workflow-specific) | mechanism | 7 | workflows.md §auto-code: The First Workflow | SkillLibrary, WorkflowRegistry |
| S12 | `InstructionAssembler` skill injection with `applies_to` filtering | mechanism | 6 | skills.md §ADK Integration, agents.md §Agent Definitions | InstructionAssembler, session state, SkillEntry `applies_to` |
| S13 | Skill index Redis cache | mechanism | 6 | skills.md §Two-Tier Library | Redis |
| S14 | Skill cache invalidation (file change + gateway API) | mechanism | 6 | skills.md §Two-Tier Library | Redis, gateway |
| S15 | Skill cascade resolution | mechanism | 6 | skills.md §Skill Cascading | SkillLoaderAgent |
| S16 | Supervision-tier skill resolution (Director/PM build-time matching) | mechanism | 6 | FRD §CAP-10 | SkillLibrary, InstructionAssembler, AgentRegistry |
| S17 | Skill validation function (callable by agents and indexer) | module | 6 | FRD §CAP-11 | SkillEntry, frontmatter parser |

### 9.2 Skill Files

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| S20 | `app/skills/` directory structure | config | 6 | skills.md §Directory Layout | — |
| S21 | `.agents/skills/` project-local directory | config | 6 | skills.md §Directory Layout | — |
| S22 | Skill: `code/api-endpoint` | skill | 6 | skills.md §Directory Layout | — |
| S23 | Skill: `code/data-model` | skill | 6 | skills.md §Directory Layout | — |
| S24 | Skill: `code/database-migration` | skill | 6 | skills.md §Directory Layout | — |
| S25 | Skill: `review/security-review` | skill | 6 | skills.md §Directory Layout | — |
| S26 | Skill: `review/performance-review` | skill | 6 | skills.md §Directory Layout | — |
| S27 | Skill: `test/unit-test-patterns` | skill | 6 | skills.md §Directory Layout | — |
| S28 | Skill: `planning/task-decomposition` | skill | 6 | skills.md §Directory Layout | — |
| S29 | Skill: `research/source-evaluation` | skill | 7b | skills.md §Directory Layout | — |
| S30 | Skill: `research/citation-standards` | skill | 7b | skills.md §Directory Layout | — |
| S33 | Skill: `authoring/skill-authoring` (+ `references/skill-template.md`) | skill | 6 | FRD §CAP-9 (FR-6.41, FR-6.44, FR-6.45) | — |
| S34 | Skill: `authoring/agent-definition` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S35 | Skill: `authoring/workflow-authoring` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S36 | Skill: `authoring/project-conventions` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S31 | Auto-code skill: `test-generation` | skill | 7 | workflows.md §auto-code: The First Workflow | — |
| S32 | Director/PM role-bound skills (governance, oversight, management) | skill | 6 | FRD §CAP-10 | SkillLibrary (`always` trigger + `applies_to`) |
| S37 | `workflow-quality` skill (gate design patterns) | skill | 7 | workflows.md §Quality Gates | — |
| S38 | `workflow-testing` skill (dry runs, testing patterns) | skill | 7 | workflows.md §Quality Gates | — |
| S39 | `director-workflow-composition` skill | skill | 7b | workflows.md §Director Workflow Authoring | — |
| S40 | `software-development-patterns` domain skill | skill | 7b | workflows.md §Director Workflow Authoring | — |
| S41 | `research-patterns` domain skill | skill | 7b | workflows.md §Director Workflow Authoring | — |

---

## 10. Workflows

Source: `architecture/workflows.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| F01 | `WorkflowRegistry` class | module | 7 | workflows.md §WorkflowRegistry | WorkflowEntry |
| F02 | `WorkflowRegistry.match()` (keyword matching) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F03 | `WorkflowRegistry.get()` (explicit lookup) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F04 | `WorkflowRegistry.list_available()` | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F05 | `WorkflowRegistry.create_pipeline()` | mechanism | 7 | workflows.md §WorkflowRegistry | GlobalToolset, SkillLibrary |
| F06 | `WorkflowEntry` Pydantic model | module | 7 | workflows.md §WorkflowRegistry | — |
| F07 | `WORKFLOW.yaml` manifest schema (progressive disclosure) | config | 7 | workflows.md §Workflow Manifest | — |
| F08 | Workflow trigger matching (keywords) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F09 | Workflow trigger matching (explicit) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F10 | Workflow ambiguity resolution (user prompt) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F11 | `RunConfig` model | config | 7 | workflows.md §WorkflowRegistry | — |
| F12 | User-level workflow directory (override by name) | config | 7 | workflows.md §Architecture | — |
| F13 | `auto-code/WORKFLOW.yaml` manifest | workflow | 7 | workflows.md §auto-code: The First Workflow | — |
| F14 | `auto-code/pipeline.py` module | module | 7 | workflows.md §auto-code: The First Workflow | All auto-code agents |
| F15 | `auto-code/agents/` (planner, coder, reviewer) | module | 7 | workflows.md §auto-code: The First Workflow | — |
| F16 | `auto-code/skills/` (workflow-specific) | config | 7 | workflows.md §auto-code: The First Workflow | — |
| F17 | Compound workflow decomposition | mechanism | 11 | workflows.md §Compound Workflows | WorkflowRegistry |
| F18 | `pipeline.py` interface contract (function signature) | config | 7 | workflows.md §WorkflowRegistry | — |
| F19 | `WorkflowManifest` Pydantic model (all fields) | module | 7 | workflows.md §Workflow Manifest | — |
| F20 | `WorkflowRegistry.get_manifest()` | mechanism | 7 | workflows.md §WorkflowRegistry | WorkflowManifest |
| F21 | Manifest validation (L1 schema, required/warning/cross-ref) | mechanism | 7 | workflows.md §WorkflowRegistry | WorkflowManifest |
| F22 | `StageDef` Pydantic model | module | 7 | workflows.md §Stage Schema | — |
| F23 | `CompletionCriteria` Pydantic model | module | 7 | workflows.md §Completion Criteria & Reports | — |
| F24 | `GateDefinition` Pydantic model | module | 7 | workflows.md §Quality Gates | — |
| F25 | Stage state keys (`pm:current_stage`, `pm:stage_*`) | mechanism | 7 | workflows.md §Stage Schema | — |
| F26 | `reconfigure_stage` FunctionTool | tool | 7 | workflows.md §Stage Schema | Stage state keys |
| F27 | `verify_stage_completion` deterministic gate | mechanism | 7 | workflows.md §Completion Criteria & Reports | CompletionCriteria |
| F28 | `verify_taskgroup_completion` deterministic gate | mechanism | 7 | workflows.md §Completion Criteria & Reports | CompletionCriteria |
| F29 | `StageExecution` DB table | db | 7 | workflows.md §Stage Schema | `workflows` |
| F30 | `TaskGroupExecution` DB table | db | 7 | workflows.md §Stage Schema | StageExecution |
| F31 | `GateResult` DB table | db | 7 | workflows.md §Quality Gates | StageExecution |
| F32 | Standard gate: `lint_check` | mechanism | 7 | workflows.md §Quality Gates | LinterAgent |
| F33 | Standard gate: `test_suite` | mechanism | 7 | workflows.md §Quality Gates | TestRunnerAgent |
| F34 | Standard gate: `regression_tests` | mechanism | 7 | workflows.md §Quality Gates | RegressionTestAgent |
| F35 | Standard gate: `code_review` | mechanism | 7 | workflows.md §Quality Gates | ReviewerAgent |
| F36 | Standard gate: `dependency_validation` | mechanism | 7 | workflows.md §Quality Gates | — |
| F37 | Standard gate: `deliverable_status_check` | mechanism | 7 | workflows.md §Quality Gates | — |
| F38 | `CompletionReport` Pydantic model | module | 7 | workflows.md §Completion Criteria & Reports | — |
| F39 | `StageStatus` enum | module | 7 | workflows.md §Stage Schema | — |
| F40 | `GateType` enum | module | 7 | workflows.md §Quality Gates | — |
| F41 | `GateSchedule` enum | module | 7 | workflows.md §Quality Gates | — |
| F42 | Stage lifecycle events (STAGE_STARTED, STAGE_COMPLETED, etc.) | mechanism | 7 | workflows.md §Stage Schema | PipelineEventType |
| F43 | `ResourcesDef` validation (credentials, services, knowledge) | mechanism | 7 | workflows.md §Workflow Manifest | — |
| F58 | `PipelineContext` dataclass (stage config, manifest ref, runtime params) | module | 7 | workflows.md §Workflow Manifest | WorkflowManifest, StageDef |
| F59 | `McpServerDef` Pydantic model (MCP server metadata for manifest parsing) | module | 7 | workflows.md §Workflow Manifest | — |
| F44 | `list_available_tools()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | GlobalToolset |
| F45 | `list_mcp_servers()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | — |
| F46 | `list_configured_credentials()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | — |
| F47 | `list_workflows()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | WorkflowRegistry |
| F48 | `list_available_skills()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | SkillLibrary |
| F49 | `validate_workflow()` Director tool | tool | 7b | workflows.md §Director Workflow Authoring | WorkflowManifest |
| F50 | Director filesystem tool scoping (path-restricted) | mechanism | 7b | workflows.md §Director Workflow Authoring | — |
| F51 | Staging directory convention | mechanism | 7b | workflows.md §Director Workflow Authoring | — |
| F52 | Workflow activation gate (CEO queue) | mechanism | 7b | workflows.md §Director Workflow Authoring | CEO queue |
| F53 | Dry run execution framework (synthetic input, lightweight LLM, token budget, E2E simulation) | mechanism | 7b | workflows.md §Director Workflow Authoring | F64, WorkflowRegistry |
| F54 | Standard gate: `source_verification` | mechanism | 7b | workflows.md §Quality Gates | — |
| F55 | Standard gate: `citation_check` | mechanism | 7b | workflows.md §Quality Gates | — |
| F56 | Auto-code gate: `integration_tests` | mechanism | 7b | workflows.md §Quality Gates | Stub-referenced from Phase 7a auto-code manifest |
| F57 | Standard gate: `architecture_conformance` | mechanism | 7b | workflows.md §Quality Gates | Stub-referenced from Phase 7a auto-code manifest |
| F60 | Standard gate: `content_review` | mechanism | 7b | workflows.md §Quality Gates | — |
| F61 | `NodeDef` Pydantic model (node schema) | module | 7b | workflows.md §Node-Based Pipeline Schema | StageDef |
| F62 | `StepDef` Pydantic model (sub-unit within node) | module | 7b | workflows.md §Node-Based Pipeline Schema | NodeDef |
| F63 | `CompositeNodeDef` Pydantic model (review loop, future composites) | module | 7b | workflows.md §Node-Based Pipeline Schema | NodeDef |
| F64 | Node schema execution engine (interprets node schema without Python codegen) | module | 7b | workflows.md §Node-Based Pipeline Schema | F61, F63, AgentRegistry, InstructionAssembler |
| F65 | auto-code node schema migration (pipeline.py to declarative schema) | workflow | 7b | workflows.md §Node-Based Pipeline Schema | F13, F14, F61 |
| F66 | AST pipeline validator (import allowlist + dangerous-call detection) | mechanism | 7b | workflows.md §Node-Based Pipeline Schema | — |
| F67 | Workflow deactivation/reactivation mechanism | mechanism | 7b | workflows.md §Workflow Deactivation & Deletion | WorkflowRegistry, CEO queue |
| F68 | Workflow deletion with double-confirm | mechanism | 7b | workflows.md §Workflow Deactivation & Deletion | WorkflowRegistry, CEO queue |
| F69 | Import-level sandboxing for pipeline.py | mechanism | 7b | workflows.md §Node-Based Pipeline Schema | F66 |
| F70 | auto-research workflow (Director-authored) | workflow | 7b | workflows.md §Director Workflow Authoring | F54, F55, F60, F52 |
| F71 | auto-writer workflow (Director-authored) | workflow | 7b | workflows.md §Director Workflow Authoring | F54, F55, F60, F52 |
| F73 | Gate rename migration (validator to gate across codebase, DB, manifests, tests, docs) | migration | 7b | workflows.md §Quality Gates, FRD CAP-15 | F24, F31, F40, F41 |

---

## 11. State & Memory

Source: `architecture/state.md`

### 11.1 Session State

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| M01 | `temp:` scope handling | mechanism | 3 | state.md §1.2 | `DatabaseSessionService` |
| M02 | `user:` scope handling | mechanism | 3 | state.md §1.2 | `DatabaseSessionService` |
| M03 | `app:` scope handling | mechanism | 3 | state.md §1.2 | `DatabaseSessionService` |
| M04 | Session (no prefix) scope handling | mechanism | 3 | state.md §1.2 | `DatabaseSessionService` |
| M05 | State template injection (`{key}` / `{key?}`) | mechanism | 5a | state.md §1.2 | Session state |
| M06 | Project config loader (tool or init callback) | tool | 5a | state.md §1.2 | `project_configs` table |

### 11.2 Memory Service

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| M10 | `PostgresMemoryService` | module | 9 | state.md §5 | SQLAlchemy, memory table |
| M11 | `add_session_to_memory()` | mechanism | 9 | state.md §5 | PostgresMemoryService |
| M12 | `search_memory()` (tsvector) | mechanism | 9 | state.md §5 | PostgresMemoryService |
| M13 | Embedding model integration (LiteLLM) | module | 9 | state.md §5 | LiteLLM |
| M14 | Embedding model config | config | 9 | state.md §5 | — |
| M15 | `MemoryLoaderAgent` (CustomAgent) | agent | 5a | state.md §1.4, agents.md | BaseMemoryService (ADK); InMemoryMemoryService in Phase 5a, PostgresMemoryService in Phase 9 |
| M16 | `LoadMemory` tool | tool | 9 | state.md §1.4 | PostgresMemoryService |
| M17 | Memory ingestion strategy (configurable) | mechanism | 9 | state.md §9.2 | — |
| M18 | pgvector semantic search | mechanism | 9 | state.md §5 | pgvector, embeddings, LiteLLM |

### 11.3 Redis Cache

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| M20 | Redis connection pool | module | ✓ | state.md §2.2 | Redis |
| M21 | Skill index cache (long TTL) | mechanism | 6 | state.md §9.5 | Redis |
| M22 | Routing config cache (long TTL) | mechanism | 3 | state.md §9.5 | Redis |
| M23 | Session state snapshot cache (short TTL) | mechanism | 11 | state.md §9.5 | Redis |
| M24 | Workflow registry cache (long TTL) | mechanism | 7 | state.md §9.5 | Redis |
| M25 | Redis cache helpers (~100 LOC) | module | 3 | state.md §11 | Redis |
| M26 | Redis Stream publishers (~100 LOC) | module | 3 | state.md §11 | Redis |
| M27 | LLM response caching | mechanism | 11 | data.md §2 | Redis |

---

## 12. Context

Source: `architecture/context.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| CT01 | Context compression (sliding window summarization) | mechanism | 3 | context.md §Context Recreation | `EventsCompactionConfig` |
| CT02 | Skill pruning (reactive context response) | mechanism | 11 | context.md §Context Budget Monitoring | Context budget monitor |
| CT03 | Artifact storage (`save_artifact`/`load_artifact`) | mechanism | 8a | context.md §Knowledge Loading Layers | ADK artifacts API |
| CT04 | `ContextBudgetMonitor` (`before_model_callback`) | module | 5a | context.md §Context Budget Monitoring | LiteLLM `token_counter`, LlmRequest |
| CT05 | Context recreation pipeline (persist → seed → fresh session → reassemble) | mechanism | 5b | context.md §Context Recreation | InstructionAssembler, MemoryService, SkillLoaderAgent |
| CT06 | `ContextRecreationRequired` exception | module | 5a | context.md §Trigger Mechanics | ContextBudgetMonitor |
| CT07 | Context caching config (provider-dependent prompt caching) | config | 3 | context.md §Context Caching | Engine App container |

---

## 13. Observability

Source: `architecture/observability.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| O01 | OpenTelemetry tracing setup | config | 10 | observability.md §1 | — |
| O02 | Structured logging (`app.*` hierarchy) | config | ✓ | observability.md §1 | — |
| O03 | Langfuse LLM tracing (self-hosted, OTel ingestion) | plugin | 11 | observability.md §1 | OpenTelemetry |
| O07 | ADK Dev UI (local development only) | config | 10 | observability.md §1 | — |
| O08 | Dashboard observability views (trace explorer, latency) | ui | 12 | observability.md §1 | Dashboard, Langfuse |

---

## 14. Autonomous Execution Engine

Source: `architecture/execution.md`

### 14.1 Submission & Orchestration

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X01 | Director-mediated project entry (seven entry modes: new, new-with-materials, extend, edit, re-run, direct execution, workstream) + brief validation + project creation + PM delegation | mechanism | 8a | execution.md §Director Execution Turn | Director agent, WorkflowRegistry, X20, X21-X24 |
| X02 | Deliverable status tracking (lifecycle management via management tools) | mechanism | 8a | execution.md §PM loop | `deliverables` table |
| X03 | Director execution turn (backlog processing, PM delegation, escalation forwarding) | workflow | 8a | execution.md §Director Execution Turn | Director agent, PM agents, V23, X13, CEO queue |
| X04 | PM batch loop (autonomous, stage-driven, sequential) | workflow | 8a | execution.md §PM loop | PM agent, `select_ready_batch`, F25, F26, F27 |
| X12 | Management tool DB wiring (replace placeholder strings with real persistence) | mechanism | 8a | tools.md §3.7, §3.8 | DB session, `deliverables`/`director_queue`/`ceo_queue` tables |
| X13 | `escalate_to_director` real implementation (write to `director_queue` table) | mechanism | 8a | tools.md §3.7 | V23, T31 |
| X18 | Brief validation against workflow `brief_template` | mechanism | 8a | workflows.md §Workflow Manifest | F19, G02 |
| X19 | Pre-execution resource validation (credentials, services, knowledge) | mechanism | 8a | workflows.md §Resources | F43, CEO queue |
| G28 | `GET /director/queue` (list Director queue items) | route | 8a | events.md §Director Queue | V23 |
| G29 | `PATCH /director/queue/{id}` (resolve/forward Director queue item) | route | 8a | events.md §Director Queue | V23, CEO queue |
| X20 | `projects` table (first-order entity: workflow_type, status, stage, deliverables, escalations, cost) | db | 8a | data.md §Data Layer, Key Tables, execution.md §Director Execution Turn | Alembic migration, `workflows`/`deliverables` tables |
| X21 | Director `create_project` tool (create project entity in DB) | tool | 8a | execution.md §Director Execution Turn | X20 (`projects` table) |
| X22 | Director `validate_brief` tool (validate brief against workflow `brief_template`) | tool | 8a | workflows.md §Workflow Manifest | F19 (BriefTemplateDef), WorkflowRegistry |
| X23 | Director `check_resources` tool (verify credentials, services, knowledge) | tool | 8a | workflows.md §Resources | F43 (ResourcesDef), CEO queue |
| X24 | Director `delegate_to_pm` tool (enqueue PM work session for project) | tool | 8a | execution.md §Director Execution Turn | X20, ARQ `run_work_session` |
| X25 | PM `checkpoint_project` tool (save critical state at TaskGroup boundary) | tool | 8a | execution.md §PM loop | X20, session state |
| CT04b | Context recreation resume at TaskGroup boundary (save state, fresh session, resume) | mechanism | 8a | context.md §Context Recreation | CT03 (artifacts), session service |

### 14.2 Failure Handling & Completion

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A63 | *(cross-ref §6.6 Pipelines)* PM outer loop (sequential batch management) | workflow | 8a | execution.md §PM loop | PM agent, `select_ready_batch` |
| X08 | Autonomous failure handling (retry/reorder/skip) | mechanism | 8a | execution.md §PM loop | PM agent |
| X11 | Batch failure threshold (consecutive failures → Director suspension) | mechanism | 8a | execution.md §PM loop | PM agent, Director queue, `project_configs` |
| X14 | Three-layer completion report wiring into INTEGRATE gates | mechanism | 8a | workflows.md §Completion Criteria & Reports | F38, F27 |
| V19 | *(cross-ref §5 Events)* Batch completion event publishing | mechanism | 8a | events.md §Unified CEO Queue | Redis Streams |

### 14.3 Parallel Execution & Isolation

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A62 | *(cross-ref §6.6 Pipelines)* Parallel batch execution (ParallelAgent) | workflow | 8b | execution.md §PM loop | `DeliverablePipeline`, git worktrees, X10, X15 |
| X05 | Git worktree creation per deliverable | mechanism | 8b | execution.md §PM loop | Git |
| X06 | Git worktree merge on completion (dependency order) | mechanism | 8b | execution.md §PM loop | Git |
| X07 | Git worktree cleanup | mechanism | 8b | execution.md §PM loop | Git |
| X15 | Parallel worker state key namespacing (`worker:{deliverable_id}:*`) | mechanism | 8b | execution.md §PM loop | E13, A62 |
| X16 | Deterministic merge conflict resolution strategy | mechanism | 8b | execution.md §PM loop | X05, X06 |
| X10 | Concurrency limits (configurable, cascaded) | config | 8b | execution.md §PM loop | `project_configs` |
| X09 | Human-in-the-loop proactive intervention at batch boundary | mechanism | 8b | execution.md §PM loop | Intervention API |

### 14.4 Project Continuity

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X26 | Workflow-defined edit operations manifest field (`edit_operations` in WORKFLOW.yaml) | config | 8a | workflows.md §Workflow Manifest | WorkflowManifest model |
| X27 | Project edit request flow (Director receives edit → creates new TaskGroup in existing project) | workflow | 8a | execution.md §Director Execution Turn | X20, X21, CAP-6 batch loop |

### 14.5 Pause & Resume Lifecycle

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X28 | Project-level pause/resume mechanism (finish current deliverable, checkpoint, stop / load state, rebuild context, resume) | mechanism | 8a | execution.md §Pause & Resume | X25 (checkpoint), CT04b (context recreation) |
| X29 | Director work layer pause/resume mechanism (stop/resume backlog processing, cascade to active PMs) | mechanism | 8a | execution.md §Pause & Resume | X03 (Director turn), X28 |
| X30 | System-wide pause/resume (iterate project-level pause/resume for all active projects) | mechanism | 8a | execution.md §Pause & Resume | X28 |
| G30 | `POST /projects/{id}/pause` | route | 8a | execution.md §Pause & Resume | X28 |
| G31 | `POST /projects/{id}/resume` | route | 8a | execution.md §Pause & Resume | X28 |
| G32 | `POST /director/pause` | route | 8a | execution.md §Pause & Resume | X29 |
| G33 | `POST /director/resume` | route | 8a | execution.md §Pause & Resume | X29 |

### 14.6 Artifact Storage

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X31 | Deliverable artifact association (store and retrieve outputs per deliverable record) | mechanism | 8a | execution.md §Artifact Storage | `deliverables` table, filesystem |
| X32 | Completion report artifact association (store reports per TaskGroup/Stage execution) | mechanism | 8a | execution.md §Artifact Storage | F30 (TaskGroupExecution), F29 (StageExecution) |

---

## 15. CLI

Source: `architecture/clients.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| C01 | `autobuilder run <spec>` | cli | 10 | clients.md §CLI Architecture | `POST /specs`, `POST /workflows/{id}/run` |
| C02 | `autobuilder status <id>` | cli | 10 | clients.md §CLI Architecture | `GET /workflows/{id}/status` |
| C03 | `autobuilder intervene <id>` | cli | 10 | clients.md §CLI Architecture | `POST /workflows/{id}/intervene` |
| C04 | `autobuilder list` | cli | 10 | clients.md §CLI Architecture | `GET /workflows` |
| C05 | `autobuilder logs <id>` | cli | 10 | clients.md §CLI Architecture | `GET /events/stream` |
| C06 | Typer CLI scaffold (arg parsing, API client) | cli | 10 | clients.md §CLI Architecture | — |

---

## 16. Dashboard

Source: `architecture/clients.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| U01 | React 19 + Vite SPA scaffold | ui | 12 | clients.md §Dashboard Architecture | — |
| U02 | TanStack Query server state layer | ui | 12 | clients.md §Dashboard Architecture | hey-api codegen |
| U03 | Zustand SSE buffer + UI state store | ui | 12 | clients.md §Dashboard Architecture | — |
| U04 | Tailwind v4 `@theme` design system | ui | 12 | clients.md §Dashboard Architecture | — |
| U05 | hey-api codegen (`npm run generate`) | config | 12 | clients.md §Dashboard Architecture | OpenAPI spec |
| U06 | Pipeline visualization (real-time SSE) | ui | 12 | clients.md §Dashboard Architecture | SSE endpoint |
| U07 | Batch progress display (dependency graph) | ui | 12 | clients.md §Dashboard Architecture | — |
| U08 | State inspector (session state, skills, memory) | ui | 12 | clients.md §Dashboard Architecture | `GET /sessions/{id}/state` |
| U09 | Cost dashboards (per-run, per-agent, per-model) | ui | 12 | clients.md §Dashboard Architecture | `GET /costs` |
| U10 | Static build (CDN-deployable) | config | 12 | clients.md §Dashboard Architecture | Vite |

---

## Dropped Components

Components removed from the registry as unnecessary or over-engineered:

| # | Component | Reason |
|---|-----------|--------|
| D09 | `skills` table | File-based + Redis cache is sufficient per current architecture |
| V17 | CEO queue Redis Stream trigger consumer | `escalate_to_ceo` FunctionTool is the write path; second write path via stream consumer is over-engineering |

*V16 (`escalate_to_ceo` FunctionTool) was a duplicate of T17 — removed entirely rather than marked DROP (v1.2.2).*

---

## Statistics

See component entries above for current counts. Use `grep -c '| [0-9]' 07-COMPONENTS.md` for totals.

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 2.6.0 | 2026-04-12 | S29 (research/source-evaluation) and S30 (research/citation-standards) moved from Phase 13 to Phase 7b — runtime dependencies for auto-research/auto-writer workflows |
| 2.5.0 | 2026-04-12 | Phase 7b FRD back-propagation: 12 new components (F61-F71, F73); F53 consolidated (was duplicate of removed F72); gate rename (validator→gate) across all existing entries; F24→GateDefinition, F31→GateResult, F40→GateType, F41→GateSchedule; F54-F57/F60 updated to gate terminology; §Quality Gates source refs corrected; §Workflow Deactivation & Deletion source refs corrected |
| 2.4.0 | 2026-04-12 | Phase 8a FRD back-propagation: X01 updated (Director-mediated entry, seven entry modes); X28-X30 added (three-layer pause/resume lifecycle); G30-G33 added (pause/resume routes); X31-X32 added (artifact storage); Sections 14.5 and 14.6 added. 9 new components |
| 2.3.0 | 2026-04-12 | Phase 8a shaping: X20-X27 and CT04b added (project entity, Director creation tools, context recreation resume, project continuity); Section 14.4 added |
| 2.1.0 | 2026-04-12 | Phase 8a split into 8a + 8b: Section 14 reorganized into phase-aligned subsections; 9 new components (X12-X16, X18-X19, G28-G29) |
| 2.0.0 | 2026-03-12 | Phase 7a expansion (Decisions #70-77): 44 new workflow components (F19-F57, S37-S41); Phase 7b added (Director authoring) |
| 1.9.0 | 2026-03-11 | Phase 6 FRD back-propagation: S16-S17, S33-S36 added; S32 moved to Phase 6; S12 updated |
| 1.8.0 | 2026-03-10 | Phase 5b FRD decisions: A16 and X11 added; A72 moved to Phase 3 |
| 1.7.0 | 2026-03-10 | Phase 5 split into 5a and 5b; A78 split into A78a/A78b; M15 moved to 5a; A37 added |
| 1.6.0 | 2026-03-10 | New §12 Context section (CT01-CT07) sourced from context.md; sections renumbered |
| 1.5.0 | 2026-03-10 | Added 7 missing agent components: A36, A75-A80 (DiagnosticsAgent, SAFETY fragment, InstructionContext, partial override, security, state auth, auditability) |
| 1.4.0 | 2026-03-09 | Agent definitions → declarative markdown files with 3-scope cascade (Decision #54) |
| 1.3.0 | 2026-03-07 | Added InstructionAssembler, AgentDef, AgentRegistry, context recreation, system reminders (Decisions #50-53) |
| 1.2.0 | 2026-02-18 | Phase 4 toolset expansion: 42 tools, Director queue enums, management.py module |
| 1.1.0 | 2026-02-17 | All 55 gaps resolved: 53 assigned to phases, 2 dropped (D09, V17) |
| 1.0.0 | 2026-02-17 | Initial BOM — exhaustive extraction from 13 architecture domain files |

---

*Document Version: 2.6.0*
*Last Updated: 2026-04-12*
