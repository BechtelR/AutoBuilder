# Workflow Composition System

**AutoBuilder Platform**
**Workflow Architecture Reference**

---

## Table of Contents

1. [Why This Cannot Be Deferred](#why-this-cannot-be-deferred)
2. [Architecture: Workflows as Discoverable, Composable Units](#architecture-workflows-as-discoverable-composable-units)
3. [Workflow Manifest](#workflow-manifest)
4. [WorkflowRegistry](#workflowregistry)
5. [What Is Shared vs. Workflow-Specific](#what-is-shared-vs-workflow-specific)
6. [Compound Workflows](#compound-workflows)
7. [auto-code: The First Workflow](#auto-code-the-first-workflow)
8. [Workflow Execution Model](#workflow-execution-model)

---

## Why This Cannot Be Deferred

Architecture Decision #15 states: workflows must be pluggable from day one, even if only one workflow ships initially.

If the auto-code pipeline structure is hardcoded and other workflows are bolted on later, assumptions baked into the core become structural debt:

- **Tool registries coupled to coding tools** — an auto-design workflow needs design tools (Figma export, image generation), not `file_edit` and `bash_exec`
- **State keys assuming code artifacts** — `code_output`, `lint_results`, `test_results` are meaningless in an auto-market workflow that produces campaign copy and channel strategies
- **Pipeline stages assuming lint/test/review** — an auto-research workflow produces reports, not code. Its quality gates are source verification and citation checking, not linting
- **Quality gates assuming code validation** — every workflow needs deterministic quality gates, but the *type* of gate varies: lint/test for code, source verification for research, constraint validation for design

The cost of making workflows pluggable from the start is low (a manifest format, a registry, a discovery pattern). The cost of retrofitting pluggability after hardcoding auto-code assumptions is high (ripping out baked-in assumptions across the entire codebase).

---

## Architecture: Workflows as Discoverable, Composable Units

A workflow follows the same discovery pattern as skills: a directory with a manifest file and implementation code. The system scans for available workflows and matches them to user requests.

### Directory Structure

```
app/workflows/
├── auto-code/
│   ├── WORKFLOW.yaml          # Manifest: name, description, triggers, tools, config
│   ├── pipeline.py            # ADK agent composition (SequentialAgent, etc.)
│   ├── agents/                # Workflow-specific agent definitions
│   │   ├── plan_agent.py
│   │   ├── code_agent.py
│   │   └── review_agent.py
│   └── skills/                # Workflow-specific skills (extend global skills)
│       └── code/
├── auto-design/
│   ├── WORKFLOW.yaml
│   ├── pipeline.py            # Different pipeline: research -> wireframe -> prototype -> review
│   └── agents/
│       ├── research_agent.py
│       ├── design_agent.py
│       └── critique_agent.py
└── auto-market/
    ├── WORKFLOW.yaml
    ├── pipeline.py            # Different pipeline: strategy -> content -> channel_adapt -> review
    └── agents/
```

Each workflow is a self-contained directory. It declares what it needs (tools, models, configuration) and provides its own pipeline composition and agent definitions. The core system provides shared infrastructure; workflows provide domain-specific orchestration.

---

## Workflow Manifest

Every workflow directory contains a `WORKFLOW.yaml` manifest that declares the workflow's identity, requirements, and configuration.

### Full Example: auto-code

```yaml
# app/workflows/auto-code/WORKFLOW.yaml
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
supports_features: true           # Can decompose spec into features?
supports_parallel: true           # Can run features in parallel?
```

### Manifest Fields

| Field | Type | Required | Description |
|---|---|----------|-------------|
| `name` | string | Yes | Unique workflow identifier. Used in API requests, CLI invocation, and WorkflowRegistry. |
| `description` | string | Yes | Human-readable summary of what the workflow does. |
| `triggers` | list | Yes | Conditions that match user requests to this workflow. |
| `required_tools` | list of strings | Yes | FunctionTools that must be available. Pipeline creation fails if any are missing. |
| `optional_tools` | list of strings | No | FunctionTools that enhance the workflow but are not required. |
| `default_models` | dict | No | Default model assignments per task type. Overridden by LLM Router and user preferences. |
| `pipeline_type` | string | Yes | How the pipeline executes: `batch_parallel` (features in parallel batches), `sequential` (one at a time), `single_pass` (no feature decomposition). |
| `supports_features` | boolean | Yes | Whether the workflow can decompose a specification into implementable features. |
| `supports_parallel` | boolean | Yes | Whether features can execute concurrently via `ParallelAgent`. |

### Trigger Matching

Workflow triggers use deterministic keyword matching (same principle as skills: no LLM in matching).

- `keywords` — if the user request contains any of these words, the workflow matches
- `explicit` — if the user explicitly names the workflow (e.g., via CLI `autobuilder run auto-code` or API `POST /workflows/run {"workflow": "auto-code"}`)

If multiple workflows match, the explicit trigger takes precedence. If ambiguous, the system prompts the user to clarify.

---

## WorkflowRegistry

The WorkflowRegistry discovers, manages, and instantiates available workflows. It follows the same scan-and-index pattern as the SkillLibrary.

### Implementation

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

### Key Design Points

**Discovery is automatic.** The registry scans the workflows directory at startup. Adding a new workflow means adding a new directory with a `WORKFLOW.yaml` manifest and a `pipeline.py` module. No registration code, no config file edits.

**Custom workflows override built-in.** The optional `custom_workflows_dir` parameter allows users to provide project-specific or organization-specific workflows that override built-in ones (same name replacement) or extend the available set.

**Pipeline instantiation is deferred.** The registry indexes manifests at startup (lightweight YAML parsing) but only instantiates the ADK pipeline when `create_pipeline()` is called. This avoids loading agent definitions and importing modules for workflows that are not used.

**create_pipeline receives shared infrastructure.** The `tool_registry`, `skill_library`, and `config` are passed to the workflow's `pipeline.py` module, which uses them to construct its ADK agent tree. The workflow does not need to know how tools or skills are managed — it receives them as dependencies.

---

## What Is Shared vs. Workflow-Specific

### Shared Infrastructure (All Workflows Use)

All workflows operate on the same platform foundation:

- **Gateway API** — FastAPI REST + SSE endpoints. Clients interact with workflows through the gateway, not directly.
- **Worker execution** — ARQ workers execute ADK pipelines. Workflows run in worker processes.
- **Tool registry** — FunctionTools available to all workflows (filesystem, bash, git, web, todo)
- **Skill library** — global + project-local skills, loaded by SkillLoaderAgent
- **LLM Router** — dynamic model selection based on task type and routing rules
- **State management** — session/user/app/temp state scopes via ADK's session system, persisted to single database
- **Event bus** — Redis Streams for event distribution (SSE, webhooks, audit)
- **Observability** — unified event stream, OpenTelemetry tracing, ADK Dev UI
- **Outer loop** — BatchOrchestrator (if workflow supports `batch_parallel` pipeline type)
- **App container** — ADK `App` class providing lifecycle management, context compression, resumability
- **Memory service** — cross-session learnings via `MemoryService` (SQLite FTS5 in Phase 1)

### Workflow-Specific

Each workflow defines its own domain-specific concerns:

- **Pipeline composition** — which agents run, in what order, with what loops and parallelism
- **Agent definitions** — instructions, tool subsets, model preferences per agent role
- **Workflow-specific skills** — auto-code has `api-endpoint.md` and `database-migration.md`; auto-design would have `design-system.md` and `accessibility-review.md`
- **Deliverable decomposition strategy** — auto-code decomposes a spec into implementable code deliverables; auto-market decomposes into content pieces and channel strategies
- **Quality gates** — auto-code gates on lint/test/review; auto-design might gate on accessibility audit and visual consistency check; auto-research might gate on source verification and citation completeness
- **Artifact types** — auto-code produces source files and tests; auto-design produces wireframes and prototypes; auto-research produces reports and citations; auto-market produces copy and media assets

---

## Compound Workflows

### What They Are

A compound workflow handles requests that span multiple workflow types. "Design and build a marketing campaign" requires:

1. **auto-design** for visual assets (logo, banner, social media templates)
2. **auto-market** for campaign strategy, copy, and channel adaptation

Neither workflow alone covers the full request.

### How They Work

1. **Decompose the request** into workflow-level tasks. A planning agent identifies which workflows are needed and in what order.
2. **Sequence the workflows** based on dependencies. Design produces assets; marketing references them. Design runs first.
3. **Share state** between workflow executions via session state. The design workflow writes asset references to state; the marketing workflow reads them.

### Architecture Support

Compound workflows are a Phase 2 capability, but the architecture supports them from day one because:

- Workflows are independent units that read/write shared session state
- The WorkflowRegistry can instantiate multiple workflows in sequence
- Session state persists between workflow executions within the same session
- No workflow makes assumptions about being the only workflow in a session
- The gateway can orchestrate multi-workflow jobs via sequential ARQ job enqueueing

### Phase 2 Implementation Sketch

```
User request: "Design and build a marketing campaign for product X"
  |
  v
Gateway receives request, planning agent decomposes into:
  1. auto-design: Create visual assets (logo, banners, social templates)
  2. auto-market: Develop campaign strategy, copy, channel adaptation
  |
  v
Gateway enqueues job 1: auto-design workflow
  |
  v
Worker executes auto-design pipeline
  writes: state["design_assets"], state["brand_guidelines"]
  publishes: completion event to Redis Streams
  |
  v
Gateway receives completion event, enqueues job 2: auto-market workflow
  |
  v
Worker executes auto-market pipeline
  reads: state["design_assets"], state["brand_guidelines"]
  |
  v
Combined output: visual assets + campaign strategy + adapted content
```

---

## auto-code: The First Workflow

auto-code is the first workflow shipped with AutoBuilder. It implements autonomous software development from specification to verified output.

### Pipeline Stages

```
1. Load spec --> generate features (spec-to-feature pipeline)
2. Resolve dependencies (topological sort via DependencyResolverAgent)
3. While incomplete features exist:
   a. Select next batch (respecting deps + concurrency limits)
   b. For each feature in batch (parallel via ParallelAgent):
      i.   Load relevant skills       (deterministic: SkillLoaderAgent)
      ii.  Plan implementation         (LLM: plan_agent)
      iii. Write code                  (LLM: code_agent)
      iv.  Lint code                   (deterministic: LinterAgent)
      v.   Run tests                   (deterministic: TestRunnerAgent)
      vi.  Review quality              (LLM: review_agent)
      vii. Loop steps iii-vi if review fails (max N iterations via LoopAgent)
   c. Merge completed features
   d. Run regression tests             (deterministic: RegressionTestAgent)
   e. Optional: pause for human review (get_user_choice tool)
4. Report completion
```

### ADK Composition

```python
# auto-code inner deliverable pipeline
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),
        plan_agent,
        code_agent,
        LinterAgent(name="Lint"),
        TestRunnerAgent(name="Test"),
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,
                fix_agent,
                LinterAgent(name="ReLint"),
                TestRunnerAgent(name="ReTest"),
            ]
        )
    ]
)

# auto-code outer loop
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
            await run_regression_tests(ctx)
            await checkpoint(ctx)
```

### Key Properties

| Property | Value |
|----------|-------|
| `pipeline_type` | `batch_parallel` |
| `supports_features` | `true` |
| `supports_parallel` | `true` |
| Required tools | `file_read`, `file_write`, `file_edit`, `bash_exec`, `git_status`, `git_commit`, `git_diff` |
| Default planning model | `anthropic/claude-opus-4-6` |
| Default implementation model | `anthropic/claude-sonnet-4-5-20250929` |
| Default review model | `anthropic/claude-sonnet-4-5-20250929` |
| Isolation | Git worktree per feature (parallel features write to separate filesystem locations) |
| Quality gates | Lint pass, test pass, review approval (all mandatory, deterministic enforcement) |
| Max review iterations | 3 (configurable via `LoopAgent.max_iterations`) |

### auto-code Specific Skills

The auto-code workflow includes workflow-specific skills in its `skills/` subdirectory. These extend the global skill library with code-generation-specific knowledge:

```
app/workflows/auto-code/skills/
└── code/
    ├── api-endpoint.md
    ├── data-model.md
    ├── database-migration.md
    └── test-generation.md
```

These skills load in addition to (not instead of) global skills and project-local skills. The SkillLoaderAgent merges all three tiers when resolving matches.

### What Makes auto-code a Workflow, Not a Hardcoded Pipeline

auto-code defines its own:

- Agent definitions (`agents/plan_agent.py`, `agents/code_agent.py`, `agents/review_agent.py`)
- Pipeline composition (`pipeline.py` with the SequentialAgent/ParallelAgent/LoopAgent tree)
- Tool requirements (`required_tools` in WORKFLOW.yaml)
- Feature decomposition strategy (spec-to-feature generation adapted from Autocoder patterns)
- Quality gates (lint + test + review, enforced by deterministic agents)

It does not define:

- How tools work (shared FunctionTools from the tool registry)
- How skills load (shared SkillLoaderAgent + SkillLibrary)
- How models are selected (shared LLM Router)
- How state persists (shared database via DatabaseSessionService)
- How events are traced (shared ADK event stream + OpenTelemetry)
- How events are distributed (shared Redis Streams event bus)
- How jobs are executed (shared ARQ worker infrastructure)

This separation means a second workflow (auto-design, auto-market, auto-research) can reuse all shared infrastructure and provide only its domain-specific pipeline, agents, and skills.

---

## Workflow Execution Model

Workflows execute inside ARQ worker processes, not the gateway. The execution lifecycle is:

1. **Client request** — CLI or dashboard sends `POST /workflows/run` with spec and workflow name
2. **Gateway validation** — validates request, resolves workflow via WorkflowRegistry, creates job record in database
3. **Job enqueueing** — gateway enqueues ARQ job with workflow name, spec, and session ID
4. **Worker pickup** — ARQ worker dequeues job, instantiates ADK pipeline via `WorkflowRegistry.create_pipeline()`
5. **Pipeline execution** — ADK agents execute in worker process. State flows through database. Events publish to Redis Streams.
6. **Event streaming** — Redis Stream consumers push events to SSE endpoints, webhook dispatchers, audit loggers
7. **Completion** — worker marks job complete in database, publishes completion event
8. **Client notification** — client receives completion via SSE stream or polls status endpoint

The gateway never runs ADK pipelines. It is a job broker and event proxy. This means:

- Workers can scale independently (add more workers for higher throughput)
- A crashed worker does not take down the gateway
- Pipeline execution is isolated from API request handling
- ADK is an internal engine behind the anti-corruption layer

---

**Document Version:** 2.0
**Last Updated:** 2026-02-11
**Status:** Framework Validated -- Prototyping Phase
