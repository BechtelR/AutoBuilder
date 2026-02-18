# AutoBuilder Component Registry (BOM)
*Version: 1.1.0*

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
| G01 | `GET /health` | route | ✓ | gateway.md §2 | — |
| G02 | `POST /specs` | route | 8 | gateway.md §2 | Spec decomposition |
| G03 | `POST /workflows/{id}/run` | route | 8 | gateway.md §2 | ARQ worker, WorkflowRegistry |
| G04 | `GET /workflows/{id}/status` | route | 8 | gateway.md §2 | `workflows` table |
| G05 | `GET /workflows` | route | 10 | gateway.md §2 | WorkflowRegistry |
| G06 | `POST /workflows/{id}/intervene` | route | 8 | gateway.md §2 | ADK session, PM agent |
| G07 | `GET /deliverables` | route | 8 | gateway.md §2 | `deliverables` table |
| G08 | `GET /deliverables/{id}` | route | 8 | gateway.md §2 | `deliverables` table |
| G09 | `GET /events/stream` | endpoint | 10 | gateway.md §2 | Redis Streams, SSE |
| G10 | `POST /chat/{session_id}/messages` | route | 5 | gateway.md §2 | Director agent, `runner.run_async` |
| G11 | `GET /chat/{session_id}/messages` | route | 5 | gateway.md §2 | ADK session / DB |
| G12 | `GET /ceo/queue` | route | 5 | gateway.md §2 | `ceo_queue` table |
| G13 | `PATCH /ceo/queue/{id}` | route | 5 | gateway.md §2 | `ceo_queue` table, session state writeback |
| G14 | `GET /ceo/queue/stream` | endpoint | 10 | gateway.md §2 | `ceo_queue` table, Redis Streams |
| G15 | `GET /sessions/{id}/state` | endpoint | 11 | state.md §10 | `DatabaseSessionService` |
| G16 | `GET /memory/search` | endpoint | 9 | state.md §10 | `PostgresMemoryService` |
| G17 | `GET /metrics/tokens` | endpoint | 11 | state.md §10 | Token tracking |
| G18 | `GET /costs` | endpoint | 11 | state.md §10 | Token tracking |
| G19 | `GET /workflows/{id}/events` | endpoint | 10 | workflows.md §8 | Redis Streams, SSE |
| G20 | Gateway Pydantic request/response models | module | ✓ | gateway.md §3 | — |
| G21 | Anti-corruption translation layer | module | 3 | gateway.md §3 | Gateway models, ADK models |
| G22 | CORS middleware | module | ✓ | gateway.md §3 | — |
| G23 | Error handling middleware | module | ✓ | gateway.md §3 | — |
| G24 | Request logging middleware | module | ✓ | gateway.md §3 | — |
| G25 | Dependency injection (`deps.py`) | module | ✓ | gateway.md §3 | DB sessions, Redis client |
| G26 | OpenAPI spec auto-generation | mechanism | ✓ | gateway.md §4 | Gateway Pydantic models |
| G27 | hey-api TypeScript codegen | mechanism | 12 | gateway.md §4 | OpenAPI spec |

---

## 2. Database

Source: `architecture/data.md`, `architecture/state.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| D01 | `specifications` table | db | ✓ | data.md §1 | Alembic |
| D02 | `workflows` table | db | ✓ | data.md §1 | Alembic |
| D03 | `deliverables` table | db | ✓ | data.md §1 | Alembic |
| D04 | `sessions` table (ADK) | db | 3 | data.md §1 | `DatabaseSessionService` |
| D05 | `ceo_queue` table | db | 5 | data.md §1, events.md §4 | Alembic |
| D06 | `events` table (audit log) | db | 10 | data.md §1 | Audit consumer |
| D07 | `webhook_listeners` table | db | 10 | data.md §1 | Alembic |
| D08 | `project_configs` table | db | 5 | data.md §1, state.md §1.2 | Alembic |
| D09 | `skills` table | db | DROP | data.md §1 | File-based + Redis cache is sufficient per current architecture |
| D10 | `memory` table (tsvector + pgvector) | db | 9 | state.md §5 | pgvector extension |
| D11 | Job metadata table (ARQ tracking) | db | 3 | state.md §2.1 | Alembic, ARQ |
| D12 | SQLAlchemy async engine (shared) | module | ✓ | state.md §2.1 | asyncpg |
| D13 | `async_sessionmaker` factory | module | ✓ | state.md §2.1 | SQLAlchemy async engine |
| D14 | Alembic migration environment | config | ✓ | data.md §1 | — |
| D15 | Initial migration (core tables) | migration | ✓ | data.md §1 | Alembic |
| D16 | CEO queue migration | migration | 5 | events.md §4 | Alembic |
| D17 | Memory table migration | migration | 9 | state.md §5 | Alembic, pgvector |
| D18 | Events + webhook_listeners migration | migration | 10 | data.md §1 | Alembic |
| D19 | Project configs migration | migration | 5 | data.md §1 | Alembic |

---

## 3. Engine (ADK App Container)

Source: `architecture/engine.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| E01 | `App` container (`autobuilder`) | module | 3 | engine.md §5 | Director agent, plugins, configs |
| E02 | `build_director()` factory | module | 5 | engine.md §5 | Director agent config, project IDs |
| E03 | `build_pm()` factory | module | 5 | engine.md §5 | Project config, PM tools |
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
| W01 | ARQ WorkerSettings | config | ✓ | workers.md §2 | Redis |
| W02 | ARQ worker entry point | module | ✓ | workers.md §2 | ARQ WorkerSettings |
| W03 | `run_workflow()` ARQ job function | module | 3 | workers.md §3 | ADK Runner, session, events |
| W04 | `create_adk_runner()` factory | module | 3 | workers.md §3 | Anti-corruption layer |
| W05 | `create_or_resume_session()` | module | 3 | workers.md §3 | `DatabaseSessionService` |
| W06 | `translate_event()` | module | 3 | workers.md §3 | Gateway event models |
| W07 | `publish_to_stream()` | module | 3 | workers.md §3 | Redis Streams |
| W08 | `update_workflow_state()` | module | 3 | workers.md §3 | `workflows` table |
| W09 | ARQ cron jobs (heartbeat, cleanup) | mechanism | ✓ | workers.md §2 | ARQ, Redis |
| W10 | Worker re-delivery / idempotency handling | mechanism | 11 | workers.md §2 | `create_or_resume_session` |
| W11 | Multi-worker concurrency validation | mechanism | 11 | workers.md §2 | ARQ |

---

## 5. Events & CEO Queue

Source: `architecture/events.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| V01 | Per-workflow Redis Stream publishing | mechanism | 3 | events.md §1 | Redis Streams, `translate_event` |
| V02 | Redis Stream naming convention | config | 3 | events.md §1 | — |
| V03 | Redis Stream retention config | config | 10 | events.md §1 | Redis |
| V04 | Redis Stream consumer groups | mechanism | 10 | events.md §1 | Redis Streams |
| V05 | At-least-once delivery (ACK/NACK) | mechanism | 10 | events.md §1 | Consumer groups |
| V06 | SSE consumer | module | 10 | events.md §2 | Redis Streams, `GET /events/stream` |
| V07 | Webhook dispatcher consumer | module | 10 | events.md §2 | `webhook_listeners` table, httpx |
| V08 | Audit logger consumer | module | 10 | events.md §2 | `events` table |
| V09 | SSE reconnection (`Last-Event-ID` replay) | mechanism | 10 | events.md §3 | Redis Stream IDs |
| V10 | Webhook HMAC signature | mechanism | 10 | events.md §3 | Webhook dispatcher |
| V11 | Webhook retry (exponential backoff) | mechanism | 10 | events.md §3 | Webhook dispatcher |
| V12 | Event listener CRUD (register/unregister) | module | 10 | events.md §3 | `webhook_listeners` table |
| V13 | CEO queue type enum (`NOTIFICATION`, `APPROVAL`, `ESCALATION`, `TASK`) | config | 5 | events.md §4 | — |
| V14 | CEO queue priority enum (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`) | config | 5 | events.md §4 | — |
| V15 | CEO queue status enum (`PENDING`, `SEEN`, `RESOLVED`, `DISMISSED`) | config | 5 | events.md §4 | — |
| V16 | `enqueue_ceo_item` FunctionTool | tool | 4 | events.md §4 | CEO queue table |
| V17 | CEO queue Redis Stream trigger consumer | mechanism | DROP | events.md §4 | `enqueue_ceo_item` FunctionTool is the write path; second write path via stream consumer is over-engineering |
| V18 | CEO resolved approval → session state writeback | mechanism | 5 | events.md §4 | CEO queue, ADK session |
| V19 | Batch completion event publishing | mechanism | 8 | events.md §4 | Redis Streams |

---

## 6. Agents

Source: `architecture/agents.md`, `architecture/execution.md`

### 6.1 Supervision Tier

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A01 | Director agent (LlmAgent, opus) | agent | 5 | agents.md §4 | `build_director`, PM agents |
| A02 | PM agent (LlmAgent, sonnet) | agent | 5 | agents.md §5 | `build_pm`, PM tools |
| A03 | `build_director()` factory | module | 5 | agents.md §3 | Project IDs from DB |
| A04 | `build_pm()` factory | module | 5 | agents.md §3 | Project config |
| A05 | Director → PM delegation (`transfer_to_agent`) | mechanism | 5 | agents.md §5, §12 | ADK primitives |
| A06 | PM → Director escalation (`transfer_to_agent`) | mechanism | 5 | agents.md §5, §12 | ADK primitives |
| A07 | Hard limits cascade (CEO → Director → PM → Workers) | mechanism | 5 | agents.md §5 | `project_configs` |
| A08 | Director personality state (`user:` scope) | config | 5 | agents.md §4 | `user:` state, seed config |
| A09 | Director personality seed config file | config | 5 | agents.md §4 | — |
| A10 | Director tool authoring + CEO approval gate | mechanism | 13+ | agents.md §4 | Tool registry, CEO queue |
| A11 | Director cross-project pattern propagation | mechanism | 14 | agents.md §4 | `MemoryService` |
| A12 | Director governance tools | tool | 13+ | agents.md §4 | `AutoBuilderToolset` |
| A13 | Director "Main" project (permanent chat session) | mechanism | 5 | agents.md §4 | Session model |
| A14 | `before_agent_callback` (Director supervision) | callback | 5 | agents.md §5 | Director agent |
| A15 | `after_agent_callback` (Director supervision) | callback | 5 | agents.md §5 | Director agent |

### 6.2 Worker Tier — LLM Agents

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A20 | `plan_agent` (LlmAgent, opus) | agent | 5 | agents.md §7 | Read-only tools, skills |
| A21 | `code_agent` (LlmAgent, sonnet) | agent | 5 | agents.md §7 | Full tools, plan output |
| A22 | `review_agent` (LlmAgent, sonnet) | agent | 5 | agents.md §7 | Read-only tools, lint/test results |
| A23 | `fix_agent` (LlmAgent, sonnet) | agent | 5 | agents.md §7 | Full tools, review output |

### 6.3 Worker Tier — Custom (Deterministic) Agents

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A30 | `SkillLoaderAgent` (CustomAgent) | agent | 5 | agents.md §8 | SkillLibrary |
| A31 | `LinterAgent` (CustomAgent) | agent | 5 | agents.md §8 | Filesystem |
| A32 | `TestRunnerAgent` (CustomAgent) | agent | 5 | agents.md §8 | Filesystem |
| A33 | `FormatterAgent` (CustomAgent) | agent | 5 | agents.md §8 | Filesystem |
| A34 | `DependencyResolverAgent` (CustomAgent) | agent | 5 | agents.md §8 | Deliverable deps |
| A35 | `RegressionTestAgent` (CustomAgent) | agent | 5 | agents.md §8 | PM regression policy |

### 6.4 Callbacks & Hooks

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A40 | `verify_batch_completion` (`after_agent_callback`) | callback | 5 | agents.md §5 | PM agent |
| A41 | `checkpoint_project` (`after_agent_callback`) | callback | 5 | agents.md §5 | DeliverablePipeline |
| A42 | `context_budget_monitor` (`before_model_callback`) | callback | 5 | agents.md §8 | LlmRequest token counting |
| A43 | `before_model_callback` context injection | callback | 5 | agents.md §7 | Session state |
| A44 | `before_model_callback` LLM Router override | callback | 3 | agents.md §11 | LlmRouter |

### 6.5 Agent Communication

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A50 | `output_key` state communication | mechanism | 5 | agents.md §12.1 | Session state |
| A51 | `{key}` state template injection | mechanism | 5 | agents.md §12.2 | Session state |
| A52 | `InstructionProvider` dynamic instructions | mechanism | 5 | agents.md §12.3 | Session state |
| A53 | `plan_instruction_provider` | mechanism | 5 | agents.md §12.3 | `loaded_skills`, `memory_context` |
| A54 | `context_from_state` helper | module | 5 | agents.md §8 | Session state |

### 6.6 Pipelines & Loops

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A60 | `DeliverablePipeline` (SequentialAgent) | workflow | 5 | agents.md §2.1 | All worker agents |
| A61 | `ReviewCycle` (LoopAgent, max=3) | workflow | 5 | agents.md §2.1 | review, fix, lint, test agents |
| A62 | Parallel batch execution (ParallelAgent) | workflow | 8 | execution.md §PM loop | `DeliverablePipeline`, git worktrees |
| A63 | PM outer loop (batch management) | workflow | 8 | execution.md §PM loop | PM agent, `select_ready_batch` |

### 6.7 Session Model

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| A70 | Chat session model (per-message `runner.run_async`) | mechanism | 5 | execution.md §Multi-Session | Director, `DatabaseSessionService` |
| A71 | Work session model (long-running ARQ job) | mechanism | 3 | execution.md §Multi-Session | ARQ, `DatabaseSessionService` |
| A72 | Cross-session bridge (`app:`/`user:` state + memory + Redis Streams) | mechanism | 5 | execution.md §Multi-Session | Multiple subsystems |
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
| T04 | `file_search` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T05 | `directory_list` FunctionTool | tool | 4 | tools.md §3.1 | — |
| T06 | `bash_exec` FunctionTool | tool | 4 | tools.md §3.2 | — |
| T07 | `git_status` FunctionTool | tool | 4 | tools.md §3.5 | — |
| T08 | `git_commit` FunctionTool | tool | 4 | tools.md §3.5 | — |
| T09 | `git_branch` FunctionTool | tool | 4 | tools.md §3.5 | — |
| T10 | `git_diff` FunctionTool | tool | 4 | tools.md §3.5 | — |
| T11 | `web_search` FunctionTool | tool | 4 | tools.md §3.3 | Tavily primary, Brave fallback |
| T12 | `web_fetch` FunctionTool | tool | 4 | tools.md §3.3 | — |
| T13 | `todo_read` FunctionTool | tool | 4 | tools.md §3.4 | Session state |
| T14 | `todo_write` FunctionTool | tool | 4 | tools.md §3.4 | Session state |
| T15 | `todo_list` FunctionTool | tool | 4 | tools.md §3.4 | Session state |
| T16 | `select_ready_batch` FunctionTool | tool | 4 | tools.md §3.7 | Deliverable state |
| T17 | `enqueue_ceo_item` FunctionTool | tool | 4 | tools.md §3.7 | CEO queue |

### 7.2 Tool Modules

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| T20 | `app/tools/filesystem.py` | module | 4 | tools.md §7.1 | — |
| T21 | `app/tools/git.py` | module | 4 | tools.md §7.1 | — |
| T22 | `app/tools/execution.py` | module | 4 | tools.md §7.1 | — |
| T23 | `app/tools/web.py` | module | 4 | tools.md §7.1 | — |
| T24 | `app/tools/task.py` | module | 4 | tools.md §7.1 | — |
| T25 | `app/tools/project.py` | module | 4 | tools.md §7.1 | — |

### 7.3 Toolset & Permissions

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| T30 | `AutoBuilderToolset` (BaseToolset) | module | 4 | tools.md §7.3 | All FunctionTools |
| T31 | `resolve_role()` (role from ReadonlyContext) | module | 4 | tools.md §7.3 | ADK ReadonlyContext |
| T32 | Cascading permission config | config | 4 | tools.md §7.4 | — |
| T33 | Role scoping: `plan_agent` (read-only) | config | 4 | tools.md §7.5 | AutoBuilderToolset |
| T34 | Role scoping: `code_agent` (full tools) | config | 4 | tools.md §7.5 | AutoBuilderToolset |
| T35 | Role scoping: `review_agent` (read-only) | config | 4 | tools.md §7.5 | AutoBuilderToolset |
| T36 | Role scoping: PM (batch + shared) | config | 4 | tools.md §7.5 | AutoBuilderToolset |
| T37 | Role scoping: Director (governance + shared) | config | 4 | tools.md §7.5 | AutoBuilderToolset |

---

## 8. LLM Router

Source: `architecture/agents.md §11`, `architecture/tools.md §6`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| R01 | `LlmRouter` module | module | 3 | agents.md §11 | LiteLLM |
| R02 | Routing rules (static config) | config | 3 | agents.md §11 | — |
| R03 | Fallback chain resolution (3-step) | mechanism | 3 | agents.md §11 | Provider availability |
| R04 | `before_model_callback` model override | callback | 3 | agents.md §11 | LlmRouter |
| R05 | Adaptive router (cost-aware, latency-aware) | mechanism | 11 | agents.md §11 | Token tracking |

---

## 9. Skills

Source: `architecture/skills.md`

### 9.1 Skills Infrastructure

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| S01 | `SkillEntry` Pydantic model | module | 6 | skills.md §2 | Pydantic |
| S02 | `SkillLibrary` class | module | 6 | skills.md §3 | SkillEntry, frontmatter parser |
| S03 | Frontmatter parser (YAML from markdown) | module | 6 | skills.md §2 | — |
| S04 | `deliverable_type` trigger matcher | mechanism | 6 | skills.md §4 | — |
| S05 | `file_pattern` trigger matcher (glob) | mechanism | 6 | skills.md §4 | — |
| S06 | `tag_match` trigger matcher (set intersection) | mechanism | 6 | skills.md §4 | — |
| S07 | `explicit` trigger matcher | mechanism | 6 | skills.md §4 | — |
| S08 | `always` trigger matcher | mechanism | 6 | skills.md §4 | — |
| S09 | Description keyword fallback (interop) | mechanism | 6 | skills.md §5 | — |
| S10 | Two-tier scan (global + project-local override) | mechanism | 6 | skills.md §3 | — |
| S11 | Three-tier merge (+ workflow-specific) | mechanism | 7 | workflows.md §7 | SkillLibrary, WorkflowRegistry |
| S12 | `InstructionProvider` skill injection (`{loaded_skills}`) | mechanism | 6 | skills.md §6 | Session state, agent identity |
| S13 | Skill index Redis cache | mechanism | 6 | skills.md §7 | Redis |
| S14 | Skill cache invalidation (file change + gateway API) | mechanism | 6 | skills.md §7 | Redis, gateway |

### 9.2 Skill Files

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| S20 | `app/skills/` directory structure | config | 6 | skills.md §3 | — |
| S21 | `.app/skills/` project-local directory | config | 6 | skills.md §3 | — |
| S22 | Skill: `code/api-endpoint` | skill | 6 | skills.md §3 | — |
| S23 | Skill: `code/data-model` | skill | 6 | skills.md §3 | — |
| S24 | Skill: `code/database-migration` | skill | 6 | skills.md §3 | — |
| S25 | Skill: `review/security-review` | skill | 6 | skills.md §3 | — |
| S26 | Skill: `review/performance-review` | skill | 6 | skills.md §3 | — |
| S27 | Skill: `test/unit-test-patterns` | skill | 6 | skills.md §3 | — |
| S28 | Skill: `planning/task-decomposition` | skill | 6 | skills.md §3 | — |
| S29 | Skill: `research/source-evaluation` | skill | 13 | skills.md §3 | — |
| S30 | Skill: `research/citation-standards` | skill | 13 | skills.md §3 | — |
| S31 | Auto-code skill: `test-generation` | skill | 7 | workflows.md §7 | — |
| S32 | Director/PM governance skills | skill | 13+ | agents.md §4 | — |

---

## 10. Workflows

Source: `architecture/workflows.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| F01 | `WorkflowRegistry` class | module | 7 | workflows.md §4 | WorkflowEntry |
| F02 | `WorkflowRegistry.match()` (keyword matching) | mechanism | 7 | workflows.md §4 | — |
| F03 | `WorkflowRegistry.get()` (explicit lookup) | mechanism | 7 | workflows.md §4 | — |
| F04 | `WorkflowRegistry.list_available()` | mechanism | 7 | workflows.md §4 | — |
| F05 | `WorkflowRegistry.create_pipeline()` | mechanism | 7 | workflows.md §4 | AutoBuilderToolset, SkillLibrary |
| F06 | `WorkflowEntry` Pydantic model | module | 7 | workflows.md §4 | — |
| F07 | `WORKFLOW.yaml` manifest schema | config | 7 | workflows.md §5 | — |
| F08 | Workflow trigger matching (keywords) | mechanism | 7 | workflows.md §4 | — |
| F09 | Workflow trigger matching (explicit) | mechanism | 7 | workflows.md §4 | — |
| F10 | Workflow ambiguity resolution (user prompt) | mechanism | 7 | workflows.md §4 | — |
| F11 | `RunConfig` model | config | 7 | workflows.md §4 | — |
| F12 | Custom workflows directory (overrides) | config | 7 | workflows.md §4 | — |
| F13 | `auto-code/WORKFLOW.yaml` manifest | workflow | 7 | workflows.md §7 | — |
| F14 | `auto-code/pipeline.py` module | module | 7 | workflows.md §7 | All auto-code agents |
| F15 | `auto-code/agents/` (plan, code, review, fix) | module | 7 | workflows.md §7 | — |
| F16 | `auto-code/skills/` (workflow-specific) | config | 7 | workflows.md §7 | — |
| F17 | Compound workflow decomposition | mechanism | 11 | workflows.md §6 | WorkflowRegistry |
| F18 | `pipeline.py` interface contract (function signature) | config | 7 | workflows.md §4 | — |

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
| M05 | State template injection (`{key}` / `{key?}`) | mechanism | 5 | state.md §1.2 | Session state |
| M06 | Project config loader (tool or init callback) | tool | 5 | state.md §1.2 | `project_configs` table |

### 11.2 Memory Service

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| M10 | `PostgresMemoryService` | module | 9 | state.md §5 | SQLAlchemy, memory table |
| M11 | `add_session_to_memory()` | mechanism | 9 | state.md §5 | PostgresMemoryService |
| M12 | `search_memory()` (tsvector) | mechanism | 9 | state.md §5 | PostgresMemoryService |
| M13 | Embedding model integration (LiteLLM) | module | 9 | state.md §5 | LiteLLM |
| M14 | Embedding model config | config | 9 | state.md §5 | — |
| M15 | `PreloadMemoryTool` | tool | 9 | state.md §1.4 | PostgresMemoryService |
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

## 12. Observability

Source: `architecture/observability.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| O01 | OpenTelemetry tracing setup | config | 10 | observability.md §1 | — |
| O02 | Structured logging (`app.*` hierarchy) | config | ✓ | observability.md §1 | — |
| O03 | Langfuse LLM tracing (self-hosted, OTel ingestion) | plugin | 11 | observability.md §1 | OpenTelemetry |
| O04 | Context compression (sliding window summarization) | mechanism | 3 | observability.md §2 | `EventsCompactionConfig` |
| O05 | Skill pruning (reactive context response) | mechanism | 11 | observability.md §2 | Context budget monitor |
| O06 | Artifact storage (`save_artifact`/`load_artifact`) | mechanism | 8 | observability.md §3 | ADK artifacts API |
| O07 | ADK Dev UI (local development only) | config | 10 | observability.md §1 | — |
| O08 | Dashboard observability views (trace explorer, latency) | ui | 12 | observability.md §1 | Dashboard, Langfuse |

---

## 13. Spec Pipeline & Execution

Source: `architecture/execution.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| X01 | Spec submission + decomposition | mechanism | 8 | execution.md §1 | `specifications` table |
| X02 | Deliverable status tracking | mechanism | 8 | execution.md §2 | `deliverables` table |
| X03 | Director execution loop | workflow | 8 | execution.md §3 | Director agent, PM agents |
| X04 | PM batch loop (autonomous) | workflow | 8 | execution.md §4 | PM agent, `select_ready_batch` |
| X05 | Git worktree creation per deliverable | mechanism | 8 | execution.md §4 | Git |
| X06 | Git worktree merge on completion | mechanism | 8 | execution.md §4 | Git |
| X07 | Git worktree cleanup | mechanism | 8 | execution.md §4 | Git |
| X08 | Autonomous failure handling (retry/reorder/skip) | mechanism | 8 | execution.md §4 | PM agent |
| X09 | Human-in-the-loop pause at batch boundary | mechanism | 8 | execution.md §4 | Intervention API |
| X10 | Concurrency limits (configurable, cascaded) | config | 8 | execution.md §4 | `project_configs` |

---

## 14. CLI

Source: `architecture/clients.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| C01 | `autobuilder run <spec>` | cli | 10 | clients.md §1 | `POST /specs`, `POST /workflows/{id}/run` |
| C02 | `autobuilder status <id>` | cli | 10 | clients.md §1 | `GET /workflows/{id}/status` |
| C03 | `autobuilder intervene <id>` | cli | 10 | clients.md §1 | `POST /workflows/{id}/intervene` |
| C04 | `autobuilder list` | cli | 10 | clients.md §1 | `GET /workflows` |
| C05 | `autobuilder logs <id>` | cli | 10 | clients.md §1 | `GET /events/stream` |
| C06 | Typer CLI scaffold (arg parsing, API client) | cli | 10 | clients.md §1 | — |

---

## 15. Dashboard

Source: `architecture/clients.md`

| # | Component | Type | Phase | Source | Dependencies |
|---|-----------|------|-------|--------|--------------|
| U01 | React 19 + Vite SPA scaffold | ui | 12 | clients.md §2 | — |
| U02 | TanStack Query server state layer | ui | 12 | clients.md §2 | hey-api codegen |
| U03 | Zustand SSE buffer + UI state store | ui | 12 | clients.md §2 | — |
| U04 | Tailwind v4 `@theme` design system | ui | 12 | clients.md §2 | — |
| U05 | hey-api codegen (`npm run generate`) | config | 12 | clients.md §2 | OpenAPI spec |
| U06 | Pipeline visualization (real-time SSE) | ui | 12 | clients.md §2 | SSE endpoint |
| U07 | Batch progress display (dependency graph) | ui | 12 | clients.md §2 | — |
| U08 | State inspector (session state, skills, memory) | ui | 12 | clients.md §2 | `GET /sessions/{id}/state` |
| U09 | Cost dashboards (per-run, per-agent, per-model) | ui | 12 | clients.md §2 | `GET /costs` |
| U10 | Static build (CDN-deployable) | config | 12 | clients.md §2 | Vite |

---

## Dropped Components

Components removed from the registry as unnecessary or over-engineered:

| # | Component | Reason |
|---|-----------|--------|
| D09 | `skills` table | File-based + Redis cache is sufficient per current architecture |
| V17 | CEO queue Redis Stream trigger consumer | `enqueue_ceo_item` FunctionTool is the write path; second write path via stream consumer is over-engineering |

---

## Statistics

| Metric | Count |
|--------|-------|
| Total components | 272 |
| Dropped | 2 |
| Active components | 270 |
| Assigned (with phase) | 270 |
| **Unassigned (gaps)** | **0** |
| Phase 0-2 (done) | 19 |
| Phase 3 | 35 |
| Phase 4 | 33 |
| Phase 5 | 50 |
| Phase 6 | 23 |
| Phase 7 | 20 |
| Phase 8 | 19 |
| Phase 9 | 11 |
| Phase 10 | 25 |
| Phase 11 | 17 |
| Phase 12 | 11 |
| Phase 13 / 13+ / 14 | 6 |

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 1.1.0 | 2026-02-17 | All 55 gaps resolved: 53 assigned to phases, 2 dropped (D09, V17) |
| 1.0.0 | 2026-02-17 | Initial BOM — exhaustive extraction from 13 architecture domain files |

---

*Document Version: 1.1.0*
*Last Updated: 2026-02-17*
