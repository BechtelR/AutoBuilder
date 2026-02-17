# Agents

**AutoBuilder Platform**
**Agent Architecture Reference**

---

## Table of Contents

1. [Overview](#overview)
2. [Agent Hierarchy](#agent-hierarchy)
3. [Director Agent](#director-agent)
4. [PM Agent](#pm-agent)
5. [Execution Environment](#execution-environment)
6. [Worker-Tier LLM Agents](#worker-tier-llm-agents)
7. [Worker-Tier Custom Agents (Deterministic)](#worker-tier-custom-agents)
8. [Plan/Execute Separation](#planexecute-separation)
9. [Agent Tool Restrictions](#agent-tool-restrictions)
10. [LLM Router](#llm-router)
11. [Agent Communication via Session State](#agent-communication-via-session-state)

---

## Overview

AutoBuilder uses a **three-tier hierarchical supervision model** (CEO -> Director -> PM -> Workers) mapped to ADK's native agent tree. Within this hierarchy, two fundamentally different types of agents participate as equal workflow citizens:

| Agent Type | ADK Primitive | Execution Model | Examples |
|------------|---------------|-----------------|----------|
| **LLM Agents** | `LlmAgent` | Probabilistic -- LLM decides approach | Director, PM, `plan_agent`, `code_agent`, `review_agent`, `fix_agent` |
| **Custom Agents** | `CustomAgent` (inherits `BaseAgent`) | Guaranteed -- runs exactly as coded | `SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`, `FormatterAgent`, `DependencyResolverAgent`, `RegressionTestAgent`, `ContextBudgetAgent` |

Both types participate in the same state system, emit events into the same unified event stream, and compose naturally with ADK's `SequentialAgent`, `ParallelAgent`, and `LoopAgent` workflow primitives. This is the decisive architectural advantage of Google ADK over alternatives: deterministic agents are first-class workflow citizens, not shadow functions called outside the framework.

For FunctionTools (LLM-callable tool wrappers), see [09-TOOLS.md](./09-TOOLS.md). The key distinction: tools are passive (LLM decides when to call them), agents are active (pipeline structure determines when they run).

Note: The worker-level examples below use auto-code agents (plan/code/lint/test/review). Other workflows define their own agent sets with the same patterns. The architecture is workflow-agnostic; the agent *roles* are workflow-specific.

---

## Agent Hierarchy

```
CEO (dev user / human)
  └── Director (LlmAgent, opus) — root_agent of App
        ├── PM: Project Alpha (LlmAgent, sonnet) — per-project, IS the outer loop
        │     ├── tools: select_ready_batch, run_regression, checkpoint
        │     ├── after_agent_callback: verify_batch_completion
        │     └── sub_agents: DeliverablePipeline instances (workers)
        ├── PM: Project Beta (LlmAgent, sonnet)
        │     └── ...
        └── [cross-project agents as needed]
```

| Tier | Agent Type | Model | Role | Scope |
|------|-----------|-------|------|-------|
| **Director** | `LlmAgent` | opus | Cross-project governance, CEO liaison, strategic decisions, resource allocation | All projects, global settings |
| **PM** | `LlmAgent` | sonnet | Autonomous project management, batch strategy, quality oversight, worker supervision. IS the outer batch loop. | Single project |
| **Workers** | `LlmAgent` + `CustomAgent` | varies | Execution -- planning, coding, reviewing, linting, testing, formatting | Single deliverable |

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
        SkillLoaderAgent(name="LoadSkills"),     # Deterministic
        plan_agent,                                # LLM
        code_agent,                                # LLM
        LinterAgent(name="Lint"),                  # Deterministic
        TestRunnerAgent(name="Test"),               # Deterministic
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM
                fix_agent,                         # LLM
                LinterAgent(name="ReLint"),        # Deterministic
                TestRunnerAgent(name="ReTest"),     # Deterministic
            ]
        )
    ]
)
```

---

## Director Agent

The Director is the **permanent** `root_agent` of the ADK `App`. It is created at worker startup, not per workflow execution.

| Property | Value |
|----------|-------|
| **Role** | Cross-project governance, CEO liaison, strategic decisions, resource allocation |
| **ADK Type** | `LlmAgent` |
| **Model** | `anthropic/claude-opus-4-6` (strategic reasoning requires strongest model) |
| **Scope** | All projects, global settings |
| **Sub-agents** | PM agents (one per active project), cross-project utility agents |

### Capabilities

- **Full observability** into all active projects via event stream and supervision hooks
- **Direct intervention** in any project when patterns go wrong
- **Multi-level memory** accumulation (standards, project patterns, CEO preferences)
- **Hard limit enforcement** -- sets per-project resource limits (cost, time, concurrency)
- **Intelligent escalation** -- decides when to pause for CEO input (rare, due to accumulated memory)
- **Cross-project pattern propagation** -- learnings from one project inform others
- **Tools and skills** -- like all agents, Director has access to FunctionTools (governance tools, resource management) and skills (governance policies, global conventions)

### ADK Integration

```python
director_agent = LlmAgent(
    name="Director",
    model="anthropic/claude-opus-4-6",
    instruction="Cross-project governance agent. Manage PMs, allocate resources, "
                "enforce hard limits, intervene when patterns go wrong.",
    sub_agents=[pm_alpha, pm_beta],  # PM agents are Director's sub_agents
)

# Director is the permanent root_agent
app = App(name="autobuilder", root_agent=director_agent, ...)
```

---

## PM Agent

PMs are per-project autonomous managers. They use LLM reasoning (not programmatic orchestration) to manage the outer batch loop -- selecting batches, supervising workers, and handling failures.

| Property | Value |
|----------|-------|
| **Role** | Autonomous project management, batch strategy, quality oversight, worker supervision. IS the outer batch loop. |
| **ADK Type** | `LlmAgent` |
| **Model** | `anthropic/claude-sonnet-4-5-20250929` (project management reasoning) |
| **Scope** | Single project |
| **Tools** | `select_ready_batch`, `run_regression_tests`, `checkpoint_project` |
| **Callbacks** | `after_agent_callback: verify_batch_completion` |
| **Sub-agents** | `DeliverablePipeline` instances (workers) |

### Why LlmAgent, Not CustomAgent

PMs need LLM reasoning to:
- Decide batch strategy based on project context
- Handle unexpected failures without escalating every issue to Director
- Reorder deliverables based on discovered dependencies
- Assess quality gate failures and decide retry vs. escalate vs. skip
- Reason between batches -- a mechanical loop cannot adapt strategy based on emergent patterns

### PM as the Outer Loop

The PM manages the batch execution loop directly, rather than delegating to a separate orchestrator agent. Mechanical operations are exposed as FunctionTools; deterministic safety is provided by callbacks:

| When | Who | How |
|------|-----|-----|
| Before batch | PM (LLM) | Reasons about batch composition via `select_ready_batch` tool, sets strategy |
| During batch | Callbacks (deterministic) | `after_agent_callback` monitors each pipeline, flags critical failures |
| After batch | PM (LLM) | Observes results, runs `run_regression_tests`, decides retry/skip/escalate/continue |
| Between batches | PM (LLM) | Full reasoning -- reorder, adjust, `checkpoint_project`, escalate to Director |

### ADK Integration

```python
pm_alpha = LlmAgent(
    name="PM_ProjectAlpha",
    model="anthropic/claude-sonnet-4-5-20250929",
    instruction="Autonomous project manager for Project Alpha. You ARE the outer batch loop. "
                "Use select_ready_batch to pick work, supervise DeliverablePipeline workers, "
                "run regression tests between batches, checkpoint progress, and escalate only "
                "when you cannot resolve an issue.",
    tools=[
        FunctionTool(select_ready_batch),
        FunctionTool(run_regression_tests),
        FunctionTool(checkpoint_project),
    ],
    sub_agents=[],  # DeliverablePipeline instances added dynamically per batch
    after_agent_callback=verify_batch_completion,
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

### plan_agent (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Decompose a feature specification into a structured implementation plan |
| **Input** | `{current_deliverable_spec}`, `{loaded_skills}`, `{memory_context}`, `{app:coding_standards}` |
| **Output** | `output_key: "implementation_plan"` |
| **Model** | `anthropic/claude-opus-4-6` (planning benefits from strongest reasoning) |
| **Tool Access** | Read-only -- filesystem read, directory list, search. No write tools. |

The plan agent reads the feature specification, loaded skills, cross-session memory context, and project coding standards from session state. It produces a structured implementation plan that the code agent consumes. It never writes code or modifies files.

### code_agent (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Implement code according to the plan, using project conventions from skills |
| **Input** | `{implementation_plan}`, `{loaded_skills}`, `{app:coding_standards}` |
| **Output** | `output_key: "code_output"` |
| **Model** | `anthropic/claude-sonnet-4-5-20250929` (standard complexity) or `anthropic/claude-opus-4-6` (complex architecture) |
| **Tool Access** | Full -- filesystem read/write/edit, bash execution, git operations |

The code agent consumes the structured plan and writes implementation code. Model selection is handled dynamically by the LLM Router based on task complexity. The code agent has full write access to the filesystem within its git worktree.

### review_agent (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Evaluate code quality against project standards, lint results, and test results |
| **Input** | `{code_output}`, `{lint_results}`, `{test_results}`, `{loaded_skills}` |
| **Output** | `output_key: "review_result"` |
| **Model** | `anthropic/claude-sonnet-4-5-20250929` |
| **Tool Access** | Read-only -- filesystem read, directory list, search. No write tools. |

The review agent reads the code output alongside lint and test results written to state by deterministic agents. It evaluates quality and either approves the feature or produces structured feedback for the fix agent. If the review fails, the `LoopAgent` wrapper triggers another fix/lint/test/review cycle (up to `max_iterations`).

### fix_agent (auto-code example)

| Property | Value |
|----------|-------|
| **Role** | Apply targeted fixes based on review feedback |
| **Input** | `{review_result}`, `{code_output}`, `{lint_results}`, `{test_results}` |
| **Output** | `output_key: "code_output"` (overwrites previous code output) |
| **Model** | `anthropic/claude-sonnet-4-5-20250929` |
| **Tool Access** | Full -- filesystem read/write/edit, bash execution |

The fix agent receives structured review feedback and applies targeted corrections. It operates within the `LoopAgent` review cycle, iterating until the review agent approves or `max_iterations` is reached.

### Instruction Patterns

All LLM agents receive instructions through a layered mechanism:

| Layer | Mechanism | What It Provides |
|-------|-----------|-----------------|
| 1 | Static instruction string | Base personality and role definition |
| 2 | `InstructionProvider` function | Project conventions, feature spec, patterns (resolved at invocation time from state) |
| 3 | `before_model_callback` | File context, codebase analysis, test results (injected right before LLM call) |
| 4 | `{key}` state templates | Direct injection of specific state values into instruction text |

---

## Worker-Tier Custom Agents

Worker-tier deterministic agents inherit from ADK's `BaseAgent` and implement `_run_async_impl`. They execute guaranteed workflow steps that must not be skippable by LLM judgment. Each emits events into the unified event stream and writes results to session state.

The `SkillLoaderAgent` is shared across all workflows at worker level. Other deterministic agents are workflow-specific -- auto-code uses LinterAgent and TestRunnerAgent; other workflows define their own validators appropriate to their output type.

Like all agents, deterministic agents execute inside worker processes. Their subprocess calls (linter, test runner, formatter) have access to the worker's filesystem and environment.

### SkillLoaderAgent

**Purpose:** Resolve and load relevant skills into session state as the first step in every feature pipeline.

Matches skills against current feature context using deterministic pattern matching (no LLM call). Writes matched skill content to state so all subsequent agents in the pipeline can access it.

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

**Why a CustomAgent instead of a tool:** Skill resolution must be observable in the event stream, deterministic (cannot be skipped by LLM judgment), and load skills into state once for all subsequent agents. A FunctionTool would be LLM-discretionary.

### LinterAgent

**Purpose:** Run the project linter against generated code and write structured results to session state.

| State Write | Value |
|-------------|-------|
| `lint_results` | Structured lint output (errors, warnings, file locations) |
| `lint_passed` | Boolean pass/fail |

The review agent reads `{lint_results}` to evaluate code quality. If lint fails, the fix agent receives the errors as actionable feedback.

### TestRunnerAgent

**Purpose:** Run the project test suite against generated code and write structured results to session state.

| State Write | Value |
|-------------|-------|
| `test_results` | Structured test output (passed, failed, errors, coverage) |
| `tests_passed` | Boolean pass/fail |

### FormatterAgent

**Purpose:** Run the project code formatter (e.g., Black, Prettier) on generated code. Unlike lint, formatting is auto-corrective -- it modifies files directly.

### DependencyResolverAgent

**Purpose:** Perform topological sorting of features based on their declared dependencies. Determines which features can execute in parallel and which must wait for predecessors.

This agent runs once before the batch loop begins. It writes the sorted feature execution order to session state, which the PM reads (via `select_ready_batch` tool) to construct batches.

### RegressionTestAgent

**Purpose:** Run cross-feature regression tests after each batch completes. Ensures that newly implemented features have not broken previously completed features.

Runs at the batch level (after `ParallelAgent` completes), not at the individual feature level. The PM triggers this via the `run_regression_tests` tool.

### ContextBudgetAgent

**Purpose:** Check token usage against context window limits and trigger compression if needed.

Implements the gap identified in ADK: there is no built-in context-window usage metric. This agent token-counts the assembled `LlmRequest` via `before_model_callback`, writes the usage percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). Approximately 50 lines of implementation.

---

## Plan/Execute Separation

**Architecture Decision #5:** Planning agents never write code; execution agents consume structured plans.

This principle is adopted from oh-my-opencode's Prometheus/Atlas pattern, where strict role boundaries between planning and execution proved effective at scale across 11 specialized agents.

### How It Works in AutoBuilder

```
plan_agent (LLM)          code_agent (LLM)
  |                          |
  | Reads: feature spec,     | Reads: implementation_plan,
  |   skills, memory,        |   skills, coding_standards
  |   coding_standards       |
  |                          |
  | Writes:                  | Writes:
  |   implementation_plan    |   code_output (files)
  |                          |
  | Tools: READ-ONLY         | Tools: FULL ACCESS
  |   file_read              |   file_read, file_write,
  |   file_search            |   file_edit, bash_exec,
  |   directory_list         |   git_commit, git_diff
```

### Why This Matters

1. **Prevents scope creep** -- a planning agent with write access might start "just writing a quick file" instead of producing a structured plan
2. **Enables better review** -- the plan is a discrete artifact that can be evaluated before any code is written
3. **Supports different models** -- planning benefits from the strongest reasoning model; implementation can use a capable but faster model
4. **Improves debuggability** -- when code is wrong, you can trace whether the plan was wrong or the implementation deviated from a good plan

---

## Agent Tool Restrictions

**Architecture Decision #6:** Read-only agents for exploration prevent scope creep.

All agent tiers (Director, PM, Workers) have access to tools and skills. However, not all agents should have access to *all* tools. AutoBuilder enforces role-based tool restrictions across every tier:

| Agent | Filesystem | Execution | Git |
|-------|-----------|-----------|-----|
| `plan_agent` | Read-only (`file_read`, `file_search`, `directory_list`) | None | Read-only (`git_status`, `git_diff`) |
| `code_agent` | Full (`file_read`, `file_write`, `file_edit`) | `bash_exec` | Full (`git_commit`, `git_branch`) |
| `review_agent` | Read-only | None | Read-only |
| `fix_agent` | Full | `bash_exec` | None (code agent handles commits) |

ADK supports this through `BaseToolset.get_tools()`, which returns different tool sets based on the agent or feature type. This keeps tool restriction logic centralized rather than scattered across agent definitions.

All tool access is within the worker's filesystem context, scoped to the appropriate git worktree for the feature being executed.

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
```

For full model reference (all providers, pricing, fallback chains): see [11-PROVIDERS.md](./11-PROVIDERS.md).

### Implementation

```python
class LlmRouter:
    """Selects optimal model per task based on routing rules."""

    def __init__(self, routing_config: RoutingConfig):
        self.rules = routing_config.rules
        self.fallback_chains = routing_config.fallback_chains

    def select_model(self, task_type: str, complexity: str = "standard") -> str:
        """Returns LiteLLM model string for the given task context."""
        for rule in self.rules:
            if rule.matches(task_type, complexity):
                return rule.model
        return self.fallback_chains.get(task_type, self.default_model)
```

### Fallback Chain Resolution

Provider fallback chains use 3-step resolution (adopted from oh-my-opencode):

1. **User override** -- if the user has specified a model preference in `user:` state, use it
2. **Fallback chain** -- if the primary model is unavailable/rate-limited, walk the fallback chain
3. **Default** -- if all else fails, use the system default model

### Integration with ADK

Each `LlmAgent` can have its model set dynamically. The router runs in one of two ways:

- **At agent construction time** -- when the PM builds the pipeline for each deliverable batch
- **Via `before_model_callback`** -- to override the model on the `LlmRequest` at invocation time

Both approaches keep routing logic centralized rather than scattered across individual agent definitions.

### Phase 1 Implementation

Start simple: static routing config mapping `task_type` to model. No ML-based routing, no cost optimization. A clean lookup table that is easy to change. Phase 2 adds cost tracking, latency monitoring, and adaptive selection.

---

## Agent Communication via Session State

### Hierarchical Communication

Between tiers, agents communicate via ADK's delegation primitives:

| Pattern | Mechanism | Example |
|---------|-----------|---------|
| Director -> PM delegation | `transfer_to_agent` or `AgentTool` | Director assigns a project to a PM |
| PM -> Worker orchestration | `sub_agents` tree | PM constructs DeliverablePipeline workers per batch |
| Worker -> PM escalation | State write + event | Worker writes failure to state; PM reads and decides |
| PM -> Director escalation | State write + event | PM writes unresolvable issue; Director intervenes |
| Director observation | `before_agent_callback` / `after_agent_callback` | Director monitors PM events via supervision hooks |

### Worker-Level Communication

Within a pipeline tier, agents do not communicate via direct message passing. All inter-agent communication flows through session state using four mechanisms:

### 1. output_key

Each agent writes its result to a named state key. The next agent in the pipeline reads from that key.

```
plan_agent  --writes-->  state["implementation_plan"]
code_agent  --reads-->   state["implementation_plan"]
code_agent  --writes-->  state["code_output"]
```

### 2. {key} Templates

Agent instructions reference state values via template injection. ADK auto-resolves these at invocation time.

```python
plan_agent = LlmAgent(
    name="plan_agent",
    instruction="""
    Implement the following deliverable: {current_deliverable_spec}

    Project coding standards: {app:coding_standards}

    Available skills for this task:
    {loaded_skills}
    """,
    output_key="implementation_plan",
)
```

Use `{key?}` for optional keys that may not exist in state.

### 3. InstructionProvider

A dynamic function that reads state and constructs context-appropriate instructions at invocation time. More powerful than static templates when the instruction structure itself needs to change based on context.

```python
def plan_instruction_provider(agent, state):
    base = "You are a planning agent. Produce a structured implementation plan."
    if state.get("loaded_skills"):
        base += f"\n\nRelevant skills:\n{state['loaded_skills']}"
    if state.get("memory_context"):
        base += f"\n\nPrior learnings:\n{state['memory_context']}"
    return base
```

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

### Communication Flow Through the Pipeline

```
Session starts
  |
  v
SkillLoaderAgent --> state["loaded_skills"], state["loaded_skill_names"]
  |
  v
PreloadMemoryTool --> state["memory_context"]
  |
  v
plan_agent reads: {current_deliverable_spec}, {loaded_skills}, {memory_context}, {app:coding_standards}
plan_agent writes: state["implementation_plan"]
  |
  v
code_agent reads: {implementation_plan}, {loaded_skills}, {app:coding_standards}
code_agent writes: state["code_output"]
  |
  v
LinterAgent writes: state["lint_results"], state["lint_passed"]
TestRunnerAgent writes: state["test_results"], state["tests_passed"]
  |
  v
review_agent reads: {code_output}, {lint_results}, {test_results}, {loaded_skills}
review_agent writes: state["review_result"]
  |
  v
(if review fails) fix_agent reads: {review_result}, {code_output}, {lint_results}, {test_results}
(if review fails) fix_agent writes: state["code_output"] (overwrite)
```

---

**Document Version:** 2.2
**Last Updated:** 2026-02-16
**Status:** Framework Validated -- Prototyping Phase
