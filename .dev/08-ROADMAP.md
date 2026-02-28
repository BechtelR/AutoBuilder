# AutoBuilder Project Roadmap
*Version: 2.1.0*

**Single source of truth for phase sequencing, status, and completion contracts.**
Component inventories and detailed checklists live in [`07-COMPONENTS.md`](./07-COMPONENTS.md) (the Component Registry / BOM).

## Overview

AutoBuilder is delivered in phased increments. Each phase produces testable, independently validatable output. No phase begins until its prerequisites are validated. The MVP (Phases 0-10) proves the core thesis: an autonomous agentic system can take a specification, decompose it into deliverables, execute them in parallel, and produce verified output with minimal human intervention -- through a production-grade API gateway with async worker execution.

**Status -- Phase 0: COMPLETE | Phase 1: DONE | Phase 2: DONE | Phase 3: DONE | Phase 4: DONE | Phase 5: NEXT**

---

## Phase 0: Project Scaffold & Dev Environment `S`

**Goal**: Working empty project that builds, lints, and type-checks clean.
**Status**: DONE
**Prerequisites**: None


### Scope Summary
Project configuration (pyproject.toml, Alembic, Docker Compose), directory scaffold matching `03-STRUCTURE.md`, Pydantic Settings configuration module, shared domain models (enums, constants, base models), and dev tooling verification (uv, ruff, pyright, pytest).

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| ✓ | `docker compose up -d` starts PostgreSQL and Redis | NFR-6 |
| ✓ | `uv sync && uv run ruff check . && uv run pyright && uv run pytest` all pass | NFR-5 |
| ✓ | Directory structure matches `.dev/03-STRUCTURE.md` | NFR-5 |
| ✓ | Configuration loads from environment variables with sensible defaults | NFR-6 |
| ✓ | Shared enums and base models importable from `app.models` | NFR-5 |

---

## Phase 1: ADK Prototype Validation `M`

**Goal**: Validate critical ADK assumptions before full commitment. Go/no-go gate.
**Status**: DONE
**Prerequisites**: Phase 0 (project scaffold exists, dependencies installable)


### Scope Summary
Five focused prototypes validating that Google ADK can serve as AutoBuilder's orchestration engine. P1-P4 validate core patterns (basic agent loop, mixed agent coordination, parallel execution, dynamic outer loop) with Claude via LiteLLM. P5 validates alternate providers (OpenAI, Gemini) as production fallbacks.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| ✓ | P1-P4 prototypes pass their criteria | NFR-3, NFR-5 |
| ✓ | P5 alternate providers validated as fallback-ready | NFR-3 |
| ✓ | Go/no-go decision updated with P5 results | NFR-5 |
| ✓ | Any ADK quirks or workarounds documented | NFR-3 |

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

| Status | Contract Item | PRD |
|--------|--------------|-----|
| ✓ | `uv run uvicorn app.gateway.main:app` starts and serves `/health` | NFR-4, NFR-5 |
| ✓ | `uv run arq app.workers.settings.WorkerSettings` starts worker | PR-9 |
| ✓ | `uv run alembic upgrade head` creates tables | NFR-5 |
| ✓ | Redis `PING` succeeds | NFR-6 |
| ✓ | Gateway can enqueue a test job, worker can dequeue and process it | PR-9 |
| ✓ | All quality gates pass (ruff, pyright, pytest) | NFR-5 |

---

## Phase 3: ADK Engine Integration `L`

**Goal**: ADK running inside ARQ workers behind the anti-corruption layer, with LLM routing via LiteLLM.
**Status**: DONE
**Prerequisites**: Phase 2 (gateway + workers operational)


### Scope Summary
Anti-corruption layer translating gateway commands to ADK Runner calls and ADK Events to Redis Stream messages. ADK App container with context compression and resumability config. Static LLM routing (model_role x complexity to model) with fallback chains via LiteLLM. DatabaseSessionService for ADK session persistence with 4-scope state system. Worker pipeline bridge connecting ARQ jobs to ADK pipeline execution with event publishing.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| ✓ | Can enqueue a workflow job from gateway, have worker execute an ADK pipeline | PR-9, PR-10 |
| ✓ | LLM Router selects correct model per task type | PR-5 |
| ✓ | Claude responds reliably via LiteLLM through ADK | NFR-3 |
| ✓ | Session state persists across worker invocations | PR-3, NFR-3 |
| ✓ | ADK events translate to gateway events in Redis Streams | PR-34 |

---

## Phase 4: Core Toolset `M`

**Goal**: FunctionTool wrappers for all agent-accessible tools, with role-based restrictions.
**Status**: DONE
**Prerequisites**: Phase 3 (ADK engine running in workers)


### Scope Summary
42 FunctionTool wrappers across 8 categories: Filesystem (10 tools including glob, grep, multi-edit), Code Intelligence (2 tools — tree-sitter symbols + diagnostics), Execution (2 tools — bash + HTTP), Git (8 tools including log, show, worktree, apply), Web (2 tools), Task Management (6 tools — three-tier system with session todos, shared tasks, and PM-managed deliverables), PM Management (6 tools — batch selection, Director escalation, deliverable lifecycle), and Director Management (6 tools — CEO queue, project oversight, PM override). GlobalToolset (ADK-native BaseToolset) for per-role tool vending with cascading permission config.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| ✓ | All 42 tools callable from within an ADK LlmAgent | PR-5 |
| ✓ | Tool schemas auto-generated from type hints + docstrings | NFR-5 |
| ✓ | GlobalToolset vends correct tool subsets per role configuration | PR-15 |
| ✓ | bash_exec handles timeout, output capture, error reporting | PR-9 |
| ✓ | Three-tier task system operational (todos, tasks, deliverables) | PR-9 |
| ✓ | PM escalation routes to Director queue (not CEO queue) | PR-18 |
| ✓ | code_symbols extracts structure via tree-sitter | PR-5 |
| ✓ | run_diagnostics invokes configurable linter/type-checker | PR-11 |
| ✓ | Director can override PM via override_pm tool | PR-15, PR-16 |

---

## Phase 5: Agent Definitions `L`

**Goal**: All agents defined -- Director, PMs, and worker-tier LLM/custom agents -- composable via ADK primitives in a hierarchical supervision model.
**Status**: PLANNED
**Prerequisites**: Phase 4 (tools available)


### Scope Summary
Supervision hierarchy: Director (LlmAgent, opus) as stateless root_agent and PM (LlmAgent, sonnet) as per-project autonomous manager driving the batch loop through tools and callbacks. Unified CEO queue (DB-backed) for approvals, escalations, and status reports with SSE push. PM loop prototype validating reliable inter-batch reasoning. Worker-tier LLM agents (plan, code, review, fix) and custom agents (SkillLoader, Linter, TestRunner, Formatter, DependencyResolver, RegressionTest). Context budget monitor as before_model_callback. Pipeline composition: DeliverablePipeline (SequentialAgent) with ReviewCycle (LoopAgent).

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Director agent operates as root_agent (stateless config, recreated per invocation) | PR-13 |
| | PM agent manages a project autonomously via tools + deterministic safety mechanisms (`checkpoint_project`, `verify_batch_completion`, `run_regression_tests`), escalating only when necessary | PR-14 |
| | PM loop prototype validates reliable inter-batch reasoning with tools + callbacks | PR-10 |
| | Can run a single deliverable through the full DeliverablePipeline | PR-10 |
| | Plan agent produces structured plan; code agent implements it | PR-5 |
| | Lint/test agents produce structured results in state | PR-11 |
| | Review cycle loops on failure, terminates on approval or max iterations | PR-22 |
| | Context budget `before_model_callback` reports token usage percentage | PR-15 |

---

## Phase 6: Skills System `M`

**Goal**: Progressive knowledge loading -- agents get task-relevant context, not everything.
**Status**: PLANNED
**Prerequisites**: Phase 5 (SkillLoaderAgent defined)


### Scope Summary
Skill library adopting the Agent Skills open standard file format (`SKILL.md`) with deterministic loading runtime. Two-tier architecture: global skills (`app/skills/`) and project-local skills (`.app/skills/` in user repo) with override semantics. Trigger matchers (deliverable_type, file_pattern, tag_match, explicit, always) with OR-logic. InstructionProvider integration injecting filtered skills per agent. Initial skill set covering API endpoints, data models, migrations, security review, unit tests, and task decomposition. Redis-cached skill index.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | `SkillLoaderAgent` loads relevant skills for a given deliverable context | PR-31, PR-32 |
| | Skills appear in unified event stream | PR-34 |
| | `loaded_skill_names` in state shows exactly which skills loaded | PR-32 |
| | Project-local skills override globals with same name | PR-33 |
| | ~320 lines total implementation | — |

---

## Phase 7: Workflow Composition `M`

**Goal**: Pluggable workflow architecture -- auto-code is ONLY THE FIRST MVP workflow, not a hardcoded pipeline.
**Status**: PLANNED
**Prerequisites**: Phase 6 (skills system operational)


### Scope Summary
WorkflowRegistry with automatic directory scanning for `WORKFLOW.yaml` manifests, deterministic keyword matching, and deferred ADK pipeline instantiation. WORKFLOW.yaml manifest format defining triggers, required/optional tools, default models, and pipeline configuration. Auto-code workflow as first implementation with its own manifest, pipeline composition, agents, and skills.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | WorkflowRegistry discovers auto-code on startup | PR-4 |
| | `POST /workflows/run {"workflow": "auto-code"}` resolves and instantiates pipeline | PR-4 |
| | Adding a new workflow = adding a directory + manifest (zero registration code) | PR-4, NFR-5 |
| | auto-code pipeline stages match architecture doc | PR-6 |

---

## Phase 8: Spec Pipeline & Autonomous Loop `L`

**Goal**: The core thesis -- specification to parallel deliverable execution with autonomous continuation under hierarchical supervision. PM IS the outer loop.
**Status**: PLANNED
**Prerequisites**: Phase 7 (workflow composition operational)


### Scope Summary
Specification processing: submission endpoint, spec-to-deliverable decomposition, deliverable model with status tracking and dependency declaration. PM outer loop driving batch execution via `select_ready_batch()` tool with deterministic safety mechanisms (RegressionTestAgent, checkpoint_project callback). Autonomous continuation with inter-batch PM reasoning (retry/skip/reorder/escalate), Director-level cross-project management, optional human-in-the-loop pause, and partial failure handling. Git worktree isolation for parallel deliverable execution.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Can submit a spec, have it decomposed into deliverables | PR-1, PR-8 |
| | Director delegates project to PM; PM drives batch loop autonomously via tools + deterministic safety mechanisms | PR-10, PR-14 |
| | PM constructs dependency-aware parallel batches via `select_ready_batch()` tool | PR-10 |
| | Loop continues autonomously until all deliverables complete | PR-10 |
| | Failed deliverables don't block independent work | PR-12, PR-25 |
| | Git worktrees provide filesystem isolation for parallel execution | PR-9 |
| | Can intervene (pause/modify) at batch boundary via API | PR-3, PR-9 |

---

## Phase 9: Memory Service `M`

**Goal**: Cross-session searchable memory -- deliverable 47 knows what patterns deliverables 1-10 established.
**Status**: PLANNED
**Prerequisites**: Phase 8 (pipeline producing completed sessions)


### Scope Summary
PostgresMemoryService backed by PostgreSQL tsvector + pgvector for full-text and semantic search. Memory tools: PreloadMemoryTool (auto-loads relevant memories each turn) and LoadMemory (agent-decided on-demand retrieval). Configurable ingestion strategy at session completion (per-deliverable, per-batch, or session end).

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Completed sessions are ingested into searchable memory | PR-26, PR-29 |
| | Agents can search for patterns from prior runs | PR-28, PR-29 |
| | Memory persists across sessions in PostgreSQL | PR-26 |
| | Uses existing PostgreSQL database -- tsvector for keyword search, pgvector for semantic search | PR-26 |

---

## Phase 10: Event System, CLI & Observability `L`

**Goal**: Complete the MVP surface area -- real-time events, CLI interface, and tracing.
**Status**: PLANNED
**Prerequisites**: Phase 8 (pipeline operational)


### Scope Summary
Event system on Redis Streams: publisher from workers, SSE endpoint with reconnection/replay, webhook dispatcher, audit logger, event listener CRUD, and consumer group management. CLI via typer as a pure API client (run, status, intervene, list, logs). Observability via OpenTelemetry tracing (ADK-native), structured logging hierarchy, and ADK Dev UI for local development.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Client receives real-time events via SSE as pipeline executes | PR-34 |
| | SSE reconnection replays missed events (no data loss) | PR-34 |
| | Webhook listeners fire on matching events | PR-21 |
| | CLI can launch a workflow, stream events, and query status | PR-36 |
| | OpenTelemetry traces visible for pipeline execution | PR-35 |
| | **Full MVP validated end-to-end**: spec -> decompose -> parallel execute -> verify -> complete | PR-1, PR-10, PR-22 |

---

## Phase 11: Hardening `L`

**Goal**: Production reliability -- cost visibility, LLM observability, crash recovery, adaptive routing.
**Status**: PLANNED
**Prerequisites**: Phase 10 (MVP complete)


### Scope Summary
LLM observability via Langfuse (self-hosted, OpenTelemetry ingestion) with prompt tracking, latency analysis, and quality scoring. Token/cost tracking per-deliverable and per-agent with context budget awareness and reactive compression. Crash recovery via PM checkpoint resume, ADK session resume with ResumabilityConfig, and tool idempotency validation. Enhanced routing: richer CLI status, agent role-based tool restrictions, adaptive LLM Router (cost/latency-aware). Advanced capabilities: compound workflow composition and semantic memory upgrade (pgvector embeddings).

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Langfuse dashboard shows per-prompt metrics | PR-35 |
| | Token costs visible per deliverable, per agent, per model | PR-35 |
| | Pipeline resumes correctly after simulated crash | NFR-3 |
| | Adaptive router selects models based on cost/latency data | PR-15, NFR-2 |
| | Context budget triggers compression before window exhaustion | PR-15, NFR-2 |

---

## Phase 12: Web Dashboard `L`

**Goal**: Rich web interface for pipeline observation, state inspection, and cost monitoring.
**Status**: PLANNED
**Prerequisites**: Phase 11 (hardened API with metrics endpoints)


### Scope Summary
React 19 + Vite SPA with hey-api codegen (OpenAPI to typed TypeScript client + TanStack Query hooks), Tailwind v4 with CSS-first `@theme`, Zustand for client-only state, feature-sliced architecture, and atomic design system. Core features: real-time pipeline visualization via SSE, batch progress display with dependency graph, state inspector, and cost dashboards with per-run/per-agent/per-model breakdown.

### Completion Contract

| Status | Contract Item | PRD |
|--------|--------------|-----|
| | Dashboard displays live pipeline execution via SSE | PR-37 |
| | Pipeline state browsable through state inspector | PR-37 |
| | Cost data visualized with per-run and per-agent breakdown | PR-37, PR-35 |
| | Type changes in Pydantic models propagate to TypeScript at build time | NFR-5 |
| | Static build deployable to any CDN/file server | PR-37 |

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
| 7 | Web search provider (SearXNG vs Brave vs Tavily) | Closed: Tavily primary, Brave fallback. Simple `if/elif` dispatch in `web_search`. Settings: `AUTOBUILDER_SEARCH_PROVIDER`, `AUTOBUILDER_SEARCH_API_KEY`. | Phase 4 |
| 8 | Agent-browser integration approach for UI testing | Closed: Vercel `agent-browser` CLI (npm). Invoked via `bash_exec`. Implementation in Phase 7/13 (workflow-specific). | Phase 7 |
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
| 4: Core Toolset | `M` | 42 FunctionTools (8 categories), Director queue, three-tier tasks |
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
| 1.5.1 | 2026-02-16 | Aligned tool/callback distinction (checkpoint + regression are not FunctionTools); added escalate_to_ceo to PM tools |
| 1.5.2 | 2026-02-16 | Reclassified ContextBudgetAgent as `before_model_callback` (not standalone agent) to match architecture doc |
| 1.6.0 | 2026-02-16 | Revised Decision #46: replaced file-based directory-scoped tool registry with ADK-native GlobalToolset(BaseToolset) pattern |
| 1.6.1 | 2026-02-16 | Replaced vague "deterministic callback" terminology with exact ADK mechanisms: checkpoint_project = after_agent_callback, RegressionTestAgent = CustomAgent |
| 1.6.2 | 2026-02-16 | Flagged unverified ADK mechanism claims as TBD: checkpoint_project and run_regression_tests behavior is decided, exact ADK wiring deferred to Phase 5 prototype |
| 1.7.0 | 2026-02-16 | Resolved all TBD flags: checkpoint_project = `after_agent_callback` on DeliverablePipeline (persists state via CallbackContext); run_regression_tests = `RegressionTestAgent` (CustomAgent) in pipeline after each batch (reads PM regression policy from session state) |
| 1.7.1 | 2026-02-17 | Moved GlobalToolset from Phase 5 to Phase 4; removed redundant Deterministic Safety section; fixed Phase 4 completion contract to be verifiable in Phase 4 |
| 2.0.0 | 2026-02-17 | Roadmap v2: slim format, component checklists moved to 07-COMPONENTS.md (BOM) |
| 2.1.0 | 2026-02-18 | Phase 4 scope expanded: 42 tools, 8 categories, Director queue, three-tier task system |
| 2.2.0 | 2026-02-18 | Phase 4 DONE: 273 tests pass, all quality gates clean; Phase 5 is NEXT |

---

*Document Version: 2.3.0*
*Last Updated: 2026-02-28*
