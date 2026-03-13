[← Architecture Overview](../02-ARCHITECTURE.md)

# Workflow Composition System

**AutoBuilder Platform**
**Workflow Architecture Reference**

---

## Table of Contents

1. [Why Workflows Must Be Pluggable](#why-workflows-must-be-pluggable)
2. [Architecture: Workflows as Discoverable, Composable Units](#architecture-workflows-as-discoverable-composable-units)
3. [Stage Schema Architecture (D-70)](#stage-schema-architecture-d-70)
4. [Workflow Manifest](#workflow-manifest)
5. [Workflow Ecosystem Model (D-71)](#workflow-ecosystem-model-d-71)
6. [WorkflowRegistry](#workflowregistry)
7. [Resource Pre-Flight (D-72)](#resource-pre-flight-d-72)
8. [Resource Library (D-75)](#resource-library-d-75)
9. [Workflow Chaining (D-73)](#workflow-chaining-d-73)
10. [Director Workflow Authoring (D-74)](#director-workflow-authoring-d-74)
11. [auto-code: The First Workflow](#auto-code-the-first-workflow)
12. [Workflow Execution Model](#workflow-execution-model)
13. [What Is Shared vs. Workflow-Specific](#what-is-shared-vs-workflow-specific)
14. [See Also](#see-also)

---

## Why Workflows Must Be Pluggable

Architecture Decision #15 states: workflows must be pluggable from day one, even if only one workflow ships initially.

If the auto-code pipeline structure is hardcoded and other workflows are bolted on later, assumptions baked into the core become structural debt:

- **Tool registries coupled to coding tools** -- an auto-design workflow needs design tools (Figma export, image generation), not `file_edit` and `bash_exec`
- **State keys assuming code artifacts** -- `code_output`, `lint_results`, `test_results` are meaningless in an auto-market workflow that produces campaign copy and channel strategies
- **Pipeline stages assuming lint/test/review** -- an auto-research workflow produces reports, not code. Its quality gates are source verification and citation checking, not linting
- **Quality gates assuming code validation** -- every workflow needs deterministic quality gates, but the *type* of gate varies: lint/test for code, source verification for research, constraint validation for design

The cost of making workflows pluggable from the start is low (a manifest format, a registry, a discovery pattern). The cost of retrofitting pluggability after hardcoding auto-code assumptions is high (ripping out baked-in assumptions across the entire codebase).

---

## Architecture: Workflows as Discoverable, Composable Units

A workflow follows the same discovery pattern as skills: a directory with a manifest file and implementation code. The system scans for available workflows and matches them to user requests.

### Directory Structure

```
app/workflows/auto-code/
    WORKFLOW.yaml          # Manifest (stages, resources, standards, triggers)
    pipeline.py            # Pipeline factory per stage
    agents/                # Workflow-specific agent overrides
    skills/                # Workflow-specific skills
    standards/             # GOVERNANCE fragments (additive, never replace global)
    knowledge/             # Static reference materials (accessed via file_read)
    validators/            # Validator declarations (YAML)
```

Each workflow is a self-contained operating environment. Standards inject as GOVERNANCE fragments via InstructionAssembler (Decision #50). Knowledge files are accessed on-demand via file tools -- they are not loaded into context by default. Validators are declarative YAML files wired into the pipeline factory based on stage `quality_gates` declarations.

The core system provides shared infrastructure; workflows provide domain-specific orchestration. Agent definitions in `agents/` participate in the AgentRegistry 3-scope cascade (global `app/agents/` -> workflow `agents/` -> project `.agents/agents/`; Decision #54). Skills in `skills/` merge via SkillLibrary's three-tier merge (global -> workflow -> project).

---

## Stage Schema Architecture (D-70)

A stage is a filter on existing infrastructure -- it controls which agents, skills, tools, and quality gates the PM has access to during a phase of work.

### Core Concept

Workflows progress through ordered stages. Each stage scopes the PM's operating environment by filtering infrastructure resources. The PM does not need to understand stage mechanics -- context recreation (Decision #52) assembles the appropriate environment when a stage transition occurs.

### Stage Declaration

The `stages:` key in `WORKFLOW.yaml` declares an ordered list of stages:

```yaml
stages:
  - name: SHAPE
    description: Research problem space, define architecture
    approval: director
    agents: [planner]
    skills: ["planning/*", "research/*"]
    tools: [file_read, file_write, web_search, web_fetch]
    quality_gates: [spec_completeness]
    deliverable_types: [specification, architecture_doc]

  - name: BUILD
    description: Implement all code deliverables
    approval: director
    quality_gates: [lint_pass, test_pass, review_approval]
    deliverable_types: [source_file, test_file, config_file]
```

### StageConfig Model

```python
@dataclass
class StageConfig:
    name: str
    description: str
    approval: Literal["ceo", "director"]  # default: "ceo"
    agents: list[str] | None              # None = all workflow agents
    skills: list[str] | None              # Glob patterns (e.g., "code/*")
    tools: list[str] | None               # None = all workflow tools
    quality_gates: list[str]
    deliverable_types: list[str]
    pipeline_stages: list[str] | None     # None = full pipeline
    models: dict[str, str] | None         # Overrides workflow default_models
```

**Omitted fields default to workflow-level values.** A stage that specifies only `quality_gates` and `deliverable_types` inherits all agents, skills, tools, pipeline stages, and models from the workflow manifest.

**Absent `stages:` key = single implicit stage.** Workflows that do not declare stages operate as a single implicit stage with zero complexity tax. The entire manifest acts as the stage configuration.

**Stage gate approval** is configurable per-stage: `approval: ceo` requires CEO approval to advance; `approval: director` allows the Director to approve without CEO involvement. Default is `ceo`.

**SHAPE is a stage within auto-code**, not a separate workflow. Stages share project state and PM continuity -- splitting SHAPE into a separate workflow would break PM context and force artificial state handoff.

### StageSchema

```python
@dataclass
class StageSchema:
    """Ordered list of StageConfig with navigation."""
    stages: list[StageConfig]

    def get(self, name: str) -> StageConfig:
        """Get stage by name. Raises KeyError if not found."""

    def next(self, current: str) -> StageConfig | None:
        """Return the next stage after current, or None if final."""

    def is_final(self, name: str) -> bool:
        """True if this is the last stage in the workflow."""
```

### Stage Resolution

`resolve_stage_config()` is a pure function that merges workflow-level defaults with stage-specific overrides to produce an effective configuration:

```python
def resolve_stage_config(
    manifest: WorkflowManifest,
    stage_name: str,
) -> EffectiveStageConfig:
    """Merge workflow defaults + stage overrides -> effective config."""
```

Stage resolution flow:

```
WORKFLOW.yaml -> parse -> WorkflowManifest
                           |-- stages: [StageConfig, ...]  -> StageSchema
                           +-- workflow defaults (tools, models, etc.)
                                       |
                           resolve_stage_config(manifest, stage_name)
                                       |
                                       v
                               Effective StageConfig
                               |-- feeds AgentRegistry (agent filter)
                               |-- feeds SkillLibrary (skill patterns)
                               |-- feeds GlobalToolset (tool filter)
                               |-- feeds InstructionAssembler (stage TASK fragment)
                               +-- feeds create_deliverable_pipeline() (pipeline_stages param)
```

The PM adapts to stage transitions via the existing context recreation mechanism (Decision #52): Persist -> Seed -> Fresh session -> Reassemble. The MemoryLoaderAgent, SkillLoaderAgent, and InstructionAssembler rebuild the PM's operating context with the new stage's resource filters applied.

### Rejected Alternatives

- **Stage-as-directory**: Fragments the workflow across the filesystem. A workflow with 4 stages would have 4 subdirectories each duplicating manifest fragments. Rejected for complexity and maintenance burden.
- **Stage-as-workflow**: Breaks PM continuity. Stages share project state -- the PM in BUILD needs context from SHAPE. Treating stages as separate workflows forces artificial state serialization between workflow boundaries.

---

## Workflow Manifest

Every workflow directory contains a `WORKFLOW.yaml` manifest that declares the workflow's identity, requirements, stages, and configuration.

### Full Example: auto-code

```yaml
# app/workflows/auto-code/WORKFLOW.yaml
name: auto-code
description: Autonomous software development from specification to verified output
version: "1.0"

triggers:
  keywords: [build, develop, implement, code, create app, create api]
  explicit: auto-code

default_models:
  planning: anthropic/claude-opus-4-6
  implementation: anthropic/claude-sonnet-4-6
  review: anthropic/claude-opus-4-6
  fast: anthropic/claude-sonnet-4-6

pipeline_type: batch_parallel
supports_deliverables: true
supports_parallel: true

resources:
  tools:
    required: [file_read, file_write, file_edit, bash_exec, git_status, git_commit, git_diff]
    optional: [web_search, web_fetch, todo_read, todo_write]
  credentials:
    - name: llm_api_key
      purpose: LLM provider access
      required: true
      check: provider_reachable
  services:
    - name: git
      check: git_installed
      required: true
  inputs:
    - name: source_repository
      type: git_repo
      required: true

standards:
  - code-quality.md
  - testing-requirements.md

produces:
  - source_file
  - test_file
  - config_file
  - specification
  - architecture_doc

consumes: []

stages:
  - name: SHAPE
    description: Research problem space, define architecture, produce technical specification
    approval: director
    agents: [planner]
    skills: ["planning/*", "research/*"]
    tools: [file_read, file_write, web_search, web_fetch]
    quality_gates: [spec_completeness]
    deliverable_types: [specification, architecture_doc]
    pipeline_stages: [skill_loader, memory_loader, planner]
    models:
      planning: anthropic/claude-opus-4-6

  - name: PLAN
    description: Decompose specification into implementable deliverables
    approval: director
    agents: [planner, dependency_resolver]
    skills: ["planning/*"]
    tools: [file_read, file_write]
    quality_gates: [deliverable_completeness, dependency_validity]
    deliverable_types: [deliverable_spec]
    pipeline_stages: [skill_loader, memory_loader, planner]

  - name: BUILD
    description: Implement all code deliverables with full development pipeline
    approval: director
    quality_gates: [lint_pass, test_pass, review_approval]
    deliverable_types: [source_file, test_file, config_file]

  - name: VERIFY
    description: Integration testing, final quality verification
    approval: ceo
    agents: [tester, reviewer, diagnostics, regression_tester]
    skills: ["testing/*", "review/*"]
    quality_gates: [integration_test_pass, regression_pass, final_review]
    deliverable_types: [test_report, verification_report]
    pipeline_stages: [skill_loader, memory_loader, tester, diagnostics, review_cycle]
```

### Manifest Fields

| Field | Type | Required | Description |
|---|---|----------|-------------|
| `name` | string | Yes | Unique workflow identifier. Used in API requests, CLI invocation, and WorkflowRegistry. |
| `description` | string | Yes | Human-readable summary of what the workflow does. |
| `version` | string | No | Manifest schema version for forward compatibility. |
| `triggers` | object | Yes | Conditions that match user requests to this workflow (`keywords` list + `explicit` name). |
| `default_models` | dict | No | Default model assignments per task type. Overridden by LLM Router and user preferences. |
| `pipeline_type` | string | Yes | How the pipeline executes: `batch_parallel` (deliverables in parallel batches), `sequential` (one at a time), `single_pass` (no deliverable decomposition). |
| `supports_deliverables` | boolean | Yes | Whether the workflow can decompose a specification into implementable deliverables. |
| `supports_parallel` | boolean | Yes | Whether deliverables can execute concurrently via `ParallelAgent`. |
| `resources` | object | No | Resource declarations for pre-flight validation (tools, credentials, services, inputs). See [Resource Pre-Flight](#resource-pre-flight-d-72). |
| `standards` | list of strings | No | GOVERNANCE fragment files in the workflow's `standards/` directory. Additive to global standards. |
| `produces` | list of strings | No | Artifact types this workflow creates. Enables workflow chaining (D-73). |
| `consumes` | list of strings | No | Artifact types from prior workflows this workflow expects. Enables workflow chaining (D-73). |
| `stages` | list of StageConfig | No | Ordered stage declarations. Absent = single implicit stage. See [Stage Schema Architecture](#stage-schema-architecture-d-70). |

### Trigger Matching

Workflow triggers use deterministic keyword matching (same principle as skills: no LLM in matching).

- `keywords` -- if the user request contains any of these words, the workflow matches
- `explicit` -- if the user explicitly names the workflow (e.g., via CLI `autobuilder run auto-code` or API `POST /workflows/run {"workflow": "auto-code"}`)

If multiple workflows match, the explicit trigger takes precedence. If ambiguous, the system prompts the user to clarify.

---

## Workflow Ecosystem Model (D-71)

Each subdirectory within a workflow directory serves a specific architectural purpose. Together they form the workflow's self-contained operating environment.

### Subdirectory Purposes

**`standards/`** -- GOVERNANCE fragments that inject into agent instructions via InstructionAssembler (Decision #50). These are **additive** to global standards defined in `app/standards/` -- they never replace global standards. A workflow's standards encode domain-specific conventions (e.g., auto-code's testing requirements, auto-design's accessibility guidelines).

**`knowledge/`** -- Static reference materials accessed on-demand via the `file_read` tool. These are NOT loaded into agent context automatically. Agents read knowledge files when they determine the content is relevant to the current task. Examples: API style guides, framework migration guides, domain glossaries.

**`validators/`** -- Declarative YAML files that define quality gate implementations. Each validator declares its check type, pass/fail criteria, and remediation hints. Validators are wired into the pipeline factory based on the `quality_gates` declared in each stage's StageConfig.

**`agents/`** -- Workflow-specific agent definition files (Markdown + YAML frontmatter, Decision #51). These participate in the AgentRegistry 3-scope cascade: global (`app/agents/`) -> workflow (`workflows/{name}/agents/`) -> project (`{project}/.agents/agents/`). A workflow agent file with the same name as a global agent file overrides it for that workflow. Full replacement by name; partial override via frontmatter-only file that inherits the parent body (Decision #54).

**`skills/`** -- Workflow-specific skills that extend the global skill library. These merge via SkillLibrary's three-tier merge: global (`app/skills/`) -> workflow (`workflows/{name}/skills/`) -> project (`{project}/.agents/skills/`). Only truly workflow-unique skills belong here. Universal skills (e.g., code skills used by many workflows) stay at `app/skills/`.

### Ecosystem Interaction

```
app/workflows/auto-code/
    WORKFLOW.yaml          -- WorkflowRegistry indexes at startup
    pipeline.py            -- create_deliverable_pipeline() factory
    standards/             -- InstructionAssembler GOVERNANCE fragments
    knowledge/             -- file_read on-demand reference
    validators/            -- Pipeline factory wires per quality_gates
    agents/                -- AgentRegistry 3-scope cascade (scope 2)
    skills/                -- SkillLibrary 3-tier merge (tier 2)
```

---

## WorkflowRegistry

The WorkflowRegistry discovers, manages, and instantiates available workflows. It follows the same scan-and-index pattern as SkillLibrary.

### API

```python
class WorkflowRegistry:
    """Discovers and manages available workflows."""

    def __init__(
        self,
        workflows_dir: Path,
        custom_workflows_dir: Path | None = None,
    ):
        self._workflows: dict[str, WorkflowEntry] = {}
        self._scan(workflows_dir)
        if custom_workflows_dir:
            self._scan(custom_workflows_dir)  # Custom overrides built-in by name

    def match(self, user_request: str) -> WorkflowEntry | None:
        """Match user request to a workflow. Deterministic keyword matching."""

    def get(self, name: str) -> WorkflowEntry:
        """Get workflow by explicit name. Raises KeyError if not found."""

    def list_available(self) -> list[WorkflowEntry]:
        """List all discovered workflows with descriptions."""

    def create_pipeline(
        self,
        name: str,
        ctx: PipelineContext,
        stage_name: str | None = None,
    ) -> BaseAgent:
        """Instantiate pipeline for given workflow and stage.

        Resolves effective StageConfig, then delegates to workflow's
        pipeline.py create_deliverable_pipeline() factory.
        """
```

### Key Design Points

**Discovery is automatic.** The registry scans the workflows directory at startup. Adding a new workflow means adding a new directory with a `WORKFLOW.yaml` manifest and a `pipeline.py` module. No registration code, no config file edits.

**Custom workflows directory.** The optional `custom_workflows_dir` parameter (default: `~/.autobuilder/workflows/`) allows users to provide organization-specific workflows that override built-in ones (same name replacement) or extend the available set.

**Pipeline instantiation is deferred.** The registry indexes manifests at startup (lightweight YAML parsing) but only instantiates the ADK pipeline when `create_pipeline()` is called. This avoids loading agent definitions and importing modules for workflows that are not used.

**Stage-aware pipeline creation.** The `stage_name` parameter feeds into `resolve_stage_config()` to produce an effective StageConfig, which is passed to the workflow's pipeline factory. When `stage_name` is None, the first stage (or implicit single stage) is used.

**Shared infrastructure injection.** The `PipelineContext` carries `GlobalToolset`, `SkillLibrary`, `AgentRegistry`, and `InstructionAssembler`. The workflow's `pipeline.py` uses these to construct its ADK agent tree via `registry.build(agent_name, ctx)` (Decision #54) instead of direct `LlmAgent`/`CustomAgent` construction. This is the mechanism that makes workflows composable (Decision #15): a second workflow reuses global agent definitions or overrides them with its own.

---

## Resource Pre-Flight (D-72)

`ResourcePreflightAgent` is a deterministic `CustomAgent` that runs after stage selection and validates all manifest-declared resources before pipeline execution begins.

### Check Types

Resource checks are an enum covering the validation types a workflow can declare:

| Check Type | Description |
|---|---|
| `provider_reachable` | LLM provider endpoint responds |
| `api_key_valid` | API key is set and non-empty |
| `git_installed` | Git binary available on PATH |
| `runtime_available` | Language runtime (python, node, etc.) available |
| `tool_available` | Named FunctionTool registered in GlobalToolset |
| `file_exists` | File or directory exists at specified path |
| `service_reachable` | Network service responds (Redis, database, etc.) |
| `command_available` | CLI command exists on PATH |

### Behavior

1. Parse `resources` from the resolved `EffectiveStageConfig`
2. Run each declared check (all checks are deterministic, no LLM)
3. **Required resource fails** -> create CEO queue item with resolution hints, halt pipeline
4. **Optional resource fails** -> log warning, continue with degraded capability
5. **All pass** -> proceed to pipeline execution

### Per-Stage Re-Validation

Stage transitions trigger re-validation. A resource that was not needed in SHAPE (e.g., `bash_exec`) may be required in BUILD. The `ResourcePreflightAgent` runs at each stage boundary to catch configuration drift.

### Resource Declaration in Manifest

```yaml
resources:
  tools:
    required: [file_read, file_write, file_edit, bash_exec, git_status, git_commit, git_diff]
    optional: [web_search, web_fetch, todo_read, todo_write]
  credentials:
    - name: llm_api_key
      purpose: LLM provider access
      required: true
      check: provider_reachable
  services:
    - name: git
      check: git_installed
      required: true
  inputs:
    - name: source_repository
      type: git_repo
      required: true
```

---

## Resource Library (D-75)

The Resource Library is a database entity that models the CEO's available resources -- API keys, databases, external services, development tools. It stores **metadata only**, never secrets.

### Database Schema

**`resource_library` table:**

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | str | Human-readable resource name |
| `category` | ResourceCategory | Enum: `api_key`, `database`, `service`, `tool`, `runtime` |
| `description` | str | What this resource provides |
| `config` | JSONB | Non-secret configuration (endpoint URLs, versions, capabilities) |
| `secret_ref` | str | Null | Environment variable name pointing to the actual secret |
| `status` | ResourceStatus | Enum: `ACTIVE`, `INACTIVE`, `EXPIRED` |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

**`project_resources` table:**

| Column | Type | Description |
|---|---|---|
| `project_id` | UUID | FK to projects table |
| `resource_id` | UUID | FK to resource_library table |
| `bound_at` | datetime | When the resource was bound to the project |

### Access Patterns

- **Director** browses available resources via `browse_resources` tool when planning workflow execution
- **ResourcePreflightAgent** validates resource availability by checking `resource_library` status and `secret_ref` env var presence
- **CEO** manages resources through gateway CRUD routes (`/api/resources/`)
- **Secrets stay in environment variables** -- `secret_ref` is a pointer (e.g., `ANTHROPIC_API_KEY`), never the secret itself

### Gateway Routes

- `GET /api/resources/` -- list all resources (with optional category filter)
- `POST /api/resources/` -- create a resource entry
- `GET /api/resources/{id}` -- get resource details
- `PATCH /api/resources/{id}` -- update resource metadata
- `DELETE /api/resources/{id}` -- remove resource entry
- `POST /api/projects/{id}/resources` -- bind resource to project
- `DELETE /api/projects/{id}/resources/{resource_id}` -- unbind resource

---

## Workflow Chaining (D-73)

Phase 7 is single-workflow per project. The manifest supports `produces`/`consumes` declarations for forward compatibility with compound workflows in Phase 8+.

### Artifact Contracts

```yaml
# auto-code produces
produces:
  - source_file
  - test_file
  - config_file
  - specification
  - architecture_doc

# A hypothetical auto-deploy workflow consumes
consumes:
  - source_file
  - test_file
  - config_file
```

### Forward Compatibility

- `produces` declares the artifact types a workflow creates upon completion
- `consumes` declares the artifact types a workflow expects as input from a prior workflow
- Phase 8+ execution: workflow completion CAN initiate the next workflow whose `consumes` matches the completed workflow's `produces`
- Artifact contracts enable dependency inference in compound workflows -- the system can determine execution order automatically
- Session state persists between workflow executions within the same project, enabling artifact handoff

### Phase 7 Behavior

In Phase 7, `produces` and `consumes` are parsed and stored in the `WorkflowEntry` but have no runtime effect. They exist so that workflow authors can declare contracts during development without waiting for chaining infrastructure.

---

## Director Workflow Authoring (D-74)

The Director can author new workflows and compose resources using enhanced authoring skills and existing file tools.

### New Skills

**`workflow-composition`** -- Director-tier skill (`applies_to: [director]`) providing structured guidance for composing workflow manifests, stage definitions, pipeline factories, and validator declarations. Covers manifest schema, stage design patterns, resource declaration, and ecosystem directory setup.

**`resource-composition`** -- Director-tier skill for composing resource library entries, binding resources to projects, and declaring resource requirements in workflow manifests.

### New Tool

**`validate_workflow`** -- Deterministic `FunctionTool` that validates a `WORKFLOW.yaml` manifest against the schema. Returns structured validation results (errors, warnings, suggestions). Runs in worker context. Checks:
- Required fields present
- Stage names unique
- Referenced agents/skills/tools exist in the registry
- `produces`/`consumes` types are recognized artifact types
- Resource check types are valid enum values

### Updated Skills

Existing authoring skills gain `director` in their `applies_to` list:

- `skill-authoring` -- guidance for composing SKILL.md files
- `agent-definition` -- guidance for composing agent definition files (Decision #51)
- `workflow-authoring` -- guidance for workflow structure and pipeline patterns

This ensures the Director has access to all authoring guidance when composing workflows, while Worker agents do not receive irrelevant authoring context.

---

## auto-code: The First Workflow

auto-code is the first workflow shipped with AutoBuilder. It implements autonomous software development from specification to verified output, organized into four stages.

### Stage Overview

| Stage | Purpose | Approval | Key Agents |
|---|---|---|---|
| **SHAPE** | Research problem space, define architecture, produce technical specification | `director` | planner |
| **PLAN** | Decompose specification into implementable deliverables | `director` | planner, dependency_resolver |
| **BUILD** | Implement all code deliverables with full development pipeline | `director` | All (planner, coder, formatter, linter, tester, diagnostics, reviewer, fixer) |
| **VERIFY** | Integration testing, final quality verification | `ceo` | tester, reviewer, diagnostics, regression_tester |

### SHAPE Stage

Research the problem space, define architecture, and produce a technical specification. SHAPE is skippable if a Brief already exists (Director approval).

- **agents**: `[planner]`
- **skills**: `["planning/*", "research/*"]`
- **tools**: `[file_read, file_write, web_search, web_fetch]`
- **quality_gates**: `[spec_completeness]`
- **pipeline_stages**: `[skill_loader, memory_loader, planner]`

### PLAN Stage

Decompose the specification into implementable deliverables with dependency ordering.

- **agents**: `[planner, dependency_resolver]`
- **skills**: `["planning/*"]`
- **tools**: `[file_read, file_write]`
- **quality_gates**: `[deliverable_completeness, dependency_validity]`
- **pipeline_stages**: `[skill_loader, memory_loader, planner]`

### BUILD Stage

Implement all code deliverables using the full development pipeline. This is the primary execution stage with all agents and the complete pipeline.

- **agents**: None (all workflow agents available)
- **skills**: None (all workflow skills available)
- **tools**: None (all workflow tools available)
- **quality_gates**: `[lint_pass, test_pass, review_approval]`
- **pipeline_stages**: None (full pipeline: `skill_loader, memory_loader, planner, coder, formatter, linter, tester, diagnostics, review_cycle`)

### VERIFY Stage

Integration testing, regression testing, and final quality verification. CEO approval required to complete the workflow.

- **agents**: `[tester, reviewer, diagnostics, regression_tester]`
- **skills**: `["testing/*", "review/*"]`
- **quality_gates**: `[integration_test_pass, regression_pass, final_review]`
- **pipeline_stages**: `[skill_loader, memory_loader, tester, diagnostics, review_cycle]`

### Pipeline Composition

The `create_deliverable_pipeline()` function in `pipeline.py` accepts a `stages` parameter (from `EffectiveStageConfig.pipeline_stages`) that controls which pipeline stages are included:

```python
def create_deliverable_pipeline(
    ctx: PipelineContext,
    stages: list[str] | None = None,
) -> BaseAgent:
    """Build the deliverable pipeline for the current stage.

    Args:
        ctx: Pipeline context with shared infrastructure.
        stages: Pipeline stage names to include. None = full pipeline.
            Canonical names from PIPELINE_STAGE_NAMES:
            skill_loader, memory_loader, planner, coder, formatter,
            linter, tester, diagnostics, review_cycle
    """
```

This is the same `create_deliverable_pipeline()` from Phase 5 -- StageConfig feeds its `pipeline_stages` parameter to filter the agent list. No new pipeline infrastructure is required.

### Skill Placement

Code skills stay at `app/skills/code/` -- they are universal skills used by many workflows. Only truly workflow-unique skills (e.g., auto-code's deliverable decomposition patterns) go in `app/workflows/auto-code/skills/`. This avoids duplicating skills that other code-producing workflows would also need.

### Key Properties

| Property | Value |
|----------|-------|
| `pipeline_type` | `batch_parallel` |
| `supports_deliverables` | `true` |
| `supports_parallel` | `true` |
| Default planning model | `anthropic/claude-opus-4-6` |
| Default implementation model | `anthropic/claude-sonnet-4-6` |
| Default review model | `anthropic/claude-opus-4-6` |
| Isolation | Git worktree per deliverable (parallel deliverables write to separate filesystem locations) |
| Quality gates | Stage-dependent (see individual stage definitions) |
| Max review iterations | 3 (configurable via ReviewCycleAgent) |
| Stage count | 4 (SHAPE, PLAN, BUILD, VERIFY) |

### What Makes auto-code a Workflow, Not a Hardcoded Pipeline

auto-code defines its own:

- Stage progression (SHAPE -> PLAN -> BUILD -> VERIFY)
- Agent definitions (`agents/planner.md`, `agents/coder.md`, `agents/reviewer.md`)
- Pipeline composition (`pipeline.py` with stage-aware pipeline factory)
- Resource requirements (`resources` in WORKFLOW.yaml)
- Standards (`standards/code-quality.md`, `standards/testing-requirements.md`)
- Deliverable decomposition strategy (spec-to-deliverable generation)
- Quality gates per stage (stage-specific enforcement)

It does not define:

- How tools work (shared FunctionTools from GlobalToolset)
- How skills load (shared SkillLoaderAgent + SkillLibrary)
- How models are selected (shared LLM Router)
- How state persists (shared database via DatabaseSessionService)
- How events are traced (shared ADK event stream + OpenTelemetry)
- How events are distributed (shared Redis Streams event bus)
- How jobs are executed (shared ARQ worker infrastructure)
- How stages resolve (shared `resolve_stage_config()` + StageSchema)
- How resources validate (shared ResourcePreflightAgent)

This separation means a second workflow can reuse all shared infrastructure and provide only its domain-specific stages, agents, and skills.

---

## Workflow Execution Model

Workflows execute inside ARQ worker processes, not the gateway. The execution lifecycle is:

1. **Client request** -- CLI or dashboard sends `POST /workflows/run` with spec and workflow name
2. **Gateway validation** -- validates request, resolves workflow via WorkflowRegistry, creates job record in database
3. **Job enqueueing** -- gateway enqueues ARQ job with workflow name, spec, session ID, and initial stage
4. **Worker pickup** -- ARQ worker dequeues job, resolves effective StageConfig via `resolve_stage_config()`
5. **Resource pre-flight** -- ResourcePreflightAgent validates all declared resources for the current stage
6. **Pipeline execution** -- ADK agents execute in worker process. State flows through database. Events publish to Redis Streams.
7. **Stage transitions** -- on stage completion, publish `STAGE_TRANSITION` event to Redis Streams. `current_stage` column on project table tracks position. Re-run resource pre-flight for the new stage.
8. **Stage gate approval** -- depending on `approval` config (`ceo` or `director`), create CEO queue item or Director approval request before advancing
9. **Event streaming** -- Redis Stream consumers push events to SSE endpoints, webhook dispatchers, audit loggers
10. **Completion** -- worker marks job complete in database, publishes completion event
11. **Client notification** -- client receives completion via SSE stream or polls status endpoint

The gateway never runs ADK pipelines. It is a job broker and event proxy. This means:

- Workers can scale independently (add more workers for higher throughput)
- A crashed worker does not take down the gateway
- Pipeline execution is isolated from API request handling
- ADK is an internal engine behind the anti-corruption layer

---

## What Is Shared vs. Workflow-Specific

### Shared Infrastructure (All Workflows Use)

All workflows operate on the same platform foundation:

- **Gateway API** -- FastAPI REST + SSE endpoints. Clients interact with workflows through the gateway, not directly.
- **Worker execution** -- ARQ workers execute ADK pipelines. Workflows run in worker processes.
- **GlobalToolset** -- FunctionTools available to all workflows (filesystem, bash, git, web, todo), vended per-role via ADK's `BaseToolset.get_tools()`
- **Skill library** -- global + workflow + project-local skills, loaded by SkillLoaderAgent
- **AgentRegistry** -- scans agent definition files (markdown + YAML frontmatter) and builds ADK agents on demand (Decision #54); workflows call `registry.build()` instead of constructing agents directly
- **InstructionAssembler** -- 6-type fragment composition (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL) replacing static instruction strings (Decisions #50, #55); assembles context-aware instructions per agent
- **LLM Router** -- dynamic model selection based on task type and routing rules
- **State management** -- session/user/app/temp state scopes via ADK's session system, persisted to single database
- **Event bus** -- Redis Streams for event distribution (SSE, webhooks, audit)
- **Observability** -- unified event stream, OpenTelemetry tracing, ADK Dev UI
- **Stage schema resolution** -- `resolve_stage_config()` pure function, StageSchema navigation
- **Resource pre-flight** -- ResourcePreflightAgent validation at stage boundaries
- **Resource library** -- database-backed resource catalog with secret_ref indirection
- **Context recreation** -- Persist -> Seed -> Fresh session -> Reassemble (Decision #52)
- **Outer loop** -- PM agent drives batch orchestration via tools and deterministic safety mechanisms (if workflow supports `batch_parallel` pipeline type)
- **App container** -- ADK `App` class providing lifecycle management, context compression, resumability
- **Memory service** -- cross-session learnings via `MemoryService` (PostgreSQL tsvector + pgvector)

### Workflow-Specific

Each workflow defines its own domain-specific concerns:

- **Stage definitions** -- ordered stages with per-stage resource scoping
- **Pipeline composition** -- which agents run, in what order, with what loops and parallelism
- **Agent definitions** -- instructions, tool subsets, model preferences per agent role
- **Workflow-specific skills** -- domain knowledge unique to the workflow
- **Standards** -- GOVERNANCE fragments encoding domain conventions
- **Knowledge** -- static reference materials for on-demand access
- **Validators** -- quality gate implementations wired per stage
- **Deliverable decomposition strategy** -- how a spec becomes implementable units
- **Quality gates** -- per-stage quality requirements and enforcement
- **Artifact types** -- what the workflow produces and consumes
- **Resource requirements** -- declared dependencies on tools, credentials, services

---

## See Also

- [Agents](./agents.md) -- agent architecture, composition, plan/execute separation
- [Tools](./tools.md) -- FunctionTool vs CustomAgent, MCP guidance, tool isolation
- [Skills](./skills.md) -- skill-based knowledge injection, progressive disclosure
- [Execution](./execution.md) -- ARQ workers, job lifecycle, event streaming
- [Context](./context.md) -- context assembly, budgeting, recreation

---

**Document Version:** 4.0
**Last Updated:** 2026-03-12
**Status:** Architecture Complete -- Phase 7 Design
