# AutoBuilder Component Registry (BOM)
*Version: 2.0.0*

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
| G02 | `POST /specs` | route | 8 | gateway.md §Route Structure | Spec decomposition |
| G03 | `POST /workflows/{id}/run` | route | 8 | gateway.md §Route Structure | ARQ worker, WorkflowRegistry |
| G04 | `GET /workflows/{id}/status` | route | 8 | gateway.md §Route Structure | `workflows` table |
| G05 | `GET /workflows` | route | 10 | gateway.md §Route Structure | WorkflowRegistry |
| G06 | `POST /workflows/{id}/intervene` | route | 8 | gateway.md §Route Structure | ADK session, PM agent |
| G07 | `GET /deliverables` | route | 8 | gateway.md §Route Structure | `deliverables` table |
| G08 | `GET /deliverables/{id}` | route | 8 | gateway.md §Route Structure | `deliverables` table |
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
| V19 | Batch completion event publishing | mechanism | 8 | events.md §Unified CEO Queue | Redis Streams |
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
| A62 | Parallel batch execution (ParallelAgent) | workflow | 8 | execution.md §PM loop | `DeliverablePipeline`, git worktrees |
| A63 | PM outer loop (batch management) | workflow | 8 | execution.md §PM loop | PM agent, `select_ready_batch` |

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
| S29 | Skill: `research/source-evaluation` | skill | 13 | skills.md §Directory Layout | — |
| S30 | Skill: `research/citation-standards` | skill | 13 | skills.md §Directory Layout | — |
| S33 | Skill: `authoring/skill-authoring` (+ `references/skill-template.md`) | skill | 6 | FRD §CAP-9 (FR-6.41, FR-6.44, FR-6.45) | — |
| S34 | Skill: `authoring/agent-definition` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S35 | Skill: `authoring/workflow-authoring` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S36 | Skill: `authoring/project-conventions` | skill | 6 | FRD §CAP-9 (FR-6.41) | — |
| S31 | Auto-code skill: `test-generation` | skill | 7 | workflows.md §auto-code: The First Workflow | — |
| S32 | Director/PM role-bound skills (governance, oversight, management) | skill | 6 | FRD §CAP-10 | SkillLibrary (`always` trigger + `applies_to`) |

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
| F07 | `WORKFLOW.yaml` manifest schema | config | 7 | workflows.md §Workflow Manifest | — |
| F08 | Workflow trigger matching (keywords) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F09 | Workflow trigger matching (explicit) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F10 | Workflow ambiguity resolution (user prompt) | mechanism | 7 | workflows.md §WorkflowRegistry | — |
| F11 | `RunConfig` model | config | 7 | workflows.md §WorkflowRegistry | — |
| F12 | Custom workflows directory (overrides) | config | 7 | workflows.md §WorkflowRegistry | — |
| F13 | `auto-code/WORKFLOW.yaml` manifest | workflow | 7 | workflows.md §auto-code: The First Workflow | — |
| F14 | `auto-code/pipeline.py` module | module | 7 | workflows.md §auto-code: The First Workflow | All auto-code agents |
| F15 | `auto-code/agents/` (planner, coder, reviewer) | module | 7 | workflows.md §auto-code: The First Workflow | — |
| F16 | `auto-code/skills/` (workflow-specific) | config | 7 | workflows.md §auto-code: The First Workflow | — |
| F17 | Compound workflow decomposition | mechanism | 8 | workflows.md §Workflow Chaining | WorkflowRegistry |
| F18 | `pipeline.py` interface contract (function signature) | config | 7 | workflows.md §WorkflowRegistry | — |
| F19 | `WorkflowManifest` Pydantic model | module | 7 | workflows.md §Workflow Manifest | — |
| F20 | `StageConfig` frozen dataclass | module | 7 | workflows.md §Stage Schema Architecture | — |
| F21 | `StageSchema` frozen dataclass (ordered list, `get()`, `next()`, `is_final()`) | module | 7 | workflows.md §Stage Schema Architecture | StageConfig |
| F22 | `resolve_stage_config()` function (merge workflow defaults + stage overrides) | mechanism | 7 | workflows.md §Stage Schema Architecture | WorkflowManifest, StageConfig |
| F23 | `PipelineType` enum (`BATCH_PARALLEL`, `SEQUENTIAL`, `SINGLE_PASS`) | config | 7 | workflows.md §Workflow Manifest | — |
| F24 | `ResourceDeclaration` model (tools, credentials, services, inputs) | module | 7 | workflows.md §Resource Pre-Flight | — |
| F25 | `ValidatorDeclaration` model (name, type, schedule, required, fail_action) | module | 7 | workflows.md §Workflow Ecosystem Model | — |
| F26 | `ResourcePreflightAgent` (deterministic CustomAgent) | agent | 7 | workflows.md §Resource Pre-Flight | ResourceDeclaration, CEO queue |
| F27 | `ResourceCheckType` enum (8 check types) | config | 7 | workflows.md §Resource Pre-Flight | — |
| F28 | `resource_preflight.md` agent definition file | config | 7 | workflows.md §Resource Pre-Flight | AgentRegistry |
| F29 | `ResourceEntry` SQLAlchemy model (`resource_library` table) | db | 7 | workflows.md §Resource Library | Alembic |
| F30 | `ProjectResource` SQLAlchemy model (`project_resources` table) | db | 7 | workflows.md §Resource Library | Alembic |
| F31 | `resource_library` + `project_resources` migration | migration | 7 | workflows.md §Resource Library | Alembic |
| F32 | `GET/POST/PUT/DELETE /resources` CRUD routes | route | 7 | workflows.md §Resource Library | ResourceEntry |
| F33 | `POST /projects/{id}/resources/bind` route | route | 7 | workflows.md §Resource Library | ProjectResource |
| F34 | `browse_resources` FunctionTool (Director tool) | tool | 7 | workflows.md §Resource Library | ResourceEntry |
| F35 | `validate_workflow` FunctionTool | tool | 7 | workflows.md §Director Workflow Authoring | WorkflowManifest, WorkflowRegistry |
| F36 | `current_stage` column migration (project table) | migration | 7 | workflows.md §Stage Schema Architecture | Alembic |
| F37 | `CeoQueueItemType.STAGE_APPROVAL` enum value | config | 7 | workflows.md §Stage Schema Architecture | enums.py |
| F38 | `STAGE_TRANSITION` event type | config | 7 | workflows.md §Stage Schema Architecture | enums.py |
| F39 | Stage-aware pipeline factory (StageConfig → `create_deliverable_pipeline()`) | mechanism | 7 | workflows.md §Stage Schema Architecture | pipeline.py |
| F40 | AgentRegistry stage filter (`agent_filter` parameter) | mechanism | 7 | workflows.md §Stage Schema Architecture | _registry.py |
| F41 | InstructionAssembler stage context (TASK + GOVERNANCE fragments) | mechanism | 7 | workflows.md §Stage Schema Architecture | assembler.py |
| F42 | `auto-code/standards/coding-standards.md` GOVERNANCE fragment | config | 7 | workflows.md §auto-code: The First Workflow | — |
| F43 | `auto-code/validators/` (lint.yaml, test.yaml, review.yaml) | config | 7 | workflows.md §auto-code: The First Workflow | — |
| F44 | Skill: `authoring/workflow-composition` (Director-tier) | skill | 7 | workflows.md §Director Workflow Authoring | — |
| F45 | Skill: `authoring/resource-composition` (Director-tier) | skill | 7 | workflows.md §Director Workflow Authoring | — |
| F46 | `produces`/`consumes` manifest declarations (forward-compatible) | config | 7 | workflows.md §Workflow Chaining | — |
| F47 | `ResourceCategory` enum | config | 7 | workflows.md §Resource Library | enums.py |
| F48 | `ResourceStatus` enum | config | 7 | workflows.md §Resource Library | enums.py |

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
| M15 | `MemoryLoaderAgent` | CustomAgent | 5a | state.md §1.4, agents.md | BaseMemoryService (ADK); InMemoryMemoryService in Phase 5a, PostgresMemoryService in Phase 9 |
| M16 | `LoadMemory` tool | tool | 9 | state.md §1.4 | PostgresMemoryService |
| M17 | Memory ingestion strategy (configurable) | mechanism | 9 | state.md §9.2 | — |
| M18 | pgvector semantic search upgrade | mechanism | 11 | state.md §5 | pgvector, embeddings |

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
| CT03 | Artifact storage (`save_artifact`/`load_artifact`) | mechanism | 8 | context.md §Knowledge Loading Layers | ADK artifacts API |
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

## 14. Spec Pipeline & Execution

Source: `architecture/execution.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X01 | Spec submission + decomposition | mechanism | 8 | execution.md §Director loop | `specifications` table |
| X02 | Deliverable status tracking | mechanism | 8 | execution.md §PM loop | `deliverables` table |
| X03 | Director execution loop | workflow | 8 | execution.md §Director loop | Director agent, PM agents |
| X04 | PM batch loop (autonomous) | workflow | 8 | execution.md §PM loop | PM agent, `select_ready_batch` |
| X05 | Git worktree creation per deliverable | mechanism | 8 | execution.md §PM loop | Git |
| X06 | Git worktree merge on completion | mechanism | 8 | execution.md §PM loop | Git |
| X07 | Git worktree cleanup | mechanism | 8 | execution.md §PM loop | Git |
| X08 | Autonomous failure handling (retry/reorder/skip) | mechanism | 8 | execution.md §PM loop | PM agent |
| X09 | Human-in-the-loop pause at batch boundary | mechanism | 8 | execution.md §PM loop | Intervention API |
| X10 | Concurrency limits (configurable, cascaded) | config | 8 | execution.md §PM loop | `project_configs` |
| X11 | Batch failure threshold (consecutive failures → Director suspension) | mechanism | 8 | execution.md §PM loop | PM agent, Director queue, `project_configs` |

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

| Metric | Count |
|--------|-------|
| Total components | 361 |
| Dropped | 2 |
| Active components | 359 |
| Assigned (with phase) | 359 |
| **Unassigned (gaps)** | **0** |
| Phase 0-2 (done) | 19 |
| Phase 3 | 37 |
| Phase 4 | 62 |
| Phase 5a | 48 |
| Phase 5b | 21 |
| Phase 6 | 31 |
| Phase 7 | 51 |
| Phase 8 | 22 |
| Phase 9 | 10 |
| Phase 10 | 25 |
| Phase 11 | 16 |
| Phase 12 | 12 |
| Phase 13 / 13+ / 14 | 5 |

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 2.0.0 | 2026-03-12 | Phase 7 architecture: F19-F48 added (WorkflowManifest, StageConfig, StageSchema, resolve_stage_config, PipelineType, ResourceDeclaration, ValidatorDeclaration, ResourcePreflightAgent, ResourceCheckType, resource_preflight.md, ResourceEntry, ProjectResource, resource migrations, resource CRUD routes, browse_resources tool, validate_workflow tool, current_stage migration, STAGE_APPROVAL/STAGE_TRANSITION enums, stage-aware pipeline factory, AgentRegistry stage filter, InstructionAssembler stage context, auto-code standards/validators, workflow-composition/resource-composition skills, produces/consumes declarations, ResourceCategory/ResourceStatus enums); F17 moved 11→8 (compound workflow is Phase 8 scope); statistics updated (Total 331→361, Active 329→359, Phase 7 21→51, Phase 8 21→22, Phase 11 17→16) |
| 1.9.0 | 2026-03-11 | Phase 6 FRD back-propagation: S16-S17 added (supervision-tier resolution, skill validation); S33-S36 added (4 authoring skills); S32 moved 13+→6 (Director/PM role-bound skills); S12 updated (adds `applies_to` filtering); statistics updated (Total 325→331, Active 323→329, Phase 6 24→31, Phase 13+/14 6→5) |
| 1.8.1 | 2026-03-10 | Fix Phase 3 count 36→37 (A72 move was not reflected in statistics) |
| 1.8.0 | 2026-03-10 | Phase 5b FRD decisions: A16 added (Director queue consumption, 5b); X11 added (batch failure threshold, 8); A72 moved 5b→3 (cross-session bridge already operational via state scopes + Redis Streams); statistics updated (Total 323→325, Active 321→323, Phase 0-2 19→20, Phase 8 20→21) |
| 1.7.0 | 2026-03-10 | Phase 5 split into 5a (Agent Definitions & Pipeline) and 5b (Supervision & Integration); A78 split into A78a (type validation, 5a) and A78b (tool_role ceiling, 7); M15 moved from Phase 9 to 5a (degraded mode with InMemoryMemoryService); A37 added for MemoryLoaderAgent agent entry |
| 1.6.0 | 2026-03-10 | New §12 Context section (CT01-CT07) sourced from context.md; O04-O06 migrated to CT01-CT03; A42 absorbed into CT04; sections renumbered (Observability→13, Spec Pipeline→14, CLI→15, Dashboard→16) |
| 1.5.0 | 2026-03-10 | Add 7 missing agent components: DiagnosticsAgent (A36), SAFETY fragment (A75), InstructionContext (A76), partial override (A77), project-scope security (A78), state key authorization (A79), resolution auditability (A80); update A57 fragment types; fix v1.4.0 cascade scope count (4→3) |
| 1.4.0 | 2026-03-09 | Agent definitions → declarative markdown files with 3-scope cascade (Decision #54); AgentDef dataclass removed |
| 1.3.0 | 2026-03-07 | Add InstructionAssembler, AgentDef, AgentRegistry, context recreation, system reminders (Decisions #50-53) |
| 1.2.3 | 2026-02-27 | Fix: all source references updated from ordinal §N to named section headings across gateway, workers, events, agents, skills, workflows, execution, clients domain files |
| 1.2.2 | 2026-02-18 | Fix: drop duplicate V16 entry (`escalate_to_ceo` counted twice); canonical entry is T17 in Section 7.1; update statistics (Total 306→305, Dropped 2→3, Active 304→302, Phase 4 63→62) |
| 1.2.1 | 2026-02-18 | Fix: section ref mismatches (T06-T17), ID collisions (Tool Modules → TM##, Toolset → TS##), add missing fixer scoping (TS07), correct statistics, fix dashboard phase comment in 03-STRUCTURE.md |
| 1.2.0 | 2026-02-18 | Phase 4 toolset expansion: 42 tools, Director queue enums, management.py module + new code.py |
| 1.1.0 | 2026-02-17 | All 55 gaps resolved: 53 assigned to phases, 2 dropped (D09, V17) |
| 1.0.0 | 2026-02-17 | Initial BOM — exhaustive extraction from 13 architecture domain files |

---

*Document Version: 2.0.0*
*Last Updated: 2026-03-12*
