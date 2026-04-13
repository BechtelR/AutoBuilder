[← Architecture Overview](../02-ARCHITECTURE.md)

# Agents

**AutoBuilder Platform**
**Agent Architecture Reference**

---

## Table of Contents

1. [Overview](#overview)
2. [Agent Hierarchy](#agent-hierarchy)
3. [Agent Definitions](#agent-definitions)
4. [Director Agent](#director-agent)
5. [PM Agent](#pm-agent)
6. [Execution Environment](#execution-environment)
7. [Worker-Tier LLM Agents](#worker-tier-llm-agents)
8. [Worker-Tier Custom Agents](#worker-tier-custom-agents)
9. [Context Management](#context-management)
10. [Plan/Execute Separation](#planexecute-separation)
11. [Agent Tool Restrictions](#agent-tool-restrictions)
12. [LLM Router](#llm-router)
13. [Agent Communication via Session State](#agent-communication-via-session-state)

---

## Overview

AutoBuilder uses a **three-tier hierarchical supervision model** (Director -> PM -> Workers) mapped to ADK's native agent tree. The CEO (human user) sits above the hierarchy but is not a tier -- the Director is the top-level agent. Within this hierarchy, two ADK primitives participate as equal workflow citizens:

| Agent Type | ADK Primitive | Execution Model | Examples |
|------------|---------------|-----------------|----------|
| **LLM Agents** | `LlmAgent` | Probabilistic -- ADK manages the LLM interaction loop | Director, PM, `planner`, `coder`, `reviewer`, `fixer` |
| **Custom Agents** | `CustomAgent` (inherits `BaseAgent`) | Deterministic control flow in `_run_async_impl`. Purely deterministic or **hybrid** (internal LLM calls via LiteLLM). | Deterministic: `SkillLoaderAgent`, `MemoryLoaderAgent`, `LinterAgent`, `TestRunnerAgent`, `FormatterAgent`, `RegressionTestAgent`. Hybrid: `DependencyResolverAgent`, `DiagnosticsAgent`. |

Pure LlmAgent and pure deterministic CustomAgent are two ends of a spectrum. Hybrid CustomAgents use LiteLLM calls inside `_run_async_impl` for specific reasoning steps while maintaining deterministic process flow. The `type` field in agent definitions is always `llm` or `custom` -- hybrid is a behavioral subcategory of `custom`, not a separate type.

Both types participate in the same state system, emit events into the same unified event stream, and compose naturally with ADK's `SequentialAgent`, `ParallelAgent`, and `LoopAgent` workflow primitives. This is the decisive architectural advantage of Google ADK over alternatives: deterministic agents are first-class workflow citizens, not shadow functions called outside the framework.

For FunctionTools (LLM-callable tool wrappers), see [Tools](./tools.md). The key distinction: tools are passive (LLM decides when to call them), agents are active (pipeline structure determines when they run).

Note: The worker-level examples below use auto-code agents (plan/code/lint/test/review). Other workflows define their own agent sets with the same patterns. The architecture is workflow-agnostic; the agent *roles* are workflow-specific.

---

## Agent Hierarchy

```
CEO (dev user / human)
  └── Director (LlmAgent, opus) — root_agent, stateless config, state in DB
        │     formation: {user:director_identity} + {user:ceo_profile} + {user:operating_contract}
        │     sessions: settings (formation) + chat (CEO interaction) + work (per-project oversight)
        │     delegation: transfer_to_agent → PM
        ├── PM: Project Alpha (LlmAgent, sonnet) — per-project, IS the outer loop
        │     ├── tools: select_ready_batch, escalate_to_director, update_deliverable, query_deliverables, reorder_deliverables, manage_dependencies (FunctionTools)
        │     ├── after_agent_callback: verify_batch_completion
        │     ├── checkpoint_project: `after_agent_callback` on DeliverablePipeline (persists state via CallbackContext)
        │     ├── run_regression_tests: `RegressionTestAgent` (CustomAgent) in pipeline after each batch (reads PM regression policy from session state)
        │     ├── transfers back to Director on batch completion or escalation
        │     └── sub_agents: DeliverablePipeline instances (workers)
        ├── PM: Project Beta (LlmAgent, sonnet)
        │     └── ...
        └── [cross-project agents as needed]
```

| Tier | Agent Type | Model | Role | Scope |
|------|-----------|-------|------|-------|
| **Director** | `LlmAgent` | opus | Cross-project governance, CEO liaison, strategic decisions, resource allocation | All projects, global settings |
| **PM** | `LlmAgent` | sonnet | Autonomous project management, batch strategy, quality oversight, worker supervision. IS the outer batch loop. | Single project |
| **Workers** | `LlmAgent` + `CustomAgent` (deterministic and hybrid) | varies | Execution -- planning, coding, reviewing, linting, testing, formatting, diagnostics | Single deliverable |

Each tier operates autonomously. Escalation is the exception, not the norm:
- **Workers** handle execution problems (lint failures, test failures, review feedback)
- **PMs** handle project problems (batch reordering, deliverable failures, retries, quality gate failures)
- **Director** handles cross-project problems (resource conflicts, priority shifts, pattern propagation)
- **CEO** handles only what Director truly cannot resolve (rare)

### How Workers Compose

```python
# Inner deliverable pipeline — declarative composition (worker-level)
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # CustomAgent — deterministic
        MemoryLoaderAgent(name="LoadMemory"),    # CustomAgent — deterministic
        planner,                                # LlmAgent
        coder,                                # LlmAgent
        LinterAgent(name="Lint"),                  # CustomAgent — deterministic
        TestRunnerAgent(name="Test"),               # CustomAgent — deterministic
        DiagnosticsAgent(name="Diagnostics"),      # CustomAgent — hybrid (LiteLLM internally)
        ReviewCycleAgent(                     # CustomAgent — replaces LoopAgent
            name="ReviewCycle",                 #   (LoopAgent terminates on escalate events,
            max_iterations=3,                   #    which LlmAgents cannot produce)
            sub_agents=[
                reviewer,                      # LlmAgent
                fixer,                         # LlmAgent
                LinterAgent(name="ReLint"),        # CustomAgent — deterministic
                TestRunnerAgent(name="ReTest"),     # CustomAgent — deterministic
            ]
        )
    ]
)
```

---

## Agent Definitions

Agents are defined as **markdown files with YAML frontmatter** (Decision #54). Frontmatter carries structured metadata. The markdown body is the agent's base instruction content (IDENTITY + GOVERNANCE fragments). No Python dataclasses -- the filesystem is the registry.

For **LlmAgents**, everything is data: the name, what model to use, what tools are available, what instructions to compose. ADK manages the full LLM interaction loop. The Director can influence any of these per-project through configuration and state.

For **CustomAgents (deterministic)**, the behavior is pure code (`_run_async_impl`). No LLM calls. The definition file registers them so the system knows they exist and maps `class` to a Python type, but their logic is fixed. Examples: `SkillLoaderAgent`, `MemoryLoaderAgent`, `LinterAgent`, `TestRunnerAgent`, `FormatterAgent`.

For **CustomAgents (hybrid)**, the outer behavior is code (`_run_async_impl`) with deterministic control flow, but specific steps make LLM calls via LiteLLM as an intelligence layer. The definition file uses `type: custom` (same as deterministic), maps `class` to a Python type, and optionally carries `model_role` (for LLM routing via LiteLLM) and a markdown body (instruction content consumed by the internal LLM calls, not by ADK's agent loop). Examples: `DependencyResolverAgent`, `DiagnosticsAgent`. Four common hybrid patterns:

1. **LLM input -> deterministic output** -- LLM analyzes input, agent enforces structured output
2. **LLM input -> LLM process -> deterministic output** -- multi-step LLM reasoning within deterministic guardrails
3. **Deterministic input -> LLM output** -- deterministic preparation, LLM synthesis
4. **Deterministic input -> LLM process -> deterministic output** -- deterministic framing, LLM reasoning, deterministic validation

### Agent Definition Files

Each agent is a single `.md` file. The filename (`{agent_name}.md`) is the discovery key for override resolution.

**LlmAgent example** -- `coder.md`:

```markdown
---
name: coder
description: Implement code according to plan using project conventions
type: llm
tool_role: coder
model_role: code_implementation
output_key: code_output
---

You are the Code Agent. You write production-quality code that follows
project conventions and passes all quality gates.

## Governance

- Never modify files outside the deliverable scope
- Escalate to PM if the plan is ambiguous or contradictory
- Always include error handling for I/O operations
```

**CustomAgent example** -- `linter.md`:

```markdown
---
name: linter
description: Run project linters and return structured diagnostics
type: custom
class: app.engine.agents.linter.LinterAgent
output_key: lint_results
---
```

Purely deterministic CustomAgent files have no body -- their behavior is entirely in `_run_async_impl`. The `class` field is a dotted path resolved by the class registry at build time.

**CustomAgent (hybrid) example** -- `dependency_resolver.md`:

```markdown
---
name: dependency_resolver
description: Resolve deliverable dependencies using topological sort with LLM-assisted ambiguity resolution
type: custom
class: app.engine.agents.dependency_resolver.DependencyResolverAgent
model_role: classification
output_key: dependency_order
---

When dependency relationships are ambiguous, analyze the deliverable descriptions
and infer implicit dependencies based on:
- Data flow (if A produces data that B consumes, A depends on B)
- API contracts (if A defines an interface that B implements, A should come first)
- Shared resources (if both modify the same file, serialize them)

Be conservative -- when unsure, declare a dependency rather than risk parallel conflicts.
```

**CustomAgent (hybrid) example** -- `diagnostics.md`:

```markdown
---
name: diagnostics
description: Analyze lint and test results to produce structured diagnostics with pattern detection
type: custom
class: app.engine.agents.diagnostics.DiagnosticsAgent
model_role: classification
output_key: diagnostics_analysis
---

Analyze the provided lint errors and test failures. Identify:
- Recurring patterns (same error type across files)
- Root causes vs symptoms (a missing import may cause cascading failures)
- Priority ordering (fix structural issues before style issues)

Output a structured analysis, not raw error lists.
```

Note the frontmatter is identical to deterministic CustomAgents (`type: custom`) -- the distinction is behavioral: the class uses LiteLLM internally for the analysis step. Hybrid agent files have a markdown body that provides instruction content for internal LLM calls made within `_run_async_impl`, not for ADK's agent loop. The `model_role` field routes the internal LLM calls through the same `LlmRouter` used by LlmAgents.

**Frontmatter field reference:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | yes | `str` | Canonical agent identity. Must match filename stem. |
| `description` | yes | `str` | Human-readable purpose. |
| `type` | yes | `llm` \| `custom` | Determines build path. Hybrid agents use `custom`. |
| `tool_role` | llm only | `str` | Maps to GlobalToolset for tool filtering. |
| `model_role` | llm required, custom optional | `str` | Maps to LlmRouter for model selection. Required for LlmAgents. Optional for hybrid CustomAgents (routes internal LiteLLM calls). |
| `output_key` | no | `str` | Session state key for agent output. |
| `class` | custom only | `str` | Dotted path to `BaseAgent` subclass (deterministic and hybrid). |

### Definition Cascade

Agent definitions follow a **3-scope file cascade** parallel to [Skills](./skills.md):

| Priority | Scope | Location | Author |
|----------|-------|----------|--------|
| 1 (lowest) | Global | `app/agents/` | AutoBuilder ships these |
| 2 | Workflow | `app/workflows/{name}/agents/` | Workflow-specific agents |
| 3 (highest) | Project | `{project}/.agents/agents/` | User or Director overrides |

**Override semantics: full replacement by name.** A project-scope `coder.md` replaces the global `coder.md` entirely -- no merge. This mirrors Skill override behavior.

**Partial override (frontmatter-only):** If a project-scope file contains only frontmatter (no markdown body after the closing `---`), it is treated as a partial override: its frontmatter fields merge over the parent scope's frontmatter, and the parent's body is inherited. This avoids copying entire instruction content to change a single field like `model_role`.

```markdown
# {project}/.agents/agents/coder.md -- partial override
---
name: coder
model_role: planning
---
```

This overrides only `model_role` -- identity, governance, tool_role, and output_key are inherited from the workflow or global scope.

**Resolution order:**

```
scan((global_dir, GLOBAL), (workflow_dir, WORKFLOW), (project_dir, PROJECT))
         ↓                        ↓                        ↓
      base set               override by               override by
                            filename match             filename match
```

Later scopes override earlier scopes. The final index maps each agent name to exactly one definition source.

**Director runtime influence** is a separate mechanism, not a fourth cascade scope. The Director writes governance and project fragments to session state, which the InstructionAssembler consumes at assembly time. This shapes agent behavior per-project without modifying definition files. See [§Instruction Composition](#instruction-composition) for fragment types.

**Scan timing:** Global and workflow scopes (deployment artifacts) are scanned at worker startup and cached. Project scope (user-mutable) is scanned per-invocation. Cache invalidation follows the same pattern as the [Skills library](./skills.md).

#### Project-Scope Restrictions

Project-scope definition files are user-mutable and therefore subject to security constraints:

- **`type: llm` only.** Project-scope files with `type: custom` are rejected at scan time. Arbitrary `class` paths from user-controlled directories are not loaded.
- **`tool_role` ceiling.** Project-scope `tool_role` must be within the workflow's permitted tool ceiling, validated against the workflow's `required_tools` + `optional_tools` in `WORKFLOW.yaml`. A project-scope override cannot grant tools that the workflow does not permit.
- **`model_role` unrestricted.** Users can choose their preferred model routing -- this affects cost and quality but not security.

### How Definitions Resolve

Resolution happens in two phases. At **build time**, `AgentRegistry.build()` resolves the definition into an ADK agent. At **runtime**, ADK resolves state templates just before each LLM call.

```
BUILD TIME (registry.build)                    RUNTIME (ADK per LLM call)
─────────────────────────                      ────────────────────────────
Agent Definition File                          Session State
  ├── model_role  → LlmRouter → model string     ├── {memory_context}   ← MemoryLoaderAgent
  ├── tool_role   → GlobalToolset → tool list     ├── {current_deliverable_spec} ← PM
  └── body        → InstructionAssembler          └── {key} templates resolved
                     ├── + PROJECT (DB)                 into final LLM prompt
                     ├── + TASK (state)
                     ├── + SKILL (loaded, filtered by applies_to)
                     └── → instruction string
                          (contains {key} placeholders)
```

| System | Input | Output | Details |
|--------|-------|--------|---------|
| **LlmRouter** | `model_role` (e.g. "planning") | LiteLLM model string | Routing rules + fallback chains. See [§LLM Router](#llm-router). |
| **GlobalToolset** | `tool_role` (e.g. "planner") | List of FunctionTools | Role-based filtering via ADK's `BaseToolset.get_tools()`. See [Tools](./tools.md). |
| **InstructionAssembler** | file body + runtime context | Composed instruction string | Fragment-based composition. See below. |

These are implementation details -- the agent definition doesn't know or care how they work. It just declares role strings.

`InstructionContext` is a lightweight container carrying the runtime data needed for assembly: project configuration (from DB), current deliverable spec (from session state), and loaded skills. It is created per invocation and passed through to all resolution systems. **Director and PM require separate `InstructionContext` instances** with independently resolved skill sets -- they must not share a single context, even when built in the same `build_work_session_agents()` call. Each tier's role-bound skills are resolved via `SkillLibrary.match()` with a tier-specific `SkillMatchContext`.

### Instruction Composition

All LLM agent instructions are composed from **typed fragments** by the `InstructionAssembler`. Each fragment has a category, content, and audit source:

```python
@dataclass
class InstructionFragment:
    fragment_type: str              # "safety", "identity", "governance", "project", "task", "skill"
    content: str
    source: str = ""                # Audit: where this came from

class InstructionAssembler:
    """Composes typed fragments into agent instructions. ~100 lines."""

    def assemble(self, agent_name: str, body: str, ctx: InstructionContext) -> str:
        """Assemble full instructions from file body + dynamic context + skills.
        SAFETY fragment is always prepended (hardcoded, non-overridable).
        The body provides IDENTITY + GOVERNANCE base content.
        Filters skills by applies_to per agent role."""
```

The assembler receives the file body directly during `assemble()` -- no `register_base()` step needed.

| Category | Source | Content | Lifecycle |
|----------|--------|---------|-----------|
| **SAFETY** | Hardcoded in InstructionAssembler | Core safety constraints, tool boundary enforcement, escalation protocol | Immutable, always prepended |
| **IDENTITY** | Agent definition file body | Role, persona, behavioral boundaries | Static per agent role |
| **GOVERNANCE** | Agent definition file body | Hard limits, escalation rules, safety constraints | Static per agent role |
| **PROJECT** | Database (project entity) | Coding standards, conventions, project-specific patterns | Dynamic per invocation |
| **TASK** | Session state | Current deliverable spec, implementation plan, review feedback | Dynamic per invocation |
| **SKILL** | SkillLoaderAgent output | Loaded skill content, filtered by `applies_to` per agent role | Dynamic per invocation |

Each fragment carries a `source` field for auditability -- you can trace exactly where every piece of an agent's instruction came from.

**Skill fragment vs state template:** The SKILL fragments composed by the assembler are role-filtered (via `applies_to`) and baked into the instruction at build time. The `{loaded_skills}` state template is NOT used for LLM agents -- it exists for CustomAgents that need programmatic access to loaded skill content. LLM agents receive skills exclusively through the assembler's SKILL fragments, avoiding duplication.

**`applies_to` filtering:** The `InstructionAssembler` filters loaded skills per-agent at assembly time using the `applies_to` metadata carried alongside skill content. For workers, `loaded_skills` in session state is a mapping of skill name to `{"content": ..., "applies_to": ...}` (written by `SkillLoaderAgent`). For Director/PM, skills are already in the `InstructionContext` from build-time resolution. In both cases, the assembler performs the same per-agent filtering: if a skill specifies `applies_to: [coder, reviewer]`, only those agents receive it. Skills without `applies_to` go to all agents.

**Constitutional safety layer:** The SAFETY fragment is hardcoded in the InstructionAssembler and cannot be overridden by any scope -- not by project-scope definition files, not by Director session state, not by skill content. It contains core safety constraints: no data exfiltration, respect tool boundaries, follow escalation protocol. This is distinct from the GOVERNANCE fragment in definition files, which carries agent-specific behavioral rules and CAN be overridden via the cascade. SAFETY is the floor; GOVERNANCE is the ceiling.

**Director influence:** The Director controls agent behavior per-project by writing governance and project fragments to session state. It doesn't rewrite prompts -- it shapes the fragments that the assembler composes.

#### Coexistence with ADK Layers

| Layer | Mechanism | Status |
|-------|----------|--------|
| Static instruction string | File body content (IDENTITY, GOVERNANCE) | Fed to assembler |
| Static assembled string | `InstructionAssembler.assemble()` (all 6 fragment types) | Produced by assembler, passed as `instruction=str` |
| `before_model_callback` | Unchanged -- heavyweight runtime injection (file contents, codebase analysis) | Coexists |
| `{key}` state templates | Unchanged -- direct state value injection within assembled output | Coexists |

#### What the Assembler Produces vs What ADK Resolves

The assembled instruction string contains `{key}` state template placeholders (e.g., `{memory_context}`, `{current_deliverable_spec}`). The assembler does NOT resolve these -- ADK resolves them at runtime from session state, just before each LLM call. This means state can be populated *after* the agent is built but *before* it runs. Note: skills are NOT injected via `{loaded_skills}` template -- they are composed directly into the instruction string as SKILL fragments by the assembler (see Skill fragment vs state template note above).

The assembler escapes literal curly braces in SKILL and PROJECT fragments (`{` -> `{{`, `}` -> `}}`) before composing the instruction string. Only explicitly declared state template references (e.g., `{memory_context}`, `{current_deliverable_spec}`) remain unescaped for ADK resolution. This prevents coding standards or skill content containing curly-brace syntax (common in Python, Rust, Go) from being misinterpreted as state templates.

The pipeline populates state in execution order before LLM agents read it:

```
SkillLoaderAgent    → state["loaded_skills"]         # deterministic, runs first
MemoryLoaderAgent   → state["memory_context"]         # searches MemoryService
PM writes           → state["current_deliverable_spec"]  # from batch selection
```

LLM agents consume these via `{key}` templates in their assembled instructions. See [§Agent Communication via Session State](#agent-communication-via-session-state) for the full pipeline data flow.

#### Callbacks

Agent definition files do not carry callbacks. Callbacks are wired in Python — either in `pipeline.py` via `registry.build()` overrides or directly on structural agents:

- `before_model_callback` on LlmAgents: context budget monitor, system reminders (see [§Context Management](#context-management))
- `after_agent_callback` on pipeline agents: `verify_batch_completion`, `checkpoint_project`

These are infrastructure concerns, not agent identity — they belong in code, not in definition files.

### AgentRegistry

The registry scans directories for `.md` agent definition files, indexes them by frontmatter, and builds ADK agents on demand. Shared across all workflows.

The registry index is rebuilt per-pipeline. `scan()` is called with exactly the relevant directories for the current workflow: `scan((global_dir, GLOBAL), (workflow_agents_dir, WORKFLOW), (project_dir, PROJECT))`. Agents from other workflows are not in the index.

```python
class AgentRegistry:
    """Scans agent definition files, builds ADK agents. ~60 lines."""

    def __init__(self, assembler: InstructionAssembler, router: LlmRouter, toolset: GlobalToolset):
        self._index: dict[str, AgentFileEntry] = {}  # name → parsed file entry
        self._class_registry: dict[str, type] = {}   # dotted path → BaseAgent subclass
        self._assembler = assembler
        self._router = router
        self._toolset = toolset

    def scan(self, *dirs: tuple[Path, DefinitionScope]) -> None:
        """Scan directories for .md agent definition files.
        3-scope cascade: GLOBAL → WORKFLOW → PROJECT.
        Later scopes override earlier by filename match.
        Parses frontmatter and body eagerly — full file read at scan time.
        parse_agent_file() validates that frontmatter `name` matches the filename stem;
        mismatch raises an error at scan time. Invalid files are skipped with a warning log."""
        for dir_path, scope in dirs:
            for f in dir_path.glob("*.md"):
                entry = parse_agent_file(f)  # raises on name/filename mismatch
                self._index[entry.name] = entry

    def build(self, name: str, ctx: InstructionContext, *, definition: str | None = None, **overrides) -> BaseAgent:
        """Resolve a definition file into a running ADK agent.
        name: the ADK agent name (can be dynamic, e.g., 'PM_alpha').
        definition: the definition file to look up (defaults to name).
        Raises AgentNotFoundError (not KeyError) with available names and scan dirs."""
        key = definition or name
        if key not in self._index:
            raise AgentNotFoundError(key, available=list(self._index.keys()))
        entry = self._index[key]
        if entry.type == "custom":
            cls = self._class_registry[entry.class_ref]
            # Warning logged if overrides are passed — CustomAgents ignore them.
            # Hybrid CustomAgents receive model_role and body for internal LLM calls.
            return cls(
                name=name,
                model_role=entry.model_role,       # None for purely deterministic
                instruction_body=entry.body,        # None for purely deterministic
            )
        # Permitted overrides: sub_agents, before_model_callback, after_model_callback,
        # before_agent_callback, after_agent_callback. Do NOT override instruction/model/tools.
        return LlmAgent(
            name=name,
            model=self._router.select_model(entry.model_role),
            instruction=self._assembler.assemble(name, entry.body, ctx),
            tools=self._toolset.get_tools_for_role(entry.tool_role),
            output_key=entry.output_key,
            **overrides,
        )
```

The `_class_registry` maps dotted path strings from the `class` frontmatter field to actual Python types. It is populated via explicit manual registration in `_registry.py` — a dict literal mapping class names to imported types. This is the security allowlist; only pre-registered classes can be instantiated from definition files.

**Resolution auditability:** `build()` logs the resolution source (scope + file path) for each agent to the event stream. The resolution map is also written to session state at `agent_resolution_sources` for diagnostic inspection.

### Agent Tree Construction

The agent tree is built per invocation using the registry. All agents are **stateless config** -- recreated each time. Continuity lives in the database via `DatabaseSessionService`.

```python
def build_agent_tree(registry: AgentRegistry, project_ids: list[str], ctx: InstructionContext) -> LlmAgent:
    """Recreate agent tree from registry + runtime context. Stateless --
    all continuity is in the ADK session (DB-backed)."""
    pms = [registry.build(f"PM_{pid}", ctx, definition="pm", sub_agents=[]) for pid in project_ids]
    return registry.build("director", ctx, sub_agents=pms)
```

### File vs Code Split

| In Definition Files (.md) | In Python Code |
|---------------------------|----------------|
| Agent identity and governance instructions (LlmAgent + hybrid CustomAgent body) | `CustomAgent._run_async_impl` logic (deterministic and hybrid -- hybrid agents make LiteLLM calls within this method) |
| Metadata: model_role, tool_role, output_key | Pipeline composition (Sequential/Parallel/Loop) |
| Description and discovery info | Callback functions (before/after agent/model) |
| CustomAgent class reference (dotted path) | Tool implementations |
| | `build_agent_tree()` orchestration |

The definition file format is identical for deterministic and hybrid CustomAgents (`type: custom`). Hybrid agents simply have a `model_role` field and a markdown body consumed by internal LiteLLM calls. Pipeline composition stays in code because ADK structural primitives (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) are programmatic -- they wire agents together, not configure them.

---

## Director Agent

The Director is the `root_agent` of the ADK `App`. It is **stateless config** -- the agent definition is pure configuration, recreated per invocation. All continuity lives in the database via `DatabaseSessionService`. This pattern is consistent across all tiers (Director, PM, Workers).

| Property | Value |
|----------|-------|
| **Role** | Cross-project governance (COO) + CEO-adapted personal assistant. Acts as both. |
| **ADK Type** | `LlmAgent` |
| **Model** | `anthropic/claude-opus-4-6` (strategic reasoning requires strongest model) |
| **Scope** | All projects, global settings |
| **Lifecycle** | Stateless config, recreated per invocation. All state in DB. |
| **Sub-agents** | PM agents (one per active project), cross-project utility agents |
| **Delegation** | `transfer_to_agent` to hand off projects to PMs |

### Director Identity & Formation

The Director's personality emerges from a dedicated **Settings conversation** between the CEO and Director. Three structured artifacts in `user:` scope define the working relationship. Different CEO logins get different artifacts -- the Director adapts to each user.

| Artifact | State Key | Content | Mutability |
|----------|-----------|---------|------------|
| **Director Identity** | `user:director_identity` | Name (optional), personality traits, communication style, working metaphor, decision approach, team management philosophy | CEO edits via Settings conversation or any chat; Director proposes changes via CEO queue |
| **CEO Profile** | `user:ceo_profile` | Name, working style, communication preferences, domain expertise, collaboration patterns, autonomy comfort, decision-making style, strengths to leverage | Formation conversation; Director proposes updates (approved via CEO queue) |
| **Operating Contract** | `user:operating_contract` | Proactivity level, escalation sensitivity, decision-making autonomy, feedback style, notification preferences, working hours, when to push back, when to just execute | Formation conversation; user settings; Director proposes adjustments |

**Formation flow:**

1. First system access → Settings session auto-created (like "Main")
2. Director detects empty artifacts (`user:formation_status` == `PENDING`) → enters formation mode
3. Conversational exchange (~5-10 professional but warm questions) exploring CEO preferences, desired Director personality, working style, collaboration norms
4. Director proposes structured artifact values → CEO approves/edits in conversation
5. Artifacts written to `user:` scope → available across all sessions and projects; `formation_status` set to `COMPLETE`

**Instruction template integration:** Each artifact maps to a natural InstructionAssembler fragment type:
- `{user:director_identity}` → IDENTITY fragment (who the Director is for this user)
- `{user:ceo_profile}` → PROJECT fragment (user context available to all project work)
- `{user:operating_contract}` → GOVERNANCE fragment (behavioral parameters)

The Director's agent definition file provides the **static base** (role, capabilities, behavioral framework -- same for every user). The formation artifacts **augment** that base with per-user personalization via template injection.

**Formation state:** `user:formation_status` tracks progress: `PENDING` → `IN_PROGRESS` → `COMPLETE`. When not `COMPLETE`, the Director enters formation mode in Settings sessions. When `COMPLETE`, the Settings session becomes an evolution conversation where either party can propose changes.

**Artifact update proposals:** The Director can propose artifact updates from **any** conversation (not just Settings). Proposals go through the CEO queue as `APPROVAL` type items. The CEO resolves in the queue or navigates to the Settings session to discuss further.

**Reset:** CEO can request formation reset in the Settings session. Director clears the three artifact keys and `user:formation_status`, then re-enters formation mode on the next message.

**Storage:** Database only -- artifacts persist in `user:` scope state via DatabaseSessionService (PostgreSQL). No file export/import. Consistent with "all persistence through gateway API" constraint.

### Session Model

The Director operates via **multiple sessions**:

| Session Type | Purpose | Lifecycle |
|-------------|---------|-----------|
| **Settings session** | Director formation and relationship evolution | One per user, permanent, auto-created on first access |
| **Chat session** | CEO interaction (conversation, commands, status queries) | Created per conversation, multiple per project |
| **Work session** | Background project oversight (monitoring, intervention) | One per project, long-lived |

A "Main" project acts as the permanent default -- the Director's home context. Multiple chat sessions can exist per project. The Settings session is user-scoped (not project-scoped) and always available.

### Capabilities

- **Full observability** into all active projects via event stream and supervision hooks
- **Direct intervention** in any project when patterns go wrong
- **Multi-level memory** accumulation (standards, project patterns, CEO preferences)
- **Hard limit enforcement** -- sets per-project resource limits (cost, time, concurrency)
- **Intelligent escalation** -- decides when to pause for CEO input (rare, due to accumulated memory)
- **Cross-project pattern propagation** -- learnings from one project inform others
- **Tool authoring** -- Director can create new tools; CEO approval required by default
- **Tools and skills** -- governance tools, resource management FunctionTools, governance policies and global convention skills. Director receives role-bound skills at **build time** via `SkillLibrary.match()` with `agent_role="director"` -- not at pipeline runtime. Skills with `always` trigger + `applies_to: [director]` are part of the Director's operational identity across all session types.

### Director Tools

| Tool | Purpose |
|------|---------|
| `validate_brief` | Validate a CEO brief against workflow requirements (Decision D10) |
| `create_project` | Create a new project record bound to a workflow type (Decision D10) |
| `check_resources` | Verify resource availability before execution (Decision D10) |
| `delegate_to_pm` | Delegate a project to a PM for execution (Decision D10) |
| `escalate_to_ceo` | Push items to CEO queue (Director-only) |
| `list_projects` | Cross-project visibility |
| `query_project_status` | PM status, batch progress, cost |
| `override_pm` | Direct PM intervention (pause/resume/reorder/correct) |
| `get_project_context` | Detect project type, stack, conventions |
| `query_dependency_graph` | Query/visualize dependency graph |

### Director Override Mechanism

`override_pm` enables the Director to directly intervene in PM operations: pause execution, resume paused projects, reorder deliverable priority, or correct PM strategy. All overrides are logged to the event stream for audit. The Director uses this when PM behavior deviates from expectations or when cross-project concerns require coordinated changes.

### ADK Integration

```python
# Simplified for illustration; actual construction via AgentRegistry.build()
director_agent = LlmAgent(
    name="Director",
    model="anthropic/claude-opus-4-6",
    instruction="Cross-project governance agent. {user:director_identity} "
                "{user:ceo_profile} {user:operating_contract} "
                "Manage PMs via transfer_to_agent, allocate resources, "
                "enforce hard limits, intervene when patterns go wrong.",
    tools=[
        FunctionTool(validate_brief),
        FunctionTool(create_project),
        FunctionTool(check_resources),
        FunctionTool(delegate_to_pm),
        FunctionTool(escalate_to_ceo),
        FunctionTool(list_projects),
        FunctionTool(query_project_status),
        FunctionTool(override_pm),
        FunctionTool(get_project_context),
        FunctionTool(query_dependency_graph),
    ],
    sub_agents=[pm_alpha, pm_beta],
)
```

---

## PM Agent

PMs are per-project autonomous managers. They use LLM reasoning (not programmatic orchestration) to manage the outer batch loop -- selecting batches, supervising workers, and handling failures. Like the Director, PMs are **stateless config** -- recreated per invocation, all continuity in DB via `DatabaseSessionService`.

| Property | Value |
|----------|-------|
| **Role** | Autonomous project management, batch strategy, quality oversight, worker supervision. IS the outer batch loop. |
| **ADK Type** | `LlmAgent` |
| **Model** | `anthropic/claude-sonnet-4-6` (project management reasoning) |
| **Scope** | Single project |
| **Lifecycle** | Stateless config, recreated per invocation. Session continuity in DB. Consistent with Director tier. |
| **Tools** | `select_ready_batch`, `escalate_to_director`, `update_deliverable`, `query_deliverables`, `reorder_deliverables`, `manage_dependencies` (FunctionTools) |
| **`after_agent_callback`** | `verify_batch_completion` (automatic, after every deliverable) |
| **Checkpoint** | `checkpoint_project` -- `after_agent_callback` on DeliverablePipeline; fires after each deliverable completes, persists state via `CallbackContext` |
| **Regression** | `run_regression_tests` -- `RegressionTestAgent` (CustomAgent) wired into pipeline after each batch; reads PM regression policy from session state, runs tests when policy says to, no-ops otherwise; always present (not skippable), policy-aware |
| **Sub-agents** | `DeliverablePipeline` instances (workers) |
| **Parent** | Director (via `transfer_to_agent` delegation). PM transfers back to Director on batch completion or escalation. |

### PM Skills

The PM receives role-bound skills at **build time** via `SkillLibrary.match()` with `agent_role="pm"` -- not at pipeline runtime via `SkillLoaderAgent`. Skills with `always` trigger + `applies_to: [pm]` load for every PM invocation. The PM's `InstructionContext` is separate from the Director's -- each tier gets independently resolved skills even when built in the same work session (see [Skills: Supervision-Tier Skill Resolution](./skills.md#supervision-tier-skill-resolution)).

### Why LlmAgent, Not CustomAgent

PMs need LLM reasoning to:
- Decide batch strategy based on project context
- Handle unexpected failures without escalating every issue to Director
- Reorder deliverables based on discovered dependencies
- Assess quality gate failures and decide retry vs. escalate vs. skip
- Reason between batches -- a mechanical loop cannot adapt strategy based on emergent patterns

### Director-PM Delegation

PMs are Director's `sub_agents`. The Director uses `transfer_to_agent` for "go manage this project" handoff -- the PM receives full control and transfers back to Director on batch completion or escalation. `transfer_to_agent` (not `AgentTool`, which forces synchronous execution, or a declarative tree, which removes Director reasoning about when/how to delegate).

### PM as the Outer Loop

The PM manages the batch execution loop directly, rather than delegating to a separate orchestrator agent. Batch composition is a FunctionTool (PM reasons about what to include). Checkpointing and regression testing are **not** LLM-discretionary -- they fire automatically per policy (not skippable):

| When | Mechanism | How |
|------|-----------|-----|
| Before batch | PM (LLM) | Reasons about batch composition via `select_ready_batch` FunctionTool, sets strategy |
| During batch | `after_agent_callback` | `verify_batch_completion` monitors each pipeline, flags critical failures |
| After deliverable | `after_agent_callback` on DeliverablePipeline | `checkpoint_project` -- fires after each deliverable completes, persists state via `CallbackContext` |
| After batch | `RegressionTestAgent` (CustomAgent) in pipeline | `run_regression_tests` -- reads PM regression policy from session state, runs tests when policy says to, no-ops otherwise; always present, policy-aware |
| Between batches | PM (LLM) | Full reasoning -- reorder, adjust, escalate to Director via `transfer_to_agent` |

### ADK Integration

```python
# Simplified for illustration; actual construction via AgentRegistry.build()
pm_alpha = LlmAgent(
    name="PM_ProjectAlpha",
    model="anthropic/claude-sonnet-4-6",
    instruction="Autonomous project manager for Project Alpha. You ARE the outer batch loop. "
                "Use select_ready_batch to pick work, supervise DeliverablePipeline workers, "
                "and escalate only when you cannot resolve an issue. "
                "Transfer back to Director on batch completion or escalation.",
    tools=[
        FunctionTool(select_ready_batch),
        FunctionTool(escalate_to_director),
        FunctionTool(update_deliverable),
        FunctionTool(query_deliverables),
        FunctionTool(reorder_deliverables),
        FunctionTool(manage_dependencies),
    ],
    sub_agents=[],  # DeliverablePipeline instances added dynamically per batch
    after_agent_callback=verify_batch_completion,
    # checkpoint_project: after_agent_callback on DeliverablePipeline
    #   Fires after each deliverable completes, persists state via CallbackContext.
    # run_regression_tests: RegressionTestAgent (CustomAgent) in pipeline after each batch
    #   Reads PM regression policy from session state. Runs when policy says to, no-ops otherwise.
    #   Always present in pipeline (not skippable), policy-aware.
)
```

### Hard Limits Cascade

```
CEO sets global limits → Director operates within globals, sets per-project limits
Director sets project limits → PM operates within project limits
PM sets worker constraints → Workers execute within constraints
```

---

## Execution Environment

**Agents run inside ARQ worker processes, not the FastAPI gateway.**

The gateway is responsible for API routes, job enqueueing, and SSE streaming. Workers are responsible for ADK pipeline execution. This separation means:

- **All agent code executes in worker context.** LLM agents, deterministic agents, and the FunctionTools they invoke all run inside worker processes. The gateway never instantiates or runs agents directly.
- **Agents have filesystem access in the worker environment.** Tools like `file_write`, `bash_exec`, and `git_commit` operate on the worker's filesystem (git worktrees for parallel isolation).
- **State flows through the database.** Workers read/write session state via `DatabaseSessionService` backed by the shared database (SQLAlchemy 2.0 async).
- **Events flow through Redis Streams.** Agent events are published to Redis Streams for consumption by SSE endpoints, webhook dispatchers, and audit loggers.
- **The gateway enqueues workflow jobs.** A client request to run a workflow results in an ARQ job being enqueued. A worker picks up the job and executes the ADK pipeline.

```
Client --> Gateway (FastAPI)
             |
             | enqueue job
             v
           Redis (ARQ queue)
             |
             | dequeue + execute
             v
           Worker (ARQ)
             |
             | runs ADK pipeline
             v
           Agents + Tools
             |
             | publish events
             v
           Redis Streams --> SSE / Webhooks / Audit
```

This architecture means agents are unaware of the gateway. They interact with state (database), events (Redis Streams), and the filesystem -- all accessible from the worker process. The anti-corruption layer between the gateway and ADK ensures that ADK is a swappable internal engine, not an exposed surface.

---

## Worker-Tier LLM Agents

Worker-tier LLM Agents handle execution tasks that require reasoning, creativity, and judgment. Each agent has a distinct role, instruction set, tool subset, and model assignment. These agents operate under PM supervision within a project's `DeliverablePipeline` structure.

### planner (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Decompose a deliverable specification into a structured implementation plan |
| **Input** | `{current_deliverable_spec}`, `{memory_context}`, `{app:coding_standards}` + SKILL fragments (via assembler) |
| **Output** | `output_key: "implementation_plan"` |
| **Model** | `anthropic/claude-opus-4-6` (planning benefits from strongest reasoning) |
| **Tool Access** | Read-only -- filesystem read, directory list, search. No write tools. |

The plan agent reads the deliverable specification, cross-session memory context, and project coding standards from session state. Skills are injected as SKILL fragments by the InstructionAssembler (filtered by `applies_to`). It produces a structured implementation plan that the code agent consumes. It never writes code or modifies files.

### coder (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Implement code according to the plan, using project conventions from skills |
| **Input** | `{implementation_plan}`, `{app:coding_standards}` + SKILL fragments (via assembler) |
| **Output** | `output_key: "code_output"` |
| **Model** | `anthropic/claude-sonnet-4-6` (standard complexity) or `anthropic/claude-opus-4-6` (complex architecture) |
| **Tool Access** | Full -- filesystem read/write/edit, bash execution, git operations |

The code agent consumes the structured plan and writes implementation code. Model selection is handled dynamically by the LLM Router based on task complexity. The code agent has full write access to the filesystem within its git worktree.

### reviewer (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Evaluate code quality against project standards, lint results, test results, and diagnostics |
| **Input** | `{code_output}`, `{lint_results}`, `{test_results}`, `{diagnostics_analysis}` + SKILL fragments (via assembler) |
| **Output** | `output_key: "review_result"` |
| **Model** | `anthropic/claude-sonnet-4-6` |
| **Tool Access** | Read-only -- filesystem read, directory list, search. No write tools. |

The review agent reads the code output alongside lint and test results written to state by deterministic agents. It evaluates quality and either approves the deliverable or produces structured feedback for the fix agent. If the review fails, the `ReviewCycleAgent` wrapper triggers another fix/lint/test/review cycle (up to `max_iterations`).

### fixer (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Apply targeted fixes based on review feedback |
| **Input** | `{review_result}`, `{code_output}`, `{lint_results}`, `{test_results}` |
| **Output** | `output_key: "code_output"` (overwrites previous code output) |
| **Model** | `anthropic/claude-sonnet-4-6` |
| **Tool Access** | Full -- filesystem read/write/edit, bash execution |

The fix agent receives structured review feedback and applies targeted corrections. It operates within the `ReviewCycleAgent` review cycle, iterating until the review agent approves or `max_iterations` is reached.

---

## Worker-Tier Custom Agents

Worker-tier Custom Agents inherit from ADK's `BaseAgent` and implement `_run_async_impl`. They execute guaranteed workflow steps that must not be skippable by LLM judgment. Each emits events into the unified event stream and writes results to session state. Custom Agents are either **purely deterministic** (no LLM calls) or **hybrid** (deterministic process flow with internal LLM calls via LiteLLM).

The `SkillLoaderAgent` is shared across all workflows at worker level. Other Custom Agents are workflow-specific -- auto-code uses LinterAgent and TestRunnerAgent; other workflows define their own gates appropriate to their output type.

Like all agents, Custom Agents execute inside worker processes. Their subprocess calls (linter, test runner, formatter) and any internal LiteLLM calls have access to the worker's filesystem and environment.

### SkillLoaderAgent (deterministic, workers only)

**Purpose:** Resolve and load relevant skills into session state as the first step in every `DeliverablePipeline`.

Matches skills against current deliverable context using deterministic pattern matching (no LLM call). Writes matched skill content (with `applies_to` metadata) to state so the `InstructionAssembler` can filter per-agent at assembly time.

`SkillLoaderAgent` runs **only in worker-tier pipelines**. Director and PM receive their skills at agent build time via direct `SkillLibrary.match()` calls -- see [Skills: Supervision-Tier Skill Resolution](./skills.md#supervision-tier-skill-resolution).

```python
class SkillLoaderAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        matched = skill_library.match(context_from_state(ctx))
        loaded = [skill_library.load(entry) for entry in matched]
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": {
                    s.entry.name: {"content": s.content, "applies_to": s.entry.applies_to}
                    for s in loaded
                },
                "loaded_skill_names": [s.entry.name for s in loaded],
            })
        )
```

**Why a CustomAgent instead of a tool:** Skill resolution must be observable in the event stream, deterministic (cannot be skipped by LLM judgment), and load skills into state once for all subsequent agents. A FunctionTool would be LLM-discretionary.

### MemoryLoaderAgent (deterministic)

**Purpose:** Search the MemoryService for cross-session context relevant to the current deliverable and load it into session state.

Runs immediately after SkillLoaderAgent as the second step in every deliverable pipeline. Queries the memory service using deliverable context (project, workflow, deliverable spec) and writes retrieved memory fragments to state so all subsequent agents can access cross-session learnings.

| State Write | Value |
|-------------|-------|
| `memory_context` | Retrieved memory fragments relevant to the current deliverable |

If the MemoryService is unavailable, the agent writes an empty `memory_context` and logs a warning -- it does not halt the pipeline.

### LinterAgent (deterministic)

**Purpose:** Run the project linter against generated code and write structured results to session state.

| State Write | Value |
|-------------|-------|
| `lint_results` | Structured lint output (errors, warnings, file locations) |
| `lint_passed` | Boolean pass/fail |

The review agent reads `{lint_results}` to evaluate code quality. If lint fails, the fix agent receives the errors as actionable feedback.

### TestRunnerAgent (deterministic)

**Purpose:** Run the project test suite against generated code and write structured results to session state.

| State Write | Value |
|-------------|-------|
| `test_results` | Structured test output (passed, failed, errors, coverage) |
| `tests_passed` | Boolean pass/fail |

### FormatterAgent (deterministic)

**Purpose:** Run the project code formatter (e.g., Black, Prettier) on generated code. Unlike lint, formatting is auto-corrective -- it modifies files directly. Runs after coder and before linter in the pipeline (omitted from the simplified pipeline example in [§How Workers Compose](#how-workers-compose) for brevity).

### DependencyResolverAgent (hybrid)

**Purpose:** Perform topological sorting of deliverables based on their declared dependencies. Determines which deliverables can execute in parallel and which must wait for predecessors.

This agent runs once before the batch loop begins. It writes the sorted deliverable execution order to session state, which the PM reads (via `select_ready_batch` tool) to construct batches. The topological sort is deterministic; when dependency relationships are ambiguous (e.g., implicit data flow between deliverables), the agent uses an internal LiteLLM call to classify the relationship before enforcing a deterministic ordering.

### DiagnosticsAgent (hybrid)

**Purpose:** Analyze lint errors and test failures to produce structured diagnostics with pattern detection. Takes deterministic inputs (lint_results, test_results), uses an internal LiteLLM call to identify recurring patterns, root causes vs symptoms, and priority ordering, then outputs a structured analysis to session state.

| State Write | Value |
|-------------|-------|
| `diagnostics_analysis` | Structured analysis (patterns, root causes, priority ordering) |

This is a pattern 4 hybrid agent: deterministic input -> LLM process -> deterministic output. The LLM reasoning is bounded by the structured input and validated output schema.

### Regression Testing (`run_regression_tests`) (deterministic)

**Purpose:** Run cross-deliverable regression tests after each batch completes. Ensures that newly implemented deliverables have not broken previously completed deliverables.

Implemented as `RegressionTestAgent` (CustomAgent, inherits `BaseAgent`). Wired into the pipeline after each batch (after `ParallelAgent` completes), not at the individual deliverable level. Always present in the pipeline -- cannot be skipped by LLM judgment. Reads the PM's regression policy from session state (`regression_policy`). When the policy says to run (e.g., every batch, every N deliverables, on specific triggers), executes the cross-deliverable regression suite and writes results to state. When the policy says to skip, no-ops (yields a state_delta recording the skip). This is a substantial operation involving cross-deliverable test execution and result analysis.

---

## Context Management

Long-running sessions require two runtime mechanisms to manage agent context effectively:

- **Context Recreation** (Decision #52) -- when the context window fills up, the session is recreated losslessly: persist progress to memory, seed critical state keys into a fresh session, reassemble instructions via `InstructionAssembler` + `SkillLoaderAgent` + `MemoryLoaderAgent`. Superior to lossy summarization. The `context_budget_monitor` (`before_model_callback`) tracks token usage and triggers recreation at threshold. ADK's `EventsCompactionConfig` remains as a fallback safety net.

- **System Reminders** (Decision #53) -- ephemeral governance nudges (token budget warnings, state change notifications, progress notes) injected via `before_model_callback`. Soft nudges only -- hard governance lives in IDENTITY and GOVERNANCE instruction fragments. Acceptable to lose during context recreation.

For the full context lifecycle -- assembly, budgeting, recreation, and knowledge loading -- see [context.md](./context.md).

---

## Plan/Execute Separation

Planning agents never write code; execution agents consume structured plans.

This follows the oh-my-opencode Prometheus/Atlas pattern: strict role boundaries between planning and execution scale effectively across specialized agent teams.

### How It Works in AutoBuilder

```
planner (LLM)          coder (LLM)
  |                          |
  | Reads: deliverable spec,  | Reads: implementation_plan,
  |   skills, memory,        |   skills, coding_standards
  |   coding_standards       |
  |                          |
  | Writes:                  | Writes:
  |   implementation_plan    |   code_output (files)
  |                          |
  | Tools: READ-ONLY         | Tools: FULL ACCESS
  |   file_read, file_glob,  |   file_read, file_write,
  |   file_grep,             |   file_edit, file_insert,
  |   directory_list,        |   file_multi_edit, bash_exec,
  |   code_symbols           |   git_commit, git_diff
```

### Why This Matters

1. **Prevents scope creep** -- a planning agent with write access might start "just writing a quick file" instead of producing a structured plan
2. **Enables better review** -- the plan is a discrete artifact that can be evaluated before any code is written
3. **Supports different models** -- planning benefits from the strongest reasoning model; implementation can use a capable but faster model
4. **Improves debuggability** -- when code is wrong, you can trace whether the plan was wrong or the implementation deviated from a good plan

---

## Agent Tool Restrictions

Read-only agents for exploration prevent scope creep.

All agent tiers (Director, PM, Workers) have access to tools and skills. However, not all agents should have access to *all* tools. AutoBuilder enforces role-based tool restrictions across every tier.

### Tool Registry

Tools are Python functions in `app/tools/`, organized by function type (filesystem, code, execution, git, web, task, management). `GlobalToolset(BaseToolset)` handles per-role tool filtering via ADK's native `get_tools(readonly_context)` mechanism. Cascading permission config restricts tools top-down through the supervision hierarchy -- a PM cannot access Director-specific tools, a Worker cannot access PM-specific tools. The Director can author new tools; CEO approval is required by default before new tools become active. See [Tools](./tools.md) for full toolset architecture.

### Worker-Level Tool Matrix

| Agent | Filesystem | Code Intelligence | Execution | Git | Web | Tasks |
|-------|-----------|-------------------|-----------|-----|-----|-------|
| `planner` | Read-only (`file_read`, `file_glob`, `file_grep`, `directory_list`) | Full (`code_symbols`, `run_diagnostics`) | None | Read-only (`git_status`, `git_diff`, `git_log`, `git_show`) | Full | Session todos |
| `coder` | Full (all 10) | Full | Full (`bash_exec`, `http_request`) | Full (all 8) | Full | Session todos |
| `reviewer` | Read-only | Full | None | Read-only | Full | Session todos |
| `fixer` | Full | Full | `bash_exec` | Read-only (code agent handles commits) | Full | Session todos |

### Management-Level Tool Matrix

| Agent | Management Tools | Tasks | Escalation |
|-------|-----------------|-------|------------|
| PM | `select_ready_batch`, `update_deliverable`, `query_deliverables`, `reorder_deliverables`, `manage_dependencies` | Shared tasks + session todos | `escalate_to_director` → Director queue |
| Director | `escalate_to_ceo`, `list_projects`, `query_project_status`, `override_pm`, `get_project_context`, `query_dependency_graph` | Shared tasks + session todos | `escalate_to_ceo` → CEO queue |

ADK supports this through `BaseToolset.get_tools()`, which returns different tool sets based on the agent or deliverable type. This keeps tool restriction logic centralized rather than scattered across agent definitions.

All tool access is within the worker's filesystem context, scoped to the appropriate git worktree for the deliverable being executed.

---

## LLM Router

### Purpose

Different tasks have different optimal models. A code implementation task benefits from Claude's coding strength. A quick classification might be better served by a fast, cheap model. A complex planning task warrants a reasoning-heavy model. The LLM Router centralizes this decision.

### Routing Rules

The router selects the optimal model per task based on:

1. **Task type** -- coding, planning, reviewing, summarizing, classifying
2. **Complexity** -- simple boilerplate vs. complex architecture decisions
3. **Cost/speed tradeoff** -- batch operations use cheaper models; critical-path uses best available
4. **Fallback chains** -- if the primary model is unavailable or rate-limited, fall back gracefully

### Example Configuration

```yaml
routing_rules:
  - model_role: code_implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-6"
  - model_role: code_implementation
    complexity: complex
    model: "anthropic/claude-opus-4-6"
  - model_role: planning
    model: "anthropic/claude-opus-4-6"
  - model_role: review
    model: "anthropic/claude-sonnet-4-6"
  - model_role: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - model_role: summarization
    model: "anthropic/claude-haiku-4-5-20251001"
```

For full model reference (all providers, pricing, fallback chains): see [Providers](../06-PROVIDERS.md).

### Implementation

```python
class LlmRouter:
    """Selects optimal model per task based on routing rules."""

    def __init__(self, routing_config: RoutingConfig):
        self.rules = routing_config.rules
        self.fallback_chains = routing_config.fallback_chains

    def select_model(self, model_role: str, complexity: str = "standard") -> str:
        """Returns LiteLLM model string for the given task context."""
        for rule in self.rules:
            if rule.matches(model_role, complexity):
                return rule.model
        return self.fallback_chains.get(model_role, self.default_model)
```

### Fallback Chain Resolution

Provider fallback chains use 3-step resolution:

1. **User override** -- if the user has specified a model preference in `user:` state, use it
2. **Fallback chain** -- if the primary model is unavailable/rate-limited, walk the fallback chain
3. **Default** -- if all else fails, use the system default model

### Integration with ADK

Each `LlmAgent` can have its model set dynamically. The router runs in one of two ways:

- **At agent construction time** -- when the PM builds the pipeline for each deliverable batch
- **Via `before_model_callback`** -- to override the model on the `LlmRequest` at invocation time

Both approaches keep routing logic centralized rather than scattered across individual agent definitions.

### Phase 1 Implementation

Start simple: static routing config mapping `model_role` to model. No ML-based routing, no cost optimization. A clean lookup table that is easy to change. Phase 2 adds cost tracking, latency monitoring, and adaptive selection.

---

## Agent Communication via Session State

### Hierarchical Communication

Between tiers, agents communicate via ADK's delegation primitives:

| Pattern | Mechanism | Example |
|---------|-----------|---------|
| Director -> PM delegation | `transfer_to_agent` | Director hands off project to PM ("go manage this") |
| PM -> Director return | `transfer_to_agent` back to Director | PM transfers back on batch completion or escalation |
| PM -> Worker orchestration | `sub_agents` tree | PM constructs DeliverablePipeline workers per batch |
| Worker -> PM escalation | State write + event | Worker writes failure to state; PM reads and decides |
| PM -> Director escalation | `transfer_to_agent` back to Director | PM transfers back with escalation context |
| Director observation | `before_agent_callback` / `after_agent_callback` | Director monitors PM events via supervision hooks |

### Worker-Level Communication

Within a pipeline tier, agents do not communicate via direct message passing. All inter-agent communication flows through session state using four mechanisms:

### 1. output_key

Each agent writes its result to a named state key. The next agent in the pipeline reads from that key.

```
planner  --writes-->  state["implementation_plan"]
coder  --reads-->   state["implementation_plan"]
coder  --writes-->  state["code_output"]
```

### 2. {key} Templates

Agent instructions reference state values via template injection. ADK auto-resolves these at invocation time.

```python
planner = LlmAgent(
    name="planner",
    instruction="""
    Implement the following deliverable: {current_deliverable_spec}

    Project coding standards: {app:coding_standards}

    Cross-session context:
    {memory_context}
    """,
    output_key="implementation_plan",
)
```

Note: Skills are NOT injected via `{loaded_skills}` template for LLM agents. Skills are composed into the instruction string by `InstructionAssembler` as SKILL fragments, filtered per-agent via `applies_to`. See [§Instruction Composition](#instruction-composition).

Use `{key?}` for optional keys that may not exist in state.

### 3. InstructionAssembler

Composes typed fragments from durable sources into a complete instruction string at invocation time. See [§Agent Definitions](#agent-definitions) for the full architecture.

### 4. before_model_callback

Injects additional context (file contents, test results, codebase analysis) right before the LLM call. Used for heavyweight context that should not be part of the static instruction string.

### State Update Rules

State updates happen exclusively via `Event.actions.state_delta` -- never direct mutation. This ensures all state changes are auditable in the event stream and are rewind-safe.

```python
yield Event(
    author=self.name,
    actions=EventActions(state_delta={
        "lint_results": structured_lint_output,
        "lint_passed": True,
    })
)
```

State values must be serializable (strings, numbers, booleans, simple lists/dicts). No complex objects.

> **VERIFIED (Phase 1):** Direct `ctx.session.state["key"] = value` writes inside `_run_async_impl` do NOT persist. This is mandatory, not a style preference -- the session service only processes state changes delivered via `state_delta`. See `.knowledge/adk/ERRATA.md` #1.

#### State Key Authorization (Decision #58)

Governance-sensitive state keys use tier prefixes. The `EventPublisher` ACL validates that the event author's tier matches the prefix on `state_delta` keys before publishing to the event stream.

**Access control matrix:**

| Key Prefix | Director READ | Director WRITE | PM READ | PM WRITE | Worker READ | Worker WRITE |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| `director:*` | yes | yes | yes | **no** | yes | **no** |
| `pm:*` | yes | yes | yes | yes | yes | **no** |
| `worker:*` | yes | yes | yes | yes | yes | yes |
| `app:*` | yes | yes | yes | yes | yes | **no** |
| `session` (no prefix) | yes | yes | yes | yes | yes | yes |
| `user:*` | yes | yes | yes | yes | yes | yes |
| `temp:*` | yes | yes | yes | yes | yes | yes |

**Key design points:**

- **Reads are unrestricted.** Any tier can read any state key. Visibility is not a security concern -- a worker reading `director:governance_override` to understand constraints is correct behavior. Only writes are restricted.
- **Writes are tier-gated.** The `EventPublisher` ACL inspects `state_delta` keys on every yielded `Event`. If a key's tier prefix exceeds the author's tier, the entire `state_delta` is rejected (not partially applied) and an error event is published to the stream.
- **Non-prefixed keys are shared workspace.** Keys like `implementation_plan`, `lint_results`, `code_output` are accessible by all tiers. This is the primary communication mechanism within a pipeline.
- **`app:` scope is Director/PM-writable only.** `app:` keys are global across all sessions — a write affects every active session in the system. Workers read `app:coding_standards` but never write it. This restriction matches the blast radius: global state changes are governance decisions, not worker-tier operations. `user:` scope follows ADK native semantics (all tiers writable) since it is scoped to a single user.
- **Violation behavior:** Rejected writes produce a loud error event (author, attempted key, tier mismatch) in the Redis Stream for audit. The originating agent receives an error response, not silent failure.

### Communication Flow Through the Pipeline

```
Session starts
  |
  v
SkillLoaderAgent --> state["loaded_skills"], state["loaded_skill_names"]
  |
  v
MemoryLoaderAgent --> state["memory_context"]
  |
  v
planner reads: {current_deliverable_spec}, {memory_context}, {app:coding_standards} + SKILL fragments (via assembler)
planner writes: state["implementation_plan"]
  |
  v
coder reads: {implementation_plan}, {app:coding_standards} + SKILL fragments (via assembler)
coder writes: state["code_output"]
  |
  v
LinterAgent writes: state["lint_results"], state["lint_passed"]
TestRunnerAgent writes: state["test_results"], state["tests_passed"]
  |
  v
DiagnosticsAgent reads: {lint_results}, {test_results}
DiagnosticsAgent writes: state["diagnostics_analysis"]
  |
  v
reviewer reads: {code_output}, {lint_results}, {test_results}, {diagnostics_analysis} + SKILL fragments (via assembler)
reviewer writes: state["review_result"]
  |
  v
(if review fails) fixer reads: {review_result}, {code_output}, {lint_results}, {test_results}
(if review fails) fixer writes: state["code_output"] (overwrite)
```

### Communication Decision Criteria

Two categories of communication serve different architectural needs. Use the decision table to select the right mechanism:

| Criteria | State-Based | Escalation-Based |
|----------|-------------|------------------|
| **Session scope** | Same session | Cross-session or cross-tier |
| **Timing** | Synchronous (pipeline order) | Asynchronous (event-driven) |
| **Typical use** | Data flow within a pipeline | Failure handling, tier delegation |
| **Mechanisms** | `output_key`, `{key}` templates, `InstructionAssembler`, `before_model_callback` | `transfer_to_agent`, `escalate_to_director`/`escalate_to_ceo`, Redis Streams events |

**When to use which:**

- **output_key + {key} templates** -- Agent A produces data that Agent B consumes in the same pipeline. This is the default for worker-level communication. Deterministic, auditable, zero overhead.
- **InstructionAssembler** -- Composing context from multiple durable sources (skills, project config, governance) into a coherent instruction at build time. Not for runtime data passing.
- **before_model_callback** -- Injecting heavyweight dynamic context (file contents, large diagnostic output) right before an LLM call. Use when the data is too large or too volatile for static state templates.
- **transfer_to_agent** -- Tier-crossing delegation (Director -> PM, PM -> Director on escalation). Transfers control flow, not just data.
- **Event publishing (Redis Streams)** -- Cross-session observation, audit logging, real-time UI updates. Consumed by SSE endpoints, webhook dispatchers, and audit loggers. Never for intra-pipeline data flow.

The four state-based mechanisms are distinct: `output_key` writes data, `{key}` templates read data into instructions, `InstructionAssembler` composes fragments at build time, and `before_model_callback` injects at call time. They operate at different lifecycle points and do not overlap.

---

## See Also

- [Context](./context.md) -- Context assembly lifecycle, budgeting, recreation, knowledge loading
- [Execution Loop](./execution.md) -- The autonomous execution loop (Director-level and PM-level)
- [Tools](./tools.md) -- Tool registry, toolset architecture, and tool restrictions
- [Workers](./workers.md) -- ARQ worker processes and job execution
- [Events](./events.md) -- Redis Streams event bus and event distribution
- [State & Memory](./state.md) -- ADK session state, memory service, and cross-session context
- [Skills](./skills.md) -- Skill-based knowledge injection and progressive disclosure
- [Architecture Overview](../02-ARCHITECTURE.md) -- Full system architecture

---

**Document Version:** 5.4
**Last Updated:** 2026-04-12
**Status:** Phase 8a Shaping -- Director-Mediated Entry Propagated
