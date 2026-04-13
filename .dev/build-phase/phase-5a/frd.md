# Phase 5a FRD: Agent Definitions & Pipeline
*Generated: 2026-03-10*

## Objective

Make autonomous agent execution possible. Before this phase, the system has infrastructure (gateway, workers, tools) but no real agents — just stubs. Phase 5a defines all agents as declarative files, composes them into a working pipeline that can execute a single deliverable end-to-end, and establishes forward-dependency contracts for services that arrive in later phases. Traces to PR-5, PR-5a, PR-5b, PR-5c, PR-10, PR-15a, PR-15b, NFR-4a, NFR-4b.

## Consumer Roles

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| System (Pipeline Runtime) | The AutoBuilder runtime that assembles agents from definition files, composes them into pipelines, routes LLM calls, and manages context budgets | Agent definition file on disk → configured ADK agent executing in a worker with correct tools, assembled instructions, and routed model; deliverable input in session state → structured pipeline output in session state |
| Developer (Platform Extender) | A developer who authors agent definition files, customizes agent behavior per-project via partial overrides, or extends the agent system with new agents | Definition file written to any scope directory → agent built with correct overrides and assembled instructions; invalid or unauthorized definition → clear rejection with file path and reason |

## Appetite

L- size: ~5–7 days. 48 BOM components, but many are thin agent wrappers (~50–80 lines each) and definition files. The critical path runs through AgentRegistry and InstructionAssembler — these are the complex components. Pipeline composition and agent definitions are high-volume but low-complexity.

## Prerequisites

- Phase 4 complete: 42 FunctionTools available via GlobalToolset, LLM Router operational, DatabaseSessionService with 4-scope state, EventPublisher with Redis Streams
- DB infrastructure tables created in this phase: `ceo_queue`, `director_queue`, `project_configs` (with Alembic migrations)

## Capabilities

### CAP-1: Agent Definition & Registry

The system discovers, resolves, and builds agents from declarative definition files. Agents are defined as markdown files with YAML frontmatter — the filesystem is the registry. An AgentRegistry scans definition directories, resolves a 3-scope file cascade, validates definitions, and builds configured ADK agents on demand with full resolution auditability.

**Requirements:**

- [x] **FR-5a.01**: When the system starts a worker, it scans agent definition directories and indexes all valid definition files by agent name, extracting frontmatter metadata (name, type, tool_role, model_role, output_key, description) and instruction body content.
- [x] **FR-5a.02**: When building an agent, the system resolves the 3-scope file cascade — project-scope overrides workflow-scope overrides global-scope, matched by filename. In Phase 5a, the workflow scope is non-functional (empty directory or None); resolution operates over global + project scopes only.
- [x] **FR-5a.03**: When a project-scope definition file contains only frontmatter (no instruction body after the closing `---`), the system treats it as a partial override — its frontmatter fields merge over the parent scope's frontmatter while inheriting the parent scope's instruction body.
- [x] **FR-5a.04**: When a definition file has invalid frontmatter (missing required fields, unknown type, malformed YAML), the system rejects it with an error identifying the file path and the specific problem. The agent is not built.
- [x] **FR-5a.05**: When a project-scope definition specifies `type: custom`, the system rejects it. Only `type: llm` is permitted from project-scope directories. This prevents arbitrary class paths from user-controlled directories.
- [x] **FR-5a.06**: When building an agent, the system records which scope (global, workflow, project) provided the definition, the file path used, and whether a partial override was applied. This resolution map is written to session state for diagnostic inspection.
- [x] **FR-5a.07**: When building an LLM agent, the system uses the definition's `model_role` to resolve a LiteLLM model string via the LLM Router, and uses the definition's `tool_role` to resolve a filtered tool set via the GlobalToolset.
- [x] **FR-5a.08**: When building a custom agent, the system uses the definition's `class` field to locate and instantiate the CustomAgent implementation. Hybrid custom agents receive a `model_role` for internal LiteLLM routing and may receive an `instruction_body` for internal LLM guidance.
- [x] **FR-5a.09**: When no definition file exists for a requested agent name in any scope, the system raises a clear error. It does not silently substitute a default agent.
- [x] **FR-5a.10**: When two definition files in the same scope directory have the same `name` in their frontmatter, the system rejects both with an error identifying the collision.

---

### CAP-2: Instruction Composition

Agent instructions are composed from 6 typed fragments via an InstructionAssembler. Each fragment type has a defined source, lifecycle, and override behavior. A constitutional SAFETY fragment is hardcoded and non-overridable. The assembly is auditable — each fragment's source is tracked.

**Requirements:**

- [x] **FR-5a.11**: When composing instructions for any LLM agent, the system prepends a hardcoded SAFETY fragment. This fragment cannot be overridden, removed, or modified by any scope — not project-scope definitions, not Director session state, not skill content, not any other fragment type.
- [x] **FR-5a.12**: When composing instructions, the system assembles fragments in defined order: SAFETY (hardcoded), then IDENTITY and GOVERNANCE (from the agent definition file body), then PROJECT (from database-backed project configuration), then TASK (from session state — current deliverable spec, plan, review feedback), then SKILL (from loaded skills filtered by the agent's applies_to configuration).
- [x] **FR-5a.13**: When the PROJECT or SKILL fragments contain literal curly braces (common in code snippets — Python, Rust, Go, JSON), the system escapes them to prevent misinterpretation as `{key}` state template placeholders. Only declared template placeholders remain unescaped.
- [x] **FR-5a.14**: When composing instructions, the system records which source provided each fragment (hardcoded, definition file path, database entity, session state key, skill name) for diagnostic auditability. The source map is queryable.
- [x] **FR-5a.15**: When project configuration is unavailable (no entry in `project_configs` table), the PROJECT fragment is omitted and the system logs a debug message. Instruction assembly succeeds without it.
- [x] **FR-5a.16**: When task context is unavailable in session state (no current deliverable spec), the TASK fragment is omitted. Instruction assembly succeeds without it.
- [x] **FR-5a.17**: When no skills are loaded (NullSkillLibrary in Phase 5a, or no matches), the SKILL fragment is omitted. Instruction assembly succeeds without it.
- [x] **FR-5a.18**: When composing instructions, the system preserves `{key}` and `{key?}` template placeholders for ADK runtime resolution. The assembler does not resolve these — ADK does at LLM call time. `{key?}` silently resolves to empty string if the key is absent from state; `{key}` raises if absent.

---

### CAP-3: Worker Agents (LLM)

Four LLM worker agents execute individual deliverables within the pipeline. Each agent has a defined role, receives assembled instructions with relevant context, uses role-appropriate tools, and writes structured output to session state via its `output_key`.

**Requirements:**

- [x] **FR-5a.19**: When the planner agent receives a deliverable specification in session state, it produces a structured implementation plan and writes it to session state via its output_key. The plan is consumable by the coder agent downstream.
- [x] **FR-5a.20**: When the coder agent receives a plan in session state, it implements the plan using the full tool set (filesystem, execution, git, code intelligence) and writes its output to session state via its output_key.
- [x] **FR-5a.21**: When the reviewer agent receives implementation output and lint/test results in session state, it evaluates quality against the deliverable specification and writes a structured review (pass/fail with specific findings) to session state via its output_key.
- [x] **FR-5a.22**: When the fixer agent receives review feedback in session state, it corrects the identified issues using the full tool set and writes updated output to session state. The fixer's output overwrites the coder's output_key — this is intentional for the review cycle.
- [x] **FR-5a.23**: When any LLM worker agent is built, it receives a model routed via the LLM Router (model_role → LiteLLM model string) and a tool set filtered by the GlobalToolset (tool_role → permitted tools). The planner and reviewer receive read-only tool sets; the coder and fixer receive full tool sets.
- [x] **FR-5a.24**: When an LLM worker agent writes to session state via output_key, the write persists through ADK's Event/state_delta mechanism. Direct state assignment (ctx.session.state["key"] = val) is never used — it does not persist.

---

### CAP-4: Worker Agents (Custom — Deterministic & Hybrid)

Deterministic custom agents execute mandatory pipeline steps with no LLM involvement. Hybrid custom agents combine deterministic control flow with internal LiteLLM calls for classification or synthesis. All custom agents implement ADK's CustomAgent interface (`_run_async_impl`) and communicate results via Event state_delta.

**Requirements:**

- [x] **FR-5a.25**: When the SkillLoaderAgent runs, it queries the SkillLibraryProtocol for skills matching the current deliverable context and writes loaded skill names and content to session state. In Phase 5a with NullSkillLibrary, it writes empty results (`loaded_skills: {}`, `loaded_skill_names: []`) and succeeds — the pipeline continues without skill-injected context.
- [x] **FR-5a.26**: When the MemoryLoaderAgent runs, it queries the memory service (BaseMemoryService) for cross-session context relevant to the current deliverable and writes results to session state. In Phase 5a with InMemoryMemoryService, it returns empty results (`memory_context: {}`, `memory_loaded: true`) and succeeds — the pipeline continues without cross-session memory.
- [x] **FR-5a.27**: When the memory service is unreachable or throws during the MemoryLoaderAgent's execution, the agent writes `memory_context: {}`, `memory_loaded: false` to state and logs a warning. It does not fail the pipeline.
- [x] **FR-5a.28**: When the LinterAgent runs, it executes the project's configured linter(s) and writes structured lint results (pass/fail, file locations, messages) to session state.
- [x] **FR-5a.29**: When the TestRunnerAgent runs, it executes the project's configured test suite and writes structured test results (pass/fail, test names, output) to session state.
- [x] **FR-5a.30**: When the FormatterAgent runs, it executes the project's configured code formatter(s) on the working tree. It writes a summary of changes (files modified, formatting applied) to session state.
- [x] **FR-5a.31**: When the DependencyResolverAgent runs, it analyzes deliverable dependencies using deterministic graph resolution with internal LiteLLM calls (routed via model_role) for ambiguous relationship classification. It writes a dependency order to session state.
- [x] **FR-5a.32**: When the DiagnosticsAgent runs, it reads lint results and test results from session state and synthesizes actionable diagnostics using deterministic aggregation with internal LiteLLM calls (routed via model_role) for root-cause analysis. It writes structured diagnostics to session state.
- [x] **FR-5a.33**: When the RegressionTestAgent is defined, its agent definition file and CustomAgent implementation exist and are buildable by the AgentRegistry. Its integration into batch-level execution is deferred to Phase 8a (it runs after ParallelAgent completes batches, which requires Phase 8a's batch execution infrastructure).
- [x] **FR-5a.34**: When any hybrid custom agent makes an internal LiteLLM call, the call is routed via the agent's `model_role` through the LLM Router, using the same fallback chains as LLM agents.

---

### CAP-5: Pipeline Composition

Agents compose into a DeliverablePipeline (SequentialAgent) that processes a single deliverable end-to-end. The pipeline includes a ReviewCycle (LoopAgent) for iterative quality improvement. Agents communicate through session state — each agent reads upstream output and writes its own via output_key.

**Requirements:**

- [x] **FR-5a.35**: When a single deliverable is dispatched, it executes through the DeliverablePipeline in this sequence: SkillLoaderAgent → MemoryLoaderAgent → planner → coder → FormatterAgent → LinterAgent → TestRunnerAgent → DiagnosticsAgent → ReviewCycle.
- [x] **FR-5a.36**: When the ReviewCycle begins, it iterates through: reviewer → fixer → LinterAgent (re-lint) → TestRunnerAgent (re-test), up to a configurable maximum iterations (default: 3).
- [x] **FR-5a.37**: When the reviewer approves the implementation (structured review indicates pass), the ReviewCycle terminates immediately. The deliverable proceeds to completion.
- [x] **FR-5a.38**: When the ReviewCycle reaches maximum iterations without approval, the deliverable is marked as failed with the final review findings preserved in session state.
- [x] **FR-5a.39**: When an agent in the pipeline writes to session state via its output_key, downstream agents can read that value through `{key}` template injection in their instructions or through direct state access in CustomAgent `_run_async_impl`.
- [x] **FR-5a.40**: When the pipeline completes (success or failure), all agent outputs are preserved in session state. No intermediate state is lost — the planner's plan, the coder's output, lint/test results, review findings, and fix attempts are all retained.
- [x] **FR-5a.41**: When a custom agent needs to read upstream state in `_run_async_impl`, a `context_from_state` helper extracts typed values from session state with clear error messages for missing required keys.

---

### CAP-6: Context Budget Management

The system monitors token usage before each LLM call and signals when context capacity is approaching its limit. The signal triggers context recreation (not lossy compaction). In Phase 5a, the monitor and exception are operational; the full recreation pipeline is implemented in Phase 5b.

**Requirements:**

- [x] **FR-5a.42**: Before each LLM call, the ContextBudgetMonitor (a before_model_callback) estimates the token count of the pending request using LiteLLM's token_counter and compares it against the model's context window limit.
- [x] **FR-5a.43**: When the ContextBudgetMonitor estimates token usage, it writes the usage percentage to session state (e.g., `context_budget_used_pct: 73.2`). This value is available for diagnostic observation and system reminders.
- [x] **FR-5a.44**: When token usage exceeds the configured threshold (default: 80% of the model's context window), the monitor raises a `ContextRecreationRequired` exception. This exception is the signal for context recreation — it does not trigger lossy compaction (EventsCompactionConfig remains as a safety net only).
- [x] **FR-5a.45**: When the configured threshold is set to a value outside 0–100, the system rejects it at startup with a configuration error.
- [x] **FR-5a.46**: When the model's context window limit cannot be determined from LiteLLM's model registry, the monitor logs a warning and uses a conservative default (100,000 tokens). It does not skip monitoring.

## Non-Functional Requirements

- [x] **NFR-5a.01**: All agent definition files in the global scope are scanned, parsed, and indexed within 2 seconds of worker startup. Scanning is cached for subsequent builds within the same worker lifecycle.
- [x] **NFR-5a.02**: InstructionAssembler produces deterministic output for identical inputs — same definition file, same project config, same session state, same loaded skills → identical assembled instruction string. No randomness, no timestamp injection, no ordering variance.
- [x] **NFR-5a.03**: The ContextBudgetMonitor adds no more than 5ms overhead per LLM call (token counting + state write + threshold check).
- [x] **NFR-5a.04**: All quality gates pass (ruff check, pyright strict, pytest) with the complete agent system. Zero type: ignore exceptions that are not documented with a rationale comment.
- [x] **NFR-5a.05**: Each custom agent implementation is ≤150 lines. Each LLM agent definition file is self-contained (frontmatter + instruction body). No agent's logic spans multiple files except through shared utilities.

## Rabbit Holes

- **Direct state writes don't persist in CustomAgent**: `ctx.session.state["key"] = val` inside `_run_async_impl` is silently ignored by ADK. All state writes must use `yield Event(actions=EventActions(state_delta={...}))`. This will burn hours if missed. Every custom agent must use the Event/state_delta pattern.

- **Hybrid CustomAgent vs LlmAgent confusion**: Hybrid agents use `type: custom` in their definition (same as deterministic), but have `model_role` + `instruction_body`. The body guides internal LiteLLM calls — it is NOT consumed by ADK's agent loop. Easy to conflate the two uses of "instructions."

- **Fragment escaping in InstructionAssembler**: SKILL and PROJECT fragments often contain code with curly braces (`{`, `}`). These must be escaped to prevent ADK from interpreting them as `{key}` template placeholders. Only declared `{placeholder}` patterns should remain unescaped. Getting this wrong produces cryptic KeyError failures at LLM call time.

- **Partial override semantics**: A project-scope definition file with only frontmatter inherits the parent body. But what constitutes "only frontmatter"? The file must end after the closing `---` with no content (or only whitespace). Any non-whitespace content after `---` is treated as a full replacement body. Edge case: a file with `---\n\n---\n` (empty body between fences) is ambiguous — define and test the boundary.

- **LoopAgent termination condition**: ADK's LoopAgent requires the sub-agent to signal completion. The reviewer must write a clear pass/fail signal that the LoopAgent can evaluate to decide whether to continue or stop. Verify how ADK LoopAgent reads termination — is it `escalate` callback, output inspection, or max_iterations only?

- **InMemoryMemoryService limitations**: ADK's built-in InMemoryMemoryService is keyword-only and non-persistent. It satisfies the interface but behavior may differ from PostgresMemoryService (Phase 9). Phase 5a tests should not depend on search quality — only on the search-write-to-state contract.

## No-Gos

- **No supervision mechanisms**: Director↔PM delegation, escalation, supervision callbacks, hard limits cascade — all Phase 5b. Phase 5a defines Director and PM as agent configurations only; their supervision behavior is not wired.
- **No CEO queue or chat gateway routes**: The database tables are created (migration infrastructure), but the gateway routes (GET /ceo/queue, PATCH /ceo/queue/{id}, POST /chat/{session_id}/messages) are Phase 5b.
- **No state key authorization**: Tier-prefix validation (director:, pm:, worker:) in EventPublisher ACL is Phase 5b.
- **No context recreation pipeline**: Phase 5a raises `ContextRecreationRequired`; Phase 5b catches it and runs the 4-step recreation (persist → seed → fresh → reassemble).
- **No real SkillLibrary**: Phase 5a uses NullSkillLibrary (returns empty). Real skill matching (trigger matchers, two-tier scan, Redis cache) is Phase 6.
- **No real MemoryService**: Phase 5a uses InMemoryMemoryService (returns empty in practice). PostgresMemoryService with tsvector/pgvector search is Phase 9.
- **No tool_role ceiling validation**: Project-scope type:llm restriction is enforced. tool_role ceiling validation (against workflow manifest) requires WORKFLOW.yaml which is Phase 7a.
- **No batch execution**: DeliverablePipeline handles a single deliverable. Parallel batch execution via ParallelAgent and PM-driven batch loop are Phase 8a.
- **No system reminders**: Ephemeral nudges via before_model_callback (A58) are Phase 5b.
- **No Director formation**: Director formation artifacts in user: scope are Phase 5b.

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-5a.01, FR-5a.02, FR-5a.03, FR-5a.04, FR-5a.09, FR-5a.10 | PR-5b: Declarative agent definition files | Agent Definitions |
| FR-5a.02, FR-5a.03 | PR-5c: 3-scope file cascade | Agent Definitions |
| FR-5a.05 | NFR-4b: Project-scope restrictions (type: llm only) | Security |
| FR-5a.06 | PR-35a: Agent definition resolution auditability | Observability |
| FR-5a.07, FR-5a.08, FR-5a.23 | PR-5: Stage-appropriate agent configuration | Agent Config |
| FR-5a.11 | NFR-4a: Constitutional SAFETY fragment | Security |
| FR-5a.12, FR-5a.13, FR-5a.14, FR-5a.15, FR-5a.16, FR-5a.17, FR-5a.18 | PR-5a: InstructionAssembler with typed fragments | Instruction Composition |
| FR-5a.19, FR-5a.20 | PR-5: Plan agent produces plan; code agent implements | Worker Agents |
| FR-5a.21, FR-5a.22 | PR-22: Review cycle verification | Quality |
| FR-5a.23, FR-5a.24 | PR-5: Agent tool/model configuration | Worker Agents |
| FR-5a.25 | PR-5a: Skill fragment injection via InstructionAssembler | Skills |
| FR-5a.26, FR-5a.27 | PR-15b: MemoryLoaderAgent deterministic pipeline step | Memory |
| FR-5a.28, FR-5a.29 | PR-11: Validators as mandatory pipeline steps | Quality |
| FR-5a.30 | PR-11: Mandatory formatting step | Quality |
| FR-5a.31, FR-5a.32, FR-5a.34 | PR-5: Hybrid CustomAgent with internal LLM routing | Agent Config |
| FR-5a.33 | PR-11: RegressionTestAgent defined (batch integration Phase 8a) | Quality |
| FR-5a.35, FR-5a.36, FR-5a.37, FR-5a.38 | PR-10: Deliverable pipeline execution | Pipeline |
| FR-5a.39, FR-5a.40, FR-5a.41 | PR-5: Inter-agent state communication | Pipeline |
| FR-5a.42, FR-5a.43, FR-5a.44, FR-5a.45, FR-5a.46 | PR-15: Bounded authority — context budget; PR-15a: Context recreation trigger | Context |
| NFR-5a.01 | NFR-2: System overhead not meaningful contributor | Performance |
| NFR-5a.02 | PR-5a: Deterministic instruction composition | Reliability |
| NFR-5a.03 | NFR-2: System overhead not meaningful contributor | Performance |
| NFR-5a.04 | NFR-5: Quality gates | Engineering |
| NFR-5a.05 | NFR-5: Maintainability — module size limits | Engineering |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | InstructionAssembler composes agent instructions from typed fragments with source auditability | CAP-2: FR-5a.11, FR-5a.12, FR-5a.14 |
| 2 | AgentRegistry scans agent definition files (.md) and builds configured agents (LlmAgent and CustomAgent) with 3-scope file cascade | CAP-1: FR-5a.01, FR-5a.02, FR-5a.07, FR-5a.08 |
| 3 | SAFETY fragment present in all assembled instructions, not overridable by project-scope or state | CAP-2: FR-5a.11 |
| 4 | Can run a single deliverable through the full DeliverablePipeline | CAP-5: FR-5a.35 |
| 5 | Plan agent produces structured plan; code agent implements it | CAP-3: FR-5a.19, FR-5a.20 |
| 6 | Lint/test agents produce structured results in state | CAP-4: FR-5a.28, FR-5a.29 |
| 7 | Review cycle loops on failure, terminates on approval or max iterations | CAP-5: FR-5a.36, FR-5a.37, FR-5a.38 |
| 8 | Context budget before_model_callback reports token usage percentage | CAP-6: FR-5a.42, FR-5a.43 |
| 9 | Context budget monitor triggers context recreation (not lossy compaction) | CAP-6: FR-5a.44 |
| 10 | MemoryLoaderAgent executes in pipeline; returns empty context in degraded mode | CAP-4: FR-5a.26, FR-5a.27 |
| 11 | SkillLoaderAgent executes in pipeline via SkillLibraryProtocol; returns empty skills with NullSkillLibrary | CAP-4: FR-5a.25 |
| 12 | Hybrid CustomAgents (DependencyResolver, DiagnosticsAgent) use LiteLLM internally with model_role routing | CAP-4: FR-5a.31, FR-5a.32, FR-5a.34 |
| 13 | Project-scope agent definitions rejected if type: custom | CAP-1: FR-5a.05 |

---

*Document Version: 1.0.0*
*Phase: 5a — Agent Definitions & Pipeline*
*Last Updated: 2026-03-10*
