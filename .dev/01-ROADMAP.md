# AutoBuilder Project Roadmap
*Version: 1.4.0*

**Single source of truth for project status and phased delivery.**

## Overview

AutoBuilder is delivered in phased increments. Each phase produces testable, independently validatable output. No phase begins until its prerequisites are validated. The MVP (Phases 0–10) proves the core thesis: an autonomous agentic system can take a specification, decompose it into deliverables, execute them in parallel, and produce verified output with minimal human intervention — through a production-grade API gateway with async worker execution.

**Status — Phase 0: COMPLETE ✓ | Phase 1: DONE ✓ | Phase 2: DONE ✓ | Phase 3: NEXT**

---

## Phase 0: Project Scaffold & Dev Environment `S`

**Goal**: Working empty project that builds, lints, and type-checks clean.

**Status**: COMPLETE

**Prerequisites**: None

### Deliverables

#### Project Configuration
- [x] `pyproject.toml` (uv, ruff, pyright, pytest, hatchling)
- [x] `alembic.ini` + initial Alembic configuration
- [x] `.gitignore` (Python, Node, IDE, env files)
- [x] `pre-commit` configuration (ruff + pyright hooks)
- [x] `docker-compose.yml` (PostgreSQL + Redis services)
- [x] Docker verification: `docker compose up -d` starts PostgreSQL + Redis

#### Directory Scaffold
- [x] `app/` package with `__init__.py` and `__main__.py`
- [x] All subdirectories per `.dev/03-STRUCTURE.md` with `__init__.py` files
- [x] `tests/conftest.py` skeleton
- [x] `scripts/` directory
- [x] `dashboard/` placeholder (Phase 12)

#### Configuration Module
- [x] `app/config/` — Pydantic Settings for environment variables
- [x] Default values matching CLAUDE.md environment table

#### Shared Domain Models
- [x] `app/models/enums.py` — initial domain enums (WorkflowStatus, DeliverableStatus, AgentRole)
- [x] `app/models/constants.py` — shared constants
- [x] `app/models/base.py` — Pydantic base models

#### Dev Tooling
- [x] `uv sync` installs all dependencies
- [x] `ruff check .` passes
- [x] `ruff format --check .` passes
- [x] `pyright` passes (strict mode)
- [x] `pytest` runs (3 scaffold tests pass)

### Completion Contract

- [x] `docker compose up -d` starts PostgreSQL and Redis
- [x] `uv sync && uv run ruff check . && uv run pyright && uv run pytest` all pass
- [x] Directory structure matches `.dev/03-STRUCTURE.md`
- [x] Configuration loads from environment variables with sensible defaults
- [x] Shared enums and base models importable from `app.models`

---

## Phase 1: ADK Prototype Validation `M`

**Goal**: Validate critical ADK assumptions before full commitment. Go/no-go gate.

**Status**: DONE

**Prerequisites**: Phase 0 (project scaffold exists, dependencies installable)

### Overview

Five focused prototypes validate that Google ADK can serve as AutoBuilder's orchestration engine. P1–P4 validate core patterns with Claude via LiteLLM. P5 validates alternate providers (OpenAI, Gemini) as production fallbacks.

### Deliverables

#### P1: Basic Agent Loop + Claude via LiteLLM
- [x] ADK `LlmAgent` with Claude via LiteLLM wrapper
- [x] `FunctionTool` wrappers: file-read, file-write, bash
- [x] **Validates**: Claude reliability through LiteLLM, latency, token counting accuracy
- [x] **Pass criteria**: Claude responds reliably, tools execute correctly, token counts are accurate

#### P2: Mixed Agent Coordination (LLM + Deterministic)
- [x] `plan_agent` (LlmAgent) + `linter_agent` (CustomAgent)
- [x] `SequentialAgent` pipeline wiring
- [x] State passing via `output_key` → state read
- [x] **Validates**: Unified event stream, state persistence across agent types, observability of deterministic steps
- [x] **Pass criteria**: Deterministic agent events appear in same stream; state written by one agent is readable by next

#### P3: Parallel Execution
- [x] 3 `LlmAgent` instances via `ParallelAgent`
- [x] Each writes to distinct state keys
- [x] **Validates**: No state collision, proper isolation, concurrent LLM calls, correct event interleaving
- [x] **Pass criteria**: All 3 agents produce correct output without cross-contamination

#### P4: Dynamic Outer Loop (CustomAgent Orchestrator)
- [x] `CustomAgent` that dynamically constructs `ParallelAgent` batches
- [x] "While incomplete features exist" loop with dependency ordering
- [x] Test with 5 simple features
- [x] **Validates**: Dynamic workflow construction, execution order respects dependencies, failure handling
- [x] **Pass criteria**: Features execute in dependency order; failed features don't block independent ones; loop terminates

#### P5: Alternate Provider Validation (OpenAI + Gemini)
- [x] OpenAI basic response + tool calling via `LiteLlm(model="openai/gpt-5-nano")`
- [x] Gemini basic response + tool calling via `LiteLlm(model="gemini/gemini-2.5-flash-lite")`
- [x] **Validates**: LiteLLM translation layer works for function calling across all 3 providers
- [x] **Pass criteria**: Each provider responds reliably and calls FunctionTools correctly through ADK

### Completion Contract

- [x] P1–P4 prototypes pass their criteria
- [x] P5 alternate providers validated as fallback-ready
- [x] Go/no-go decision updated with P5 results
- [x] Any ADK quirks or workarounds documented

### Decision Gate

| Prototype | Pass? | Decision |
|-----------|-------|----------|
| P1: Claude via LiteLLM | PASS | Proceed with ADK + LiteLLM |
| P2: Mixed Agents | PASS | Proceed with SequentialAgent + CustomAgent pattern |
| P3: Parallel Execution | PASS | Proceed with ParallelAgent for concurrent execution |
| P4: Dynamic Outer Loop | PASS | Proceed with CustomAgent orchestrator pattern |
| P5: OpenAI via LiteLLM | PASS | Proceed — OpenAI validated as fallback provider |
| P5: Gemini via LiteLLM | PASS | Proceed — Gemini validated as fallback provider |

---

## Phase 2: Gateway + Infrastructure `L`

**Goal**: Production-grade FastAPI gateway, Redis infrastructure, database layer, and ARQ workers — the foundation everything else sits on.

**Status**: DONE

**Prerequisites**: Phase 1 (ADK validated)

### Deliverables

#### FastAPI Gateway
- [x] App factory with lifespan management (`app/gateway/main.py`)
- [x] Health endpoint (`GET /health`)
- [x] CORS middleware
- [x] Error handling middleware (structured error responses)
- [x] Dependency injection (`app/gateway/deps.py` — DB sessions, Redis client)
- [x] Pydantic request/response models (`app/gateway/models/`)

#### Database Layer
- [x] AsyncEngine + AsyncSession factory (`app/db/engine.py`)
- [x] SQLAlchemy mapped models (`app/db/models.py`) — specifications, workflows, deliverables
- [x] Alembic migration environment configured
- [x] Initial migration (core tables)

#### Redis Infrastructure
- [x] Redis client connection with health check
- [x] ARQ worker settings (`app/workers/settings.py`)
- [x] ARQ worker entry point with Redis URL configuration
- [x] ARQ cron skeleton (heartbeat, stale job cleanup)

#### Logging & Exceptions
- [x] Structured logging setup (`app/lib/logging.py`)
- [x] Custom exception hierarchy (`app/lib/exceptions.py`)
- [x] Request logging middleware

#### Docker (App Containerization)
- [x] `Dockerfile` — production image (gateway + worker in single image)

### Completion Contract

- [x] `uv run uvicorn app.gateway.main:app` starts and serves `/health`
- [x] `uv run arq app.workers.settings.WorkerSettings` starts worker
- [x] `uv run alembic upgrade head` creates tables
- [x] Redis `PING` succeeds
- [x] Gateway can enqueue a test job, worker can dequeue and process it
- [x] All quality gates pass (ruff, pyright, pytest)

---

## Phase 3: ADK Engine Integration `L`

**Goal**: ADK running inside ARQ workers behind the anti-corruption layer, with LLM routing via LiteLLM.

**Status**: PLANNED

**Prerequisites**: Phase 2 (gateway + workers operational)

### Deliverables

#### Anti-Corruption Layer
- [ ] Gateway-to-ADK command translation (workflow run → ADK Runner)
- [ ] ADK-to-gateway event translation (ADK Events → Redis Stream messages)
- [ ] ADK types never exposed through gateway API

#### ADK App Container
- [ ] `App` class instantiation with `EventsCompactionConfig` (context compression)
- [ ] `ResumabilityConfig` for crash recovery
- [ ] Lifecycle hooks (startup/shutdown for connections, registries)

#### LLM Router
- [ ] Static routing config (YAML): task_type × complexity → model
- [ ] Fallback chain resolution (3-step: user override → chain → default)
- [ ] LiteLLM integration for provider-agnostic model calls
- [ ] Router accessible at agent construction and via `before_model_callback`

#### DatabaseSessionService Integration
- [ ] ADK session persistence to shared database
- [ ] 4-scope state system operational (session, user:, app:, temp:)
- [ ] State updates via `Event.actions.state_delta` (event-sourced)

#### Worker Pipeline Bridge
- [ ] ARQ job function: `run_workflow(ctx, workflow_id, params)`
- [ ] Session creation/resumption per workflow execution
- [ ] Event publishing to Redis Streams during pipeline execution

### Completion Contract

- [ ] Can enqueue a workflow job from gateway, have worker execute an ADK pipeline
- [ ] LLM Router selects correct model per task type
- [ ] Claude responds reliably via LiteLLM through ADK
- [ ] Session state persists across worker invocations
- [ ] ADK events translate to gateway events in Redis Streams

---

## Phase 4: Core Toolset `M`

**Goal**: FunctionTool wrappers for all agent-accessible tools, with role-based restrictions.

**Status**: PLANNED

**Prerequisites**: Phase 3 (ADK engine running in workers)

### Deliverables

#### Filesystem Tools
- [ ] `file_read(path)` — read file contents
- [ ] `file_write(path, content)` — write/create file
- [ ] `file_edit(path, old, new)` — targeted string replacement
- [ ] `file_search(pattern, path)` — grep/find across codebase
- [ ] `directory_list(path)` — tree listing

#### Execution Tools
- [ ] `bash_exec(command, cwd)` — subprocess with timeout and output capture
- [ ] Idempotency protection for ADK Resume compatibility

#### Git Tools
- [ ] `git_status(path)`, `git_commit(path, message)`, `git_branch(path, name, action)`, `git_diff(path, ref)`

#### Web Tools
- [ ] `web_search(query)` — via SearXNG/Brave/Tavily
- [ ] `web_fetch(url)` — fetch and extract content

#### Task Management Tools
- [ ] `todo_read()`, `todo_write(action, task_id, content)`, `todo_list(filter)`

#### PM-Level Tools (Phase 5 Integration)
- [ ] `select_ready_batch()` — dependency-aware batch selection (topological sort of deliverables)
- [ ] `run_regression_tests()` — cross-deliverable regression suite at batch boundary
- [ ] `checkpoint_project()` — persist project state for resume/recovery

> **Note:** These FunctionTools are defined here as part of the core toolset but consumed by the PM agent (Phase 5). The PM calls these tools to manage the batch loop — they replace what was previously envisioned as a separate BatchOrchestrator agent.

#### Tool Registry
- [ ] Central `FunctionTool` registration
- [ ] Per-workflow tool subset selection (from `WORKFLOW.yaml` required_tools)
- [ ] `BaseToolset.get_tools()` for role-based filtering

### Completion Contract

- [ ] All tools callable from within an ADK LlmAgent
- [ ] Tool schemas auto-generated from type hints + docstrings
- [ ] plan_agent gets read-only tools; code_agent gets full tools
- [ ] bash_exec handles timeout, output capture, error reporting

---

## Phase 5: Agent Definitions `L`

**Goal**: All agents defined — Director, PMs, and worker-tier LLM/deterministic agents — composable via ADK primitives in a hierarchical supervision model.

**Status**: PLANNED

**Prerequisites**: Phase 4 (tools available)

### Deliverables

#### Supervision Hierarchy (Director + PM)
- [ ] `Director` agent (LlmAgent, opus) — permanent root_agent of App; cross-project governance, CEO (user) liaison, resource allocation
- [ ] `PM` agent (LlmAgent, sonnet) — per-project autonomous manager; PM IS the outer loop (no separate BatchOrchestrator). Uses tools (`select_ready_batch`, `run_regression_tests`, `checkpoint_project`) for mechanical operations and `after_agent_callback` for intra-batch oversight. PM reasons between batches to decide retry/skip/reorder/escalate.
- [ ] Director → PM delegation via `transfer_to_agent` or `AgentTool`
- [ ] Hard limits cascade: CEO → Director → PM → Workers
- [ ] Supervision hooks (`before_agent_callback` / `after_agent_callback`) for Director observability over PM, and PM observability over DeliverablePipeline workers

#### PM Loop Prototype
- [ ] Validate that LlmAgent PM reliably manages batch loop with tools + callbacks (similar to P4 validation of the mechanical pattern)
- [ ] Test: PM calls `select_ready_batch()`, constructs `ParallelAgent`, runs batch, observes results via `after_agent_callback`, decides continuation strategy
- [ ] Confirm PM inter-batch reasoning is reliable (not degenerate repetition)

#### Worker-Tier LLM Agents (auto-code)
- [ ] `plan_agent` — spec → structured implementation plan (read-only tools, opus model)
- [ ] `code_agent` — plan → code implementation (full tools, sonnet model)
- [ ] `review_agent` — evaluate code quality against standards (read-only tools)
- [ ] `fix_agent` — apply targeted fixes from review feedback (full tools)

#### Worker-Tier Deterministic Agents (CustomAgent / BaseAgent)
- [ ] `SkillLoaderAgent` — resolve and load relevant skills into state
- [ ] `LinterAgent` — run project linter, write structured results to state
- [ ] `TestRunnerAgent` — run test suite, write results to state
- [ ] `FormatterAgent` — run code formatter (auto-corrective)
- [ ] `DependencyResolverAgent` — topological sort of features
- [ ] `RegressionTestAgent` — cross-feature regression at batch boundary
- [ ] `ContextBudgetAgent` — token-count `LlmRequest`, write usage % to state (~50 LOC)

#### Agent Communication
- [ ] Hierarchical delegation (Director → PM → Workers) via ADK primitives
- [ ] `output_key` state writes for inter-agent data flow (worker-level)
- [ ] `{key}` template injection in agent instructions
- [ ] `InstructionProvider` for dynamic context construction
- [ ] `before_model_callback` for runtime context injection

#### Pipeline Composition (auto-code inner loop)
- [ ] `DeliverablePipeline` (SequentialAgent): SkillLoader → plan → code → lint → test → ReviewCycle
- [ ] `ReviewCycle` (LoopAgent, max=3): review → fix → re-lint → re-test

### Completion Contract

- [ ] Director agent operates as permanent root_agent
- [ ] PM agent manages a project autonomously via tool-driven batch loop, escalating only when necessary
- [ ] PM loop prototype validates reliable inter-batch reasoning with tools + callbacks
- [ ] Can run a single deliverable through the full DeliverablePipeline
- [ ] Plan agent produces structured plan; code agent implements it
- [ ] Lint/test agents produce structured results in state
- [ ] Review cycle loops on failure, terminates on approval or max iterations
- [ ] ContextBudgetAgent reports token usage percentage

---

## Phase 6: Skills System `M`

**Goal**: Progressive knowledge loading — agents get task-relevant context, not everything.

**Status**: PLANNED

**Prerequisites**: Phase 5 (SkillLoaderAgent defined)

### Deliverables

#### Skill Library Core
- [ ] Adopt [Agent Skills open standard](https://agentskills.io/specification) file format — `SKILL.md` naming convention, L1/L2/L3 progressive disclosure structure, standard frontmatter schema
- [ ] `SkillEntry` Pydantic model (frontmatter metadata aligned with Agent Skills standard where applicable)
- [ ] `SkillLibrary` class — index building, matching, loading (~120 LOC)
- [ ] Frontmatter parser (YAML extraction from markdown)
- [ ] Trigger matchers: `deliverable_type` (exact), `file_pattern` (glob), `tag_match` (set), `explicit` (named), `always`
- [ ] OR-logic: skill matches if ANY trigger matches

> **Standard adoption:** File format follows the Agent Skills open standard (agentskills.io). Our deterministic loading runtime (`SkillLoaderAgent`) is custom — ADK's `SkillToolset` is experimental and LLM-discretionary, which does not meet our requirement for deterministic skill injection.

#### Two-Tier Architecture
- [ ] Global skills scan (`app/skills/`) — each skill as `<skill-name>/SKILL.md` with optional `references/` and `assets/` subdirectories
- [ ] Project-local skills scan (`.app/skills/` in user repo) — same `SKILL.md` convention
- [ ] Override: project-local replaces global with same `name`

#### InstructionProvider Integration
- [ ] Filter loaded skills by `applies_to` per agent
- [ ] Skills injected into agent instructions via `{loaded_skills}` state key

#### Initial Skill Set
- [ ] `code/api-endpoint.md` — REST endpoint patterns
- [ ] `code/data-model.md` — SQLAlchemy + Pydantic model patterns
- [ ] `code/database-migration.md` — Alembic migration patterns
- [ ] `review/security-review.md` — OWASP basics
- [ ] `test/unit-test-patterns.md` — pytest patterns
- [ ] `planning/task-decomposition.md` — decomposition guidance

#### Caching
- [ ] Skill index cached in Redis (invalidated on file change)

### Completion Contract

- [ ] `SkillLoaderAgent` loads relevant skills for a given feature context
- [ ] Skills appear in unified event stream
- [ ] `loaded_skill_names` in state shows exactly which skills loaded
- [ ] Project-local skills override globals with same name
- [ ] ~320 lines total implementation

---

## Phase 7: Workflow Composition `M`

**Goal**: Pluggable workflow architecture — auto-code is ONLY THE FIRST mvp workflow, not a hardcoded pipeline.

**Status**: PLANNED

**Prerequisites**: Phase 6 (skills system operational)

### Deliverables

#### WorkflowRegistry
- [ ] Automatic directory scanning for `WORKFLOW.yaml` manifests
- [ ] Manifest parsing and workflow indexing
- [ ] `match(user_request)` — deterministic keyword matching
- [ ] `get(name)` — explicit workflow lookup
- [ ] `create_pipeline(name, config)` — deferred ADK pipeline instantiation
- [ ] Custom workflow override support

#### WORKFLOW.yaml Manifest Format
- [ ] Fields: name, description, triggers, required_tools, optional_tools, default_models, pipeline_type, supports_features, supports_parallel
- [ ] Trigger types: keywords, explicit

#### auto-code Workflow
- [ ] `app/workflows/auto-code/WORKFLOW.yaml` manifest
- [ ] `app/workflows/auto-code/pipeline.py` — ADK composition (SequentialAgent/ParallelAgent/LoopAgent)
- [ ] `app/workflows/auto-code/agents/` — workflow-specific agent definitions
- [ ] `app/workflows/auto-code/skills/` — workflow-specific skills

### Completion Contract

- [ ] WorkflowRegistry discovers auto-code on startup
- [ ] `POST /workflows/run {"workflow": "auto-code"}` resolves and instantiates pipeline
- [ ] Adding a new workflow = adding a directory + manifest (zero registration code)
- [ ] auto-code pipeline stages match architecture doc

---

## Phase 8: Spec Pipeline & Autonomous Loop `L`

**Goal**: The core thesis — specification to parallel deliverable execution with autonomous continuation under hierarchical supervision. PM IS the outer loop.

**Status**: PLANNED

**Prerequisites**: Phase 7 (workflow composition operational)

### Deliverables

#### Specification Processing
- [ ] Spec submission endpoint (`POST /specs`)
- [ ] Spec-to-deliverable decomposition (adapted from Autocoder patterns)
- [ ] Deliverable model: status tracking, dependency declaration, assignment
- [ ] Deliverable status enum: PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED

#### PM Outer Loop (Batch Execution)
- [ ] PM (LlmAgent) drives the "while incomplete deliverables exist" loop — no separate BatchOrchestrator agent
- [ ] PM calls `select_ready_batch()` tool for dependency-aware deliverable selection (topological sort, dynamic `ParallelAgent` construction)
- [ ] PM calls `run_regression_tests()` tool at batch boundary for cross-deliverable regression
- [ ] PM calls `checkpoint_project()` tool for resume/recovery persistence
- [ ] Concurrency limits (configurable max parallel deliverables, cascaded from Director)
- [ ] `after_agent_callback` on each `DeliverablePipeline` — monitors completion, flags critical failures
- [ ] `before_agent_callback` — injects context, verifies preconditions

#### Autonomous Continuation
- [ ] PM reasons between batches — observes results, decides retry/skip/reorder/escalate/continue
- [ ] Director-level cross-project management — Director oversees multiple concurrent PMs
- [ ] Optional human-in-the-loop pause at batch boundary (`get_user_choice` tool)
- [ ] Intervention API endpoint (`POST /workflows/{id}/intervene`)
- [ ] Partial failure handling: failed deliverables don't block independent ones
- [ ] PM handles failures autonomously (retry, reorder, skip); escalates to Director only when necessary

#### Git Worktree Isolation
- [ ] Worktree creation per parallel deliverable
- [ ] Filesystem isolation between concurrent features
- [ ] Merge on deliverable completion
- [ ] Cleanup on pipeline completion

### Completion Contract

- [ ] Can submit a spec, have it decomposed into deliverables
- [ ] Director delegates project to PM; PM drives batch loop autonomously via tools
- [ ] PM constructs dependency-aware parallel batches via `select_ready_batch()` tool
- [ ] Loop continues autonomously until all deliverables complete
- [ ] Failed deliverables don't block independent work
- [ ] Git worktrees provide filesystem isolation for parallel execution
- [ ] Can intervene (pause/modify) at batch boundary via API

---

## Phase 9: Memory Service `M`

**Goal**: Cross-session searchable memory — deliverable 47 knows what patterns deliverables 1–10 established.

**Status**: PLANNED

**Prerequisites**: Phase 8 (pipeline producing completed sessions)

### Deliverables

#### PostgresMemoryService
- [ ] `BaseMemoryService` implementation backed by PostgreSQL tsvector + pgvector (~200–500 LOC)
- [ ] `add_session_to_memory(session)` — ingest completed session
- [ ] `search_memory(app_name, user_id, query)` — full-text search via tsvector

#### Memory Integration
- [ ] `PreloadMemoryTool` — auto-loads relevant memories each turn
- [ ] `LoadMemory` tool — agent-decided on-demand retrieval
- [ ] Memory context injected into agent instructions via `{memory_context}`

#### Ingestion Strategy
- [ ] Memory ingestion at session completion (configurable: per-feature, per-batch, or session end)

### Completion Contract

- [ ] Completed sessions are ingested into searchable memory
- [ ] Agents can search for patterns from prior runs
- [ ] Memory persists across sessions in PostgreSQL
- [ ] Uses existing PostgreSQL database — tsvector for keyword search, pgvector for semantic search

---

## Phase 10: Event System, CLI & Observability `L`

**Goal**: Complete the MVP surface area — real-time events, CLI interface, and tracing.

**Status**: PLANNED

**Prerequisites**: Phase 8 (pipeline operational)

### Deliverables

#### Event System (Redis Streams)
- [ ] Event publisher — workers publish translated ADK events to per-workflow streams
- [ ] SSE endpoint (`GET /events/stream`) — gateway reads stream, pushes to connected clients
- [ ] SSE reconnection — `Last-Event-ID` header triggers replay from Redis Stream position
- [ ] Webhook dispatcher — reads events, dispatches via httpx to registered listeners
- [ ] Audit logger — reads events, writes to database
- [ ] Event listener CRUD — register webhook endpoints + filters in database
- [ ] Consumer group management for independent consumers

#### CLI (typer)
- [ ] `autobuilder run <spec>` — submit spec + launch workflow
- [ ] `autobuilder status <id>` — query workflow state
- [ ] `autobuilder intervene <id>` — human-in-the-loop
- [ ] `autobuilder list` — list workflows
- [ ] `autobuilder logs <id>` — stream events to terminal via SSE
- [ ] Pure API client — no database access, no ADK access

#### Observability
- [ ] OpenTelemetry tracing — ADK-native auto-tracing of agents, tools, runner
- [ ] Structured logging — `app.*` logger hierarchy
- [ ] ADK Dev UI — local development debugging (not production)

### Completion Contract

- [ ] Client receives real-time events via SSE as pipeline executes
- [ ] SSE reconnection replays missed events (no data loss)
- [ ] Webhook listeners fire on matching events
- [ ] CLI can launch a workflow, stream events, and query status
- [ ] OpenTelemetry traces visible for pipeline execution
- [ ] **Full MVP validated end-to-end**: spec → decompose → parallel execute → verify → complete

---

## Phase 11: Hardening `L`

**Goal**: Production reliability — cost visibility, LLM observability, crash recovery, adaptive routing.

**Status**: PLANNED

**Prerequisites**: Phase 10 (MVP complete)

### Deliverables

#### LLM Observability
- [ ] Langfuse integration (self-hosted, OpenTelemetry ingestion)
- [ ] Prompt tracking, latency analysis, quality scoring

#### Cost & Token Tracking
- [ ] `TokenTrackingPlugin` — per-feature and per-agent token/cost metrics
- [ ] Context budget awareness — reactive compression/pruning at threshold
- [ ] Extended API: `GET /metrics`, `GET /costs`, `GET /memory`

#### Crash Recovery
- [ ] PM checkpoint recovery — resume batch loop from last `checkpoint_project()` state
- [ ] ADK session resume with `ResumabilityConfig`
- [ ] Tool idempotency validation (re-run safety)

#### Enhanced Routing
- [ ] Richer CLI status commands (pipeline progress, cost summaries, agent status)
- [ ] Agent role-based tool restrictions enforcement
- [ ] Adaptive LLM Router (cost-aware, latency-aware, fallback chain monitoring)

#### Advanced Capabilities
- [ ] Compound workflow composition (multi-workflow request decomposition)
- [ ] Semantic memory upgrade — enable pgvector embeddings for semantic similarity search

### Completion Contract

- [ ] Langfuse dashboard shows per-prompt metrics
- [ ] Token costs visible per feature, per agent, per model
- [ ] Pipeline resumes correctly after simulated crash
- [ ] Adaptive router selects models based on cost/latency data
- [ ] Context budget triggers compression before window exhaustion

---

## Phase 12: Web Dashboard `L`

**Goal**: Rich web interface for pipeline observation, state inspection, and cost monitoring.

**Status**: PLANNED

**Prerequisites**: Phase 11 (hardened API with metrics endpoints)

### Deliverables

#### Dashboard Foundation
- [ ] React 19 + Vite SPA (static build)
- [ ] hey-api codegen — OpenAPI spec → typed TypeScript client + TanStack Query hooks
- [ ] Tailwind v4 with CSS-first `@theme` (fully tokenized design system)
- [ ] Zustand for client-only state (SSE buffer, connection status, UI preferences)
- [ ] Feature-sliced architecture (app/, features/, ui/, lib/, stores/, types/)
- [ ] Atomic design system (ui/atoms, ui/molecules, ui/organisms)

#### Core Features
- [ ] Real-time pipeline visualization — live agent execution via SSE
- [ ] Batch progress display — dependency graph, parallel execution status
- [ ] State inspector — browse session state, loaded skills, memory entries
- [ ] Cost dashboards — per-run, per-agent, per-model cost visualization with trends

#### Type Safety Chain
- [ ] `npm run generate` regenerates TS client from OpenAPI spec
- [ ] Build fails if types drift — generated client won't compile if API changes

### Completion Contract

- [ ] Dashboard displays live pipeline execution via SSE
- [ ] Pipeline state browsable through state inspector
- [ ] Cost data visualized with per-run and per-agent breakdown
- [ ] Type changes in Pydantic models propagate to TypeScript at build time
- [ ] Static build deployable to any CDN/file server

---

## Future Phases

### Phase 13: Additional Workflow Types `L`

Auto-design, auto-research, auto-market — new workflow directories with their own pipelines, agents, skills, and quality gates. Validates that the workflow composition system is truly pluggable.

### Phase 14: Self-Learning Patterns `M`

Agents improve across runs based on accumulated memory and discovered patterns. Feedback loops from review outcomes to planning strategies.

---

## Architecture Boundaries

### Gateway vs. Worker Separation

| Concern | Gateway | Worker |
|---------|---------|--------|
| API routes + auth | Yes | No |
| Job enqueueing | Yes | No |
| SSE streaming | Yes | No |
| ADK pipeline execution | No | Yes |
| FunctionTool execution | No | Yes |
| Filesystem / git operations | No | Yes |
| Database access | Yes | Yes |
| Redis access | Yes | Yes |

### Event Flow

```
Worker (ADK pipeline) → Redis Streams → Consumers
                                          ├── SSE endpoint (gateway) → Client
                                          ├── Webhook dispatcher → External
                                          └── Audit logger → Database
```

### Client Architecture

All clients are pure API consumers. No client talks to ADK directly.

```
CLI (typer) ────────→ Gateway (FastAPI) → Workers (ARQ + ADK)
Dashboard (React) ──→ Gateway (FastAPI) → Workers (ARQ + ADK)
```

---

## Open Questions

| # | Question | Status | Target Phase |
|---|----------|--------|--------------|
| 1 | Deliverable file format (JSON, SQLite, other?) | Open | Phase 8 |
| 2 | Spec parsing — how sophisticated should deliverable decomposition be? | Open | Phase 8 |
| 3 | Regression strategy — random sampling or dependency-aware? | Open | Phase 8 |
| 4 | Reuse Automaker TS libs or rewrite in Python? | Open | Phase 8 |
| 5 | Agent role system granularity | Open | Phase 11 |
| 6 | Context budget strategy — per-agent limits with pruning? | Open | Phase 11 |
| 7 | Web search provider (SearXNG vs Brave vs Tavily) | Open | Phase 4 |
| 8 | Agent-browser integration approach for UI testing | Open | Phase 4 |
| 9 | Durable execution — native ADK resume sufficient or need Temporal? | Likely sufficient | Phase 11 |
| 10 | Memory ingestion — after each feature, each batch, or session end? | Open | Phase 9 |
| 11 | pgvector embedding strategy for semantic memory | Decided: tsvector for keyword search; pgvector available when needed | Phase 9 |
| 12 | Quote style — double vs single for Python | Decided: double quotes (ruff default) | Phase 0 |
| 13 | Auth strategy for gateway API | TBD | Phase 11 |
| 14 | Docker configuration details | Decided: docker-compose with PostgreSQL + Redis | Phase 0 |
| 15 | Director persistence model — how does Director state survive worker restarts? | Open | Phase 5 |
| 16 | PM batch tool design — exact signatures for `select_ready_batch`, `run_regression_tests`, `checkpoint_project` | Open | Phase 5 |
| 17 | Agent Skills standard mapping — which frontmatter fields from agentskills.io map to our trigger system | Open | Phase 6 |

---

## Risk Register

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Claude unreliable through LiteLLM/ADK | High | Prototype P1 validates first; Pydantic AI fallback path |
| ADK CustomAgent outer loop too clunky | Medium | Prototype P4 validates; could simplify to plain Python loop |
| Google deprecates/pivots ADK | Low-Medium | Apache 2.0 license = forkable; patterns transfer to other frameworks |
| Context window exhaustion in long runs | Medium | Token-counting callback + reactive compression + checkpoint/restart |
| Non-Gemini models as second-class citizens | Medium | Test thoroughly in prototyping; stay on LiteLLM latest |
| Redis single point of failure | Low | Single instance acceptable in Phase 1; Sentinel/cluster if needed |
| ARQ worker crash mid-pipeline | Medium | ADK resume + checkpoint strategy; worker health via ARQ cron |

### Architectural Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Feature scope creep toward 117k LOC | High | Phased delivery; MVP ruthlessness; max ~500 per module |
| Skills system becomes too rigid | Low | OR-logic triggers; project overrides add flexibility |
| Google ecosystem gravity (Vertex AI pull) | Medium | Strict discipline: local PostgreSQL only; no GCP services |
| Gateway/worker coupling | Medium | Anti-corruption layer isolates ADK; gateway routes are AutoBuilder-owned |

---

## Effort Scale

| Code | Duration | Description |
|------|----------|-------------|
| `XS` | < 1 day | Simple feature, minimal complexity |
| `S` | 1–2 days | Small feature, straightforward implementation |
| `M` | 3–5 days | Medium feature, some complexity |
| `L` | 1–2 weeks | Large feature, significant complexity |
| `XL` | 2+ weeks | Extra large, complex system component |

## Timeline Summary

| Phase | Effort | Key Deliverable |
|-------|--------|-----------------|
| 0: Project Scaffold | `S` | Working empty project (lint/typecheck/test clean) |
| 1: ADK Validation | `M` | 4 prototypes pass → commit to ADK |
| 2: Gateway + Infra | `L` | FastAPI, Redis, ARQ workers, database, config |
| 3: ADK Engine | `L` | Anti-corruption layer, LLM Router, LiteLLM, session state |
| 4: Core Toolset | `M` | FunctionTools (filesystem, bash, git, web, todo) |
| 5: Agent Definitions | `L` | Director + PM (outer loop) hierarchy, PM loop prototype, worker agents, pipeline composition |
| 6: Skills System | `M` | SkillLibrary, two-tier matching, initial skills |
| 7: Workflow Composition | `M` | WorkflowRegistry, auto-code workflow, WORKFLOW.yaml |
| 8: Spec Pipeline | `L` | PM-driven batch loop, spec decomposition, autonomous continuation, git worktrees |
| 9: Memory Service | `M` | PostgresMemoryService, cross-session search |
| 10: Events, CLI, Observability | `L` | SSE, webhooks, typer CLI, OpenTelemetry |
| 11: Hardening | `L` | Langfuse, cost tracking, crash recovery, adaptive routing |
| 12: Dashboard | `L` | React 19 SPA, pipeline visualization, cost dashboards |
| 13+: Future | — | Additional workflows, self-learning patterns |

**MVP (Phases 0–10)**: ~8–10 weeks
**Production-grade (Phases 0–11)**: ~11–13 weeks
**Full feature set (Phases 0–12)**: ~14–16 weeks

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-02-12 | Initial roadmap — restructured from delivery plan into phased increments with completion contracts |
| 1.1.0 | 2026-02-12 | Renumbered all phases to sequential whole numbers (eliminated sub-phases) |
| 1.2.0 | 2026-02-12 | Phase 0 verified COMPLETE — all deliverables and completion contract pass |
| 1.3.0 | 2026-02-14 | Hierarchical supervision (Director → PM → Workers) integrated into Phase 5, 8 |
| 1.4.0 | 2026-02-16 | PM absorbs BatchOrchestrator; tool/agent terminology aligned; Agent Skills standard adopted |

---

*Document Version: 1.4.0*
*Last Updated: 2026-02-16*
