# Phase 5a Spec: Agent Definitions & Pipeline
*Generated: 2026-03-11*

## Overview

Phase 5a makes autonomous agent execution possible. Before this phase, AutoBuilder has infrastructure (gateway, workers, tools, LLM router, session persistence) but no real agents — just echo/director stubs. This phase delivers:

1. **Instruction composition** — InstructionAssembler composes typed fragments (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL) from auditable sources into agent instructions. A constitutional SAFETY fragment is hardcoded and non-overridable.
2. **Agent definitions** — Declarative markdown files with YAML frontmatter define all agents. An AgentRegistry scans directories, resolves a 3-scope file cascade, and builds configured ADK agents on demand.
3. **Custom agents** — 8 CustomAgent implementations (6 deterministic, 2 hybrid) handle pipeline steps like skill loading, linting, testing, formatting, dependency resolution, and diagnostics.
4. **Pipeline composition** — DeliverablePipeline (SequentialAgent) composes all agents into an end-to-end deliverable execution flow with a ReviewCycle (LoopAgent) for iterative quality improvement.
5. **Context budget monitoring** — ContextBudgetMonitor fires before each LLM call, tracks token usage, and raises ContextRecreationRequired when threshold is exceeded.
6. **Database tables** — ceo_queue, director_queue, and project_configs tables with Alembic migrations (used by Phase 5b; tables created here).

Forward-dependency contracts: SkillLibraryProtocol + NullSkillLibrary (Phase 6), BaseMemoryService + InMemoryMemoryService (Phase 9). No supervision, no batch execution, no real skills or memory — those are Phase 5b+.

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 4: Core Toolset | MET | 42 FunctionTools in `app/tools/`, GlobalToolset with role-based vending, all quality gates pass |
| Phase 3: ADK Engine Integration | MET | LlmRouter, DatabaseSessionService, EventPublisher, anti-corruption layer, 4-scope state operational |
| Phase 2: Gateway + Infrastructure | MET | FastAPI gateway, ARQ workers, Redis, database with migrations |

## Design Decisions

### DD-1: Custom Agent File Placement

Custom agent Python implementations live in `app/agents/custom/`. Definition files (`.md`) for all agents (LLM and custom) live flat in `app/agents/`. The `app/agents/llm/` directory is removed — LLM agents are defined purely via `.md` files with no Python implementation. All file paths are reflected in `03-STRUCTURE.md` v1.8.

### DD-2: Class Registry in _registry.py

`_registry.py` contains both the AgentRegistry (scans `.md` files, resolves cascade, builds agents) and a class registry — a `dict[str, type[BaseAgent]]` mapping `class` frontmatter strings (e.g., `"LinterAgent"`) to importable Python types. Custom agent registration uses explicit imports, not dynamic `importlib` discovery.

### DD-3: SkillLibraryProtocol & NullSkillLibrary

A `SkillLibraryProtocol` (Python Protocol class) defines the interface SkillLoaderAgent depends on. A `NullSkillLibrary` implementation always returns empty results (`{}`). This satisfies FR-5a.25 without requiring the real SkillLibrary (Phase 6). The protocol lives in `app/agents/protocols.py`.

### DD-4: MemoryService Forward Dependency

Phase 5a uses ADK's `InMemoryMemoryService` for the MemoryLoaderAgent. The agent calls `search_memory()` but gets empty/minimal results. If the service is unreachable, the agent degrades gracefully (FR-5a.27). `PostgresMemoryService` (Phase 9) replaces it.

### DD-5: Pipeline Composition Location

The `DeliverablePipeline` lives in `app/agents/pipeline.py` as a factory function that constructs the full SequentialAgent tree. In Phase 5a, workers call this factory directly. In Phase 7, the auto-code workflow's `pipeline.py` delegates to it. This avoids premature coupling to the workflow registry.

### DD-6: ReviewCycle Termination Signal

ADK's `LoopAgent` continues until `max_iterations` is reached or an `escalate` action occurs. The reviewer writes `review_passed: true/false` to session state via `state_delta`. A custom `should_continue` function (set as the `LoopAgent`'s termination check) reads `review_passed` from state — if `true`, returns `False` (stop looping). If the ADK `LoopAgent` does not support a custom termination function, the alternative is wrapping the review cycle in a `CustomAgent` that implements the loop logic directly. The implementer must verify the ADK LoopAgent API in `.dev/.knowledge/adk/` before choosing.

### DD-7: before_model_callback Composition

ADK agents accept a single `before_model_callback`. Phase 3 uses it for LLM Router model override. Phase 5a adds context budget monitoring (CT04) and context injection (A43). Solution: a `compose_callbacks` function that chains multiple callbacks in order. Each callback returns `None` (continue) or `LlmResponse` (short-circuit). The compositor calls them sequentially: router override → context injection → budget monitor.

```python
def compose_callbacks(
    *callbacks: Callable[[CallbackContext, LlmRequest], LlmResponse | None],
) -> Callable[[CallbackContext, LlmRequest], LlmResponse | None]:
    """Chain multiple before_model_callbacks. First non-None return wins."""
    def composed(ctx: CallbackContext, req: LlmRequest) -> LlmResponse | None:
        for cb in callbacks:
            result = cb(ctx, req)
            if result is not None:
                return result
        return None
    return composed
```

### DD-8: Agent Definition File Format

Frontmatter fields (YAML between `---` fences):

```yaml
---
name: coder                    # Required: agent identifier (matches filename stem)
description: Implement code    # Required: one-line purpose
type: llm                     # Required: "llm" or "custom"
tool_role: coder              # Optional: maps to GlobalToolset role
model_role: code              # Optional: maps to LlmRouter ModelRole
output_key: code_output       # Optional: session state key for output
class: LinterAgent            # Required for type:custom only: class registry key
applies_to:                   # Optional: skill filtering for InstructionAssembler
  - coder
  - fixer
---

Instruction body content (IDENTITY + GOVERNANCE fragments)...
```

The body after the closing `---` is the agent's instruction content. For LLM agents, this becomes the IDENTITY + GOVERNANCE fragments. For custom agents, hybrid agents use this as internal LLM guidance; purely deterministic agents may have an empty body.

**Partial override**: A file with only frontmatter (nothing after closing `---`, or only whitespace) inherits the parent scope's instruction body. Any non-whitespace content after `---` is a full body replacement.

### DD-9: InstructionContext Container

`InstructionContext` is a dataclass that bundles per-invocation assembly data:

```python
@dataclass(frozen=True)
class InstructionContext:
    project_config: str | None       # PROJECT fragment content (from DB)
    task_context: str | None         # TASK fragment content (from session state)
    loaded_skills: dict[str, str]    # SKILL fragments (skill_name → content)
    agent_name: str                  # For audit trail
```

The assembler reads this to inject dynamic fragments. The caller (AgentRegistry or pipeline setup) populates it from available sources.

### DD-10: Migration Numbering

Migrations follow sequential `NNN_description.py` naming per engineering standards. The latest existing migration number must be checked; the new migration continues the sequence. All three tables (ceo_queue, director_queue, project_configs) go in a single migration file since they have no cross-dependencies and are created together.

---

## Deliverables

### P5a.D1: Database Tables & Migrations
**Files:** `app/models/enums.py`, `app/db/models.py`, `app/db/migrations/versions/NNN_ceo_director_queues_project_configs.py`
**Depends on:** —
**Description:** Add CeoQueueStatus enum. Add SQLAlchemy mapped models for ceo_queue, director_queue, and project_configs tables using the established TimestampMixin pattern. Create a single Alembic migration for all three tables. CeoItemType, EscalationPriority, EscalationRequestType, and DirectorQueueStatus enums already exist in `app/models/enums.py`.
**BOM Components:**
- [ ] `D05` — `ceo_queue` table
- [ ] `D08` — `project_configs` table
- [ ] `D16` — CEO queue migration
- [ ] `D19` — Project configs migration
- [ ] `V13` — CEO queue type enum (`CeoItemType` — exists, verify usage)
- [ ] `V14` — CEO queue priority enum (`EscalationPriority` — exists, verify usage)
- [ ] `V15` — CEO queue status enum (`CeoQueueStatus` — new)
- [ ] `V23` — `director_queue` table
- [ ] `V24` — `director_queue` migration
**Requirements:**
- [ ] `CeoQueueStatus` enum exists in `app/models/enums.py` with values `PENDING`, `SEEN`, `RESOLVED`, `DISMISSED`
- [ ] `CeoQueueItem` model exists with fields: id (UUID PK), type (CeoItemType), priority (EscalationPriority), status (CeoQueueStatus), message (str), source_project_id (UUID, nullable, indexed), source_agent (str), metadata (JSONB, nullable), session_id (str, nullable), created_at, updated_at
- [ ] `DirectorQueueItem` model exists with fields: id (UUID PK), type (EscalationRequestType), priority (EscalationPriority), status (DirectorQueueStatus), context (str), source_project_id (UUID, nullable, indexed), source_agent (str), metadata (JSONB, nullable), created_at, updated_at
- [ ] `ProjectConfig` model exists with fields: id (UUID PK), project_id (UUID, unique, indexed), name (str), config (JSONB), created_at, updated_at
- [ ] All models use `TimestampMixin` and follow existing patterns in `app/db/models.py`
- [ ] Migration creates all three tables and applies cleanly with `alembic upgrade head`
- [ ] Migration uses sequential NNN numbering (not hash-based)
- [ ] `pyright` passes with strict mode on all modified files
**Validation:**
- `uv run alembic upgrade head` — migration applies without error
- `uv run pyright app/db/models.py app/models/enums.py`
- `uv run pytest tests/db/ -v`

---

### P5a.D2: Instruction Composition System
**Files:** `app/agents/assembler.py`, `app/agents/protocols.py`, `app/agents/state_helpers.py`
**Depends on:** —
**Description:** Implement the InstructionAssembler that composes typed fragments into agent instructions. Includes InstructionFragment dataclass, InstructionContext container, 6 fragment types with SAFETY hardcoded and non-overridable, curly brace escaping for SKILL/PROJECT fragments, source auditability, and {key}/{key?} placeholder preservation. Also implements the `context_from_state` helper for custom agents to read typed state values, the SkillLibraryProtocol with NullSkillLibrary stub, and the project config loader function.
**BOM Components:**
- [ ] `A52` — InstructionAssembler — fragment-based instruction composition
- [ ] `A53` — InstructionFragment dataclass
- [ ] `A57` — Base instruction fragments (6 types: SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL)
- [ ] `A75` — SAFETY instruction fragment (hardcoded, non-overridable)
- [ ] `A76` — InstructionContext container (per-invocation assembly data)
- [ ] `A51` — `{key}` state template injection (placeholder preservation)
- [ ] `M05` — State template injection (`{key}` / `{key?}`)
- [ ] `A54` — `context_from_state` helper
- [ ] `M06` — Project config loader (tool or init callback)
- [ ] `A43` — `before_model_callback` context injection
**Requirements:**
- [ ] `InstructionFragment` is a dataclass with fields: `fragment_type` (str), `content` (str), `source` (str)
- [ ] `InstructionContext` is a frozen dataclass with fields: `project_config` (str | None), `task_context` (str | None), `loaded_skills` (dict[str, str]), `agent_name` (str)
- [ ] `InstructionAssembler.assemble()` accepts agent_name, body (str), and InstructionContext; returns assembled instruction string
- [ ] SAFETY fragment is always prepended and is identical regardless of inputs (hardcoded content, source="hardcoded")
- [ ] Fragment assembly order: SAFETY → IDENTITY/GOVERNANCE (from body) → PROJECT → TASK → SKILL
- [ ] Literal `{` and `}` in PROJECT and SKILL fragment content are escaped to `{{` and `}}`, except declared `{key}` and `{key?}` patterns
- [ ] `InstructionAssembler.get_sources()` returns a list of `(fragment_type, source)` tuples for the last assembly (auditability)
- [ ] When PROJECT config is None, the PROJECT fragment is omitted; assembly succeeds
- [ ] When task_context is None, the TASK fragment is omitted; assembly succeeds
- [ ] When loaded_skills is empty, the SKILL fragment is omitted; assembly succeeds
- [ ] Identical inputs produce identical output (deterministic — NFR-5a.02)
- [ ] `context_from_state(state, key, expected_type, required)` returns typed value or raises `ValueError` with clear message for missing required keys
- [ ] `SkillLibraryProtocol` defines `match_skills(context: dict[str, object]) -> dict[str, str]` method
- [ ] `NullSkillLibrary` implements `SkillLibraryProtocol` and always returns `{}`
- [ ] `load_project_config(session, project_id)` loads config from `project_configs` table and returns config dict or None
- [ ] `compose_callbacks(*callbacks)` chains multiple `before_model_callback` functions; first non-None return wins
- [ ] Context injection callback writes relevant state keys to `LlmRequest` content (no-op in Phase 5a; wired in Phase 5b)
**Validation:**
- `uv run pyright app/agents/assembler.py app/agents/protocols.py app/agents/state_helpers.py`
- `uv run pytest tests/agents/test_assembler.py tests/agents/test_state_helpers.py -v`

---

### P5a.D3: AgentRegistry & Definition File Infrastructure
**Files:** `app/agents/_registry.py`
**Depends on:** P5a.D2
**Description:** AgentRegistry scans agent definition directories for `.md` files, parses YAML frontmatter and instruction bodies, resolves the 3-scope file cascade (global → workflow → project), validates definitions, and builds configured ADK agents (LlmAgent and CustomAgent) on demand. Includes class registry for CustomAgent type resolution, partial override support, project-scope type:custom rejection, and resolution auditability via session state.
**BOM Components:**
- [ ] `A55` — Agent definition files (markdown + YAML frontmatter format)
- [ ] `A56` — AgentRegistry class (scan + build from files)
- [ ] `A77` — Partial override (frontmatter-only definition files inherit parent body)
- [ ] `A78a` — Project-scope type validation (`type: llm` only from project scope)
- [ ] `A80` — Resolution auditability (`agent_resolution_sources` session state key)
- [ ] `A50` — `output_key` state communication (set on built agents)
- [ ] `E02` — Agent tree construction (via `AgentRegistry.build()`)
- [ ] `E03` — PM agent construction (via `AgentRegistry.build()`)
**Requirements:**
- [ ] `AgentRegistry.__init__(global_dir, workflow_dir=None, project_dir=None)` accepts 1-3 directory paths
- [ ] `AgentRegistry.scan()` discovers all `.md` files in provided directories and indexes by agent name (filename stem)
- [ ] Scanning extracts frontmatter (name, description, type, tool_role, model_role, output_key, class, applies_to) and instruction body
- [ ] Required frontmatter fields: `name`, `description`, `type`; missing any → rejection with file path and field name
- [ ] Unknown `type` values (not "llm" or "custom") → rejection with file path
- [ ] 3-scope cascade: project-scope file overrides workflow-scope overrides global-scope, matched by filename stem
- [ ] Partial override: definition file with no content after closing `---` (only whitespace) inherits parent scope's body
- [ ] Partial override: frontmatter fields from child scope merge over parent scope's frontmatter
- [ ] Full override: any non-whitespace content after `---` replaces the parent body entirely
- [ ] Project-scope definition with `type: custom` → rejection with error identifying file path (FR-5a.05)
- [ ] Name collision (two files in same scope with same `name` frontmatter) → rejection of both with file paths (FR-5a.10)
- [ ] `AgentRegistry.build(name, ctx, definition=None)` builds a configured agent; `definition` param overrides lookup key (e.g., `build("PM_proj1", ctx, definition="pm")`)
- [ ] For `type: llm`: builds `LlmAgent` with model from `LlmRouter.select_model(model_role)`, tools from `GlobalToolset` for `tool_role`, instruction from `InstructionAssembler.assemble()`, `output_key` set on agent
- [ ] For `type: custom`: resolves `class` field via class registry dict, instantiates with `model_role` for hybrids and `instruction_body` if present
- [ ] Missing agent name (no definition in any scope) → raises error (FR-5a.09)
- [ ] Resolution auditability: builds a dict of `{agent_name: {scope, file_path, partial_override}}` and writes to session state key `agent_resolution_sources`
- [ ] Class registry: `dict[str, type[BaseAgent]]` mapping string names to Python CustomAgent types; populated via explicit registration
- [ ] Scan completes within 2 seconds for all global-scope definition files (NFR-5a.01); scan results cached for subsequent builds
- [ ] `pyright` passes with strict mode
**Validation:**
- `uv run pyright app/agents/_registry.py`
- `uv run pytest tests/agents/test_registry.py -v`

---

### P5a.D4: LLM Agent Definition Files
**Files:** `app/agents/director.md`, `app/agents/pm.md`, `app/agents/planner.md`, `app/agents/coder.md`, `app/agents/reviewer.md`, `app/agents/fixer.md`
**Depends on:** P5a.D3
**Description:** Author all 6 LLM agent definition files as markdown with YAML frontmatter. Each file defines the agent's identity, governance rules, tool_role, model_role, output_key, and instruction body. Director and PM definitions are configurations only — their supervision behavior (delegation, escalation, callbacks) is Phase 5b. Worker agents (planner, coder, reviewer, fixer) have complete instruction bodies for pipeline execution.
**BOM Components:**
- [ ] `A01` — Director agent (LlmAgent, opus)
- [ ] `A02` — PM agent (LlmAgent, sonnet)
- [ ] `A03` — Director agent definition file (`director.md`)
- [ ] `A04` — PM agent definition file (`pm.md`)
- [ ] `A20` — `planner` (LlmAgent, opus)
- [ ] `A21` — `coder` (LlmAgent, sonnet)
- [ ] `A22` — `reviewer` (LlmAgent, sonnet)
- [ ] `A23` — `fixer` (LlmAgent, sonnet)
**Requirements:**
- [ ] Each file has valid YAML frontmatter with required fields (name, description, type: llm)
- [ ] `director.md`: name=director, model_role=plan, tool_role=director, output_key=director_response. Body covers cross-project governance, CEO communication, PM delegation intent (wired in Phase 5b)
- [ ] `pm.md`: name=pm, model_role=plan, tool_role=pm, output_key=pm_response. Body covers project management, batch strategy, quality oversight, escalation protocol (wired in Phase 5b)
- [ ] `planner.md`: name=planner, model_role=plan, tool_role=planner, output_key=implementation_plan. Body instructs structured plan output consumable by coder, references `{current_deliverable_spec}` and `{loaded_skills}`
- [ ] `coder.md`: name=coder, model_role=code, tool_role=coder, output_key=code_output. Body instructs implementation from plan, references `{implementation_plan}` and `{loaded_skills}`
- [ ] `reviewer.md`: name=reviewer, model_role=review, tool_role=reviewer, output_key=review_result. Body instructs structured review (pass/fail with findings), references `{code_output}`, `{lint_results}`, `{test_results}`
- [ ] `fixer.md`: name=fixer, model_role=code, tool_role=fixer, output_key=code_output. Body instructs targeted fixes from review, references `{review_result}`. Note: output_key=code_output (overwrites coder's output — intentional for review cycle)
- [ ] All files parseable by AgentRegistry.scan() without errors
- [ ] All files buildable by AgentRegistry.build() into configured LlmAgent instances
- [ ] `{key}` placeholders in instruction bodies reference valid state keys that will exist at runtime
**Validation:**
- `uv run pytest tests/agents/test_registry.py -k "test_build_llm" -v`

---

### P5a.D5: Deterministic Custom Agents
**Files:** `app/agents/custom/skill_loader.py`, `app/agents/custom/memory_loader.py`, `app/agents/custom/linter.py`, `app/agents/custom/test_runner.py`, `app/agents/custom/formatter.py`, `app/agents/custom/regression_tester.py`, `app/agents/custom/__init__.py`, `app/agents/skill_loader.md`, `app/agents/memory_loader.md`, `app/agents/linter.md`, `app/agents/tester.md`, `app/agents/formatter.md`, `app/agents/regression_tester.md`
**Depends on:** P5a.D2, P5a.D3
**Description:** Implement 6 deterministic CustomAgent subclasses and their definition files. Each agent overrides `_run_async_impl`, reads upstream state, performs its operation, and writes results to session state via `Event(actions=EventActions(state_delta={...}))`. SkillLoaderAgent uses NullSkillLibrary (empty results). MemoryLoaderAgent uses InMemoryMemoryService (empty results, graceful degradation). Linter/TestRunner/Formatter execute configurable commands. RegressionTestAgent is defined and buildable but not integrated into batch execution (Phase 8).
**BOM Components:**
- [ ] `A30` — SkillLoaderAgent (CustomAgent)
- [ ] `A31` — LinterAgent (CustomAgent)
- [ ] `A32` — TestRunnerAgent (CustomAgent)
- [ ] `A33` — FormatterAgent (CustomAgent)
- [ ] `A35` — RegressionTestAgent (CustomAgent)
- [ ] `A37` — MemoryLoaderAgent (CustomAgent)
- [ ] `M15` — MemoryLoaderAgent (state.md cross-reference)
**Requirements:**
- [ ] All agents extend `BaseAgent` and override `_run_async_impl` with `# type: ignore[override]`
- [ ] All state writes use `yield Event(author=self.name, actions=EventActions(state_delta={...}))` — never direct `ctx.session.state["key"] = val`
- [ ] SkillLoaderAgent: queries `SkillLibraryProtocol.match_skills()`, writes `loaded_skills: {}` and `loaded_skill_names: []` with NullSkillLibrary
- [ ] MemoryLoaderAgent: queries `BaseMemoryService.search_memory()`, writes `memory_context: {}` and `memory_loaded: true` with InMemoryMemoryService
- [ ] MemoryLoaderAgent: on service error, writes `memory_context: {}`, `memory_loaded: false` and logs warning; does not raise
- [ ] LinterAgent: reads project config for linter command (default: `ruff check .`), runs via subprocess, writes structured `lint_results` (pass/fail, file locations, messages) and `lint_passed` (bool) to state
- [ ] TestRunnerAgent: reads project config for test command (default: `pytest`), runs via subprocess, writes structured `test_results` (pass/fail, test names, output) and `tests_passed` (bool) to state
- [ ] FormatterAgent: reads project config for formatter command (default: `ruff format .`), runs via subprocess, writes summary of changes to state
- [ ] RegressionTestAgent: defined with valid definition file and CustomAgent implementation; buildable by AgentRegistry; no pipeline integration (Phase 8)
- [ ] Each agent implementation ≤ 150 lines (NFR-5a.05)
- [ ] Each definition file has valid frontmatter with `type: custom` and `class` field matching the class registry key
- [ ] All agents registered in class registry in `_registry.py`
**Validation:**
- `uv run pyright app/agents/custom/`
- `uv run pytest tests/agents/test_custom_agents.py -v`

---

### P5a.D6: Hybrid Custom Agents
**Files:** `app/agents/custom/dependency_resolver.py`, `app/agents/custom/diagnostics.py`, `app/agents/dependency_resolver.md`, `app/agents/diagnostics.md`
**Depends on:** P5a.D5
**Description:** Implement 2 hybrid CustomAgent subclasses that combine deterministic control flow with internal LiteLLM calls for classification/synthesis. DependencyResolverAgent analyzes deliverable dependencies using graph resolution with LLM for ambiguous cases. DiagnosticsAgent reads lint/test results and synthesizes actionable diagnostics. Both route internal LLM calls through the LLM Router via model_role.
**BOM Components:**
- [ ] `A34` — DependencyResolverAgent (hybrid CustomAgent)
- [ ] `A36` — DiagnosticsAgent (hybrid CustomAgent)
**Requirements:**
- [ ] Both agents extend `BaseAgent`, override `_run_async_impl`, write results via `state_delta`
- [ ] DependencyResolverAgent: reads deliverable list from state, performs topological sort, uses internal `litellm.acompletion()` (routed via model_role through LlmRouter) for ambiguous dependency classification, writes dependency order to state
- [ ] DiagnosticsAgent: reads `lint_results` and `test_results` from state, aggregates findings deterministically, uses internal `litellm.acompletion()` for root-cause analysis, writes structured `diagnostics` to state
- [ ] Internal LiteLLM calls use `LlmRouter.select_model(model_role)` for model selection (FR-5a.34)
- [ ] Internal LiteLLM calls use the agent's `instruction_body` (from definition file) as system prompt for the internal call
- [ ] Both definition files have `type: custom`, `class` field, and `model_role` field
- [ ] Each implementation ≤ 150 lines (NFR-5a.05)
- [ ] Both agents registered in class registry
**Validation:**
- `uv run pyright app/agents/custom/dependency_resolver.py app/agents/custom/diagnostics.py`
- `uv run pytest tests/agents/test_hybrid_agents.py -v`

---

### P5a.D7: Context Budget Monitor
**Files:** `app/agents/context_monitor.py`
**Depends on:** —
**Description:** Implement the ContextBudgetMonitor (a `before_model_callback`) that token-counts the pending LLM request, writes usage percentage to session state, and raises `ContextRecreationRequired` when the configured threshold is exceeded. Also defines the `ContextRecreationRequired` exception class.
**BOM Components:**
- [ ] `CT04` — ContextBudgetMonitor (`before_model_callback`)
- [ ] `CT06` — ContextRecreationRequired exception
**Requirements:**
- [ ] `ContextRecreationRequired` is a custom exception (subclass of `Exception`, not `AutoBuilderError`) — it is a control flow signal, not an error
- [ ] `ContextBudgetMonitor` is a callable matching the `before_model_callback` signature: `(CallbackContext, LlmRequest) -> LlmResponse | None`
- [ ] Uses `litellm.token_counter(model, text)` to estimate token count of the pending request
- [ ] Compares estimate against model's context window limit from LiteLLM's `litellm.model_cost` registry
- [ ] Writes `context_budget_used_pct` (float, e.g., `73.2`) to session state via `callback_context.state`
- [ ] When usage exceeds configured threshold (default: 80%), raises `ContextRecreationRequired`
- [ ] Threshold configurable via `Settings` (new field `context_budget_threshold: int = 80`)
- [ ] Threshold outside 0–100 rejected at startup via Pydantic validator (FR-5a.45)
- [ ] When model's context window cannot be determined from LiteLLM, logs warning and uses 100,000 token default (FR-5a.46)
- [ ] Monitor adds ≤ 5ms overhead per call (NFR-5a.03) — no network I/O, just local token counting
- [ ] `pyright` passes with strict mode
**Validation:**
- `uv run pyright app/agents/context_monitor.py`
- `uv run pytest tests/agents/test_context_monitor.py -v`

---

### P5a.D8: Pipeline Composition & Worker Integration
**Files:** `app/agents/pipeline.py`, `app/workers/adk.py` (modify), `app/workers/tasks.py` (modify)
**Depends on:** P5a.D3, P5a.D4, P5a.D5, P5a.D6, P5a.D7
**Description:** Implement the DeliverablePipeline factory that composes all agents into a SequentialAgent with an embedded ReviewCycle (LoopAgent). Integrate with the existing worker infrastructure so `run_workflow` can execute a real deliverable through the full pipeline. Wire up the `compose_callbacks` chain (router override → context injection → budget monitor).
**BOM Components:**
- [ ] `A60` — DeliverablePipeline (SequentialAgent)
- [ ] `A61` — ReviewCycle (LoopAgent, max=3)
**Requirements:**
- [ ] `create_deliverable_pipeline(registry, ctx)` factory function returns a configured SequentialAgent
- [ ] Pipeline sequence: SkillLoaderAgent → MemoryLoaderAgent → planner → coder → FormatterAgent → LinterAgent → TestRunnerAgent → DiagnosticsAgent → ReviewCycle
- [ ] ReviewCycle is a LoopAgent with `max_iterations=3` containing: reviewer → fixer → LinterAgent (re-lint) → TestRunnerAgent (re-test)
- [ ] ReviewCycle terminates early when reviewer writes `review_passed: true` to state (termination mechanism per DD-6)
- [ ] When ReviewCycle reaches max iterations without approval, deliverable status is marked failed in state with final review findings preserved
- [ ] All agent outputs preserved in session state after pipeline completion (success or failure) — plan, code output, lint/test results, review findings, fix attempts
- [ ] Downstream agents read upstream output via `{key}` template injection in instructions or `context_from_state` in CustomAgents
- [ ] Pipeline wired into `run_workflow` task: when workflow params indicate a deliverable pipeline, the worker constructs and executes a DeliverablePipeline
- [ ] `compose_callbacks` chains: `create_model_override_callback` → context injection → `ContextBudgetMonitor`
- [ ] `before_model_callback` on all LLM agents in the pipeline uses the composed callback chain
- [ ] Pipeline catches `ContextRecreationRequired` at the top level (logs it; actual recreation is Phase 5b)
- [ ] Single deliverable executes end-to-end through the pipeline (validation: integration test with mocked LLM)
**Validation:**
- `uv run pyright app/agents/pipeline.py app/workers/adk.py app/workers/tasks.py`
- `uv run pytest tests/agents/test_pipeline.py tests/workers/ -v`
- `uv run ruff check . && uv run pyright && uv run pytest` (full quality gates — NFR-5a.04)

---

## Build Order

```
Batch 1 (parallel): P5a.D1, P5a.D2, P5a.D7
  D1: Database tables & migrations — app/db/models.py, migration
  D2: InstructionAssembler + state helpers — app/agents/assembler.py, protocols.py, state_helpers.py
  D7: Context budget monitor — app/agents/context_monitor.py

Batch 2 (sequential): P5a.D3
  D3: AgentRegistry — app/agents/_registry.py (depends on D2 assembler)

Batch 3 (parallel): P5a.D4, P5a.D5
  D4: LLM agent definition files — 6 .md files (depends on D3 registry)
  D5: Deterministic custom agents — 6 .py + 6 .md files (depends on D2, D3)

Batch 4 (sequential): P5a.D6
  D6: Hybrid custom agents — 2 .py + 2 .md files (depends on D5)

Batch 5 (sequential): P5a.D8
  D8: Pipeline composition + worker integration — pipeline.py, adk.py, tasks.py (depends on D3, D4, D5, D6, D7)
```

## Completion Contract Traceability

### FRD Coverage

| Capability | FRD Requirement | Deliverable(s) |
|---|---|---|
| CAP-1: Agent Definition & Registry | FR-5a.01 | P5a.D3 |
| *(same)* | FR-5a.02 | P5a.D3 |
| *(same)* | FR-5a.03 | P5a.D3 |
| *(same)* | FR-5a.04 | P5a.D3 |
| *(same)* | FR-5a.05 | P5a.D3 |
| *(same)* | FR-5a.06 | P5a.D3 |
| *(same)* | FR-5a.07 | P5a.D3 |
| *(same)* | FR-5a.08 | P5a.D3 |
| *(same)* | FR-5a.09 | P5a.D3 |
| *(same)* | FR-5a.10 | P5a.D3 |
| CAP-2: Instruction Composition | FR-5a.11 | P5a.D2 |
| *(same)* | FR-5a.12 | P5a.D2 |
| *(same)* | FR-5a.13 | P5a.D2 |
| *(same)* | FR-5a.14 | P5a.D2 |
| *(same)* | FR-5a.15 | P5a.D2 |
| *(same)* | FR-5a.16 | P5a.D2 |
| *(same)* | FR-5a.17 | P5a.D2 |
| *(same)* | FR-5a.18 | P5a.D2 |
| CAP-3: Worker Agents (LLM) | FR-5a.19 | P5a.D4, P5a.D8 |
| *(same)* | FR-5a.20 | P5a.D4, P5a.D8 |
| *(same)* | FR-5a.21 | P5a.D4, P5a.D8 |
| *(same)* | FR-5a.22 | P5a.D4, P5a.D8 |
| *(same)* | FR-5a.23 | P5a.D3, P5a.D4 |
| *(same)* | FR-5a.24 | P5a.D4, P5a.D8 |
| CAP-4: Worker Agents (Custom) | FR-5a.25 | P5a.D5 |
| *(same)* | FR-5a.26 | P5a.D5 |
| *(same)* | FR-5a.27 | P5a.D5 |
| *(same)* | FR-5a.28 | P5a.D5 |
| *(same)* | FR-5a.29 | P5a.D5 |
| *(same)* | FR-5a.30 | P5a.D5 |
| *(same)* | FR-5a.31 | P5a.D6 |
| *(same)* | FR-5a.32 | P5a.D6 |
| *(same)* | FR-5a.33 | P5a.D5 |
| *(same)* | FR-5a.34 | P5a.D6 |
| CAP-5: Pipeline Composition | FR-5a.35 | P5a.D8 |
| *(same)* | FR-5a.36 | P5a.D8 |
| *(same)* | FR-5a.37 | P5a.D8 |
| *(same)* | FR-5a.38 | P5a.D8 |
| *(same)* | FR-5a.39 | P5a.D8 |
| *(same)* | FR-5a.40 | P5a.D8 |
| *(same)* | FR-5a.41 | P5a.D2 |
| CAP-6: Context Budget Management | FR-5a.42 | P5a.D7 |
| *(same)* | FR-5a.43 | P5a.D7 |
| *(same)* | FR-5a.44 | P5a.D7 |
| *(same)* | FR-5a.45 | P5a.D7 |
| *(same)* | FR-5a.46 | P5a.D7 |
| Non-Functional | NFR-5a.01 | P5a.D3 |
| *(same)* | NFR-5a.02 | P5a.D2 |
| *(same)* | NFR-5a.03 | P5a.D7 |
| *(same)* | NFR-5a.04 | P5a.D8 (full gates) |
| *(same)* | NFR-5a.05 | P5a.D5, P5a.D6 |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| D05 | `ceo_queue` table | P5a.D1 |
| D08 | `project_configs` table | P5a.D1 |
| D16 | CEO queue migration | P5a.D1 |
| D19 | Project configs migration | P5a.D1 |
| V13 | CEO queue type enum | P5a.D1 |
| V14 | CEO queue priority enum | P5a.D1 |
| V15 | CEO queue status enum | P5a.D1 |
| V23 | `director_queue` table | P5a.D1 |
| V24 | `director_queue` migration | P5a.D1 |
| A52 | InstructionAssembler | P5a.D2 |
| A53 | InstructionFragment dataclass | P5a.D2 |
| A57 | Base instruction fragments (6 types) | P5a.D2 |
| A75 | SAFETY instruction fragment | P5a.D2 |
| A76 | InstructionContext container | P5a.D2 |
| A51 | `{key}` state template injection | P5a.D2 |
| M05 | State template injection | P5a.D2 |
| A54 | `context_from_state` helper | P5a.D2 |
| M06 | Project config loader | P5a.D2 |
| A43 | `before_model_callback` context injection | P5a.D2 |
| A55 | Agent definition files format | P5a.D3 |
| A56 | AgentRegistry class | P5a.D3 |
| A77 | Partial override | P5a.D3 |
| A78a | Project-scope type validation | P5a.D3 |
| A80 | Resolution auditability | P5a.D3 |
| A50 | `output_key` state communication | P5a.D3 |
| E02 | Agent tree construction | P5a.D3 |
| E03 | PM agent construction | P5a.D3 |
| A01 | Director agent (LlmAgent) | P5a.D4 |
| A02 | PM agent (LlmAgent) | P5a.D4 |
| A03 | Director definition file | P5a.D4 |
| A04 | PM definition file | P5a.D4 |
| A20 | planner (LlmAgent) | P5a.D4 |
| A21 | coder (LlmAgent) | P5a.D4 |
| A22 | reviewer (LlmAgent) | P5a.D4 |
| A23 | fixer (LlmAgent) | P5a.D4 |
| A30 | SkillLoaderAgent | P5a.D5 |
| A31 | LinterAgent | P5a.D5 |
| A32 | TestRunnerAgent | P5a.D5 |
| A33 | FormatterAgent | P5a.D5 |
| A35 | RegressionTestAgent | P5a.D5 |
| A37 | MemoryLoaderAgent | P5a.D5 |
| M15 | MemoryLoaderAgent (state.md ref) | P5a.D5 |
| A34 | DependencyResolverAgent | P5a.D6 |
| A36 | DiagnosticsAgent | P5a.D6 |
| CT04 | ContextBudgetMonitor | P5a.D7 |
| CT06 | ContextRecreationRequired exception | P5a.D7 |
| A60 | DeliverablePipeline (SequentialAgent) | P5a.D8 |
| A61 | ReviewCycle (LoopAgent) | P5a.D8 |

*48 BOM components, 48 mapped. Zero unmapped.*

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | InstructionAssembler composes agent instructions from typed fragments with source auditability | P5a.D2 | `pytest tests/agents/test_assembler.py` |
| 2 | AgentRegistry scans agent definition files (.md) and builds configured agents (LlmAgent and CustomAgent) with 3-scope file cascade | P5a.D3 | `pytest tests/agents/test_registry.py` |
| 3 | SAFETY fragment present in all assembled instructions, not overridable by project-scope or state | P5a.D2 | `pytest tests/agents/test_assembler.py -k safety` |
| 4 | Can run a single deliverable through the full DeliverablePipeline | P5a.D8 | `pytest tests/agents/test_pipeline.py -k integration` |
| 5 | Plan agent produces structured plan; code agent implements it | P5a.D4, P5a.D8 | `pytest tests/agents/test_pipeline.py -k "plan and code"` |
| 6 | Lint/test agents produce structured results in state | P5a.D5 | `pytest tests/agents/test_custom_agents.py -k "linter or test_runner"` |
| 7 | Review cycle loops on failure, terminates on approval or max iterations | P5a.D8 | `pytest tests/agents/test_pipeline.py -k review_cycle` |
| 8 | Context budget before_model_callback reports token usage percentage | P5a.D7 | `pytest tests/agents/test_context_monitor.py -k usage_pct` |
| 9 | Context budget monitor triggers context recreation (not lossy compaction) | P5a.D7 | `pytest tests/agents/test_context_monitor.py -k recreation` |
| 10 | MemoryLoaderAgent executes in pipeline; returns empty context in degraded mode | P5a.D5 | `pytest tests/agents/test_custom_agents.py -k memory_loader` |
| 11 | SkillLoaderAgent executes in pipeline via SkillLibraryProtocol; returns empty skills with NullSkillLibrary | P5a.D5 | `pytest tests/agents/test_custom_agents.py -k skill_loader` |
| 12 | Hybrid CustomAgents (DependencyResolver, DiagnosticsAgent) use LiteLLM internally with model_role routing | P5a.D6 | `pytest tests/agents/test_hybrid_agents.py` |
| 13 | Project-scope agent definitions rejected if type: custom | P5a.D3 | `pytest tests/agents/test_registry.py -k project_scope_custom_rejected` |

*13 contract items, 13 covered. Zero uncovered.*

## Research Notes

### ADK LoopAgent Termination
The implementer must verify the exact ADK `LoopAgent` termination API before implementing the ReviewCycle. Check `.dev/.knowledge/adk/` for:
1. Does `LoopAgent` support a `should_continue` callback or similar?
2. Does it check sub-agent state for a stop signal?
3. Is `escalate` from a sub-agent the termination mechanism?

If LoopAgent only supports `max_iterations`, the alternative is a `CustomAgent` wrapper that implements the review loop manually with explicit state checking.

### ADK before_model_callback State Writes
The `ContextBudgetMonitor` writes to `callback_context.state["context_budget_used_pct"]`. Verify in `.dev/.knowledge/adk/ERRATA.md` whether `callback_context.state` writes in `before_model_callback` persist or if they require a different mechanism than `state_delta`.

### LiteLLM Token Counter
`litellm.token_counter(model, text)` returns an int token count. It handles provider-specific tokenizers. No direct tiktoken/anthropic tokenizer dependency needed. Verify the import path: `from litellm import token_counter`.

### LiteLLM Model Cost Registry
`litellm.model_cost` is a dict mapping model strings to cost/context info. Access `litellm.model_cost[model]["max_input_tokens"]` for context window size. May raise `KeyError` for unknown models — handle with fallback default.

### Existing AGENT_ROLE_MAP in GlobalToolset
The existing `AGENT_ROLE_MAP` in `app/tools/_toolset.py` maps agent names to roles:
```python
AGENT_ROLE_MAP = {
    "plan_agent": "planner",
    "code_agent": "coder",
    "review_agent": "reviewer",
    "fix_agent": "fixer",
    "director": "director",
}
```
Phase 5a agent names differ (e.g., `planner` not `plan_agent`). The `AGENT_ROLE_MAP` must be updated or the `tool_role` from the definition file frontmatter should be used directly (preferred — eliminates the hardcoded map). The `resolve_role()` function in `GlobalToolset` should accept an explicit `tool_role` parameter.

### Definition File Parsing
YAML frontmatter is delimited by `---` on its own line. The body is everything after the closing `---`. Use a simple parser (split on `---`, parse first block as YAML, rest is body). Do not use a heavy library — `yaml.safe_load()` on the frontmatter block and string slicing for the body is sufficient.

### Custom Agent ADK Import
```python
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
```
Verify these import paths in `.dev/.knowledge/adk/` before implementation.

---

*Document Version: 1.0.0*
*Phase: 5a — Agent Definitions & Pipeline*
*Last Updated: 2026-03-11*
