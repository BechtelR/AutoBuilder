# AutoBuilder Delivery Plan
*Version: 1.0.0*

## Phased Delivery

AutoBuilder is delivered in three phases. Phase 1 is the MVP — the smallest surface area that demonstrates the autonomous spec-to-software pipeline end to end. Phases 2 and 3 layer on production hardening and scale capabilities. No phase starts until the prior phase is validated.

---

### Phase 1: MVP — Core Loop + Foundation

The MVP proves the core thesis: an autonomous agentic system can take a specification, decompose it into features, implement them in parallel, and produce verified output with minimal human intervention.

| # | Deliverable | Description |
|---|------------|-------------|
| 1 | ADK App container | Context compression + resumability via `App` class with `EventsCompactionConfig` and `ResumabilityConfig` |
| 2 | Core toolset | Filesystem, bash, git, web, todo — implemented as lightweight `FunctionTool` wrappers |
| 3 | Skills system | `SkillLibrary` + `SkillLoaderAgent` — deterministic skill matching and progressive knowledge loading |
| 4 | Workflow composition system | `WorkflowRegistry` + auto-code as first workflow — pluggable from day one |
| 5 | LLM Router | Static routing config: task_type to model mapping via LiteLLM |
| 6 | Multi-level memory | `DatabaseSessionService` + 4 state scopes (session/user/app/temp) + `SqliteFtsMemoryService` |
| 7 | Plan/Execute agent separation | Planning agents never write code; execution agents consume structured plans |
| 8 | Autonomous continuation loop | "Run until done" — while incomplete features exist, select next batch and execute |
| 9 | Git worktree isolation | True filesystem isolation for parallel code generation |
| 10 | Spec-to-feature pipeline | Specification decomposed into implementable features (adapted from Autocoder patterns) |
| 11 | Basic CLI interface | Primary interface for launching and monitoring workflow execution |

### Phase 2: Production Hardening

Phase 2 strengthens reliability, cost visibility, and operational maturity.

| # | Deliverable | Description |
|---|------------|-------------|
| 12 | CustomAgent resume | `BaseAgentState` subclass + checkpoint steps in `BatchOrchestrator` for crash recovery |
| 13 | Cost/token tracking | `TokenTrackingPlugin` — per-feature and per-agent cost and token usage metrics |
| 14 | Agent role-based tool restrictions | Read-only exploration agents, write-capable execution agents — prevent scope creep |
| 15 | Context budget management | Reactive context-window awareness — token-counting callback triggers compression/pruning |
| 16 | Adaptive LLM Router | Cost-aware, latency-aware model selection with fallback chain monitoring |
| 17 | Temporal evaluation | Evaluate Temporal only if native ADK resume proves insufficient for multi-hour runs |

### Phase 3: Scale & Polish

Phase 3 expands capabilities beyond the core auto-code workflow.

| # | Deliverable | Description |
|---|------------|-------------|
| 18 | Web dashboard | TypeScript UI for workflow monitoring, intervention, and configuration |
| 19 | Additional workflow types | auto-design, auto-market — new workflow directories with their own pipelines and agents |
| 20 | Compound workflow composition | Multi-workflow request decomposition ("design and build" spans two workflows) |
| 21 | Self-learning/self-correcting patterns | Agents improve across runs based on accumulated memory and discovered patterns |
| 22 | Semantic memory upgrade | Vector-backed `MemoryService` (ChromaDB/FAISS/SQLite-VSS) if FTS5 proves insufficient |

---

## Prototype Validation Plan

Before full commitment to ADK, four focused prototypes validate the critical assumptions. If all four pass, commit to ADK. If Claude integration proves unreliable (P1) or the CustomAgent outer loop is too clunky (P4), re-evaluate Pydantic AI.

### Prototype 1: Basic Agent Loop + Claude via LiteLLM

- Create ADK `LlmAgent` with Claude via LiteLLM wrapper
- Define file-read, file-write, bash as `FunctionTool`s
- **Critical validation**: Claude reliability through LiteLLM? Latency? Token counting accuracy?
- **Success criteria**: Claude responds reliably, tools execute correctly, token counts are accurate

### Prototype 2: Mixed Agent Coordination (LLM + Deterministic)

- Create `plan_agent` (LlmAgent) and `linter_agent` (CustomAgent)
- Wire in `SequentialAgent` pipeline
- Pass data via session state (`output_key` to state read)
- **Critical validation**: Unified event stream, state persistence across agent types, observability of deterministic steps
- **Success criteria**: Deterministic agent events appear in same stream as LLM agent events; state written by one agent is readable by the next

### Prototype 3: Parallel Execution

- Run 3 `LlmAgent` instances concurrently via `ParallelAgent`
- Each writes to distinct state keys
- **Critical validation**: No state collision, proper isolation, concurrent LLM calls, correct event interleaving
- **Success criteria**: All 3 agents produce correct output without cross-contamination; state keys are distinct and accurate

### Prototype 4: Dynamic Outer Loop (CustomAgent Orchestrator)

- Build `CustomAgent` that dynamically constructs `ParallelAgent` batches
- Implement "while incomplete features exist" loop with dependency ordering
- Test with 5 simple features
- **Critical validation**: Dynamic workflow construction, execution order respects dependencies, failure handling, continuation after partial failure
- **Success criteria**: Features execute in correct dependency order; failed features do not block independent features; loop terminates correctly

---

## Open Questions

| # | Question | Status | Target Phase |
|---|----------|--------|--------------|
| 1 | Feature file format (JSON, SQLite, other?) | Open | Phase 1 |
| 2 | Spec parsing — how sophisticated should generation be? | Open | Phase 1 |
| 3 | Regression strategy — random sampling or dependency-aware? | Open | Phase 1 |
| 4 | Reuse Automaker TS libs or rewrite in Python? | Open — language change affects reuse | Phase 1 |
| 5 | Agent role system granularity | Open | Phase 2 |
| 6 | Context budget strategy — per-agent limits with pruning? | Open | Phase 2 |
| 7 | Web search provider selection (SearXNG vs Brave vs Tavily) | Open | Phase 1 |
| 8 | Agent-browser integration approach for UI testing | Open | Phase 1 |
| 9 | Durable execution — native ADK resume sufficient or need Temporal? | Likely sufficient — evaluate in Phase 2 | Phase 2 |
| 10 | Memory ingestion strategy — after each feature, each batch, or session end? | Open | Phase 1 |
| 11 | SQLite FTS5 vs vector store for MemoryService — is FTS5 sufficient? | Start with FTS5, evaluate in Phase 2 | Phase 1/2 |

---

## Risk Register

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Claude unreliable through LiteLLM/ADK | High | Prototype 1 validates this first; Pydantic AI fallback path |
| ADK CustomAgent outer loop too clunky | Medium | Prototype 4 validates; could simplify to plain Python loop using ADK for inner pipelines only |
| Google deprecates/pivots ADK | Low-Medium | Apache 2.0 license means forkable; core architecture patterns transfer to other frameworks |
| Context window exhaustion in long runs | Medium | Token-counting callback + reactive compression + checkpoint/restart |
| Non-Gemini models as second-class citizens | Medium | Test thoroughly; stay on LiteLLM latest; community pressure keeps this improving |

### Architectural Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Feature scope creep toward 117k LOC | High | Phased delivery; MVP ruthlessness; max ~300 lines per module |
| Skills system becomes too rigid | Low | OR-logic triggers keep matching simple; project overrides add flexibility |
| Google ecosystem gravity (Vertex AI pull) | Medium | Strict discipline: local SQLite/Postgres only; document boundaries; no GCP services |

---

*Document version: 1.0.0 | Last updated: 2026-02-11*
