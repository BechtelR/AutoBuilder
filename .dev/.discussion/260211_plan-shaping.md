# AutoBuilder: Plan Shaping (Consolidated)

**Date**: 2026-02-11
**Status**: Framework Validated — Prototyping Phase
**Supersedes**: `260114_plan-shaping.md`, `260211_framework-decision-evolution.md`, `260211_technical-spike-adk-vs-pydantic.md`

---

## 1. Vision

AutoBuilder is an autonomous agentic workflow system built on Google ADK that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. It supports pluggable workflow composition (auto-code, auto-design, auto-research, etc.), dynamic LLM routing across providers via LiteLLM, six-level progressive memory architecture, skill-based knowledge injection, and git worktree isolation for parallel execution. The system runs continuously from specification to verified output with optional human-in-the-loop intervention points. Built as a Python engine with TypeScript UI.

### Core Differentiators

1. **Autonomous completion** — "run until done" loop, not session-based human interaction
2. **Deterministic + probabilistic composition** — LLM agents and deterministic tools are equal workflow participants
3. **Spec-to-deliverable pipeline** — specification → deliverable decomposition → parallel execution → verified output
4. **Multi-model orchestration** — route tasks to optimal models by capability
5. **Structured quality gates** — validation, verification, and review cycles are guaranteed workflow steps, not LLM suggestions

### What AutoBuilder Is Not

- Not a plugin for an existing editor/CLI (standalone orchestrator)
- Not a chat-based assistant (autonomous executor)
- Not a single-agent harness (multi-agent team coordination)

---

## 2. Problems Being Solved

1. **Excessive human-in-the-loop** — existing tools (Claude Code, Cursor, chat LLMs) require constant human steering
2. **No intelligent orchestration** — lack of sequential vs parallel process coordination across agent teams
3. **Expensive autonomous alternatives** — tools like Blitzy cost $10k+ per project
4. **Fragmented ecosystem** — agent harnesses that do specific things instead of orchestrating multi-agent teams
5. **Insufficient quality control** — too little reflection, verification, and structured review in autonomous workflows
6. **Blocking on feedback** — systems that halt entirely for human input when unrelated work could continue
7. **No shared memory architecture** — no multi-level context (business standards, project conventions, session state)
8. **Token waste** — excessive human-friendly language when machine-formatted structures would suffice
9. **Over-reliance on LLM judgment** — non-deterministic processing where scripts and tools should guarantee outcomes
10. **No progressive knowledge loading** — agents either get everything or nothing, no task-appropriate context

---

## 3. Prior Art Analysis

### Frameworks Evaluated

| Framework | Key Strength | Key Weakness | Lesson for AutoBuilder |
|-----------|-------------|--------------|----------------------|
| **Autocoder** | Autonomous execution, spec→150-400+ deliverables, regression testing | Single agent, no parallelism, Claude-only | Spec-to-deliverable pipeline pattern; auto-continuation loop |
| **Automaker** | Git worktree isolation, dependency resolution, concurrent execution | Bloated (19 views, 32 themes, 150+ routes), no auto-continuation | Topological sorting; worktree isolation for parallel work |
| **SpecDevLoop** | Fresh context per iteration via ledger handoff | Subprocess overhead, Claude-only, single workflow | Ledger/handoff pattern (achievable without subprocess overhead) |
| **oh-my-opencode** | 11 specialized agents, multi-model fallback chains, plan/execute separation | 117k LOC, plugin coupling, no autonomous loop, no spec pipeline | Agent role restrictions; provider fallback chains; plan/execute boundary |

### Key Patterns Adopted from Prior Art

- **Provider fallback chains** (oh-my-opencode) — 3-step resolution: user override → fallback chain → default
- **Plan/Execute separation** (oh-my-opencode) — planning agents never write code; execution agents consume structured plans
- **Agent tool restrictions** (oh-my-opencode) — read-only agents for exploration prevent scope creep
- **Git worktree isolation** (Automaker) — true filesystem isolation for parallel code generation
- **Topological dependency sorting** (Automaker) — deliverables execute in dependency order
- **Spec-to-deliverable generation** (Autocoder) — specification decomposed into 150-400+ implementable deliverables
- **Auto-continuation loop** (Autocoder) — run until all deliverables complete, no human prompting needed

### Patterns Explicitly Avoided

- **Monolithic files** — max ~500 lines per module
- **Hook/plugin systems as primary extension** — prefer explicit workflow phases
- **Magic keyword triggers** — structured config, not prompt keyword detection
- **Platform-specific binaries** — pure Python, no native dependencies
- **Plugin coupling to host tools** — standalone system, no external CLI dependency

---

## 4. Architecture Decisions

### Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | SDK over headless CLI | Less overhead, better parallelism, native streaming, multi-model support | 2026-01-14 |
| 2 | New app, not modified Automaker | Reuse architectural patterns, skip complexity debt | 2026-01-14 |
| 3 | Multi-workflow architecture | Future-proof for auto-design, auto-market, etc. | 2026-01-14 |
| 4 | Standalone orchestrator, not plugin | Plugin coupling is fragile; autonomous loop needs full control | 2026-01-14 |
| 5 | Plan/Execute phase separation | Strict role boundaries proven by oh-my-opencode's Prometheus/Atlas | 2026-01-14 |
| 6 | Agent role-based tool restrictions | Read-only exploration agents prevent scope creep | 2026-01-14 |
| 7 | Provider fallback chains | 3-step resolution (user → chain → default) is proven and pragmatic | 2026-01-14 |
| 8 | **Python for core engine** | Agent ecosystem is Python-first; all candidate frameworks are Python-native | 2026-02-11 |
| 9 | **TypeScript only for UI** | Dashboard/web UI layer, separate concern from orchestration engine | 2026-02-11 |
| 10 | **No custom provider abstraction** | Both Pydantic AI and Google ADK handle multi-model natively; building our own is unnecessary | 2026-02-11 |
| 11 | **Claude Agent SDK rejected** | It's an agent harness (single Claude agent), not a workflow orchestrator; Claude-only, TS-only | 2026-02-11 |
| 12 | **Google ADK selected as framework** | Unified composition of LLM agents + deterministic tools; first-class workflow primitives | 2026-02-11 |
| 13 | **Phased MVP delivery** | Targeting all 15+ capabilities simultaneously risks bloat; MVP focuses on 6 core capabilities | 2026-02-11 |
| 14 | **Skills system as Phase 1 component** | Agents without skills are generic; skills produce project-appropriate output from day one | 2026-02-11 |
| 15 | **Workflow composition system as Phase 1** | Workflows must be pluggable from day one; hardcoding auto-code then bolting on others later would require ripping out assumptions | 2026-02-11 |
| 16 | **MCP used sparingly** | MCPs add significant context bloat; prefer lightweight FunctionTools; use agent-browser for browser automation | 2026-02-11 |
| 17 | **LLM Router for dynamic model selection** | Different tasks benefit from different models; route by capability/cost/speed, not hardcoded model strings | 2026-02-11 |
| 18 | **ADK App class as application container** | App provides lifecycle management, context compression, resumability, plugin registration — use as the top-level container | 2026-02-11 |
| 19 | **Multi-level memory as Phase 1** | Agents must accumulate learnings across deliverables and sessions; without memory, deliverable 47 can't know what patterns deliverables 1-10 established | 2026-02-11 |

---

## 5. Framework Selection: Google ADK

### Why ADK Over Pydantic AI

Both frameworks were evaluated head-to-head across 18 requirements. See `260211_technical-spike-adk-vs-pydantic.md` for the full comparison. The decisive factor was **deterministic tool execution as first-class citizens**.

AutoBuilder needs two fundamentally different types of tool execution:

1. **LLM-discretionary** — "use search if you need info" — the LLM decides when/how
2. **Deterministic** — run linter, run tests, format code — MUST execute at specific workflow points regardless of LLM judgment

**In Pydantic AI**, all tools are LLM-discretionary via `@agent.tool`. Deterministic steps must be plain Python functions called outside the framework — invisible to tracing, state management, and observability. They exist in a "shadow world."

**In Google ADK**, deterministic tools are first-class via `CustomAgent` (inheriting `BaseAgent`):
- Participate in the same state system as LLM agents
- Visible to tracing/observability (same Event stream)
- Cannot be skipped by LLM judgment — they're workflow steps, not suggestions
- Compose naturally with LLM agents in Sequential/Parallel/Loop workflows
- Re-run deterministically in loops without LLM re-invocation

AutoBuilder is fundamentally an **orchestration problem** where LLM agents are one component alongside deterministic tooling. ADK treats this as the core design principle; PAI treats agents as the primary abstraction and leaves orchestration to you.

### ADK Primitives Used

| Primitive | Role in AutoBuilder |
|-----------|-------------------|
| `LlmAgent` | Planning, execution, reviewing — probabilistic steps |
| `CustomAgent` (BaseAgent) | Validators, test runners, formatters, skill loader, outer loop orchestrator — deterministic steps (workflow-specific) |
| `SequentialAgent` | Inner deliverable pipeline (plan → execute → validate → verify → review) |
| `ParallelAgent` | Concurrent deliverable execution within a batch |
| `LoopAgent` | Review/fix cycles with max iteration bounds |
| `Session State` | Inter-agent communication (4 scopes: session/user/app/temp) |
| `Event Stream` | Unified observability for all agent types |
| `InstructionProvider` | Dynamic context/knowledge loading per invocation |
| `before_model_callback` | Context injection, token budget monitoring |
| `BaseToolset` | Dynamic tool selection based on deliverable type |
| `DatabaseSessionService` | State persistence to SQLite/Postgres |

### Acknowledged Tradeoffs

| Weakness | Severity | Mitigation |
|----------|----------|------------|
| Gemini-first bias | Medium | LiteLLM wrapper for Claude; test thoroughly in prototyping |
| No Temporal-style durability | Medium-High | Build checkpoint/resume on DatabaseSessionService; evaluate Temporal if insufficient |
| Google ecosystem gravity | Medium | Discipline: local SQLite/Postgres only; skip all Vertex AI services |
| Documentation accuracy issues | Low | Test everything empirically |
| Type safety less emphasized | Low | Use Pydantic models for structured outputs within ADK agents |
| No context-window usage awareness | Low | `before_model_callback` → token-count `LlmRequest` → write % to state (~50 lines) |

### Where PAI Would Have Won

If AutoBuilder were primarily an LLM-centric application where agents were the main abstraction and deterministic tooling was secondary, PAI's lighter weight, true model agnosticism, and superior type safety would make it the clear winner. PAI is also better for applications needing Temporal-grade durability from day one.

---

## 6. Core Architecture

### The Autonomous Execution Loop

```
1. Load spec → generate deliverables (spec-to-deliverable pipeline)
2. Resolve dependencies (topological sort)
3. While incomplete deliverables exist:
   a. Select next batch (respecting deps + concurrency limits)
   b. For each deliverable in batch (parallel):
      i.   Load relevant skills (deterministic: SkillLoaderAgent)
      ii.  Plan implementation (LLM: plan_agent)
      iii. Execute plan (LLM: execute_agent)
      iv.  Validate output (deterministic: workflow-specific ValidatorAgent)
      v.   Verify output (deterministic: workflow-specific VerifyAgent)
      vi.  Review quality (LLM: review_agent)
      vii. Loop steps iii-vi if review fails (max N iterations)
   c. Merge completed deliverables
   d. Run regression checks
   e. Optional: pause for human review
4. Report completion
```

### ADK Mapping

**Outer loop**: `CustomAgent` dynamically constructs `ParallelAgent` batches per iteration, manages dependency-aware batch selection, handles checkpoint/resume.

**Inner pipeline**: `SequentialAgent` with nested `LoopAgent` for review cycles.

**Deterministic steps**: `CustomAgent` subclasses as equal workflow participants. The specific validators are workflow-specific (LinterAgent + TestRunnerAgent for auto-code, SourceVerifierAgent + CitationCheckerAgent for auto-research, etc.).

```python
# Inner deliverable pipeline — declarative composition (auto-code example)
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # Deterministic: shared
        plan_agent,                                # LLM: workflow-specific
        execute_agent,                             # LLM: workflow-specific
        LinterAgent(name="Lint"),                  # Deterministic: auto-code
        TestRunnerAgent(name="Test"),               # Deterministic: auto-code
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM
                fix_agent,                         # LLM
                LinterAgent(name="ReLint"),        # Deterministic: auto-code
                TestRunnerAgent(name="ReTest"),     # Deterministic: auto-code
            ]
        )
    ]
)

# Outer loop — dynamic orchestrator
class BatchOrchestrator(BaseAgent):
    """Dynamically constructs ParallelAgent batches per iteration."""
    async def _run_async_impl(self, ctx):
        while incomplete_deliverables_exist(ctx):
            batch = select_next_batch(ctx)  # Dependency-aware, respects concurrency
            parallel = ParallelAgent(
                name=f"Batch_{batch.id}",
                sub_agents=[create_pipeline(d) for d in batch.deliverables]
            )
            async for event in parallel.run_async(ctx):
                yield event
            await run_regression_checks(ctx)
            await checkpoint(ctx)
```

### State Architecture

| Scope | Contents | Persistence |
|-------|----------|-------------|
| **Session** (no prefix) | Current batch, deliverable statuses, loaded skills, validation results, verification results | Per-run (persistent via `DatabaseSessionService`) |
| **User** (`user:` prefix) | Preferences, model selections, intervention settings | Cross-session per user |
| **App** (`app:` prefix) | Project config, global conventions, skill index | Cross-user, cross-session |
| **Temp** (`temp:` prefix) | Intermediate LLM outputs, scratch data | Discarded after invocation |
| **Memory** (`MemoryService`) | Cross-session learnings, past decisions, discovered patterns | Persistent, searchable archive |

*See Section 11 for full Session/State/Memory architecture.*

### Multi-Agent Communication

Agents communicate via session state, not direct message passing:

1. `output_key` — agent writes its result to a named state key
2. `{key}` templates — agent reads from state via template injection in instructions
3. `InstructionProvider` — dynamic function reads state and constructs context-appropriate instructions
4. `before_model_callback` — injects additional context (file contents, test results) right before LLM call

### Observability

ADK's event-driven architecture provides unified observability without custom bridging:

1. **Event stream** — every agent (LLM or deterministic) emits `Event` objects into a unified chronological stream
2. **ADK Dev UI** — `adk web` for local debugging with detailed traces
3. **OpenTelemetry native** — auto-traces `BaseAgent.run_async`, `FunctionTool.run_async`, `Runner.run_async`
4. **Python logging** — hierarchical loggers under `google.adk.*`
5. **Plugin system** — `LoggingPlugin` + custom plugins intercept at workflow callback points
6. **Third-party** — Langfuse, Arize Phoenix, LangWatch, AgentOps (all OTel-compatible)

Full pipeline visibility from plan → code → lint → test → review without additional instrumentation. Deterministic `CustomAgent` steps emit events into the same stream as `LlmAgent` steps.

### Context Window Management

ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt. Two built-in mechanisms manage growth:

- **Context compression** — sliding window summarization of older events (config-driven, interval + overlap)
- **Context caching** — caches static prompt parts server-side (system instructions, knowledge bases)

**Gap identified**: ADK has no built-in context-window usage metric. Agents can't reactively respond to "you're at 80% capacity." Solution: `before_model_callback` that token-counts the assembled `LlmRequest`, writes percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). ~50 lines of code.

**Implication for pipeline design**: For longer pipelines, agents shouldn't rely on reading raw event history from prior steps. Better to use SkillLoaderAgent + explicit state writes so each agent gets precisely the context it needs, not the full event log.

### Dynamic Context & Knowledge Loading

ADK provides injection hooks but no built-in knowledge management system. AutoBuilder's knowledge loading is layered:

| Layer | Mechanism | What It Loads |
|-------|-----------|---------------|
| 1 | Static instruction string | Base agent personality/role |
| 2 | `InstructionProvider` function | Project conventions, patterns, deliverable spec (at invocation time) |
| 3 | `before_model_callback` | File context, codebase analysis, test results (right before LLM call) |
| 4 | `BaseToolset.get_tools()` | Different tools per deliverable type |
| 5 | Artifacts (`save_artifact`/`load_artifact`) | Large data (full file contents, generated code) |
| 6 | Context compression | Sliding window summarization for long autonomous runs |

No built-in RAG/vector store. Google's answer is Vertex AI (we're avoiding). For AutoBuilder, knowledge is deterministic lookup (conventions from files, codebase via tools, specs via state, patterns from local directory) — InstructionProvider + callbacks are sufficient.

---

## 7. Skills System

### The Problem

Agents need specialized knowledge (project conventions, framework patterns, test strategies) but loading everything into every prompt wastes tokens and degrades focus. The solution is progressive disclosure — agents see a lightweight index of available skills and load full content only when relevant.

### Design Principles

1. **Skills are just files** — Markdown with YAML frontmatter, no database
2. **Frontmatter is the index** — lightweight metadata enables matching without reading full content
3. **Progressive disclosure** — index visible to agents; full content loads only when matched
4. **Two-tier library** — global skills (ship with AutoBuilder) + project-local skills (live in the repo, override globals)
5. **Composable** — multiple skills apply to one task
6. **No LLM in matching** — deterministic pattern matching, not another LLM call

### Skill File Format

```markdown
---
name: fastapi-endpoint
description: How to implement a REST API endpoint following project conventions
triggers:
  - deliverable_type: api_endpoint
  - file_pattern: "*/routes/*.py"
tags: [api, http, routing, fastapi]
applies_to: [code_agent, review_agent]
priority: 10
---

## API Endpoint Implementation
[Full implementation guide, conventions, test patterns...]
```

### Trigger Matching

| Trigger Type | Matches Against | Logic |
|---|---|---|
| `deliverable_type` | `state["current_deliverable_type"]` | Exact match |
| `file_pattern` | Any file in `state["target_files"]` | Glob match |
| `tag_match` | Any tag in `state["deliverable_tags"]` | Set intersection |
| `explicit` | `state["requested_skills"]` | Named request |
| `always` | Always matches for specified agents | Unconditional |

A skill matches if **any** of its triggers match (OR logic). Project-local skills with the same `name` as a global skill override it.

### ADK Integration

Skills integrate via `SkillLoaderAgent` — a deterministic `CustomAgent` that runs as the first step in the deliverable pipeline:

```python
class SkillLoaderAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        matched = skill_library.match(context_from_state(ctx))
        loaded = [skill_library.load(entry) for entry in matched]
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": {s.entry.name: s.content for s in loaded},
                "loaded_skill_names": [s.entry.name for s in loaded],
            })
        )
```

This approach is preferred because:
- Skill resolution appears in the event stream (observable, debuggable)
- Skills load into state once, available to all subsequent agents in the pipeline
- It's a deterministic step — cannot be skipped by LLM judgment
- You can see exactly which skills were loaded for any given deliverable execution

### Directory Layout

```
autobuilder/skills/              # Global (ships with AutoBuilder)
├── code/
│   ├── api-endpoint.md
│   ├── data-model.md
│   └── database-migration.md
├── review/
│   ├── security-review.md
│   └── performance-review.md
├── test/
│   └── unit-test-patterns.md
└── planning/
    └── feature-decomposition.md

user-project/.autobuilder/skills/  # Project-local (overrides/extends)
├── code/
│   ├── api-endpoint.md            # Overrides global with project conventions
│   └── auth-middleware.md         # Project-specific, no global equivalent
└── review/
    └── compliance-review.md
```

Estimated scope: ~300-400 lines for core SkillLibrary + SkillLoaderAgent + frontmatter parsing. Disproportionate value for the effort.

---

## 8. Tool Inventory

### What ADK Provides (Usable for AutoBuilder)

ADK gives excellent *plumbing* for building tools but almost nothing directly usable for AutoBuilder's needs. Most built-in tools are Gemini-only or GCP-specific.

**Genuinely usable built-ins:**

| Tool | Module | Purpose |
|------|--------|---------|
| `load_web_page` | `load_web_page` | Fetch and parse URLs |
| `exit_loop` | `exit_loop_tool` | Break out of LoopAgent cycles |
| `get_user_choice` | `get_user_choice_tool` | Human-in-the-loop intervention points |
| `transfer_to_agent` | `transfer_to_agent_tool` | Dynamic agent delegation |
| `agent_tool` | `agent_tool` | Wrap agent as callable tool |
| `FunctionTool` | `function_tool` | Wrap any Python function as a tool (auto-schema from type hints + docstring) |
| `OpenAPIToolset` | `openapi_tool` | Generate tools from any OpenAPI spec |
| `LangChain adapter` | `langchain_tool` | Wrap any LangChain tool |

**Not usable (Gemini-only or GCP-specific):**
`google_search` (Gemini grounding), `BuiltInCodeExecutor` (Gemini-only), `BigQuery`, `enterprise_search_tool`, `vertex_ai_search_tool`, `apihub_tool`, `application_integration_tool`, `google_maps_grounding_tool`

**MCP approach:** Use sparingly. MCPs are notorious for context bloat — they inject tool schemas and protocol overhead that burns tokens. Prefer lightweight `FunctionTool` wrappers for most needs. MCP reserved for cases where a well-maintained server provides substantial value we can't easily replicate (e.g., complex database connectors). For browser automation, use agent-browser (purpose-built, lighter footprint) instead of Playwright MCP.

### AutoBuilder Core Toolset (Build as FunctionTools)

Each of these is a thin Python function (~5-30 lines) that ADK auto-wraps via `FunctionTool`:

**Filesystem:**
- `file_read(path: str) -> str` — read file contents
- `file_write(path: str, content: str) -> str` — write/create files
- `file_edit(path: str, old: str, new: str) -> str` — targeted string replacement
- `file_search(pattern: str, path: str) -> str` — grep/find across codebase
- `directory_list(path: str) -> str` — list directory contents/tree

**Execution:**
- `bash_exec(command: str, cwd: str | None) -> str` — run shell commands (subprocess wrapper with timeout, output capture)

**Web:**
- `web_search(query: str) -> str` — search the web (via SearXNG, Brave, or Tavily API — no Gemini dependency)
- `web_fetch(url: str) -> str` — fetch and extract content from URL (supplement ADK's `load_web_page` if needed)

**Task Management:**
- `todo_read() -> str` — read current task list from session state
- `todo_write(action: str, task_id: str, content: str) -> str` — add/update/complete/remove tasks
- `todo_list(filter: str | None) -> str` — list tasks with optional status filter

**Git:**
- `git_status(path: str) -> str` — current repo state
- `git_commit(path: str, message: str) -> str` — stage and commit
- `git_branch(path: str, name: str, action: str) -> str` — create/switch/delete branches
- `git_diff(path: str, ref: str | None) -> str` — show changes

### Deterministic Agents (Build as CustomAgent/BaseAgent)

These are workflow-level participants, not LLM-callable tools:

- **`SkillLoaderAgent`** — resolve and load relevant skills into state
- **`LinterAgent`** — run project linter, write results to state
- **`TestRunnerAgent`** — run test suite, write results to state
- **`FormatterAgent`** — run code formatter
- **`DependencyResolverAgent`** — topological sort of features
- **`RegressionTestAgent`** — run cross-feature regression suite
- **`ContextBudgetAgent`** — check token usage, trigger compression if needed

### LLM Router (Dynamic Model Selection)

Different tasks have different optimal models. A code implementation task benefits from Claude's coding strength. A quick classification or extraction might be better served by a fast, cheap model. A complex planning task might warrant a reasoning-heavy model.

The LLM Router is a `before_model_callback` or `CustomAgent` that dynamically selects the model for each LLM agent invocation based on:

1. **Task type** — coding, planning, reviewing, summarizing, classifying
2. **Complexity** — simple boilerplate vs. complex architecture decisions
3. **Cost/speed tradeoff** — batch operations use cheaper models; critical-path uses best available
4. **Fallback chains** — if primary model is unavailable/rate-limited, fall back gracefully

```python
class LlmRouter:
    """Selects optimal model per task based on routing rules."""
    
    def __init__(self, routing_config: RoutingConfig):
        self.rules = routing_config.rules
        self.fallback_chains = routing_config.fallback_chains
    
    def select_model(self, task_type: str, complexity: str = "standard") -> str:
        """Returns LiteLLM model string for the given task context."""
        # Match against routing rules
        for rule in self.rules:
            if rule.matches(task_type, complexity):
                return rule.model
        return self.fallback_chains.get(task_type, self.default_model)

# Example routing config (YAML or Python dict)
routing_rules:
  - task_type: code_implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: code_implementation
    complexity: complex  
    model: "anthropic/claude-opus-4-6"
  - task_type: planning
    model: "anthropic/claude-opus-4-6"
  - task_type: review
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - task_type: summarization
    model: "anthropic/claude-haiku-4-5-20251001"

fallback_chains:
  anthropic/claude-opus-4-6: ["anthropic/claude-sonnet-4-5-20250929"]
  anthropic/claude-sonnet-4-5-20250929: ["anthropic/claude-haiku-4-5-20251001"]
```

**Integration with ADK:** Each `LlmAgent` can have its model set dynamically. The router runs as part of agent construction (in the `BatchOrchestrator`) or via `before_model_callback` to override the model on the `LlmRequest` at invocation time. This keeps routing logic centralized rather than scattered across agent definitions.

**Phase 1 implementation:** Start simple — static routing config mapping task_type → model. No ML-based routing, no cost optimization. Just a clean lookup table that's easy to change. Sophisticate in Phase 2 with cost tracking, latency monitoring, and adaptive selection.

---

## 9. Workflow Composition System

### Why This Can't Be Deferred

If we hardcode the auto-code pipeline structure and then try to bolt on auto-design or auto-market later, we'll discover assumptions baked into the core: tool registries coupled to coding tools, state keys assuming code artifacts, pipeline stages assuming lint→test→review. The workflow system must be pluggable from day one, even if only one workflow ships initially.

### Architecture: Workflows as Discoverable, Composable Units

A workflow follows the same discovery pattern as skills — a directory with a manifest file and implementation code. The system scans for available workflows and matches them to user requests.

```
autobuilder/workflows/
├── auto-code/
│   ├── WORKFLOW.yaml          # Manifest: name, description, triggers, required_tools, pipeline_config
│   ├── pipeline.py            # ADK agent composition (SequentialAgent, etc.)
│   ├── agents/                # Workflow-specific agent definitions
│   │   ├── plan_agent.py
│   │   ├── code_agent.py
│   │   └── review_agent.py
│   └── skills/                # Workflow-specific skills (extend global skills)
│       └── code/
├── auto-design/
│   ├── WORKFLOW.yaml
│   ├── pipeline.py            # Different pipeline: research → wireframe → prototype → review
│   └── agents/
│       ├── research_agent.py
│       ├── design_agent.py
│       └── critique_agent.py
└── auto-market/
    ├── WORKFLOW.yaml
    ├── pipeline.py            # Different pipeline: strategy → content → channel_adapt → review
    └── agents/
```

### Workflow Manifest

```yaml
# autobuilder/workflows/auto-code/WORKFLOW.yaml
name: auto-code
description: Autonomous software development from specification
triggers:
  - keywords: [build, develop, implement, code, create app, create api]
  - explicit: auto-code
required_tools: [file_read, file_write, file_edit, bash_exec, git_status, git_commit, git_diff]
optional_tools: [web_search, web_fetch, todo_read, todo_write]
default_models:
  planning: anthropic/claude-opus-4-6
  implementation: anthropic/claude-sonnet-4-5-20250929
  review: anthropic/claude-sonnet-4-5-20250929
pipeline_type: batch_parallel    # batch_parallel | sequential | single_pass
supports_decomposition: true      # Can decompose spec into deliverables?
supports_parallel: true           # Can run deliverables in parallel?
```

### Workflow Registry

```python
class WorkflowRegistry:
    """Discovers and manages available workflows."""
    
    def __init__(self, workflows_dir: Path, custom_workflows_dir: Path | None = None):
        self._workflows: dict[str, WorkflowEntry] = {}
        self._scan(workflows_dir)
        if custom_workflows_dir:
            self._scan(custom_workflows_dir)  # Custom overrides built-in
    
    def match(self, user_request: str) -> WorkflowEntry | None:
        """Match user request to a workflow. Deterministic keyword matching."""
        for workflow in self._workflows.values():
            if workflow.matches(user_request):
                return workflow
        return None
    
    def get(self, name: str) -> WorkflowEntry:
        """Get workflow by explicit name."""
        return self._workflows[name]
    
    def list_available(self) -> list[WorkflowEntry]:
        """List all discovered workflows with descriptions."""
        return list(self._workflows.values())
    
    def create_pipeline(self, workflow_name: str, config: RunConfig) -> BaseAgent:
        """Instantiate the workflow's ADK pipeline with the given config."""
        workflow = self.get(workflow_name)
        module = import_module(workflow.pipeline_module)
        return module.create_pipeline(config, self.tool_registry, self.skill_library)
```

### What's Shared vs. Workflow-Specific

**Shared infrastructure (all workflows use):**
- Tool registry (FunctionTools available to all workflows)
- Skill library (global + project-local skills)
- LLM Router (model selection)
- State management (session/user/app/temp scopes)
- Observability (event stream, tracing)
- Outer loop (BatchOrchestrator — if workflow supports batch_parallel)
- App container (lifecycle, compression, resumability)

**Workflow-specific:**
- Pipeline composition (which agents, in what order, with what loops)
- Agent definitions (instructions, tools subset, model preferences)
- Workflow-specific skills (e.g., auto-code has `api-endpoint.md`, auto-design has `design-system.md`)
- Deliverable decomposition strategy (auto-code decomposes into implementable code deliverables; auto-market decomposes into content pieces)

### Compound Workflows

"Design and create a marketing campaign" is a compound request spanning two workflows. The system should handle this by:

1. **Decompose the request** into workflow-level tasks (planning agent identifies: design workflow for visual assets + marketing workflow for campaign strategy/content)
2. **Sequence the workflows** based on dependencies (design produces assets → marketing references them)
3. **Share state** between workflow executions via session state

This is a Phase 2 capability but the architecture supports it from day one because workflows are independent units that read/write shared state.

---

## 10. App Class Implementation

ADK's `App` class (v1.14.0+) is the top-level container for an entire agent workflow. It manages lifecycle, configuration, and cross-cutting concerns. AutoBuilder uses `App` as the application shell.

### What App Provides

| Feature | Purpose | AutoBuilder Use |
|---------|---------|----------------|
| `root_agent` | The top-level agent tree | Our `BatchOrchestrator` (CustomAgent) |
| `events_compaction_config` | Context compression (sliding window summarization) | Keep long autonomous runs within context limits |
| `resumability_config` | Workflow resume after interruption | Pick up where we left off after crash/power loss |
| `plugins` | Global lifecycle hooks (logging, metrics, guardrails) | Token tracking, cost monitoring, security guardrails |
| `context_cache_config` | Cache static prompt parts server-side | Cache system instructions and skill content |
| Lifecycle hooks | `on_startup` / `on_shutdown` | Initialize DB connections, tool registry, skill library |
| State scope boundary | `app:*` prefix for app-level state | Project config, global conventions, workflow registry |

### AutoBuilder App Structure

```python
from google.adk.apps import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

# Summarizer uses a cheap/fast model — not the primary coding model
summarizer = LlmEventSummarizer(
    llm=LiteLlm(model="anthropic/claude-haiku-4-5-20251001")
)

app = App(
    name="autobuilder",
    root_agent=batch_orchestrator,   # CustomAgent: the outer loop
    
    # Context compression for long autonomous runs
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,       # Compress every 5 invocations
        overlap_size=1,              # Retain 1 invocation overlap for continuity
        summarizer=summarizer,       # Explicit model (required when root is non-LLM agent)
    ),
    
    # Enable workflow resume after interruption
    resumability_config=ResumabilityConfig(
        is_resumable=True,
    ),
    
    # Global plugins
    plugins=[
        TokenTrackingPlugin(),       # Track cost/tokens per agent per deliverable
        LoggingPlugin(),             # Structured event logging
    ],
)
```

### Resumability for CustomAgents

ADK's Resume feature (v1.16+) tracks workflow execution and allows picking up after unexpected interruption. Key considerations for AutoBuilder:

- **Resume is not automatic for CustomAgents** — we must implement `BaseAgentState` subclass and define checkpoint steps in our `BatchOrchestrator`
- Tools may run more than once on resume — our git, file write, and bash tools must be idempotent or include duplicate-run protection
- The system reinstates results from successfully completed tools and re-runs from the point of failure
- This significantly reduces the severity of the "no Temporal-style durability" tradeoff — ADK's native resume may be sufficient for Phase 1, deferring Temporal evaluation

### Runner Configuration

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# Local persistence — no GCP services
session_service = DatabaseSessionService(
    db_url="sqlite:///./autobuilder_sessions.db"  # Or postgres://...
)

runner = Runner(
    app=app,
    session_service=session_service,
    artifact_service=FileArtifactService(base_dir="./artifacts"),
)
```

### Updated Tradeoff Assessment

The discovery of ADK's native Resume feature meaningfully changes the durability picture:

| Original Assessment | Updated Assessment |
|---|---|
| "No Temporal-style durability" — Medium-High severity | "Native resume covers most crash scenarios" — Medium-Low severity |
| "Build checkpoint/resume from scratch" | "Implement BaseAgentState + checkpoint steps in CustomAgents" |
| "Evaluate Temporal in Phase 2" | "Evaluate Temporal only if resume proves insufficient for multi-hour runs" |

---

## 11. Sessions, State & Memory

### What ADK Provides Natively

ADK has a complete three-tier context management system that maps closely to AutoBuilder's needs:

**1. Session** — A single conversation thread. Contains chronological `Event` history and a `state` dict. Identified by `(app_name, user_id, session_id)`. Managed by a `SessionService`.

**2. State** — Key-value scratchpad within a session, with 4 prefix-scoped tiers:

| Prefix | Scope | Lifetime | AutoBuilder Use |
|--------|-------|----------|----------------|
| *(none)* | This session only | Persists with session (via `DatabaseSessionService`) | Current batch, deliverable statuses, loaded skills, validation/verification results, intermediate pipeline data |
| `user:` | All sessions for this user (within same app) | Persistent | User preferences, model selections, intervention settings, notification preferences |
| `app:` | All users and sessions for this app | Persistent | Project config, global conventions, skill index, workflow registry, shared templates |
| `temp:` | Current invocation only | Discarded after invocation completes | Intermediate LLM outputs, scratch calculations, data passed between tool calls within one invocation |

State updates happen via `Event.actions.state_delta` — never direct mutation. This means all state changes are auditable in the event stream. State values must be serializable (strings, numbers, booleans, simple lists/dicts). No complex objects.

State values are injectable into agent instructions via `{key}` templating: `"Implement the feature: {current_feature_spec}"` auto-resolves from `session.state['current_feature_spec']`. Use `{key?}` for optional keys that may not exist.

**3. Memory (MemoryService)** — Searchable cross-session knowledge archive. Two operations: `add_session_to_memory(session)` ingests a completed session, `search_memory(app_name, user_id, query)` retrieves relevant past context.

Built-in tools: `PreloadMemoryTool` (auto-loads relevant memories every turn) and `LoadMemory` (agent-decided retrieval). Memory can also be searched from within custom tools via `tool.Context.search_memory()`.

**4. Session Rewind** (v1.17+) — Revert to any previous invocation point. Session-level state and artifacts restored; `app:` and `user:` state NOT restored (by design — those are cross-session). External systems (filesystem, git) not managed by rewind — we handle that via git worktree isolation.

**5. Session Migration** — CLI tool for `DatabaseSessionService` schema upgrades (v0 pickle → v1 JSON). Important for production maintenance.

### SessionService Options

| Service | Persistence | Use Case |
|---------|------------|----------|
| `InMemorySessionService` | None (lost on restart) | Dev/testing only |
| `DatabaseSessionService` | SQLite or Postgres | **AutoBuilder production choice** — local, no GCP dependency |
| `VertexAiSessionService` | Vertex AI managed | Skipping — GCP dependency |

`DatabaseSessionService` requires async drivers: `sqlite+aiosqlite` for SQLite, `asyncpg` for Postgres.

### MemoryService Options

| Service | Search | Persistence | Limitations |
|---------|--------|-------------|-------------|
| `InMemoryMemoryService` | Basic keyword matching | None | Dev/testing only |
| `VertexAiMemoryBankService` | Semantic (LLM-powered extraction + search) | Managed by Vertex AI | **GCP-only — we're avoiding this** |

### The Gap: Local Semantic Memory

ADK's `MemoryService` is an interface (`BaseMemoryService`) with two methods: `add_session_to_memory()` and `search_memory()`. The only production-ready implementation is `VertexAiMemoryBankService` (GCP-only). `InMemoryMemoryService` is keyword-only and non-persistent.

AutoBuilder needs a local, persistent, semantically-searchable memory service. Options:

1. **SQLite FTS5** — Full-text search built into SQLite. No additional dependencies. Good enough for keyword + phrase matching. Lightweight. Could be sufficient for Phase 1.
2. **Local embedding + vector store** — Embed session content locally (via a small embedding model or API call), store in ChromaDB/FAISS/SQLite-VSS. True semantic search. More complex but more powerful.
3. **Hybrid** — SQLite FTS5 for structured lookups + vector store for semantic similarity. Best of both worlds but more moving parts.

**Phase 1 recommendation:** Implement `BaseMemoryService` backed by SQLite FTS5. It's zero-dependency (SQLite is already our session store), provides useful full-text search, and is sufficient for "what patterns did we establish in deliverables 1-10?" type queries. Evaluate upgrading to vector-backed semantic search in Phase 2 if FTS5 proves insufficient.

### AutoBuilder's Multi-Level Memory Architecture

Mapping our original "multi-level memory" requirement (Problem #7) to ADK's native primitives:

| Memory Level | ADK Mechanism | What It Stores | Loaded How |
|---|---|---|---|
| **Invocation context** | `temp:` state | Scratch data for current tool chain | Auto-available, discarded after |
| **Pipeline context** | Session state (no prefix) | Deliverable spec, plan, execution output, validation results, verification results | Written by agents via `state_delta`, read via `{key}` templates |
| **Project conventions** | `app:` state + Skills | Standards, architecture decisions, workflow patterns | SkillLoaderAgent + `InstructionProvider` |
| **User preferences** | `user:` state | Model preferences, notification settings, review strictness | Auto-merged into session at load |
| **Cross-session learnings** | `MemoryService` | Patterns discovered, mistakes made, architectural decisions from past runs | `PreloadMemoryTool` or `LoadMemory` tool |
| **Business knowledge** | Skills files (global + project-local) | Domain rules, compliance requirements, workflow conventions | SkillLoaderAgent (deterministic matching) |

This is six levels of progressively broader context, all using ADK-native mechanisms. No custom memory framework needed — just proper use of state scopes + MemoryService + Skills.

### How Memory Flows Through the Pipeline

```
Session starts → DatabaseSessionService loads session with merged state
  ↓
  app:* state available (project config, conventions)
  user:* state available (preferences, settings) 
  session state available (feature list, batch status from last run)
  ↓
SkillLoaderAgent → loads relevant skills into session state
  ↓
PreloadMemoryTool → searches MemoryService for relevant cross-session context
  ↓  
plan_agent reads: {current_deliverable_spec}, {loaded_skills}, {memory_context}, {app:standards}
  ↓
execute_agent reads: {implementation_plan}, {loaded_skills}, {app:standards}
  ↓
ValidatorAgent writes: validation_results to session state
VerifyAgent writes: verification_results to session state  
  ↓
review_agent reads: {execution_output}, {validation_results}, {verification_results}, {loaded_skills}
  ↓
Session complete → add_session_to_memory() ingests learnings for future runs
```

### Key Implementation Details

**State updates are event-sourced.** Never mutate `session.state` directly. Always write via `EventActions(state_delta={...})`. This ensures all changes are captured in the event stream and are rewind-safe.

**Memory ingestion is explicit.** Call `memory_service.add_session_to_memory(session)` at appropriate points — after deliverable completion, after batch completion, at session end. Not every invocation needs to be ingested.

**Rewind limitations matter for us.** Session rewind restores session-level state and artifacts but NOT `app:` or `user:` state. Since our project conventions live in `app:` state and skills, a rewind doesn't accidentally erase global learnings. This is the right behavior.

**Multiple memory services are supported.** ADK allows agents to access more than one `MemoryService`. This could be useful if we later want separate stores for different knowledge types (e.g., code patterns vs. project decisions).

Estimated scope: ~200-500 lines for `SqliteFtsMemoryService` implementing `BaseMemoryService`. The rest (state scopes, session management, event-sourced updates) is native ADK — we just use it correctly.

---

## 12. Phased Delivery

### Phase 1: MVP — Core Loop + Foundation

1. ADK App container with context compression + resumability
2. Core toolset (filesystem, bash, git, web, todo — as FunctionTools)
3. Skills system (SkillLibrary + SkillLoaderAgent)
4. Workflow composition system (WorkflowRegistry + auto-code as first workflow)
5. LLM Router (static routing config: task_type → model)
6. Multi-level memory (DatabaseSessionService + 4 state scopes + SqliteFtsMemoryService)
7. Plan/Execute agent separation
8. Autonomous continuation loop ("run until done")
9. Git worktree isolation for parallel execution
10. Spec-to-deliverable pipeline (adapted from Autocoder patterns)
11. Basic CLI interface

### Phase 2: Production Hardening

12. CustomAgent resume implementation (BaseAgentState + checkpoint steps)
13. Cost/token tracking per deliverable and agent (TokenTrackingPlugin)
14. Agent role-based tool restrictions
15. Context budget management (reactive context-window awareness)
16. Adaptive LLM Router (cost-aware, latency-aware model selection)
17. Evaluate Temporal only if native resume proves insufficient

### Phase 3: Scale & Polish

18. Web dashboard
19. Additional workflow types (auto-design, auto-market)
20. Compound workflow composition (multi-workflow request decomposition)
21. Self-learning / self-correcting patterns
22. Semantic memory upgrade (vector-backed MemoryService if FTS5 insufficient)

---

## 13. Prototype Validation Plan

Before full commitment to ADK, validate with four focused prototypes:

### Prototype 1: Basic Agent Loop + Claude via LiteLLM
- Create ADK `LlmAgent` with Claude via LiteLLM wrapper
- Define file-read, file-write, bash as `FunctionTool`s
- **Critical validation**: Claude reliability through LiteLLM? Latency? Token counting?

### Prototype 2: Mixed Agent Coordination (LLM + Deterministic)
- Create `plan_agent` (LlmAgent) and `linter_agent` (CustomAgent)
- Wire in `SequentialAgent` pipeline
- Pass data via session state (`output_key` → state read)
- **Validate**: unified event stream, state persistence across agent types, observability of deterministic steps

### Prototype 3: Parallel Execution
- Run 3 `LlmAgent` instances concurrently via `ParallelAgent`
- Each writes to distinct state keys
- **Validate**: no state collision, isolation, concurrent LLM calls, event interleaving

### Prototype 4: Dynamic Outer Loop (CustomAgent Orchestrator)
- Build `CustomAgent` that dynamically constructs `ParallelAgent` batches
- Implement "while incomplete deliverables exist" loop with dependency ordering
- Test with 5 simple deliverables
- **Validate**: dynamic workflow construction, execution order, failure handling, continuation

**Success criteria**: If all 4 prototypes work cleanly (especially Claude via LiteLLM in P1 and dynamic orchestration in P4), commit to ADK. If Claude integration proves unreliable or the CustomAgent outer loop is too clunky, re-evaluate PAI.

---

## 14. Open Questions

| # | Question | Status | Target Phase |
|---|----------|--------|-------------|
| 1 | Deliverable file format (JSON, SQLite, other?) | Open | Phase 1 |
| 2 | Spec parsing — how sophisticated should deliverable decomposition be? | Open | Phase 1 |
| 3 | Regression strategy — random sampling or dependency-aware? | Open | Phase 1 |
| 4 | Reuse Automaker TS libs or rewrite in Python? | Open — language change affects reuse | Phase 1 |
| 5 | Agent role system granularity | Open | Phase 2 |
| 6 | Context budget strategy — per-agent limits with pruning? | Open | Phase 2 |
| 7 | Web search provider selection (SearXNG vs Brave vs Tavily) | Open | Phase 1 |
| 8 | Agent-browser integration approach for UI testing | Open | Phase 1 |
| 9 | Durable execution — native ADK resume sufficient or need Temporal? | Likely sufficient — evaluate in Phase 2 | Phase 2 |
| 10 | Memory ingestion strategy — after each deliverable, each batch, or session end? | Open | Phase 1 |
| 11 | SQLite FTS5 vs vector store for MemoryService — is FTS5 sufficient? | Start with FTS5, evaluate in Phase 2 | Phase 1/2 |

---

## 15. Risk Register

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Claude unreliable through LiteLLM/ADK | High | Prototype 1 validates this first; PAI fallback |
| ADK CustomAgent outer loop too clunky | Medium | Prototype 4 validates; could simplify to plain Python loop using ADK for inner pipelines only |
| Google deprecates/pivots ADK | Low-Medium | Apache 2.0 means forkable; core architecture patterns transfer to other frameworks |
| Context window exhaustion in long runs | Medium | Token-counting callback + reactive compression + checkpoint/restart |
| Non-Gemini models as second-class citizens | Medium | Test thoroughly; stay on LiteLLM latest; community pressure keeps this improving |

### Architectural Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Scope creep toward 117k LOC | High | Phased delivery; MVP ruthlessness; max ~500 lines per module |
| Skills system becomes too rigid | Low | OR-logic triggers keep matching simple; project overrides add flexibility |
| Google ecosystem gravity (Vertex AI pull) | Medium | Strict discipline: local SQLite/Postgres only; document boundaries; no GCP services |

---

## 16. References

### AutoBuilder Discussion Documents
- Original plan shaping: `260114_plan-shaping.md`
- Framework decision evolution: `260211_framework-decision-evolution.md`
- Full ADK vs PAI technical spike: `260211_technical-spike-adk-vs-pydantic.md`

### Prior Art
- Autocoder: `/home/dmin/projects/autocoder`
- Automaker: `/home/dmin/projects/automaker`
- SpecDevLoop: `/home/dmin/projects/SpecDevLoop`
- oh-my-opencode: `/home/dmin/projects/oh-my-opencode`
- Framework comparison: `/home/dmin/projects/autocode-vs-automaker.md`

### Framework Documentation
- Google ADK docs: https://google.github.io/adk-docs/
- Google ADK GitHub: https://github.com/google/adk-python
- ADK multi-agent patterns: https://google.github.io/adk-docs/agents/multi-agents/
- ADK custom agents: https://google.github.io/adk-docs/agents/custom-agents/
- ADK context compression: https://google.github.io/adk-docs/context/compaction/
- ADK callback patterns: https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/
- ADK Apps class: https://google.github.io/adk-docs/apps/
- ADK Resume feature: https://google.github.io/adk-docs/runtime/resume/
- ADK Plugins: https://google.github.io/adk-docs/plugins/
- ADK Sessions & Memory overview: https://google.github.io/adk-docs/sessions/
- ADK Session management: https://google.github.io/adk-docs/sessions/session/
- ADK Session rewind: https://google.github.io/adk-docs/sessions/session/rewind/
- ADK Session migration: https://google.github.io/adk-docs/sessions/session/migrate/
- ADK State management: https://google.github.io/adk-docs/sessions/state/
- ADK Memory service: https://google.github.io/adk-docs/sessions/memory/
- Pydantic AI docs: https://ai.pydantic.dev/
- Pydantic AI GitHub: https://github.com/pydantic/pydantic-ai
- Pydantic AI + Temporal: https://ai.pydantic.dev/durable_execution/overview/
- Framework comparison benchmarks: https://newsletter.victordibia.com/p/autogen-vs-crewai-vs-langgraph-vs
