[← Architecture Overview](../02-ARCHITECTURE.md)

# Workflow Composition System

**AutoBuilder Platform**
**Workflow Architecture Reference**

---

## Table of Contents

1. [Why This Cannot Be Deferred](#why-this-cannot-be-deferred)
2. [Architecture: Workflows as Discoverable, Composable Units](#architecture-workflows-as-discoverable-composable-units)
3. [Workflow Manifest](#workflow-manifest)
4. [Stage Schema](#stage-schema)
5. [WorkflowRegistry](#workflowregistry)
6. [Validators & Quality Gates](#validators--quality-gates)
7. [Completion Criteria & Reports](#completion-criteria--reports)
8. [What Is Shared vs. Workflow-Specific](#what-is-shared-vs-workflow-specific)
9. [Director Workflow Authoring](#director-workflow-authoring)
10. [Workflow Execution Model](#workflow-execution-model)
11. [Compound Workflows](#compound-workflows)
12. [auto-code: The First Workflow](#auto-code-the-first-workflow)

---

## Why This Cannot Be Deferred

Architecture Decision #15: workflows must be pluggable from day one, even if only one workflow ships initially.

If auto-code's structure is hardcoded, assumptions become structural debt: tool registries coupled to coding tools, state keys assuming code artifacts, pipeline stages assuming lint/test/review, quality gates assuming code validation. An auto-research workflow produces cited reports with source verification -- not linted code. Every workflow needs quality gates, but the *type* varies per domain.

The cost of pluggability from the start is low (manifest format, registry, discovery pattern). The cost of retrofitting is high.

---

## Architecture: Workflows as Discoverable, Composable Units

A workflow follows the same discovery pattern as skills: a directory with a manifest file and implementation code. The system scans for available workflows and matches them to user requests.

### Directory Structure

```
app/workflows/                          # Built-in workflows
├── auto-code/
│   ├── WORKFLOW.yaml                   # Manifest: identity, stages, validators, config
│   ├── pipeline.py                     # ADK agent composition
│   ├── agents/                         # Workflow-specific agent definitions (override global by name)
│   │   ├── planner.md
│   │   ├── coder.md
│   │   └── reviewer.md
│   └── skills/                         # Workflow-specific skills (extend global skills)
│       └── code/
├── auto-research/
│   ├── WORKFLOW.yaml
│   ├── pipeline.py
│   └── agents/
└── auto-campaign/
    └── WORKFLOW.yaml                   # Minimal: 2-field manifest is valid

~/.autobuilder/workflows/               # User-level overrides (Decision #72, configurable via AUTOBUILDER_WORKFLOWS_DIR)
└── auto-code/                          # Overrides built-in auto-code for all projects
    ├── WORKFLOW.yaml
    ├── pipeline.py
    └── agents/

~/.autobuilder/workflows/.staging/      # Staging area for Director-authored workflows (not scanned by registry)
└── auto-research/
    ├── WORKFLOW.yaml
    └── pipeline.py
```

Each workflow is a self-contained directory. It declares what it needs (tools, models, configuration) and provides its own pipeline composition and agent definitions. The core system provides shared infrastructure; workflows provide domain-specific orchestration.

**Override model (Decision #72):** Two-tier: built-in (`app/workflows/`) and user-level (`~/.autobuilder/workflows/`, configurable via `AUTOBUILDER_WORKFLOWS_DIR`). The WorkflowRegistry scans built-in first, then user-level; a user-level `auto-code/` replaces the built-in `auto-code/` by name. There are no project-scoped workflows — workflows are selected for a project at creation time, not customized within one. Project-scoped agent and skill overrides (Decision #54) still apply within whichever workflow the project selected.

> **Key distinction**: Agents and skills are customized within a project. Workflows are selected for a project. User-level workflows are consistent with Director authoring being a CEO-level activity, not project-level.

---

## Workflow Manifest

Every workflow directory contains a `WORKFLOW.yaml` manifest that serves as the "operating manual" for that workflow domain (Decision #70). The manifest uses progressive disclosure: a valid manifest requires only `name` and `description`. Everything else has sensible defaults.

**PRD traceability:** PR-4 (stage schema, agents/tools/skills per stage, deliverable format, output format, completion reports), PR-5 (per-stage agent config), PR-8 (resource validation), PR-11 (validator scheduling), PR-22 (three-layer verification).

### Progressive Disclosure

**Tier 1 -- Minimal (2 fields):**

```yaml
name: auto-campaign
description: Generate marketing campaign content from a brief
```

Implied defaults: no triggers (explicit-only), no required tools, `pipeline_type: single_pass`, no stages, no validators, generic completion report.

**Tier 2 -- Standard (identity + infrastructure + stages):**

```yaml
name: auto-research
description: Autonomous research from question to cited report
triggers:
  - keywords: [research, investigate, analyze, study]
  - explicit: auto-research
required_tools: [web_search, web_fetch, file_read, file_write]
pipeline_type: sequential
stages:
  - name: discover
    description: Source discovery and evaluation
    agents: [researcher]
  - name: synthesize
    description: Analysis, synthesis, and report generation
    agents: [writer, reviewer]
```

**Tier 3 -- Comprehensive (full operating manual):** Adds validators, resources, deliverable types, outputs, completion reports, brief templates, conventions, Director guidance, and config. See auto-code manifest in [auto-code: The First Workflow](#auto-code-the-first-workflow).

### Root Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | **Yes** | -- | Unique workflow identifier. Kebab-case. |
| `description` | string | **Yes** | -- | Human-readable summary. Shown in workflow selection. |
| `version` | string | No | `"1"` | Manifest schema version. |
| `triggers` | list[TriggerDef] | No | `[]` | Conditions that match user requests. Empty = explicit-only. |
| `pipeline_type` | PipelineType | No | `"single_pass"` | `single_pass` / `sequential` / `batch_parallel`. |
| `required_tools` | list[string] | No | `[]` | FunctionTools that must be available. |
| `optional_tools` | list[string] | No | `[]` | FunctionTools that enhance but are not required. |
| `default_models` | dict[ModelRole, string] | No | `{}` | Default model assignments per role. |
| `stages` | list[StageDef] | No | `[]` | Ordered stage schema. Omit for single-stage workflows. |
| `validators` | list[ValidatorDef] | No | `[]` | Workflow-level validators (apply across all stages per their `schedule`). |
| `resources` | ResourcesDef | No | `{}` | External resources required before execution. |
| `deliverable` | DeliverableDef | No | `{}` | How deliverables are structured. |
| `outputs` | list[OutputDef] | No | `[]` | Artifact types this workflow produces. |
| `completion_report` | CompletionReportDef | No | `{}` | Completion report structure. |
| `brief_template` | BriefTemplateDef | No | `{}` | What a Brief looks like for this workflow type. |
| `conventions` | list[string] | No | `[]` | Workflow-wide rules injected as GOVERNANCE fragments. |
| `director_guidance` | DirectorGuidanceDef | No | `{}` | Guidance the Director needs for this workflow type. |
| `mcp_servers` | list[McpServerDef] | No | `[]` | MCP servers this workflow can use. McpServerDef has name (str) and required (bool, default false). |
| `config` | dict[string, object] | No | `{}` | Pipeline-specific configuration consumed by `pipeline.py`. |

### Manifest Type Definitions

#### TriggerDef

| Field | Type | Description |
|-------|------|-------------|
| `keywords` | list[string] | Match if user request contains any keyword |
| `explicit` | string | Match if user explicitly names this value |

Each trigger entry contains ONE of `keywords` or `explicit`, not both.

#### DeliverableDef

| Field | Type | Description |
|-------|------|-------------|
| `types` | list[object] | Deliverable type definitions |
| `types[].name` | string | Deliverable type identifier |
| `types[].description` | string | What this deliverable type produces |
| `types[].verification` | list[string] | Validator names applied to this type |

#### OutputDef

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Output artifact type identifier |
| `description` | string | What this output produces |

#### BriefTemplateDef

| Field | Type | Description |
|-------|------|-------------|
| `required_fields` | list[object] | Fields the CEO must provide |
| `required_fields[].name` | string | Field identifier |
| `required_fields[].description` | string | What to provide |
| `optional_fields` | list[object] | Optional context fields |
| `optional_fields[].name` | string | Field identifier |
| `optional_fields[].description` | string | What to provide |
| `optional_fields[].default` | string | Default value if omitted |

#### DirectorGuidanceDef

| Field | Type | Description |
|-------|------|-------------|
| `stage_transition_notes` | dict[string, string] | Per-stage guidance keyed by stage name |
| `escalation_hints` | list[string] | Conditions that should trigger CEO escalation |

### Trigger Matching

Workflow triggers use deterministic keyword matching (no LLM in matching -- same principle as skills).

- `keywords` -- if the user request contains any keyword, the workflow matches
- `explicit` -- if the user explicitly names the workflow

If multiple workflows match, the explicit trigger takes precedence. If ambiguous, the system prompts the user to clarify.

### Resources (PR-8)

Pre-execution resource validation. Three resource types: `credentials` (env vars), `services` (health checks), `knowledge` (files/directories). The Director validates all resources before the first deliverable is dispatched. Missing required resources surface to the CEO queue.

### Conventions & Director Guidance

`conventions` are string rules injected as GOVERNANCE fragments into all agents. For enforceable rules, use `validators`. `director_guidance` provides the Director with stage transition notes, escalation hints, and resource notes for this workflow type.

Full field reference with examples: see [manifest design notes](../.notes/260312_manifest-design.md).

---

## Stage Schema

Stages are the workflow's execution hierarchy (Decision #71). They define what agent configuration and quality gates apply at each point. **Stages are organizational groupings, not execution contexts** -- they share a single PM session, session state, and work session.

**PRD traceability:** PR-4 (stage schema), PR-5 (per-stage agent/tool/skill scoping).

### Design Principles

1. **Organizational, not executional.** No separate execution context or session per stage. Follows Airflow's TaskGroup lesson.
2. **Simple workflows have simple manifests.** Omit `stages` entirely for single-stage workflows.
3. **PM drives transitions, manifest declares structure.** Stage transitions are PM reasoning acts using a reconciliation pattern (observe delta between state and criteria, then act).
4. **Completion criteria compose as AND.** Deterministic checks + LLM evaluation + approval gates must all be satisfied.
5. **Stages and TaskGroups are distinct.** Stages are manifest-declared (DESIGN, BUILD). TaskGroups are PM-created runtime planning artifacts (~1h work units within a stage).

### Stage Definition

```yaml
stages:
  - name: plan
    description: Decompose specification into deliverables
    agents: [planner]
    skills: [task-decomposition]
    tools:
      required: [file_read, web_search]
      add: [spec_analyzer]
      remove: [git_commit]
    models:
      PLAN: anthropic/claude-opus-4-6
    validators:
      - name: dependency_validation
        type: deterministic
        schedule: per_stage
    completion_criteria: all_deliverables_planned
    approval: director
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | **Required** | Stage identifier. Lowercase, no spaces. |
| `description` | string | `""` | What this stage accomplishes. PM reads this. |
| `agents` | list[string] | `[]` | Agent roles active in this stage. Empty = all available. |
| `skills` | list[string] | `[]` | Additional skills to force-load (additive to context matching). |
| `tools` | StageToolsDef | `{}` | Tool scoping: `required`, `add`, `remove` relative to workflow baseline. |
| `models` | dict | `{}` | Model overrides for this stage. Merges with workflow `default_models`. |
| `validators` | list[ValidatorDef] | `[]` | Quality gates for this stage. |
| `completion_criteria` | string | `"all_verified"` | Structured completion condition evaluated by `verify_stage_completion`. |
| `approval` | `"director"` / `"ceo"` / `"auto"` | `"director"` | Who approves stage completion. |

### Per-Stage Configuration Resolution

```
Workflow defaults  <--  Stage overrides  <--  Runtime PM adjustments
```

| Dimension | Workflow-level | Stage-level behavior |
|-----------|---------------|---------------------|
| `agents` | All available | Restrict to listed agents. Omit = all. |
| `tools` | `required_tools` + `optional_tools` | `required` validated before stage start; `add` extends, `remove` narrows workflow tool set. |
| `skills` | Context-matched + role-bound | Stage `skills` force-loads named skills additively. |
| `validators` | Apply across all stages per `schedule` | Stage defines its own validators; workflow-level validators run alongside. |
| `completion` | `all_verified` | Stage specifies. Default is `all_verified` if omitted. |

### PM-Driven Stage Transitions

1. PM executes deliverables within the current stage.
2. After each batch, PM evaluates completion criteria.
3. When met, PM runs stage-completion validators, produces a completion report, publishes `STAGE_COMPLETED`.
4. If approval required, PM enqueues request and waits.
5. On approval, PM advances `pm:current_stage` and reconfigures via `reconfigure_stage` tool (state-driven, no agent tree rebuild).
6. Stages with `approval: auto` auto-advance when `verify_stage_completion()` returns True. PM reasoning is only involved for `approval: director` or `approval: ceo` stages.
7. Last stage complete = workflow complete.

### Stage State Keys

All `pm:` prefixed per Decision #58 (tier-based state key authorization):

```
pm:current_stage          # string: active stage name
pm:stage_index            # int: 0-based index
pm:stage_status           # StageStatus: PENDING | ACTIVE | COMPLETED | FAILED
pm:stages_completed       # list[string]: completed stage names
pm:workflow_stages        # list[dict]: full stage schema from manifest
```

Full stage schema detail: see [stage-schema-design.md](../.notes/260312_stage-schema-design.md).

---

## WorkflowRegistry

The WorkflowRegistry discovers, manages, and instantiates available workflows. It follows the same scan-and-index pattern as the SkillLibrary.

### Interface

```python
class WorkflowRegistry:
    """Discovers and manages available workflows."""

    def __init__(self, workflows_dir: Path, user_workflows_dir: Path | None = None, redis: ArqRedis | None = None):
        self._workflows: dict[str, WorkflowEntry] = {}
        # scan() called separately — not in __init__

    def scan(self) -> None:
        """Scan built-in dir first, then user-level. User-level overrides built-in by name."""

    def match(self, user_request: str) -> list[WorkflowEntry]:
        """Match user request to workflows. Deterministic keyword matching. Returns all matches."""

    def get(self, name: str) -> WorkflowEntry:
        """Get workflow by explicit name."""

    def get_manifest(self, name: str) -> WorkflowManifest:
        """Return parsed manifest for PM/Director consumption."""

    def list_available(self) -> list[WorkflowEntry]:
        """List all discovered workflows with descriptions."""

    def create_pipeline(self, workflow_name: str, pipeline_ctx: PipelineContext) -> BaseAgent:
        """Instantiate the workflow's ADK pipeline with the given context."""
```

`PipelineContext` is a frozen dataclass bundling all shared infrastructure a `pipeline.py` needs: `registry` (AgentRegistry), `instruction_ctx` (InstructionContext), `manifest` (WorkflowManifest), `skill_library` (SkillLibrary), `toolset` (GlobalToolset), and `before_model_callback`. A convenience `build()` classmethod constructs it from gateway dependencies.

Every workflow's `create_pipeline` function conforms to the `PipelineFactory` Protocol:

```python
class PipelineFactory(Protocol):
    async def __call__(self, ctx: PipelineContext) -> BaseAgent: ...
```

This enables static type checking for built-in workflows and runtime validation at dynamic import time for user-level workflows. Signature mismatches raise `ConfigurationError` immediately.

Three standard pipeline pattern functions conforming to `PipelineFactory` are provided:

- `single_pass_pipeline(ctx: PipelineContext) -> BaseAgent` -- one-shot agent execution
- `sequential_pipeline(ctx: PipelineContext) -> BaseAgent` -- ordered stage execution
- `batch_parallel_pipeline(ctx: PipelineContext) -> BaseAgent` -- parallel deliverable batches

Custom `pipeline.py` modules can use these patterns directly or compose their own agent trees.

### Key Design Points

**Discovery is automatic.** Adding a new workflow = adding a directory with `WORKFLOW.yaml` and `pipeline.py`. No registration code.

**User-level overrides (Decision #72).** `user_workflows_dir` (default: `~/.autobuilder/workflows/`, configurable via `AUTOBUILDER_WORKFLOWS_DIR`) allows user-authored workflows that override built-in by name or extend the set. No project-scoped workflows exist.

**Pipeline instantiation is deferred.** Manifests are indexed at startup; ADK pipeline construction happens only on `create_pipeline()`.

**get_manifest() enables reasoning.** PM and Director read the parsed manifest to understand stages, validators, and completion structure.

**create_pipeline receives PipelineContext.** The `PipelineContext` bundles `registry`, `instruction_ctx`, `manifest`, `skill_library`, `toolset`, and `before_model_callback` into a single object. Pipeline construction uses `registry.build(agent_name, ctx)` with the 3-scope cascade (global -> workflow -> project) for agents and skills. Workflows themselves are two-tier (built-in -> user-level). This is the composability mechanism (Decision #15).

### Manifest Validation

Validation runs at scan time. Invalid manifests fail loudly and are excluded from the registry.

**Required:** `name` present and kebab-case, `description` non-empty, `pipeline_type` valid if present, stage names unique, validator names unique across manifest, `deliverable.types[].verification` references declared validators.

**Warning (non-blocking):** `stages` defined but `pipeline_type` is `single_pass`, validator references agents not in any stage's agent list, resource credentials reference unset env vars.

---

## Validators & Quality Gates

Validators are mandatory quality gates that cannot be skipped by agent judgment (PR-11). They produce machine-generated evidence for completion reports (PR-22). Validators are evaluation functions dispatched by `ValidatorRunner`, not CustomAgent classes (spec DD-2 refines Decision #74). They wrap existing agent output (state keys) and record structured evidence. Skills teach the Director *about* validators; validators themselves are platform code.

### Validator Definition

```yaml
validators:
  - name: lint_check
    type: deterministic
    agent: linter
    schedule: per_deliverable
  - name: code_review
    type: deterministic
    agent: reviewer
    schedule: per_deliverable
    config:
      max_cycles: 3
  - name: regression_tests
    type: deterministic
    agent: tester
    schedule: per_batch
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | **Required** | Unique within the manifest. |
| `type` | `"deterministic"` / `"llm"` / `"approval"` | **Required** | Execution model. |
| `agent` | string | `""` | Agent role that runs this validator. |
| `schedule` | ValidatorSchedule | **Required** | When to run. |
| `config` | dict | `{}` | Validator-specific configuration. |
| `required` | bool | `true` | `false` = advisory only (logged, not blocking). |

### Validator Schedule

| Schedule | When It Runs | Example |
|----------|-------------|---------|
| `per_deliverable` | After each deliverable completes | lint, test, citation check |
| `per_batch` | After each batch completes | regression tests |
| `per_taskgroup` | After each TaskGroup completes within a stage | TaskGroup completion report |
| `per_stage` | Once at stage completion | integration tests, architecture conformance |

`per_deliverable` validators are wired into the DeliverablePipeline by `pipeline.py`. Higher-granularity validators are invoked by the PM's outer loop at the appropriate point.

### Standard Validators (Decision #74)

Ten standard validators ship with the platform (six in Phase 7; four additional research/integration validators in Phase 7b):

| Name | Type | Domain | What It Checks |
|------|------|--------|---------------|
| `lint_check` | deterministic | code | Configured linter passes with zero errors |
| `test_suite` | deterministic | code | Test runner exits 0, all tests pass |
| `regression_tests` | deterministic | code | Full test suite passes after batch changes |
| `dependency_validation` | deterministic | code | Deliverable dependency graph is acyclic |
| `deliverable_status_check` | deterministic | universal | All deliverables at required status |
| `source_verification` | llm | research | Sources are credible, accessible, relevant |
| `citation_check` | deterministic | research | All claims cite sources, citations valid |
| `content_review` | llm | research | Content is coherent, complete, well-structured |
| `code_review` | deterministic | code | Code quality, patterns, correctness |
| `architecture_conformance` | llm | code | Implementation matches documented design |

The Director cannot create custom validators (requires Python deployment) but can compose existing validators in novel combinations via the manifest.

---

## Completion Criteria & Reports

### Completion Criteria Composition (Decision #71)

Three types of completion criteria compose via AND:

| Type | Key | What It Checks | Who Evaluates |
|------|-----|---------------|---------------|
| **Deliverable** | `deliverables` | All deliverables at required status? | Deterministic: query DB |
| **Validator** | `validators` | All required validators passed? | Deterministic: check results |
| **Approval** | `approval` | Required authority approved? | Human via CEO/Director queue |

Standard deliverable conditions:

| Value | Meaning |
|-------|---------|
| `all_verified` | Every deliverable COMPLETED with all validators passed. Default. |
| `all_deliverables_planned` | Every deliverable has an implementation plan. For planning stages. |

### TaskGroup Close Conditions (PR-23)

A TaskGroup cannot close while any deliverable is outstanding, any scheduled validator is failing, or any escalation is unresolved. This is enforced deterministically via `verify_taskgroup_completion` -- a hard gate that PM reasoning cannot override. The same pattern applies at stage level via `verify_stage_completion`.

### Three-Layer Verification Reports (PR-22, Decision #75)

Every stage and TaskGroup completion report includes verification layers:

```yaml
completion_report:
  layers:
    - name: functional
      description: Does it work as specified?
      evidence_sources: [test_suite, regression_tests]
    - name: architectural
      description: Does the implementation match documented architecture?
      evidence_sources: [architecture_conformance]
    - name: contract
      description: Were all deliverables completed?
      evidence_sources: [deliverable_status_check]
  additional_sections:
    - name: code_quality
      description: Lint results, test coverage, review cycle counts
```

Each layer requires machine-generated evidence from validators. Assertion alone is never sufficient. Default layers (functional, architectural, contract) apply when `layers` is omitted. Manifests can configure which layers apply.

Workflows add domain-specific sections via `additional_sections`.

---

## What Is Shared vs. Workflow-Specific

### Shared Infrastructure (All Workflows Use)

Gateway API, ARQ worker execution, GlobalToolset (per-role), SkillLibrary + SkillLoaderAgent, AgentRegistry (Decision #54), InstructionAssembler (Decisions #50, #55), WorkflowRegistry, LLM Router, session state management, Redis Streams event bus, OpenTelemetry observability, PM outer loop, MemoryService.

### Workflow-Specific

Each workflow defines its own domain-specific concerns:

- **Pipeline composition** -- agent order, loops, parallelism
- **Agent definitions** -- instructions, tool subsets, model preferences per role
- **Workflow-specific skills** -- domain knowledge (e.g., auto-code has `api-endpoint`, `database-migration`)
- **Stage schema** -- organizational stages with per-stage scoping
- **Deliverable decomposition** -- how specs decompose into implementable units
- **Quality gates** -- which validators, at what schedule
- **Artifact types** -- what the workflow produces

---

## Director Workflow Authoring -- Phase 7b

The Director is a workflow author, not just a workflow executor (Decision #76). It creates new workflows through conversation with the CEO, using existing file tools guided by authoring skills.

**PRD traceability:** PR-6 ("workflows designed to model how to compose new workflows, by users or by the Director itself").

### Core Insight

The Director already has every primitive it needs. Workflow authoring is files-on-disk:

- **WORKFLOW.yaml** -- written via `file_write`
- **pipeline.py** -- written from established patterns (Decision #73)
- **agents/*.md** -- markdown files with YAML frontmatter
- **skills/*/SKILL.md** -- standard skill format

### 6-Phase Authoring Lifecycle

| Phase | Activity | Output |
|-------|----------|--------|
| **A. Requirements** | Structured conversation with CEO | Process understanding |
| **B. Resource Discovery** | Query available tools, MCP servers, credentials, skills, workflows | Gap analysis |
| **C. Draft Composition** | Write manifest, pipeline.py, agents, skills to **staging** | Workflow artifacts |
| **D. Validation** | Run L1-L4 validation (schema, references, parse, structural) | Validation report |
| **E. CEO Review** | Present workflow summary + validation results via CEO queue | Approval/rejection |
| **F. Activation** | Move from staging to active directory, git commit | Live workflow |

**Staging convention:** Authored workflows are written to `~/.autobuilder/workflows/.staging/{name}/` before activation. The staging directory is not scanned by WorkflowRegistry. Activation = moving files to `~/.autobuilder/workflows/{name}/` after CEO approval.

### CEO Resource Library

Five discovery tools let the Director map CEO requirements to available resources:

| Tool | Returns |
|------|---------|
| `list_available_tools()` | Registered FunctionTools with signatures |
| `list_mcp_servers()` | MCP server capabilities and status |
| `list_configured_credentials()` | Credential names (never values) |
| `list_workflows()` | Registered workflows with manifests |
| `list_available_skills()` | Skills with frontmatter metadata |

These are thin query facades over existing registries -- no new "Resource Library" entity.

### Pipeline.py Generation (Decision #73)

The Director writes `pipeline.py` from scratch, guided by skills and the three pipeline patterns (`single_pass`, `sequential`, `batch_parallel`). CEO reviews the pipeline code at the activation gate.

### Authoring Skills (Decision #77)

Nine skills support workflow authoring: 1 Director-tier master skill (`director-workflow-composition`), 4 enhanced technical reference skills (`workflow-authoring`, `agent-definition`, `skill-authoring`, `project-conventions`), 2 quality framework skills (`workflow-quality`, `workflow-testing`), and 2 domain pattern skills (`software-development-patterns`, `research-patterns`).

### Security Model

| Action | Approval |
|--------|----------|
| Write to staging | None (free authoring) |
| Activate new workflow | CEO approval required |
| Modify active workflow | CEO approval required |
| Create `type: llm` agents | Allowed (sandboxed by tool_role ceiling) |
| Create `type: custom` agents | Cannot do (requires Python deployment) |
| Create new FunctionTools | Cannot do (separate capability) |
| Access credential values | Cannot do (names only) |

### Workflow Improvement Loop

Feedback from execution (failure patterns, escalation history, workflow memory) flows back to improvement proposals. The Director drafts changes to staging, presents evidence-backed proposals to the CEO, and activates on approval.

Full authoring detail: see [director-authoring-design.md](../.notes/260312_director-authoring-design.md) and [authoring-skills-design.md](../.notes/260312_authoring-skills-design.md).

---

## Workflow Execution Model

Workflows execute inside ARQ worker processes, not the gateway. The execution lifecycle:

1. **Client request** -- CLI or dashboard sends `POST /workflows/run` with spec and workflow name
2. **Gateway validation** -- validates request, resolves workflow via WorkflowRegistry, creates job record
3. **Job enqueueing** -- gateway enqueues ARQ job with workflow name, spec, and session ID
4. **Worker pickup** -- ARQ worker dequeues job, instantiates ADK pipeline via `WorkflowRegistry.create_pipeline()`
5. **Pipeline execution** -- ADK agents execute in worker process. State flows through database. Events publish to Redis Streams.
6. **Stage transitions** -- PM drives stage advancement (if multi-stage). Reconfiguration is state-driven within the same session.
7. **Event streaming** -- Redis Stream consumers push events to SSE endpoints, webhook dispatchers, audit loggers
8. **Completion** -- worker marks job complete, publishes completion event with three-layer verification report

The gateway never runs ADK pipelines. It is a job broker and event proxy. Workers scale independently, crashed workers do not take down the gateway, and ADK remains an internal engine behind the anti-corruption layer.

---

## Compound Workflows -- Phase 11 (F17)

A compound workflow handles requests spanning multiple workflow types ("Design and build a marketing campaign" = auto-design + auto-market). This is a future capability, but the architecture supports it from day one: workflows are independent units sharing session state, the registry can instantiate multiple workflows in sequence, and no workflow assumes it is the only one in a session.

---

## auto-code: The First Workflow

auto-code implements autonomous software development from specification to verified output.

auto-code's `pipeline.py` at `app/workflows/auto-code/pipeline.py` composes the auto-code-specific agent tree (skill_loader -> memory_loader -> planner -> coder -> formatter -> linter -> tester -> diagnostics -> review_cycle) using `PipelineContext`. This is domain-specific orchestration, not shared infrastructure.

### Stage Schema

```yaml
stages:
  - name: shape
    description: Refine brief into unambiguous specification
    agents: [planner]
    validators:
      - name: spec_completeness
        type: llm
        agent: planner
        schedule: per_stage
    approval: director

  - name: design
    description: Architecture, data models, API contracts, dependency graph
    agents: [planner, reviewer]
    validators:
      - name: design_consistency
        type: llm
        agent: reviewer
        schedule: per_stage
    approval: director

  - name: plan
    description: Decompose design into dependency-ordered deliverables
    agents: [planner]
    validators:
      - name: dependency_validation
        type: deterministic
        agent: ""
        schedule: per_stage
    completion_criteria: all_deliverables_planned
    approval: auto

  - name: build
    description: Implement, lint, test, and review all deliverables
    agents: [coder, reviewer, fixer, formatter, linter, tester, diagnostics]
    validators:
      - name: lint_check
        type: deterministic
        agent: linter
        schedule: per_deliverable
      - name: test_suite
        type: deterministic
        agent: tester
        schedule: per_deliverable
      - name: code_review
        type: deterministic
        agent: reviewer
        schedule: per_deliverable
        config: { max_cycles: 3 }
      - name: regression_tests
        type: deterministic
        agent: tester
        schedule: per_batch
    approval: auto

  - name: integrate
    description: Integration testing and final verification
    agents: [tester, reviewer, diagnostics]
    validators:
      - name: integration_tests  # Phase 7b stub
        type: deterministic
        agent: tester
        schedule: per_stage
      - name: architecture_conformance  # Phase 7b stub
        type: llm
        agent: reviewer
        schedule: per_stage
        required: false
      - name: final_approval
        type: approval
        schedule: per_stage
    approval: ceo
```

> **Simplified for architectural overview.** The [Tier 3 reference manifest](../build-phase/phase-7/reference/workflow-manifest-example.yaml) is the authoritative, buildable source for auto-code's `WORKFLOW.yaml` — including per-stage `tools`, `skills`, `models`, validator `config`, and all optional fields.

### PM Execution Flow

```
Work session starts -> Load manifest, read stages
  -> pm:current_stage = "shape"

SHAPE:  planner refines brief -> spec_completeness -> Director approval
DESIGN: planner + reviewer produce architecture -> design_consistency -> Director approval
PLAN:   planner decomposes into deliverables -> dependency_validation -> auto-advance
BUILD:  batch_parallel execution (select_ready_batch -> parallel pipelines -> checkpoint
        -> regression -> repeat). Per-deliverable: lint, test, code_review.
INTEGRATE: integration tests -> architecture_conformance -> CEO approval -> workflow complete
```

### Key Properties

| Property | Value |
|----------|-------|
| `pipeline_type` | `batch_parallel` |
| Required tools | `file_read`, `file_write`, `file_edit`, `bash_exec`, `git_status`, `git_commit`, `git_diff` |
| Default planning model | `anthropic/claude-opus-4-6` |
| Default implementation model | `anthropic/claude-sonnet-4-6` |
| Isolation | Git worktree per deliverable |
| Quality gates | Lint, test, review (mandatory, deterministic enforcement) |

### What Makes auto-code a Workflow, Not a Hardcoded Pipeline

auto-code defines its own:

- **Pipeline composition** (`pipeline.py`) -- the agent node list and wiring (skill_loader -> memory_loader -> planner -> coder -> formatter -> linter -> tester -> diagnostics -> review_cycle). This is auto-code's domain-specific orchestration, not shared infrastructure.
- **Agent definitions** (`agents/`) -- workflow-scoped planner, coder, reviewer with auto-code-specific instructions
- **Tool requirements** -- file I/O, shell, git tools declared in the manifest
- **Stage schema** -- 5-stage progression with per-stage agent rosters and validators
- **Quality gates** -- lint, test, review, regression validators at appropriate schedules

It does not define how tools work, how skills load, how models are selected, how state persists, or how events are distributed. A second workflow reuses all shared infrastructure and provides only its domain-specific concerns.

---

## See Also

- [Agents](./agents.md) -- agent architecture, composition, plan/execute separation
- [Tools](./tools.md) -- FunctionTool vs CustomAgent, MCP guidance, tool isolation
- [Skills](./skills.md) -- skill-based knowledge injection, progressive disclosure
- [Execution](./execution.md) -- ARQ workers, job lifecycle, event streaming
- Design notes: [manifest design](../.notes/260312_manifest-design.md), [stage-schema](../.notes/260312_stage-schema-design.md), [director-authoring](../.notes/260312_director-authoring-design.md), [authoring-skills](../.notes/260312_authoring-skills-design.md)

---

**Document Version:** 5.1
**Last Updated:** 2026-04-11
**Status:** Phase 7 Design Complete -- Build Pending
