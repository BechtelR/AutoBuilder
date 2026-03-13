# Workflow Composition Patterns Research - March 2026

Research date: 2026-03-12
Focus: Workflow composition, stage management, and resource orchestration patterns from production systems

---

## Motivation

AutoBuilder's Phase 7 introduces a Workflow Composition System. This research analyzes eight external systems to identify proven patterns for workflow definition, stage management, resource orchestration, and quality enforcement. The goal is architectural guidance, not implementation detail.

---

## Part 1: AI-Native Workflow Systems

### 1.1 Stripe Minions

**Source**: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents

**Pattern**: Deterministic-Agent-Deterministic sandwich

**How it works**: Stripe's one-shot end-to-end coding agents use a deliberate architecture where deterministic infrastructure controls workflow flow and the LLM fills creative gaps within hard constraints. The system selects context, scopes the task, invokes the model, then deterministically validates and applies the output. The model never decides what happens next at the workflow level.

**Key findings**:

- The winning pattern is deterministic infrastructure wrapping non-deterministic AI. The system owns control flow; the model owns content generation within a scoped context.
- Code review is the quality bottleneck, not code generation. Stripe found that generating code is the easy part; verifying correctness at scale requires structured, deterministic quality gates.
- Prompt engineering becomes system engineering. At Stripe's scale, prompts are not strings in a config file. They are versioned, tested, composed from structured fragments, and treated as production infrastructure.
- One-shot execution eliminates multi-turn drift. Rather than iterating with the model, they provide maximum context upfront and expect a complete result. Retry is a system-level concern, not a conversation-level one.

**Relevance to AutoBuilder**: HIGH. Validates AutoBuilder's deterministic CustomAgent + probabilistic LlmAgent split. Reinforces that quality gates must be deterministic system checks, not LLM self-evaluation. The "sandwich" pattern maps directly to stages that scope what an agent sees and validate what it produces.

---

### 1.2 Shopify ROAST

**Source**: https://github.com/Shopify/roast

**Pattern**: Directory-based workflow definition

**How it works**: ROAST (Ruby-based agent orchestration) defines workflows as filesystem directories. Each step is a numbered subdirectory containing its own prompt file, tool configuration, and model selection. The workflow runner traverses directories in order, executing each step with its scoped configuration.

```
workflow/
  01_analyze/
    prompt.md
    config.yml
  02_implement/
    prompt.md
    config.yml
  03_review/
    prompt.md
    config.yml
```

**Key findings**:

- Configuration over code. Workflows are authored by editing files in directories, not by writing orchestration code. This makes workflows inspectable, diffable, and versionable with standard tools.
- Each step is self-contained. A step declares its own model, tools, and prompt. The workflow runner provides the execution environment; the step provides the intent.
- Workflows are portable. Because they are directories with standard file formats, they can be shared, templated, and composed without runtime dependencies.
- No step-level control flow. Steps execute sequentially. Branching and looping are handled by the system, not declared in the workflow definition. This keeps workflow definitions simple.

**Relevance to AutoBuilder**: HIGH. Directly informs the "workflow ecosystem as directory" pattern. AutoBuilder's workflow directories can follow the same principle: self-contained directories with declarative configuration, where the runtime provides execution and the directory provides intent. This aligns with the existing agent definition file pattern (markdown + YAML frontmatter).

---

### 1.3 LangGraph

**Source**: LangGraph documentation and examples

**Pattern**: Agent-as-graph with explicit state machines

**How it works**: LangGraph models agent workflows as directed graphs where nodes are processing steps and edges are conditional transitions. State is explicit and typed. Each node receives the current state, performs work, and returns a state update. Checkpointing enables human-in-the-loop patterns and crash recovery.

**Key findings**:

- Explicit state management prevents agent drift. When state is implicit (conversation history), agents lose track of objectives over long interactions. When state is a typed object with named fields, the system can enforce invariants and the agent can be reminded of its exact position.
- Subgraph composition enables workflow reuse. A review cycle can be defined once as a subgraph and embedded in multiple workflows. The parent graph passes state in and receives state updates out.
- Checkpointing is essential for human-in-the-loop. Any node can be a "pause point" where execution suspends, state is persisted, and a human provides input before resumption.
- Graph structure makes control flow visible. Unlike chain-of-thought or pure conversation approaches, the graph topology is inspectable and debuggable. You can see exactly which paths are possible and which state transitions are allowed.

**Relevance to AutoBuilder**: MEDIUM. AutoBuilder uses ADK's agent hierarchy rather than explicit graphs, but the principles apply. Explicit state management (via ADK session state with typed keys) prevents the same drift problem. The subgraph composition pattern validates AutoBuilder's approach of composable agent definitions.

---

## Part 2: General-Purpose Workflow Orchestration

### 2.1 Temporal

**Source**: Temporal documentation and architecture

**Pattern**: Durable execution with deterministic orchestration

**How it works**: Temporal separates Workflows (deterministic orchestration functions) from Activities (non-deterministic side effects). Workflows are replayed from event history on crash recovery, so they must be deterministic. Activities handle external calls, file I/O, and other side effects with automatic retry, timeout, and compensation.

**Key findings**:

- Separate deterministic orchestration from non-deterministic execution. This is the foundational insight. The workflow function decides what to do; activities do it. The workflow function is replayable; activities are not.
- History-based replay enables crash recovery without checkpointing. Because the workflow function is deterministic, replaying the event history reproduces the exact same sequence of activity invocations. Completed activities return their cached results; pending activities re-execute.
- Compensation patterns handle partial failure. When a multi-step workflow fails partway through, compensation activities can undo completed steps. This is declared, not improvised.
- Timeouts are first-class. Every activity has a start-to-close timeout, a schedule-to-start timeout, and a heartbeat timeout. The workflow function can branch on timeout vs. completion.

**Relevance to AutoBuilder**: HIGH for the separation principle. AutoBuilder's CustomAgent (deterministic) + LlmAgent (non-deterministic) split mirrors Temporal's Workflow/Activity split. The timeout and compensation patterns inform how stages should handle LLM failures: the stage (deterministic) decides retry policy; the agent (non-deterministic) executes.

---

### 2.2 Prefect

**Source**: Prefect documentation and architecture

**Pattern**: Python-native flow/task decomposition with coupling spectrum

**How it works**: Prefect uses Python decorators (`@flow`, `@task`) to define workflows. Flows can call tasks and subflows. Tasks are the unit of retry, caching, and concurrency. Subflows enable composition without code changes.

**Key findings**:

- Coupling spectrum from tight to loose. Prefect supports a progression: monoflow (everything in one function) to subflows (composed flows) to orchestrator patterns (one flow triggers others) to event-driven (flows react to external events). Teams start simple and loosen coupling as needs grow.
- Dynamic task generation handles variable-length work. A flow can generate tasks at runtime based on data (e.g., one task per file to process). This is declarative at the task level but dynamic at the flow level.
- Subflows are the composition primitive. A subflow runs as a child of the parent flow, inheriting configuration but maintaining its own state and retry boundary. This enables reuse without the complexity of event-driven coordination.
- Start simple, loosen coupling when forced. Prefect explicitly recommends starting with tightly-coupled flows and only introducing orchestrator or event-driven patterns when the tight coupling becomes a bottleneck.

**Relevance to AutoBuilder**: HIGH for the coupling spectrum insight. AutoBuilder should start with single-workflow execution (one workflow per project, tightly coupled stages) and make workflow chaining forward-compatible without implementing it now. This matches the "simplest solution for today's problem" principle.

---

### 2.3 Dagster

**Source**: Dagster documentation and architecture

**Pattern**: Software-defined assets with resources as first-class citizens

**How it works**: Dagster's core abstraction is the "asset" -- a persistent object (file, table, model) that is produced by computation. Assets declare their dependencies, forming a DAG. Resources (database connections, API clients, configuration) are injectable dependencies declared separately from asset logic.

**Key findings**:

- Resources as first-class citizens. Resources are declared, configured, and validated independently of the computation that uses them. A workflow declares which resources it needs; the runtime provides and validates them before execution begins.
- Pre-flight resource validation. Before any computation runs, Dagster validates that all declared resources are available and properly configured. This fails fast with clear errors rather than failing mid-execution when a missing resource is first accessed.
- Materialization-based execution. Assets are "materialized" (computed and persisted). The system tracks which assets are stale and which are fresh, enabling incremental re-execution.
- Separation of business logic from infrastructure. Asset functions contain pure business logic; resources abstract away infrastructure concerns. This makes assets testable with mock resources and portable across environments.

**Relevance to AutoBuilder**: HIGH for resource management. AutoBuilder projects depend on external resources (API keys, repositories, deployment targets, credentials). Declaring these as first-class entities with pre-flight validation prevents mid-workflow failures. The resource injection pattern maps to how AutoBuilder could provide validated resources to workflow stages.

---

### 2.4 N8N

**Source**: N8N documentation and community

**Pattern**: Visual workflow builder with composable templates

**How it works**: N8N provides a node-based visual workflow editor. Workflows are trigger-action chains where each node has typed inputs and outputs. Workflows can be shared as templates and composed via sub-workflow nodes.

**Key findings**:

- Workflows as shareable, composable units. N8N's community has thousands of workflow templates that users import, customize, and compose. The key enabler is a standard format (JSON) with typed node interfaces.
- Trigger diversity matters. N8N supports webhook triggers, schedule triggers, manual triggers, and event triggers. The same workflow can be invoked through multiple trigger types without modification.
- Node contracts enable composition. Each node declares its input schema and output schema. The editor validates connections at design time. This is the visual equivalent of artifact contracts.
- Community-driven workflow discovery. Users discover workflows through a shared library, not by building from scratch. The most successful workflows solve common patterns that many users need.

**Relevance to AutoBuilder**: MEDIUM. The "workflows as shareable units" and "node contracts" concepts apply, but AutoBuilder's workflows are more complex (multi-agent, multi-stage) than N8N's integration pipelines. The template/sharing model could inform a future workflow library, but is beyond Phase 7 scope.

---

## Part 3: Cross-System Synthesis

### 3.1 The Universal Pattern

Across all eight systems, one principle emerges consistently:

**"The model does not run the system. The system runs the model."**

Every successful production system places deterministic infrastructure in control of workflow progression, resource allocation, quality validation, and error recovery. The non-deterministic component (whether an LLM, a human, or an external API) operates within constraints defined by the deterministic layer. Systems that give the model control over its own workflow (pure ReAct loops, unconstrained tool use) consistently produce less reliable results at scale.

### 3.2 Artifact Contracts Between Stages

Multiple systems (Temporal, Dagster, N8N, Prefect) use typed contracts between workflow stages:

- **Temporal**: Activity return types are explicitly declared. The workflow function receives typed results.
- **Dagster**: Assets declare their output type. Downstream assets declare their input type. The framework validates compatibility.
- **N8N**: Nodes declare input/output schemas. The editor validates connections.
- **Prefect**: Tasks return typed results. Downstream tasks receive typed inputs.

The pattern: each stage declares what it **produces** and what it **consumes**. The runtime validates these contracts before execution, preventing mid-workflow type mismatches.

### 3.3 Resource Pre-Flight Validation

Systems that handle resource validation well (Dagster, Temporal) share a common pattern:

1. **Declaration**: The workflow declares all resources it needs upfront.
2. **Validation**: Before any work begins, the runtime validates that all declared resources are available and properly configured.
3. **Injection**: Validated resources are provided to workflow stages through a controlled interface, not through global state or environment inspection.
4. **Failure**: If validation fails, the workflow does not start. The error message identifies exactly which resource is missing or misconfigured.

Systems that skip pre-flight validation (early LangChain, basic ReAct loops) frequently fail mid-execution when a required API key is missing or a database is unreachable.

### 3.4 Stage-Based Progressive Complexity

Shopify ROAST, Stripe Minions, and Temporal all use stages to control complexity:

- **Stripe**: Each phase of the coding pipeline has different context, different quality criteria, and different retry policies. The model sees only what is relevant to its current phase.
- **ROAST**: Each numbered directory is a stage with its own prompt, tools, and model. The workflow runner controls progression.
- **Temporal**: Workflow functions use sequential activity invocations to model stages. Each activity has its own timeout and retry policy.

The pattern: stages are not new execution primitives. They are configuration scopes that filter which tools, agents, context, and quality criteria are active at a given point in the workflow.

---

## Part 4: Implications for AutoBuilder

### 4.1 What AutoBuilder Already Gets Right

This research validates several existing AutoBuilder design decisions:

- **API-first gateway with anti-corruption layer**: Matches the universal "system runs the model" pattern. ADK is an internal engine, never exposed.
- **Out-of-process execution (ARQ workers)**: Mirrors Temporal's separation of orchestration from execution. The gateway orchestrates; workers execute.
- **Deterministic + probabilistic agent mix**: CustomAgent (deterministic) + LlmAgent (probabilistic) directly implements the Stripe "sandwich" pattern.
- **Hierarchical supervision (CEO, Director, PM, Workers)**: Provides the deterministic control structure that all successful systems use to constrain non-deterministic execution.
- **Skills-based knowledge injection**: Scoped context delivery matches Stripe's principle of providing maximum relevant context upfront.
- **Event-driven architecture (Redis Streams)**: Enables the loose coupling that Prefect identifies as the mature end of the coupling spectrum.

### 4.2 Gaps This Research Addresses

| Gap | Informed By | Pattern |
|-----|------------|---------|
| No stage schema | Temporal, Stripe, ROAST | Stages as named configuration scopes filtering existing infrastructure (tools, agents, quality criteria) |
| No workflow ecosystem model | ROAST, N8N | Self-contained directory with standards, knowledge, validators, agent overrides |
| No resource pre-flight validation | Dagster, Temporal | Deterministic validation before any agent execution begins |
| No artifact contract declarations | Dagster, N8N, Temporal | Stages declare what they produce and consume; runtime validates compatibility |
| No Director workflow authoring | All systems (configuration over code) | Director creates workflows through skills, not code; declarative YAML + markdown |
| No resource library | Dagster | CEO-registered resources as first-class DB entities with validation metadata |

### 4.3 Architectural Decisions Informed by This Research

**D-70: Stages are named configuration scopes, not new execution primitives.**
Informed by Temporal's Workflow/Activity separation and Dagster's resource scoping. A stage definition specifies which agents are active, which tools are available, which quality gates apply, and which resources are required. The execution engine is unchanged; stages configure it.

**D-71: Workflow ecosystem = extended directory.**
Informed by Shopify ROAST's directory-based workflow definition. A workflow directory contains stage definitions, agent overrides, skill references, quality criteria, and resource declarations. The runtime reads the directory and configures itself accordingly. Workflows are inspectable, diffable, and versionable with standard tools.

**D-72: Resource pre-flight is a deterministic CustomAgent.**
Informed by Dagster's resource injection and Temporal's deterministic separation. Before any LLM agent runs, a deterministic CustomAgent validates that all declared resources (API keys, repositories, deployment targets) are available and properly configured. Failure is immediate and specific.

**D-73: Single-workflow primary, workflow chaining forward-compatible.**
Informed by Prefect's coupling spectrum. Phase 7 supports one workflow per project with tightly-coupled stages. The schema and interfaces are designed so that workflow chaining (output of one workflow feeds input of another) can be added without breaking changes, but it is not implemented until there is a proven need.

**D-74: Director authoring via skills.**
Informed by the universal "configuration over code" pattern across all systems. The Director creates and modifies workflows through a dedicated skill that generates the declarative directory structure. Workflows are never authored by writing Python code.

**D-75: Resource library is a DB entity.**
Informed by Dagster's resources-as-first-class-citizens. Resources (API keys, service accounts, repository access) are registered by the CEO, stored in the database, and referenced by name in workflow definitions. The resource library provides validation metadata, scoping rules, and lifecycle management.

---

## Part 5: Summary

### Strongest Signals

1. **Deterministic wrapping is non-negotiable.** Every successful production system places deterministic infrastructure in control. LLMs operate within scoped, validated, quality-gated stages.

2. **Configuration over code for workflow definition.** Shopify ROAST, N8N templates, Dagster asset definitions, and Prefect decorators all push workflow definition toward declarative formats. The most accessible systems use filesystems and YAML, not code.

3. **Resources must be first-class.** Dagster and Temporal demonstrate that treating resources as afterthoughts causes mid-execution failures. Declaration, validation, and injection are the three phases.

4. **Artifact contracts prevent integration failures.** When stages declare what they produce and consume, the runtime can validate compatibility before execution. This is cheaper than debugging a failed multi-hour workflow.

5. **Quality is infrastructure, not judgment.** Stripe's finding that code review is the bottleneck applies broadly. Quality gates must be deterministic system checks (linting, type checking, test execution, schema validation), not LLM self-evaluation.

6. **Start tight, loosen when forced.** Prefect's coupling spectrum is pragmatic guidance. Single-workflow execution with sequential stages is the right starting point. Event-driven workflow composition is the right destination, reached incrementally.

### What This Research Does NOT Cover

- Specific YAML schema design for workflow definitions (implementation detail)
- Stage transition state machine specification (implementation detail)
- Resource encryption and credential management (security concern, separate research)
- Workflow versioning and migration (future concern, post-Phase 7)
- Multi-tenant workflow isolation (future concern, post-Phase 7)

---

*References: All sources accessed March 2026. Stripe Minions blog, Shopify ROAST GitHub repository, LangGraph documentation, Temporal documentation, Prefect documentation, Dagster documentation, N8N documentation.*
