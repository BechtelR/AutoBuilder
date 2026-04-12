# Workflow Composition Patterns Research

**Date**: 2026-03-12
**Phase**: 7 (Workflow Composition System)
**Purpose**: Research workflow orchestration patterns across industry systems, identify patterns applicable to AutoBuilder's agentic workflow architecture.

---

## Table of Contents

1. [Per-System Analysis](#1-per-system-analysis)
2. [Stage Schema Pattern Analysis](#2-stage-schema-pattern-analysis)
3. [Plugin Architecture Comparison](#3-plugin-architecture-comparison)
4. [Variable-Scale Workflow Design Patterns](#4-variable-scale-workflow-design-patterns)
5. [Declarative vs Imperative Workflow Analysis](#5-declarative-vs-imperative-workflow-analysis)
6. [Recommendations for AutoBuilder](#6-recommendations-for-autobuilder)
7. [Key Architectural Patterns to Adopt](#7-key-architectural-patterns-to-adopt)
8. [Anti-Patterns to Avoid](#8-anti-patterns-to-avoid)

---

## 1. Per-System Analysis

### 1.1 N8N — Visual Workflow Builder

**Architecture**: Frontend-backend separation. Visual drag-and-drop editor serializes workflows as JSON. Backend execution engine processes nodes sequentially, each node's output feeding into the next. 400+ built-in nodes.

**Composition model**: Workflows are directed graphs of nodes. Two node types: trigger nodes (initiate execution) and regular nodes (process data). Sub-workflows enable modular composition via the "Execute Workflow" node, which can call another workflow by ID, URL, file, or inline JSON.

**Extension model**: Four-level extensibility: (1) Function nodes for inline JS, (2) HTTP nodes for arbitrary APIs, (3) custom node modules as npm packages (declarative JSON or programmatic TypeScript), (4) community node marketplace.

**Relevance to AutoBuilder**: N8N's sub-workflow pattern maps well to compound workflows (Decision #3). Its node-as-unit model is analogous to our agent-as-unit model. Key lesson: sub-workflows are separate execution contexts that do not share local state, similar to our session-per-workflow design. N8N's weakness for our use case: it is optimized for integration automation (connect API A to API B), not multi-stage knowledge work with variable-scale complexity. Its JSON-based workflow definitions become unwieldy for complex orchestration, and its node system lacks the hierarchical supervision AutoBuilder requires.

**Applicable patterns**:
- Sub-workflow as separate execution context (no shared local state)
- Directory-scanned plugin discovery for custom nodes
- Trigger-based workflow activation (webhook, schedule, explicit)

### 1.2 Temporal — Durable Execution Engine

**Architecture**: Workflows are deterministic programs written in general-purpose languages (Go, Java, Python, TypeScript). The runtime provides durability guarantees — workflows can run for years, surviving infrastructure failures by automatically reconstructing pre-failure state from event history.

**Composition model**: Three composition primitives:
1. **Activities** — units of work (non-deterministic, can fail, automatically retried). The basic building block.
2. **Child Workflows** — spawned from parent workflows. Separate execution context, independent worker pool, no shared local state. Communication via async Signals. Parent controls lifecycle via Parent Close Policy (TERMINATE, REQUEST_CANCEL, ABANDON).
3. **Continue-As-New** — handles unbounded iteration by creating a fresh execution with new event history, preventing history growth.

**When to use child workflows vs activities**: Temporal explicitly recommends starting with a single workflow + activities unless you need: separate worker pools, workload partitioning (1000 children x 1000 activities), per-resource state management, or periodic logic via Continue-As-New.

**Communication**: Signals (async messages to mutate workflow state), Queries (read-only inspection), Updates (validated mutations). No shared memory between workflows.

**Relevance to AutoBuilder**: Temporal's model is the closest analogue to what AutoBuilder needs. Key insights:
- **Start simple, add child workflows only when needed** — matches our variable-scale challenge
- **Activities for work, workflows for orchestration** — maps to our agents-for-work, PM-for-orchestration
- **Signals for inter-workflow communication** — analogous to our Redis Streams + state bridge
- **Continue-As-New** — relevant to our context recreation pattern (fresh session with persisted state)
- **Deterministic replay** — AutoBuilder's "agents are stateless config objects, state in DB" is the same principle

**Applicable patterns**:
- Single-workflow-first, child-workflows-when-justified
- Activity (= agent) as unit of work within orchestration workflow
- Async signal-based inter-workflow communication
- Continue-As-New for long-running orchestration (context recreation analogue)

### 1.3 Prefect — Python Workflow Orchestration

**Architecture**: Pure Python. Workflows are Python functions decorated with `@flow`. Tasks are Python functions decorated with `@task`. Dependencies via return values and futures. Observation separated from execution.

**Composition model**: Four workflow design patterns (progressively looser coupling):
1. **Monoflow** — single flow of tasks. Tightest coupling, simplest. Most common.
2. **Flow of Subflows** — parent flows call child flows. Same process. Conceptual separation, code reuse, clear ownership boundaries.
3. **Flow of Deployments** (Orchestrator Pattern) — flows trigger deployed flows on separate infrastructure. Loose coupling. Necessary when tasks need different infrastructure (e.g., GPU).
4. **Event-Triggered Flows** — maximum decoupling. Triggered flow knows nothing about the initiating flow.

**Relevance to AutoBuilder**: Prefect's progressive coupling model is directly applicable. AutoBuilder workflows span this spectrum:
- Single-stage workflows = Monoflow
- Multi-stage workflows = Flow of Subflows (same worker process)
- Compound workflows = Flow of Deployments (different ARQ jobs)
- Cross-project event reactions = Event-Triggered Flows

**Key lesson**: Prefect does not force all workflows into the same complexity pattern. Simple workflows are simple. Complex workflows use composition. The framework does not penalize simplicity.

**Applicable patterns**:
- Progressive coupling model (tight for simple, loose for complex)
- Subflows in same process for organizational clarity without overhead
- Python-native workflow definition (decorators, not YAML)
- First-class observability for nested flows in the UI

### 1.4 Apache Airflow — DAG-Based Orchestration

**Architecture**: Workflows are DAGs (Directed Acyclic Graphs) defined in Python. Tasks are operators. Dependencies via `>>` and `<<` operators. Scheduler evaluates DAG files and creates task instances.

**Composition model**:
- **TaskGroups** — hierarchical grouping for visual organization. Tasks remain on the original DAG. Not separate execution contexts — purely organizational. Recommended over the deprecated SubDAGs.
- **Dynamic Task Mapping** — `expand()` creates N task instances at runtime from previous task output. Enables variable-scale execution without knowing task count at definition time.
- **Control Flow** — `@task.branch` for conditional execution, trigger rules for complex dependency patterns (all_success, one_success, all_done, etc.).

**Relevance to AutoBuilder**: Airflow's evolution from SubDAGs to TaskGroups is instructive. SubDAGs (separate execution contexts for organizational grouping) were a mistake — they added complexity without proportional benefit. TaskGroups (visual grouping within a single DAG) solved the same problem more simply. This argues against creating separate execution contexts for stages within a single workflow.

**Dynamic Task Mapping is directly relevant**: AutoBuilder's batch execution creates N parallel deliverable pipelines per batch, analogous to Airflow's `expand()`. The key pattern: the orchestrator (PM/DAG) does not know at definition time how many parallel units will execute.

**Applicable patterns**:
- TaskGroups for organizational grouping without execution overhead
- Dynamic task mapping for variable-count parallel execution
- Trigger rules for complex dependency patterns between stages
- Lesson: avoid SubDAG anti-pattern (separate execution for organizational concerns)

### 1.5 Dagster — Software-Defined Assets

**Architecture**: Asset-centric rather than task-centric. You define what data assets should exist and how they are computed. The asset graph shows dependencies automatically. Jobs are the execution unit.

**Composition model**: Assets declare dependencies on other assets via function parameter names. The graph is inferred from declarations, not manually specified. `@asset` decorator on Python functions. `@graph_asset` for multi-step assets. `@multi_asset` for functions producing multiple outputs.

**Relevance to AutoBuilder**: Dagster's asset-centric model is a paradigm shift from task-centric orchestration. While AutoBuilder is fundamentally task-centric (plan -> code -> lint -> test -> review), Dagster's insight is valuable: **define what you produce, not just what you do**. This maps to AutoBuilder's artifact system (Decision #59) — deliverables produce artifacts (source files, tests, reports), and the artifact graph could be the workflow dependency graph.

However, adopting asset-centric design would be a fundamental architecture change inappropriate for Phase 7. The observation is noted for future consideration.

**Applicable patterns**:
- Declarative dependency inference (assets declare what they need, graph is computed)
- Partitioning for variable-scale execution
- Materialization metadata for observability (analogous to our event stream)

### 1.6 GitHub Actions — Composable CI/CD

**Architecture**: YAML-defined workflows triggered by events. Jobs contain steps. Steps use actions (reusable units). Two reuse mechanisms: reusable workflows and composite actions.

**Composition model**:
- **Reusable Workflows** — `workflow_call` trigger. Called workflow runs as separate jobs. Cannot call other reusable workflows (no nesting). Pipeline templates.
- **Composite Actions** — bundle multiple steps into one reusable action. Run inline within the calling job. Can nest up to 10 levels. Shared task templates.
- **Matrix Strategy** — dynamic parallel execution across parameter combinations.

**Design insight**: GitHub Actions explicitly separates "pipeline templates" (reusable workflows) from "shared task templates" (composite actions). This two-level reuse maps to AutoBuilder's workflow definitions (pipeline templates) vs. agent definitions (shared task templates that workflows compose).

**Relevance to AutoBuilder**: GitHub Actions' flat reusable workflow model (no nesting) is too restrictive for AutoBuilder's hierarchical supervision. But its composite action model (inline, nestable, scoped) maps well to our agent composition pattern.

**Applicable patterns**:
- Two-level reuse: pipeline templates (workflows) + shared task templates (agents)
- Matrix strategy for parallel parameterized execution
- Event-driven triggering with explicit and pattern-based triggers
- Secrets scoped to calling workflow (analogous to tool_role ceiling per workflow)

### 1.7 Kubernetes Operators / CRDs

**Architecture**: Custom Resource Definitions extend the Kubernetes API with domain-specific resources. Operators (controllers) watch CRDs and reconcile actual state toward declared desired state. The reconciliation loop is the core pattern.

**Composition model**: Declarative — users specify desired state, the system converges toward it. No explicit workflow steps; the controller decides what actions to take based on the delta between desired and actual state.

**Relevance to AutoBuilder**: The reconciliation loop is the deepest architectural insight in this research. AutoBuilder's PM loop is fundamentally a reconciliation loop: desired state = "all deliverables complete and verified," actual state = current project state. The PM observes the delta and takes action (select next batch, retry failed deliverables, escalate blockers).

However, pure reconciliation is not appropriate for all AutoBuilder workflows. Creative workflows (research, design) are not convergent — they explore a space rather than converging on a known target. The PM loop works as reconciliation for convergent workflows (code: spec -> verified implementation) but needs different semantics for divergent workflows (research: question -> exploration -> synthesis).

**Applicable patterns**:
- Desired-state declaration in manifest, convergence via controller loop
- Status subresource for observability (analogous to workflow state reporting)
- Validation webhooks (analogous to manifest validation at registration)
- CRD versioning for backward compatibility

### 1.8 Kestra — Declarative YAML Orchestration

**Architecture**: Fully declarative YAML workflows. Namespaces for organizational isolation. Built-in code editor with syntax validation. Rich plugin ecosystem (hundreds of plugins). Event-driven and scheduled execution.

**Composition model**: YAML flow definitions with typed tasks. Namespaces isolate teams/departments. Plugin-based task types. Flows are versioned and tracked via standard VCS.

**Relevance to AutoBuilder**: Kestra validates that pure-YAML workflow definitions can work at scale. Its namespace model maps to AutoBuilder's workflow directories. Its plugin model (Java-based, deep engine integration) is analogous to our workflow `pipeline.py` modules. Key lesson: Kestra's YAML-only approach works for data workflows but would be too restrictive for AutoBuilder's agent composition, which requires Python for ADK agent tree construction.

**Applicable patterns**:
- Namespace-based organizational isolation
- Built-in validation before execution
- YAML for what can be declarative, code for what needs logic

### 1.9 Argo Workflows — Kubernetes-Native Workflow Engine

**Architecture**: Workflows as Kubernetes CRDs. Templates as the unit of composition. Nine template types spanning work-defining (container, script, resource, suspend, plugin, container-set, HTTP) and execution-control (steps, DAG).

**Composition model**: Two orchestration patterns:
- **Steps** — "list of lists" structure. Outer lists run sequentially, inner lists run in parallel. Simple, explicit ordering.
- **DAG** — tasks declare dependencies. Tasks without dependencies run immediately. More expressive for complex dependency graphs.

**WorkflowTemplates** enable cross-workflow reuse via `templateRef` field. Templates compose by invoking other templates through Steps or DAG invocators.

**Relevance to AutoBuilder**: Argo's dual orchestration model (Steps for simple sequential/parallel, DAG for complex dependencies) maps directly to AutoBuilder's pipeline needs:
- Simple workflows: Steps pattern (sequential stages, parallel within stages)
- Complex workflows: DAG pattern (dependency-driven execution order)

Argo's template type system (9 types) is over-engineered for AutoBuilder. Our agent type system (2 types: llm, custom) is sufficient.

**Applicable patterns**:
- Steps (list of lists) for sequential+parallel composition
- DAG for dependency-driven execution
- WorkflowTemplates for cross-workflow template reuse
- Entrypoint as the starting template (analogous to pipeline root agent)

---

## 2. Stage Schema Pattern Analysis

### 2.1 How Existing Systems Define Stages

| System | Stage Concept | Configuration Granularity | Transition Model |
|--------|--------------|--------------------------|------------------|
| Temporal | Activities within Workflows | Per-activity: timeout, retry, heartbeat, task queue | Explicit code (await activity result) |
| Prefect | Tasks within Flows | Per-task: retries, timeout, cache_key, tags | Implicit (return values), explicit (wait_for) |
| Airflow | Operators within DAGs | Per-operator: retries, timeout, pool, priority, trigger_rule | Explicit (>> / << operators) |
| Dagster | Ops within Graphs | Per-op: config schema, required resources, retry policy | Implicit (function parameters = dependencies) |
| GitHub Actions | Steps within Jobs | Per-step: timeout, env, if-conditions, with-inputs | Sequential within job, parallel across jobs |
| Argo | Templates within Workflows | Per-template: resources, timeout, retry, node selectors | Steps (list of lists) or DAG (dependency declarations) |
| Kestra | Tasks within Flows | Per-task: type, retry, timeout, allow_failure | Sequential by default, parallel via explicit markers |
| N8N | Nodes within Workflows | Per-node: credentials, parameters, retry, timeout | Graph edges (visual connections) |

### 2.2 Per-Stage Configuration Patterns

Three dominant patterns emerge:

**Pattern A: Decorator/Annotation Configuration** (Prefect, Dagster)
Configuration is attached to the stage definition itself via decorators or annotations. Compact, co-located with the implementation.

**Pattern B: Manifest/YAML Configuration** (Airflow, Argo, Kestra, GitHub Actions)
Configuration declared in a separate manifest file. Separation of configuration from implementation. Better for non-developers and version control.

**Pattern C: Builder/Code Configuration** (Temporal, N8N)
Configuration via code-level options objects passed to API calls. Maximum flexibility, type-safe, but requires code changes for configuration updates.

**AutoBuilder assessment**: AutoBuilder already uses Pattern B for workflow-level config (WORKFLOW.yaml) and Pattern A for agent-level config (YAML frontmatter in .md files). This hybrid is appropriate: workflow manifests declare infrastructure requirements (tools, models, pipeline type), while agent definitions declare behavioral configuration (instructions, tool roles, model roles). No change needed.

### 2.3 Stage Transition and Dependency Patterns

**Sequential**: Stages execute in order. Output of stage N is input to stage N+1. Simplest. Used by: Prefect monoflow, Argo steps (outer list), Kestra default.

**Parallel-within-sequential**: Stages are grouped into sequential phases. Within each phase, multiple stages run in parallel. Used by: Argo steps (inner list), Airflow TaskGroups, AutoBuilder batches.

**DAG**: Stages declare explicit dependencies. The orchestrator computes execution order. Used by: Airflow DAGs, Argo DAG templates, Dagster asset graphs.

**Event-driven**: Stages trigger on events from other stages. Maximum decoupling. Used by: Prefect event-triggered flows, N8N webhook nodes.

**Reconciliation**: No explicit transitions. A controller loop observes current state and takes the next necessary action. Used by: Kubernetes operators.

**AutoBuilder assessment**: AutoBuilder's current model is parallel-within-sequential (batches of deliverables). The PM IS the outer loop and decides batch composition dynamically. This is closer to the reconciliation model than the DAG model: the PM observes the delta between desired state (all deliverables complete) and actual state (current progress), then selects the next batch. This is more flexible than a static DAG because the PM can reorder, retry, or skip based on runtime information.

### 2.4 Completion Criteria Patterns

| Pattern | Systems | How It Works |
|---------|---------|-------------|
| Exit code / return value | All | Stage returns success/failure |
| Quality gates | GitHub Actions, AutoBuilder | Deterministic checks must pass before proceeding |
| Approval gates | Temporal (signals), Argo (suspend), AutoBuilder (CEO queue) | Human approval required at defined points |
| Convergence | Kubernetes operators | Actual state matches desired state |
| SLA / timeout | Temporal, Airflow, Argo | Time-bounded execution with escalation |
| Composite | AutoBuilder (planned) | Multiple criteria combined (lint pass AND test pass AND review approval) |

---

## 3. Plugin Architecture Comparison

### 3.1 Discovery and Registration

| System | Discovery | Registration | Hot Reload |
|--------|-----------|-------------|------------|
| N8N | npm packages + community marketplace | Install via UI or CLI | Yes (community nodes) |
| Temporal | SDK imports | Code-level registration | No (redeployment) |
| Prefect | Python imports + blocks | Decorator-based (implicit) | No (redeployment) |
| Airflow | Python packages + providers | pip install + restart | No |
| Dagster | Python packages + resources | Decorator-based (implicit) | No (redeployment) |
| GitHub Actions | Git repos (actions/*) | YAML reference | Yes (version tags) |
| Kestra | Java plugins + marketplace | Plugin install command | Restart required |
| Argo | Container images | YAML reference | Yes (per-workflow) |

**AutoBuilder's current model**: Directory scanning at startup (same as skill system). `app/workflows/*/WORKFLOW.yaml` discovered automatically. No code registration. No hot reload (restart required). This is the simplest viable approach and matches Airflow's provider model.

### 3.2 Manifest Formats

| System | Format | Key Fields |
|--------|--------|-----------|
| GitHub Actions | YAML (`action.yml`) | name, description, inputs, outputs, runs |
| Argo | YAML (CRD spec) | templates, entrypoint, arguments, volumes |
| Kestra | YAML (flow definition) | id, namespace, tasks, triggers, inputs |
| Airflow | Python (`dag.py`) | dag_id, schedule, default_args, tasks |
| AutoBuilder (current) | YAML (`WORKFLOW.yaml`) | name, description, triggers, required_tools, pipeline_type |

**Gap in AutoBuilder's current manifest**: The current WORKFLOW.yaml lacks stage/phase definitions. It declares pipeline_type (`batch_parallel`, `sequential`, `single_pass`) but does not define what stages exist within the pipeline. For small workflows this is fine (the pipeline.py defines stages in code). For large workflows with multiple phases, the manifest should declare the phase structure so the PM and Director can reason about progress without parsing Python.

### 3.3 Permission and Resource Scoping

| System | Permission Model |
|--------|-----------------|
| GitHub Actions | GITHUB_TOKEN permissions per workflow, secret scoping |
| Kubernetes | RBAC, namespaces, resource quotas |
| Kestra | Namespace-level isolation and permissions |
| N8N | Credential scoping per workflow |
| AutoBuilder | tool_role ceiling per agent (Decision #58), state key authorization via tier prefixes |

**AutoBuilder assessment**: The current model (tool_role ceiling + state key auth) is sufficient. Workflow manifests declare required_tools which gates what the pipeline can access. No change needed.

---

## 4. Variable-Scale Workflow Design Patterns

This is the core design challenge. How do systems handle workflows ranging from simple (2 stages) to complex (5+ stages with phases)?

### 4.1 Pattern: Progressive Disclosure (Prefect)

Prefect's four patterns (monoflow -> subflows -> deployments -> events) let developers choose the right complexity level. Simple workflows are a single decorated function. Complex workflows compose smaller flows. The framework does not force all workflows into the same structural pattern.

**Applicability to AutoBuilder**: HIGH. AutoBuilder's three pipeline_types (`single_pass`, `sequential`, `batch_parallel`) are already progressive disclosure. A small workflow uses `single_pass` (one agent pass, no batching). A medium workflow uses `sequential` (multiple stages, one at a time). A large workflow uses `batch_parallel` (multiple stages with parallel deliverable execution).

### 4.2 Pattern: Template + Override (GitHub Actions, Argo)

Base templates define the common structure. Specific workflows override individual stages. GitHub Actions' composite actions are reusable step sequences. Argo's WorkflowTemplates are shareable template libraries.

**Applicability to AutoBuilder**: ALREADY ADOPTED. AutoBuilder's 3-scope agent definition cascade (global -> workflow -> project) is exactly this pattern. Global agent definitions are the "base templates." Workflow-specific agent definitions override them. This needs no change.

### 4.3 Pattern: Dynamic Task Generation (Airflow, Temporal)

Airflow's `expand()` creates N task instances at runtime. Temporal spawns N child workflows from a parent. The workflow definition does not hardcode the number of parallel units.

**Applicability to AutoBuilder**: ALREADY ADOPTED. The PM's `select_ready_batch()` tool dynamically determines batch size and composition. DeliverablePipeline instances are created per deliverable at runtime.

### 4.4 Pattern: Hierarchical Grouping Without Execution Overhead (Airflow TaskGroups)

TaskGroups are visual/organizational containers within a single DAG. They do not create separate execution contexts, worker pools, or state boundaries. They exist for human comprehension.

**Applicability to AutoBuilder**: HIGH. For large workflows with multiple phases (SHAPE, DESIGN, PLAN, BUILD, TEST, MAINTAIN), phases should be organizational groupings within a single workflow execution, not separate workflow invocations. Each phase has its own agent configurations and quality gates, but they share session state and the PM orchestrates across them.

### 4.5 Pattern: Workflow-as-Spec vs Workflow-as-Code (Kestra vs Temporal)

Kestra: YAML-only definitions. Zero code. Maximum accessibility but limited expressiveness.
Temporal: Code-only definitions. Maximum expressiveness but requires developers.
Prefect/Dagster: Hybrid — Python with decorators. Code that reads like config.

**Applicability to AutoBuilder**: The hybrid approach is correct. WORKFLOW.yaml for metadata/config, pipeline.py for agent tree construction. The manifest declares "what" (name, triggers, tools, models); the Python module defines "how" (ADK agent composition). This separation is well-validated across the industry.

### 4.6 Pattern: Phase Progression Model

No surveyed system has a first-class concept of "phases within a workflow" that maps exactly to AutoBuilder's need (SHAPE -> DESIGN -> PLAN -> BUILD -> TEST -> MAINTAIN for a large software project). The closest analogues:

- **Airflow TaskGroups**: Visual grouping, flat execution
- **Temporal Continue-As-New**: Fresh execution context per phase, but loses parent orchestration
- **Argo Steps**: Sequential groups, but static at definition time

**This is a novel requirement for AutoBuilder.** The PM needs to drive a workflow through multiple phases, where each phase may have different agent configurations, quality gates, and deliverable decomposition strategies. This is not a "workflow engine" problem — it is a "project management" problem that happens to be orchestrated by software.

**Key insight**: Phases are not a workflow engine concept. They are a PM planning concept. The workflow manifest declares what phases exist and what each phase entails. The PM (an LLM agent) decides when to transition between phases based on completion criteria, project state, and Director guidance. The workflow engine simply provides the infrastructure.

---

## 5. Declarative vs Imperative Workflow Analysis

### 5.1 Industry Position

The industry has converged on a consistent answer: **declarative for what, imperative for how**.

| Aspect | Best Expressed As | Why |
|--------|-------------------|-----|
| Workflow identity (name, description) | Declarative (YAML) | Static metadata, easy to scan |
| Trigger conditions | Declarative (YAML) | Deterministic matching, no logic |
| Resource requirements (tools, models) | Declarative (YAML) | Validation at registration time |
| Pipeline structure (agent composition) | Imperative (Python) | ADK agent tree needs conditionals, factory patterns |
| Stage transitions | Imperative (Python/LLM) | Dynamic, context-dependent |
| Quality gates | Hybrid | Gate types declared (YAML), gate implementation in code |
| Phase definitions | Declarative (YAML) | Static structure, PM reads them |
| Phase transitions | Imperative (LLM) | PM reasoning, not deterministic rules |

### 5.2 Where Pure YAML Fails

- Conditional logic (if deliverable has dependency, resolve before planning)
- Dynamic agent composition (different review agents based on artifact type)
- Runtime parametrization (model selection based on deliverable complexity)
- Error handling strategies (retry vs skip vs escalate based on failure type)

### 5.3 Where Pure Code Fails

- Discoverability (scanning Python modules for workflow metadata is fragile)
- Non-developer access (PM and Director reason about workflows from metadata, not code)
- Validation without execution (manifest validation catches errors at registration time)
- Version control readability (YAML diffs are clearer than Python AST changes)

### 5.4 AutoBuilder Assessment

AutoBuilder's current split (WORKFLOW.yaml + pipeline.py) is the right approach. The manifest should be extended to include phase definitions (declarative) while keeping pipeline composition in Python (imperative). The PM reads the manifest to understand workflow structure; the pipeline.py constructs the ADK agent tree.

---

## 6. Recommendations for AutoBuilder

### 6.1 Extend WORKFLOW.yaml With Phase Definitions

The current manifest lacks a concept of phases/stages. For variable-scale workflows:

**Small workflows** (single_pass): No phases needed. The manifest stays minimal.

**Medium workflows** (sequential): Optional `stages` field listing the sequential stages. The PM uses this for progress tracking and reporting.

**Large workflows** (batch_parallel with phases): `phases` field defining the progression model. Each phase can have its own agent overrides, quality gates, and deliverable types.

Proposed manifest extension:

```yaml
name: auto-code
description: Autonomous software development from specification

triggers:
  - keywords: [build, develop, implement, code]
  - explicit: auto-code

required_tools: [file_read, file_write, file_edit, bash_exec, git_status, git_commit]
optional_tools: [web_search, web_fetch]

default_models:
  PLAN: anthropic/claude-opus-4-6
  CODE: anthropic/claude-sonnet-4-6
  REVIEW: anthropic/claude-sonnet-4-6

pipeline_type: batch_parallel

# Optional: phase progression for multi-phase workflows
# Omit entirely for single-phase workflows (simplicity for simple cases)
phases:
  - name: plan
    description: Decompose spec into deliverables with dependency graph
    agents: [planner]
    completion: all_deliverables_planned
  - name: build
    description: Implement, lint, test, and review all deliverables
    agents: [coder, reviewer, fixer, linter, tester]
    completion: all_deliverables_verified
  - name: integrate
    description: Integration testing and final verification
    agents: [tester, reviewer]
    completion: integration_tests_pass

# Pipeline configuration
pipeline:
  max_review_cycles: 3
  timeout_seconds: 300
  enable_linting: true
  enable_testing: true
```

**Key design choice**: `phases` is optional. Small workflows omit it entirely. The PM treats a workflow without phases as a single implicit phase. This avoids over-engineering simple workflows while providing structure for complex ones.

### 6.2 Keep Pipeline Composition in Python

Do not move pipeline composition to YAML. The ADK agent tree requires:
- Factory pattern instantiation (AgentRegistry.build())
- Conditional composition (different agents based on workflow config)
- Type-safe wiring (Python type checker validates agent composition)
- Access to shared infrastructure (toolset, skill library, agent registry)

The `pipeline.py` module remains the single place where ADK agent trees are constructed. The manifest provides metadata; the code provides behavior.

### 6.3 WorkflowRegistry Design

The registry should follow the SkillLibrary pattern exactly:
- Filesystem scan at startup
- Parse WORKFLOW.yaml manifests (lightweight)
- Defer pipeline instantiation (import pipeline.py only when creating)
- Redis-cached index (same cache pattern as skills)
- Automatic invalidation on file changes

Two-tier scanning: `app/workflows/` (built-in) + configurable project-local directory (custom workflows). Custom overrides built-in by name, same as skill override semantics.

### 6.4 Phase Progression Model

Phases are a PM planning concept, not a workflow engine concept. The PM reads the phase definitions from the manifest and drives progression through its reasoning loop:

1. PM reads `phases` from workflow manifest
2. PM starts at phase[0], sets `pm:current_phase` in session state
3. PM executes deliverables assigned to current phase
4. When phase completion criteria are met, PM advances to next phase
5. PM publishes phase transition events to Redis Streams

Phase completion is evaluated by the PM (LLM reasoning) against the declared `completion` field, with deterministic verification by safety mechanisms (checkpoint_project, regression tests). This is the reconciliation pattern from Kubernetes operators: the PM observes actual state, compares to desired state (phase completion criteria), and takes action.

### 6.5 Compound Workflow Support (Deferred)

Compound workflows (Decision #3, architecture doc section 6) are Phase 11+ scope. The current architecture already supports them:
- WorkflowRegistry can instantiate multiple workflows
- Session state persists across workflow executions
- Gateway can orchestrate sequential ARQ jobs
- No workflow assumes it is the only one in a session

No additional design work is needed for compound workflows in Phase 7.

---

## 7. Key Architectural Patterns to Adopt

### 7.1 Progressive Disclosure of Complexity

From Prefect. Workflows should be as simple as they need to be, no simpler:
- `single_pass`: One agent pass. No phases, no batching. Just run the pipeline.
- `sequential`: Multiple stages, one at a time. Optional `stages` for tracking.
- `batch_parallel`: Full batch orchestration with PM loop. Optional `phases` for multi-phase projects.

### 7.2 Organizational Grouping Without Execution Overhead

From Airflow (TaskGroups). Phases within a workflow are organizational containers for the PM's benefit. They do not create separate execution contexts, sessions, or worker processes. All phases share a single work session and PM instance.

### 7.3 Two-Level Reuse

From GitHub Actions (reusable workflows + composite actions). AutoBuilder has two reuse levels:
- **Workflow definitions** = pipeline templates (define agent composition, phases, quality gates)
- **Agent definitions** = shared task templates (reusable across workflows via 3-scope cascade)

### 7.4 Manifest for What, Code for How

From the industry consensus. WORKFLOW.yaml declares metadata, triggers, requirements, and phase structure. pipeline.py implements ADK agent tree construction.

### 7.5 Directory-Scanned Discovery

From N8N, Kestra, and the existing SkillLibrary. Zero-registration plugin model. Adding a workflow = adding a directory + WORKFLOW.yaml. The registry discovers it automatically.

### 7.6 Reconciliation-Style Orchestration

From Kubernetes operators. The PM loop is a reconciliation loop: observe state -> compare to desired -> take action. This is more resilient than static DAG execution because the PM can adapt to runtime conditions (failures, new information, priority changes).

---

## 8. Anti-Patterns to Avoid

### 8.1 SubDAG Anti-Pattern (Airflow)

Creating separate execution contexts for what should be organizational grouping. Airflow deprecated SubDAGs in favor of TaskGroups for this reason. **AutoBuilder risk**: treating workflow phases as separate workflow invocations instead of organizational groupings within a single PM session.

### 8.2 YAML-Everything Anti-Pattern (Kestra, N8N)

Putting complex logic in YAML. When workflows need conditional composition, error handling strategies, or dynamic agent selection, YAML becomes a programming language without a type checker. **AutoBuilder mitigation**: keep pipeline composition in Python, keep metadata in YAML.

### 8.3 Over-Typed Template Anti-Pattern (Argo)

Argo has 9 template types. This is excessive. Each type adds API surface, documentation burden, and mental overhead. **AutoBuilder mitigation**: two agent types (llm, custom) are sufficient. Resist adding more.

### 8.4 Forced Complexity Anti-Pattern

Requiring all workflows to declare phases, stages, quality gates, and completion criteria even when they are trivially simple. **AutoBuilder mitigation**: all manifest fields except `name` are optional. Progressive disclosure means simple workflows have simple manifests.

### 8.5 Static DAG Anti-Pattern

Pre-computing the entire execution graph at workflow definition time. This works for data pipelines (deterministic dependencies) but fails for agentic workflows (PM adapts strategy based on runtime results). **AutoBuilder mitigation**: the PM IS the outer loop. The PM dynamically decides what to execute next, not a static scheduler.

### 8.6 Shared Mutable State Anti-Pattern (N8N)

N8N nodes pass data directly through the graph. This makes debugging difficult and creates implicit coupling. **AutoBuilder mitigation**: all state flows through session state (explicit, persisted, auditable). No implicit data passing between agents.

### 8.7 Plugin Discovery at Runtime Anti-Pattern

Discovering and registering plugins during execution rather than at startup. This creates unpredictable behavior and makes testing harder. **AutoBuilder mitigation**: WorkflowRegistry scans at startup. Unknown workflow names fail fast with clear error messages.

---

## Sources

### Primary Documentation
- [N8N Workflows](https://docs.n8n.io/workflows/)
- [N8N Sub-workflows](https://docs.n8n.io/flow-logic/subworkflows/)
- [N8N Architecture Deep-Dive](https://jimmysong.io/blog/n8n-deep-dive/)
- [Temporal Workflows](https://docs.temporal.io/workflows)
- [Temporal Child Workflows](https://docs.temporal.io/child-workflows)
- [Temporal Long-Running Workflows](https://temporal.io/blog/very-long-running-workflows)
- [Prefect Flows](https://docs.prefect.io/v3/concepts/flows)
- [Prefect Workflow Design Patterns](https://www.prefect.io/blog/workflow-design-patterns)
- [Airflow DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)
- [Airflow Dynamic Task Mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html)
- [Dagster Software-Defined Assets](https://docs.dagster.io/concepts/assets/software-defined-assets)
- [GitHub Actions Reusable Workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations)
- [GitHub Actions Composite Actions](https://docs.github.com/actions/creating-actions/creating-a-composite-action)
- [Kubernetes Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Kubernetes Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Kestra Declarative Orchestration](https://kestra.io/features/declarative-data-orchestration)
- [Argo Workflows Core Concepts](https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/)
- [Argo Workflow Templates](https://argo-workflows.readthedocs.io/en/latest/workflow-templates/)

### Comparative Analysis
- [State of Open Source Workflow Orchestration 2025](https://www.pracdata.io/p/state-of-workflow-orchestration-ecosystem-2025)
- [Kestra vs Temporal vs Prefect 2025](https://procycons.com/en/blogs/workflow-orchestration-platforms-comparison-2025/)
- [Airflow vs Dagster vs Prefect 2026](https://bix-tech.com/airflow-vs-dagster-vs-prefect-which-workflow-orchestrator-should-you-choose-in-2026/)

### Agentic Workflow Patterns
- [Multi-Agent Frameworks 2026](https://www.adopt.ai/blog/multi-agent-frameworks)
- [AI Agent Orchestration Guide](https://www.digitalapplied.com/blog/ai-agent-orchestration-workflows-guide)
- [Design Patterns for Agentic Workflows](https://huggingface.co/blog/dcarpintero/design-patterns-for-building-agentic-workflows)
- [Temporal + AI Agents](https://dev.to/akki907/temporal-workflow-orchestration-building-reliable-agentic-ai-systems-3bpm)
- [Agent Orchestration 2026](https://iterathon.tech/blog/ai-agent-orchestration-frameworks-2026)
