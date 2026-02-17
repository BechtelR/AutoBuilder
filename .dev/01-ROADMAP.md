# AutoBuilder Project Roadmap
*Version: 2.0.0*

**Single source of truth for phase sequencing, status, and completion contracts.**
Component inventories and detailed checklists live in [`07-COMPONENTS.md`](./07-COMPONENTS.md) (the Component Registry / BOM).

## Overview

AutoBuilder is delivered in phased increments. Each phase produces testable, independently validatable output. No phase begins until its prerequisites are validated. The MVP (Phases 0-10) proves the core thesis: an autonomous agentic system can take a specification, decompose it into deliverables, execute them in parallel, and produce verified output with minimal human intervention -- through a production-grade API gateway with async worker execution.

**Status -- Phase 0: COMPLETE | Phase 1: DONE | Phase 2: DONE | Phase 3: NEXT**

---

## Phase 0: Project Scaffold & Dev Environment `S`

**Goal**: Working empty project that builds, lints, and type-checks clean.
**Status**: DONE
**Prerequisites**: None


### Scope Summary
Project configuration (pyproject.toml, Alembic, Docker Compose), directory scaffold matching `03-STRUCTURE.md`, Pydantic Settings configuration module, shared domain models (enums, constants, base models), and dev tooling verification (uv, ruff, pyright, pytest).

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


### Scope Summary
Five focused prototypes validating that Google ADK can serve as AutoBuilder's orchestration engine. P1-P4 validate core patterns (basic agent loop, mixed agent coordination, parallel execution, dynamic outer loop) with Claude via LiteLLM. P5 validates alternate providers (OpenAI, Gemini) as production fallbacks.

### Completion Contract
- [x] P1-P4 prototypes pass their criteria
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
| P5: OpenAI via LiteLLM | PASS | Proceed -- OpenAI validated as fallback provider |
| P5: Gemini via LiteLLM | PASS | Proceed -- Gemini validated as fallback provider |

---

## Phase 2: Gateway + Infrastructure `L`

**Goal**: Production-grade FastAPI gateway, Redis infrastructure, database layer, and ARQ workers -- the foundation everything else sits on.
**Status**: DONE
**Prerequisites**: Phase 1 (ADK validated)


### Scope Summary
FastAPI app factory with lifespan, health endpoint, CORS, error handling middleware, and dependency injection. AsyncEngine + AsyncSession factory, SQLAlchemy mapped models, Alembic migrations. Redis client, ARQ worker settings and entry point, cron skeleton. Structured logging, custom exception hierarchy, request logging middleware. Production Dockerfile.

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
**Status**: NEXT
**Prerequisites**: Phase 2 (gateway + workers operational)


### Scope Summary
Anti-corruption layer translating gateway commands to ADK Runner calls and ADK Events to Redis Stream messages. ADK App container with context compression and resumability config. Static LLM routing (task_type x complexity to model) with fallback chains via LiteLLM. DatabaseSessionService for ADK session persistence with 4-scope state system. Worker pipeline bridge connecting ARQ jobs to ADK pipeline execution with event publishing.

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


### Scope Summary
FunctionTool wrappers for filesystem (read, write, edit, search, directory list), execution (bash with timeout/output capture), git (status, commit, branch, diff), web (search, fetch), and task management (todo CRUD). AutoBuilderToolset (ADK-native BaseToolset) for per-role tool vending via `get_tools(readonly_context)` with cascading permission config. PM-level tools (`select_ready_batch`, `enqueue_ceo_item`) and deterministic safety mechanisms (`checkpoint_project` as after_agent_callback, `RegressionTestAgent` as CustomAgent).

### Completion Contract
- [ ] All tools callable from within an ADK LlmAgent
- [ ] Tool schemas auto-generated from type hints + docstrings
- [ ] AutoBuilderToolset vends correct tool subsets per role configuration
- [ ] bash_exec handles timeout, output capture, error reporting

---

## Phase 5: Agent Definitions `L`

**Goal**: All agents defined -- Director, PMs, and worker-tier LLM/custom agents -- composable via ADK primitives in a hierarchical supervision model.
**Status**: PLANNED
**Prerequisites**: Phase 4 (tools available)


### Scope Summary
Supervision hierarchy: Director (LlmAgent, opus) as stateless root_agent and PM (LlmAgent, sonnet) as per-project autonomous manager driving the batch loop through tools and callbacks. Unified CEO queue (DB-backed) for approvals, escalations, and status reports with SSE push. PM loop prototype validating reliable inter-batch reasoning. Worker-tier LLM agents (plan, code, review, fix) and custom agents (SkillLoader, Linter, TestRunner, Formatter, DependencyResolver, RegressionTest). Context budget monitor as before_model_callback. Pipeline composition: DeliverablePipeline (SequentialAgent) with ReviewCycle (LoopAgent).

### Completion Contract
- [ ] Director agent operates as root_agent (stateless config, recreated per invocation)
- [ ] PM agent manages a project autonomously via tools + deterministic safety mechanisms (`checkpoint_project`, `verify_batch_completion`, `run_regression_tests`), escalating only when necessary
- [ ] PM loop prototype validates reliable inter-batch reasoning with tools + callbacks
- [ ] Can run a single deliverable through the full DeliverablePipeline
- [ ] Plan agent produces structured plan; code agent implements it
- [ ] Lint/test agents produce structured results in state
- [ ] Review cycle loops on failure, terminates on approval or max iterations
- [ ] Context budget `before_model_callback` reports token usage percentage

---

## Phase 6: Skills System `M`

**Goal**: Progressive knowledge loading -- agents get task-relevant context, not everything.
**Status**: PLANNED
**Prerequisites**: Phase 5 (SkillLoaderAgent defined)


### Scope Summary
Skill library adopting the Agent Skills open standard file format (`SKILL.md`) with deterministic loading runtime. Two-tier architecture: global skills (`app/skills/`) and project-local skills (`.app/skills/` in user repo) with override semantics. Trigger matchers (deliverable_type, file_pattern, tag_match, explicit, always) with OR-logic. InstructionProvider integration injecting filtered skills per agent. Initial skill set covering API endpoints, data models, migrations, security review, unit tests, and task decomposition. Redis-cached skill index.

### Completion Contract
- [ ] `SkillLoaderAgent` loads relevant skills for a given deliverable context
- [ ] Skills appear in unified event stream
- [ ] `loaded_skill_names` in state shows exactly which skills loaded
- [ ] Project-local skills override globals with same name
- [ ] ~320 lines total implementation

---

## Phase 7: Workflow Composition `M`

**Goal**: Pluggable workflow architecture -- auto-code is ONLY THE FIRST MVP workflow, not a hardcoded pipeline.
**Status**: PLANNED
**Prerequisites**: Phase 6 (skills system operational)


### Scope Summary
WorkflowRegistry with automatic directory scanning for `WORKFLOW.yaml` manifests, deterministic keyword matching, and deferred ADK pipeline instantiation. WORKFLOW.yaml manifest format defining triggers, required/optional tools, default models, and pipeline configuration. Auto-code workflow as first implementation with its own manifest, pipeline composition, agents, and skills.

### Completion Contract
- [ ] WorkflowRegistry discovers auto-code on startup
- [ ] `POST /workflows/run {"workflow": "auto-code"}` resolves and instantiates pipeline
- [ ] Adding a new workflow = adding a directory + manifest (zero registration code)
- [ ] auto-code pipeline stages match architecture doc

---

## Phase 8: Spec Pipeline & Autonomous Loop `L`

**Goal**: The core thesis -- specification to parallel deliverable execution with autonomous continuation under hierarchical supervision. PM IS the outer loop.
**Status**: PLANNED
**Prerequisites**: Phase 7 (workflow composition operational)


### Scope Summary
Specification processing: submission endpoint, spec-to-deliverable decomposition, deliverable model with status tracking and dependency declaration. PM outer loop driving batch execution via `select_ready_batch()` tool with deterministic safety mechanisms (RegressionTestAgent, checkpoint_project callback). Autonomous continuation with inter-batch PM reasoning (retry/skip/reorder/escalate), Director-level cross-project management, optional human-in-the-loop pause, and partial failure handling. Git worktree isolation for parallel deliverable execution.

### Completion Contract
- [ ] Can submit a spec, have it decomposed into deliverables
- [ ] Director delegates project to PM; PM drives batch loop autonomously via tools + deterministic safety mechanisms
- [ ] PM constructs dependency-aware parallel batches via `select_ready_batch()` tool
- [ ] Loop continues autonomously until all deliverables complete
- [ ] Failed deliverables don't block independent work
- [ ] Git worktrees provide filesystem isolation for parallel execution
- [ ] Can intervene (pause/modify) at batch boundary via API

---

## Phase 9: Memory Service `M`

**Goal**: Cross-session searchable memory -- deliverable 47 knows what patterns deliverables 1-10 established.
**Status**: PLANNED
**Prerequisites**: Phase 8 (pipeline producing completed sessions)


### Scope Summary
PostgresMemoryService backed by PostgreSQL tsvector + pgvector for full-text and semantic search. Memory tools: PreloadMemoryTool (auto-loads relevant memories each turn) and LoadMemory (agent-decided on-demand retrieval). Configurable ingestion strategy at session completion (per-deliverable, per-batch, or session end).

### Completion Contract
- [ ] Completed sessions are ingested into searchable memory
- [ ] Agents can search for patterns from prior runs
- [ ] Memory persists across sessions in PostgreSQL
- [ ] Uses existing PostgreSQL database -- tsvector for keyword search, pgvector for semantic search

---

## Phase 10: Event System, CLI & Observability `L`

**Goal**: Complete the MVP surface area -- real-time events, CLI interface, and tracing.
**Status**: PLANNED
**Prerequisites**: Phase 8 (pipeline operational)


### Scope Summary
Event system on Redis Streams: publisher from workers, SSE endpoint with reconnection/replay, webhook dispatcher, audit logger, event listener CRUD, and consumer group management. CLI via typer as a pure API client (run, status, intervene, list, logs). Observability via OpenTelemetry tracing (ADK-native), structured logging hierarchy, and ADK Dev UI for local development.

### Completion Contract
- [ ] Client receives real-time events via SSE as pipeline executes
- [ ] SSE reconnection replays missed events (no data loss)
- [ ] Webhook listeners fire on matching events
- [ ] CLI can launch a workflow, stream events, and query status
- [ ] OpenTelemetry traces visible for pipeline execution
- [ ] **Full MVP validated end-to-end**: spec -> decompose -> parallel execute -> verify -> complete

---

## Phase 11: Hardening `L`

**Goal**: Production reliability -- cost visibility, LLM observability, crash recovery, adaptive routing.
**Status**: PLANNED
**Prerequisites**: Phase 10 (MVP complete)


### Scope Summary
LLM observability via Langfuse (self-hosted, OpenTelemetry ingestion) with prompt tracking, latency analysis, and quality scoring. Token/cost tracking per-deliverable and per-agent with context budget awareness and reactive compression. Crash recovery via PM checkpoint resume, ADK session resume with ResumabilityConfig, and tool idempotency validation. Enhanced routing: richer CLI status, agent role-based tool restrictions, adaptive LLM Router (cost/latency-aware). Advanced capabilities: compound workflow composition and semantic memory upgrade (pgvector embeddings).

### Completion Contract
- [ ] Langfuse dashboard shows per-prompt metrics
- [ ] Token costs visible per deliverable, per agent, per model
- [ ] Pipeline resumes correctly after simulated crash
- [ ] Adaptive router selects models based on cost/latency data
- [ ] Context budget triggers compression before window exhaustion

---

## Phase 12: Web Dashboard `L`

**Goal**: Rich web interface for pipeline observation, state inspection, and cost monitoring.
**Status**: PLANNED
**Prerequisites**: Phase 11 (hardened API with metrics endpoints)


### Scope Summary
React 19 + Vite SPA with hey-api codegen (OpenAPI to typed TypeScript client + TanStack Query hooks), Tailwind v4 with CSS-first `@theme`, Zustand for client-only state, feature-sliced architecture, and atomic design system. Core features: real-time pipeline visualization via SSE, batch progress display with dependency graph, state inspector, and cost dashboards with per-run/per-agent/per-model breakdown.

### Completion Contract
- [ ] Dashboard displays live pipeline execution via SSE
- [ ] Pipeline state browsable through state inspector
- [ ] Cost data visualized with per-run and per-agent breakdown
- [ ] Type changes in Pydantic models propagate to TypeScript at build time
- [ ] Static build deployable to any CDN/file server

---

## Future Phases

### Phase 13: Additional Workflow Types `L`

Auto-design, auto-research, auto-market -- new workflow directories with their own pipelines, agents, skills, and quality gates. Validates that the workflow composition system is truly pluggable.

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
Worker (ADK pipeline) -> Redis Streams -> Consumers
                                          |-- SSE endpoint (gateway) -> Client
                                          |-- Webhook dispatcher -> External
                                          +-- Audit logger -> Database
```

### Client Architecture

All clients are pure API consumers. No client talks to ADK directly.

```
CLI (typer) ----------> Gateway (FastAPI) -> Workers (ARQ + ADK)
Dashboard (React) ----> Gateway (FastAPI) -> Workers (ARQ + ADK)
```

---

## Open Questions

| # | Question | Status | Target Phase |
|---|----------|--------|--------------|
| 1 | Deliverable file format (JSON, SQLite, other?) | Open | Phase 8 |
| 2 | Spec parsing -- how sophisticated should deliverable decomposition be? | Open | Phase 8 |
| 3 | Regression strategy -- random sampling or dependency-aware? | Open | Phase 8 |
| 4 | Reuse Automaker TS libs or rewrite in Python? | Open | Phase 8 |
| 5 | Agent role system granularity | Open | Phase 11 |
| 6 | Context budget strategy -- per-agent limits with pruning? | Open | Phase 11 |
| 7 | Web search provider (SearXNG vs Brave vs Tavily) | Open | Phase 4 |
| 8 | Agent-browser integration approach for UI testing | Open | Phase 4 |
| 9 | Durable execution -- native ADK resume sufficient or need Temporal? | Likely sufficient | Phase 11 |
| 10 | Memory ingestion -- after each deliverable, each batch, or session end? | Open | Phase 9 |
| 11 | pgvector embedding strategy for semantic memory | Closed: tsvector for keyword search; pgvector available when needed | Phase 9 |
| 12 | Quote style -- double vs single for Python | Closed: double quotes (ruff default) | Phase 0 |
| 13 | Auth strategy for gateway API | TBD | Phase 11 |
| 14 | Docker configuration details | Closed: docker-compose with PostgreSQL + Redis | Phase 0 |
| 15 | Director persistence model -- how does Director state survive worker restarts? | Closed: Stateless. Agent config recreated per invocation, all state in DB. Personality in `user:` scope. | Phase 5 |
| 16 | PM batch operations -- `select_ready_batch` (FunctionTool), `checkpoint_project` (automatic), `run_regression_tests` (PM-defined policy) | Closed: `checkpoint_project` = `after_agent_callback` on DeliverablePipeline (persists state via `CallbackContext`); `run_regression_tests` = `RegressionTestAgent` (CustomAgent) in pipeline after each batch (reads PM regression policy from session state) | Phase 5 |
| 17 | Agent Skills standard mapping -- which frontmatter fields from agentskills.io map to our trigger system | Closed: mapping defined | Phase 6 |

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
| `S` | 1-2 days | Small feature, straightforward implementation |
| `M` | 3-5 days | Medium feature, some complexity |
| `L` | 1-2 weeks | Large feature, significant complexity |
| `XL` | 2+ weeks | Extra large, complex system component |

## Timeline Summary

| Phase | Effort | Key Deliverable |
|-------|--------|-----------------|\
| 0: Project Scaffold | `S` | Working empty project (lint/typecheck/test clean) |
| 1: ADK Validation | `M` | 4 prototypes pass -> commit to ADK |
| 2: Gateway + Infra | `L` | FastAPI, Redis, ARQ workers, database, config |
| 3: ADK Engine | `L` | Anti-corruption layer, LLM Router, LiteLLM, session state |
| 4: Core Toolset | `M` | FunctionTools (filesystem, bash, git, web, todo) |
| 5: Agent Definitions | `L` | Director + PM hierarchy, PM loop prototype, worker agents, pipelines |
| 6: Skills System | `M` | SkillLibrary, two-tier matching, initial skills |
| 7: Workflow Composition | `M` | WorkflowRegistry, auto-code workflow, WORKFLOW.yaml |
| 8: Spec Pipeline | `L` | PM-driven batch loop, spec decomposition, git worktrees |
| 9: Memory Service | `M` | PostgresMemoryService, cross-session search |
| 10: Events, CLI, Observability | `L` | SSE, webhooks, typer CLI, OpenTelemetry |
| 11: Hardening | `L` | Langfuse, cost tracking, crash recovery, adaptive routing |
| 12: Dashboard | `L` | React 19 SPA, pipeline visualization, cost dashboards |
| 13+: Future | -- | Additional workflows, self-learning patterns |

**MVP (Phases 0-10)**: ~8-10 weeks
**Production-grade (Phases 0-11)**: ~11-13 weeks
**Full feature set (Phases 0-12)**: ~14-16 weeks

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-02-12 | Initial roadmap -- restructured from delivery plan into phased increments with completion contracts |
| 1.1.0 | 2026-02-12 | Renumbered all phases to sequential whole numbers (eliminated sub-phases) |
| 1.2.0 | 2026-02-12 | Phase 0 verified COMPLETE -- all deliverables and completion contract pass |
| 1.3.0 | 2026-02-14 | Hierarchical supervision (Director -> PM -> Workers) integrated into Phase 5, 8 |
| 1.4.0 | 2026-02-16 | PM IS the outer loop; tool/agent terminology aligned; Agent Skills standard adopted |
| 1.5.0 | 2026-02-16 | Resolved Q15/Q16/Q17; Phase 5 updated with stateless agents, CEO queue, tool registry, deterministic safety ops |
| 1.5.1 | 2026-02-16 | Aligned tool/callback distinction (checkpoint + regression are not FunctionTools); added enqueue_ceo_item to PM tools |
| 1.5.2 | 2026-02-16 | Reclassified ContextBudgetAgent as `before_model_callback` (not standalone agent) to match architecture doc |
| 1.6.0 | 2026-02-16 | Revised Decision #46: replaced file-based directory-scoped tool registry with ADK-native AutoBuilderToolset(BaseToolset) pattern |
| 1.6.1 | 2026-02-16 | Replaced vague "deterministic callback" terminology with exact ADK mechanisms: checkpoint_project = after_agent_callback, RegressionTestAgent = CustomAgent |
| 1.6.2 | 2026-02-16 | Flagged unverified ADK mechanism claims as TBD: checkpoint_project and run_regression_tests behavior is decided, exact ADK wiring deferred to Phase 5 prototype |
| 1.7.0 | 2026-02-16 | Resolved all TBD flags: checkpoint_project = `after_agent_callback` on DeliverablePipeline (persists state via CallbackContext); run_regression_tests = `RegressionTestAgent` (CustomAgent) in pipeline after each batch (reads PM regression policy from session state) |
| 1.7.1 | 2026-02-17 | Moved AutoBuilderToolset from Phase 5 to Phase 4; removed redundant Deterministic Safety section; fixed Phase 4 completion contract to be verifiable in Phase 4 |
| 2.0.0 | 2026-02-17 | Roadmap v2: slim format, component checklists moved to 07-COMPONENTS.md (BOM) |

---

*Document Version: 2.0.0*
*Last Updated: 2026-02-17*
