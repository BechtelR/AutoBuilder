# Phase 7b FRD: Director Workflow Authoring
*Generated: 2026-04-13*

## Objective

Enable the Director to author, validate, and activate new workflows through conversation with the CEO — proving cross-domain workflow composability with two Director-authored workflows (auto-research, auto-writer). Introduces the node-based pipeline schema that replaces per-workflow Python pipeline definitions with a declarative, validatable composition model. Renames the "validator" abstraction to "gate" across the entire codebase for clarity on an agentic platform. Derives from PR-4, PR-6, PR-8, PR-22, PR-31, NFR-4, NFR-4b.

## Consumer Roles

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| **CEO (User)** | Converses with Director to define workflow requirements; reviews authored workflows at activation gate; approves/rejects; requests improvements; deactivates/deletes workflows | Conversation input → workflow activated in registry (or rejected with feedback) → workflow deactivated/deleted on request |
| **Director (System)** | Authors workflows using discovery tools, path-restricted filesystem access, and authoring skills; proposes improvements based on execution feedback | Requirements received → validated artifacts in staging → activated on CEO approval |
| **Execution Engine (System)** | PM and workers that execute workflows using the node-based pipeline schema; consumers of real INTEGRATE agents and research-domain gates | Node schema interpreted → agents dispatched per node → artifacts produced → gates produce real evidence |

## Appetite

**Large (L).** Upsized from roadmap's original M — the node-based pipeline schema, two Director-authored proof workflows, gate rename, and full E2E dry run are substantial scope additions agreed during shaping. The roadmap completion contract must be updated to reflect these. Node-based pipeline schema is a meaningful architecture deliverable — it is the value delivery mechanism of AutoBuilder. Two Director-authored workflows (auto-research, auto-writer) prove the system end-to-end. Gate rename is systematic but touches ~40 files. Pre-activation dry run with full E2E simulation.

## Capabilities

### CAP-1: Conversational Workflow Composition

The CEO defines workflow requirements through natural conversation with the Director. The Director interviews to understand the process, domain, quality needs, and available resources, then composes a complete workflow (manifest with node schema, agent definitions, node prompts, skills) following the 6-phase authoring lifecycle: requirements → discovery → draft → validation → review → activation.

**Requirements:**
- [ ] **FR-7b.01**: When the CEO describes a new process to the Director, the Director conducts a structured requirements conversation — eliciting process stages, quality criteria, required resources, and expected outputs — before drafting any workflow artifacts.
- [ ] **FR-7b.02**: When the Director has gathered sufficient requirements, it composes a complete workflow: manifest (WORKFLOW.yaml with node schema), agent definitions (markdown with YAML frontmatter), node prompts (organized external files), and optionally workflow-specific skills.
- [ ] **FR-7b.03**: When the Director composes a workflow, all authored agent definitions are restricted to `type: llm` only. The system rejects any agent definition with `type: custom` authored through the Director pipeline.
- [ ] **FR-7b.04**: When the Director composes a workflow, all node prompts are written as external markdown files organized within the workflow directory, not as inline YAML content.
- [ ] **FR-7b.05**: When the CEO provides ambiguous or incomplete requirements, the Director asks clarifying questions rather than making assumptions. The conversation continues until the Director has sufficient clarity to draft.
- [ ] **FR-7b.05a**: When the Director drafts a workflow with the same name as an existing active workflow, the system rejects the name at L1 validation and requires the Director to choose a unique name or explicitly declare intent to replace the existing version (which routes through the improvement loop, CAP-7).

---

### CAP-2: Resource Discovery

The Director queries five platform registries — tools, MCP servers, credentials, skills, and existing workflows — to map CEO requirements to available capabilities and identify gaps before drafting.

**Requirements:**
- [ ] **FR-7b.06**: When the Director needs to discover available resources, five discovery tools return current registry state: available tools with signatures, MCP server capabilities and status, configured credential names, registered workflows with summaries, and available skills with frontmatter metadata.
- [ ] **FR-7b.07**: When the Director queries credentials, the system returns credential names and availability status only. Credential values are never exposed through any discovery tool.
- [ ] **FR-7b.08**: When a resource required by the workflow does not exist (tool not registered, credential not configured, MCP server not available), the Director surfaces the gap to the CEO with specific remediation guidance before proceeding with the draft.
- [ ] **FR-7b.09**: When the Director queries existing workflows, it receives parsed manifests including stage schemas, node definitions, agent rosters, and gate configurations — enabling it to reference existing patterns when composing new workflows.

---

### CAP-3: Staging & Filesystem Scoping

The Director writes workflow artifacts to a staging directory only, not the active registry. Filesystem access is path-restricted to the staging area. The staging directory is not scanned by the workflow registry.

**Requirements:**
- [ ] **FR-7b.10**: When the Director writes workflow artifacts, all files are created within the staging directory. The Director cannot write to the active workflow registry, the project workspace, or any path outside staging.
- [ ] **FR-7b.11**: When the workflow registry scans for available workflows, the staging directory is excluded. Staged workflows are invisible to project creation and workflow matching until activated.
- [ ] **FR-7b.12**: When the CEO rejects a workflow at the activation gate, the staged artifacts remain available for iteration. The Director can modify and resubmit without starting from scratch.
- [ ] **FR-7b.13**: When a staged workflow is abandoned (CEO explicitly cancels or a configurable timeout elapses), the system cleans up the staging directory. Cleanup is logged.

---

### CAP-4: Workflow Validation Pipeline

Before activation, workflows pass through four validation levels: L1 (schema), L2 (reference integrity), L3 (parse/import), L4 (structural analysis). Results are presented to the CEO.

**Requirements:**
- [ ] **FR-7b.14**: When a workflow is submitted for validation, L1 validates the manifest against the WORKFLOW.yaml schema — required fields present, field types correct, stage names unique, gate names unique across manifest.
- [ ] **FR-7b.15**: When L1 passes, L2 validates reference integrity — all agents declared in node schemas exist as definition files, all tools declared in stage configurations are registered, all skills referenced are available, all gate evidence sources reference declared gates.
- [ ] **FR-7b.16**: When L2 passes, L3 validates structural parse — node prompts exist as files and are readable, agent definition frontmatter parses correctly, any `pipeline.py` (escape hatch) passes AST import allowlist validation and dangerous-call detection.
- [ ] **FR-7b.17**: When L3 passes, L4 validates structural analysis — stage completion criteria are satisfiable, node `produces`/`consumes` declarations (when present) form a valid dataflow with no unsatisfied inputs, gate schedules are compatible with stage structure.
- [ ] **FR-7b.18**: When any validation level fails, the system produces a structured error report identifying the specific failures, the validation level, and remediation guidance. The Director can iterate on the draft and resubmit.
- [ ] **FR-7b.19**: When all four levels pass, the validation report is included in the activation gate submission for CEO review.

---

### CAP-5: Activation Gate

CEO approval is required to move a workflow from staging to the active registry. The Director presents a summary, validation results, and dry run results. On rejection, the Director iterates. On approval, the workflow becomes discoverable.

**Requirements:**
- [ ] **FR-7b.20**: When a workflow passes validation, the Director submits an activation request to the CEO queue containing: workflow summary (name, description, stages, agents, gates), full validation report, dry run results (if executed), and the complete workflow artifacts for review.
- [ ] **FR-7b.21**: When the CEO approves activation, the system moves workflow artifacts from staging to the active registry directory. The workflow registry rescans and the workflow becomes available for project creation.
- [ ] **FR-7b.22**: When the CEO rejects activation, the rejection reason is returned to the Director. The Director can modify the workflow and resubmit through the validation pipeline.
- [ ] **FR-7b.23**: When a workflow is activated, the system records the activation event with: who authored it (Director), who approved it (CEO), timestamp, and validation evidence. The record is immutable.

---

### CAP-6: Pre-Activation Dry Run

Before activation, the Director can execute a full E2E dry run of the workflow with synthetic input using a lightweight LLM. The dry run exercises the complete pipeline lifecycle including pause/resume and edit injection.

**Requirements:**
- [ ] **FR-7b.24**: When the Director initiates a dry run, the system executes the workflow end-to-end with synthetic input generated by the Director — using a lightweight LLM model with a hard token budget cap enforced per-node (no single node can consume the entire budget).
- [ ] **FR-7b.24a**: When a dry run exhausts its token budget before completing all nodes, the system aborts the run and produces a partial report indicating: which nodes completed, where the budget was consumed, and guidance for reducing cost (e.g., simplify prompts, reduce node count).
- [ ] **FR-7b.25**: When a dry run executes, the system exercises the complete node sequence: agent dispatch per node, artifact production, signal flow, gate evaluation, and stage transitions.
- [ ] **FR-7b.26**: When a dry run executes, the system includes lifecycle simulation: a pause at a checkpoint boundary followed by resume, and a simulated edit operation mid-execution — proving state persistence and edit handling work correctly.
- [ ] **FR-7b.27**: By default, the system runs at minimum two dry run passes: one happy-path pass and one error-path pass (with injected failures to verify escalation and recovery). The CEO can request additional passes or skip the dry run entirely (explicit opt-out).
- [ ] **FR-7b.28**: When a dry run completes, the system produces a structured report: which nodes executed, which artifacts were produced, which gates passed/failed, which lifecycle events were tested, what issues were found, and total cost.
- [ ] **FR-7b.29**: When a dry run reveals issues, the Director fixes them and re-runs. The dry run cycle continues until a clean run is achieved or the CEO decides to proceed/abort.
- [ ] **FR-7b.30**: When the CEO has not explicitly opted out, the dry run results are required as part of the activation gate submission.

---

### CAP-7: Workflow Improvement Loop

Four feedback sources trigger improvement proposals: CEO request, post-completion review, execution failure patterns, and workflow memory accumulation. The Director drafts changes to staging, presents evidence, and activates on approval.

**Requirements:**
- [ ] **FR-7b.31**: When the CEO requests a workflow improvement, the Director analyzes the current workflow, proposes specific changes, and drafts the modified workflow to staging for the standard validation → review → activation cycle.
- [ ] **FR-7b.32**: When a project using a Director-authored workflow completes, the Director reviews the completion report and execution history. If it identifies improvement opportunities (repeated escalations, gate failures, inefficient node sequences), it proposes changes to the CEO.
- [ ] **FR-7b.33**: When execution failure patterns accumulate in workflow memory (e.g., a specific node type consistently fails on certain input types), the Director surfaces the pattern and proposes a workflow revision.
- [ ] **FR-7b.34**: When the Director proposes an improvement, the proposal includes: what changed, why (with evidence from execution history), and the expected impact. The CEO can approve, reject, or modify the proposal.
- [ ] **FR-7b.35**: When an improvement is approved, the modified workflow goes through the full validation and dry run cycle before replacing the active version. The previous version is preserved (not deleted) for manual recovery. Automated rollback is not in scope for this phase.

---

### CAP-8: Director Authoring Skills

Three new skills provide domain knowledge for workflow authoring. Skills load via the standard deterministic matching engine.

**Requirements:**
- [ ] **FR-7b.36**: The `director-workflow-composition` skill provides the Director with comprehensive authoring guidance: the 6-phase lifecycle, node schema composition patterns, agent definition authoring, gate configuration, manifest structure, and staging conventions. It loads as a role-bound skill for the Director agent.
- [ ] **FR-7b.37**: The `software-development-patterns` skill provides domain knowledge for composing software development workflows: common stage progressions, code-domain agents, code quality gates, and patterns from the auto-code reference workflow.
- [ ] **FR-7b.38**: The `research-patterns` skill provides domain knowledge for composing research and analysis workflows: source discovery patterns, synthesis stages, citation requirements, research-domain gates, and report output formats.
- [ ] **FR-7b.39**: When the Director authors a workflow, the appropriate domain skill (software-development-patterns or research-patterns) loads based on the workflow's declared domain. The composition skill loads unconditionally. When the workflow's domain does not match any available domain skill, only the composition skill loads and a warning is emitted — authoring proceeds without domain-specific guidance.
- [ ] **FR-7b.39a**: The auto-research and auto-writer workflows have access to research worker skills (source-evaluation, citation-standards) at runtime, loaded via the standard deterministic matching engine based on deliverable context. These skills (S29, S30) are moved from Phase 13 to Phase 7b as runtime dependencies for the auto-research and auto-writer workflows.

*Note: The architecture doc (Decision #77) references 9 total authoring skills across all phases. This phase delivers 3 new skills (S39-S41) plus moves 2 existing research worker skills (S29, S30) from Phase 13 to Phase 7b as workflow runtime dependencies. The remaining 6 (workflow-authoring, agent-definition, skill-authoring, project-conventions, workflow-quality, workflow-testing) are Phase 6/7a deliverables already built.*

---

### CAP-9: Node-Based Pipeline Schema

The workflow manifest defines execution through a node-based composition model: stages contain nodes (process units), nodes reference agents (staff) and prompts (objectives). This replaces per-workflow Python pipeline definitions with a declarative, validatable schema. Agents are reusable across nodes with different objectives.

**Requirements:**
- [ ] **FR-7b.40**: When a workflow manifest defines stages, each stage declares an agent pool (available agents) and a sequence of nodes. Each node specifies a name, a default agent from the pool, and a reference to an external prompt file that provides the node's objective.
- [ ] **FR-7b.41**: When the execution engine processes a node, it dispatches the node's declared agent with the node's prompt loaded as the TASK instruction fragment. The agent's IDENTITY (from its definition file) remains unchanged across nodes — the task changes, the role stays.
- [ ] **FR-7b.42**: When a node declares steps, the steps are author-declared sub-units executed sequentially within the node. Steps are not decomposed or reordered by the PM. The workflow author controls the decomposition.
- [ ] **FR-7b.43**: When a node declares `produces`, the execution engine registers the symbolic artifact name and allocates storage via the existing artifact storage service (Phase 8a). When a subsequent node declares `consumes`, the engine resolves the symbol to the artifact's location and makes it available to the agent. `produces`/`consumes` declarations are optional.
- [ ] **FR-7b.43a**: When a node declares `consumes` for an artifact that does not yet exist (preceding producer node failed, was skipped, or hasn't run), the system surfaces a structured error to the PM with the missing artifact name, the expected producer node, and the consumer node that needs it. Execution of the consumer node does not proceed.
- [ ] **FR-7b.44**: When a node declares `signals`, the execution engine writes the named signal keys to session state after the node completes. Gates read signals for pass/fail evaluation. Signals are lightweight coordination metadata, not work products.
- [ ] **FR-7b.45**: When a stage declares a composite node type (e.g., review loop), the schema specifies the composite's sub-agents, iteration limit, and termination condition declaratively. The execution engine interprets the composite without per-workflow Python code.
- [ ] **FR-7b.46**: When a node references an agent by name, the agent is resolved through the existing 3-scope cascade (global → workflow → project). The same agent definition can be used by multiple nodes with different prompts — no aliasing or duplication required.
- [ ] **FR-7b.47**: The auto-code workflow's existing `pipeline.py` is migrated to the node-based schema. The migrated schema produces equivalent behavior to the original Python pipeline. The `pipeline.py` file is retained only as an escape hatch for workflows requiring imperative logic beyond the schema's expressiveness.
- [ ] **FR-7b.48**: When a `pipeline.py` escape hatch exists, the system validates it with AST import allowlisting and dangerous-call detection before execution. The same validation applies to all `pipeline.py` files regardless of author (built-in, user, or Director).
- [ ] **FR-7b.49**: When no `pipeline.py` exists and the manifest contains a node schema, the execution engine interprets the schema directly. No Python code generation is required for standard workflows.

---

### CAP-10: Real INTEGRATE Agents

The auto-code workflow's INTEGRATE stage agents produce real evaluation evidence for the `integration_tests` and `architecture_conformance` gates, replacing Phase 7a stubs.

**Requirements:**
- [ ] **FR-7b.50**: When the INTEGRATE stage executes, an integration testing agent runs the project's integration test suite and writes structured results (pass/fail, test counts, failure details) as both an artifact and a signal that the `integration_tests` gate reads.
- [ ] **FR-7b.51**: When the INTEGRATE stage executes, an architecture conformance agent evaluates whether the implementation matches the documented design — comparing deliverable outputs against the project's architecture artifacts. It writes a structured assessment as both an artifact and a signal that the `architecture_conformance` gate reads.
- [ ] **FR-7b.52**: When either INTEGRATE agent produces a failing result, the gate blocks stage completion. The PM receives structured failure evidence and can retry, remediate, or escalate.
- [ ] **FR-7b.53**: When the INTEGRATE stage produces gate results, the three-layer completion report includes real machine-generated evidence for all three layers (functional, architectural, contract) — no stub or placeholder values remain.

---

### CAP-11: Standard Research Gates

Three workflow-agnostic research-domain gates ship as standard platform gates, available to any workflow that declares them.

**Requirements:**
- [ ] **FR-7b.54**: The `source_verification` gate (LLM type) evaluates whether research sources are credible, accessible, and relevant to the deliverable's objective. Any workflow can declare it in its manifest.
- [ ] **FR-7b.55**: The `citation_check` gate (deterministic type) evaluates whether all claims in the output cite sources and whether citations are valid (format correct, source referenced). Any workflow can declare it.
- [ ] **FR-7b.56**: The `content_review` gate (LLM type) evaluates whether output content is coherent, complete, well-structured, and meets the deliverable's quality criteria. Any workflow can declare it.
- [ ] **FR-7b.57**: When a workflow declares any research gate, the gate functions identically to code-domain gates — reading agent-produced signals from state and producing structured pass/fail evidence for completion reports.

---

### CAP-12: Workflow Deactivation & Deletion

The CEO can deactivate or delete Director-authored workflows. Deactivation preserves existing project attachments; deletion removes the workflow entirely. Both prevent new projects from using the workflow.

**Requirements:**
- [ ] **FR-7b.58**: When the CEO requests workflow deactivation, the system marks the workflow as disabled. The workflow registry excludes it from discovery, matching, and new project creation. Existing projects retain their workflow reference but cannot start new workflow operations.
- [ ] **FR-7b.59**: When a workflow is deactivated and existing projects reference it, the system creates a CEO queue item for each affected project: "Workflow deactivated — assign replacement workflow before continuing."
- [ ] **FR-7b.60**: When the CEO requests workflow deletion, the system requires two confirmation steps before proceeding. The first confirmation states the action. The second confirmation states the number of affected projects and that the action is irreversible.
- [ ] **FR-7b.61**: When a workflow is deleted, existing projects with that workflow lose workflow abilities and are flagged via CEO queue for new workflow assignment before any workflow functions can resume.
- [ ] **FR-7b.62**: Only the CEO has authority to deactivate or delete workflows. The Director can propose deactivation/deletion to the CEO queue but cannot execute it directly.
- [ ] **FR-7b.62a**: Built-in platform workflows (shipped with AutoBuilder) cannot be deleted. They can be deactivated by the CEO but the system warns that deactivation removes a platform-default capability. User-level and Director-authored workflows can be both deactivated and deleted.
- [ ] **FR-7b.63**: When a deactivated workflow is reactivated by the CEO, it becomes available for new projects and existing projects regain workflow abilities. No data is lost during deactivation.

---

### CAP-13: auto-research Workflow

A complete research workflow authored through the Director authoring pipeline, proving cross-domain composability. Performs end-to-end autonomous research from question to cited report.

**Requirements:**
- [ ] **FR-7b.64**: The auto-research workflow is authored entirely through the Director authoring pipeline (CAP-1 through CAP-6) — not hand-coded. If the Director cannot author it through the system, the authoring infrastructure is incomplete.
- [ ] **FR-7b.65**: The auto-research workflow defines a multi-stage process appropriate for research: source discovery, analysis/synthesis, report generation, and review/verification.
- [ ] **FR-7b.66**: The auto-research workflow uses research-domain agents (researcher, writer, reviewer) defined as declarative agent definition files with research-specific instructions.
- [ ] **FR-7b.67**: The auto-research workflow declares research-domain gates (source_verification, citation_check, content_review) at appropriate schedules within its stage schema.
- [ ] **FR-7b.68**: The auto-research workflow passes the full pre-activation dry run cycle and demonstrates correct end-to-end execution with synthetic input.

---

### CAP-14: auto-writer Workflow

A complete research-and-writing workflow authored through the Director authoring pipeline. Performs end-to-end research followed by long-form content production.

**Requirements:**
- [ ] **FR-7b.69**: The auto-writer workflow is authored entirely through the Director authoring pipeline — not hand-coded.
- [ ] **FR-7b.70**: The auto-writer workflow defines stages for research, outlining, drafting, revision, and final review — combining research and writing concerns in a single workflow.
- [ ] **FR-7b.71**: The auto-writer workflow reuses research-domain agents and gates from the platform standard set, demonstrating that workflows compose from shared building blocks.
- [ ] **FR-7b.72**: The auto-writer workflow passes the full pre-activation dry run cycle and demonstrates correct end-to-end execution with synthetic input.

---

### CAP-15: Gate Rename

Systematic rename of "validator" to "gate" across the entire codebase — code, YAML manifests, database schema, tests, documentation, and skills. Eliminates naming confusion on an agentic platform where "validator" implies an active agent.

**Requirements:**
- [ ] **FR-7b.73**: All code symbols (classes, functions, constants, module names) referencing the "validator" concept are renamed to use "gate" terminology. The rename covers the complete codebase — no mixed terminology remains.
- [ ] **FR-7b.74**: All workflow manifest fields referencing "validators" are renamed to "gates" — at both workflow-level and stage-level declarations. All existing manifests are updated.
- [ ] **FR-7b.75**: The database schema is updated to reflect the gate rename via a reversible migration. All persistent references to "validator" in table names, column names, and relationships use "gate" terminology after migration.
- [ ] **FR-7b.76**: All test files, test functions, and assertions referencing "validator" are updated to "gate". Test coverage is preserved — no tests are lost in the rename.
- [ ] **FR-7b.77**: All architecture documents, build-phase documents, skills, and roadmap references to "validator" are updated to "gate". The rename is propagated to every document that uses the term.
- [ ] **FR-7b.78**: After the rename, the full test suite passes and all quality checks are clean. Zero regressions.

---

## Non-Functional Requirements

- [ ] **NFR-7b.01**: AST validation of `pipeline.py` files completes in under 1 second for files up to 500 lines. Validation does not require importing or executing the file.
- [ ] **NFR-7b.02**: Resource discovery tools return results within the same latency bounds as existing gateway queries. Discovery does not trigger external API calls or LLM invocations.
- [ ] **NFR-7b.03**: Node schema parsing and interpretation adds less than 100ms overhead per stage transition. The execution engine interprets the schema at stage entry, not per-node.
- [ ] **NFR-7b.04**: Credential values are never logged, stored in workflow artifacts, or exposed through any tool, API response, or event stream. Only credential names and availability status are surfaced.
- [ ] **NFR-7b.05**: Dry run execution is isolated — it does not write to production databases, modify active workflow registries, or produce artifacts outside a temporary workspace. Cleanup is automatic on completion.

## Rabbit Holes

- **ADK agent reuse across nodes.** The node model assumes the same agent definition can serve multiple nodes with different TASK prompts. If ADK's agent lifecycle requires per-invocation reconstruction (which it does — agents are stateless config objects recreated per invocation), this works naturally. But verify that instruction assembly correctly swaps the TASK fragment per node without leaking prior node context.

- **Review loop as declarative composite.** The current `ReviewCycleAgent` is a CustomAgent with Python termination logic. Expressing this declaratively (max iterations + state-signal-based termination) requires the execution engine to understand composite node types. The first composite type (review_loop) must be general enough that future composites (parallel_group, conditional) follow the same pattern — but don't build those future types now.

- **Artifact registry symbol resolution.** When a node declares `produces: [implementation_plan]` and a later node declares `consumes: [implementation_plan]`, the execution engine resolves the symbol. If execution is non-linear (retries, skipped nodes, edit injections), the artifact may not exist when expected. The engine must handle missing artifacts gracefully — surface as a structured error, not a crash.

- **Gate rename blast radius.** The rename touches ~40 files and ~550 occurrences including a DB migration. Script it rather than doing it manually. Run the full test suite after each file group (code, tests, YAML, docs) to catch regressions incrementally.

- **Staging directory permissions.** The Director needs filesystem write access to staging, which it currently does not have (governance tier has no file tools). This requires adding path-restricted file tools to the Director's tool set — scoped to the staging directory only. Ensure the path restriction cannot be bypassed via symlinks or relative paths.

- **Dry run cost control.** Full E2E dry runs with real LLM calls can be expensive if the workflow has many nodes. The hard token budget cap must be enforced per-node, not just per-run, to prevent a single verbose node from consuming the entire budget.

- **Phase 8a dependency for dry run.** CAP-6 (Pre-Activation Dry Run) requires a working execution engine that can dispatch agents per node, manage artifacts, evaluate gates, and handle lifecycle events. Phase 8a is building this engine and is currently BUILDING. The dry run may need to implement a lightweight execution path for pre-activation validation that shares the schema interpretation logic but does not depend on the full production execution loop. Alternatively, Phase 7b's dry run capability ships after 8a's execution engine is functional — sequence these deliverables accordingly.

## No-Gos

- **Custom FunctionTool creation by the Director.** The Director can compose workflows using existing tools but cannot create new FunctionTools. Tool creation requires Python deployment and is a separate capability (not in scope).
- **`type: custom` agents in Director-authored workflows.** CustomAgents require Python class definitions. Director-authored agents are `type: llm` only. Custom agents are platform code.
- **Workflow marketplace or sharing.** Workflows are local-first. No publishing, discovery, or installation from external sources in this phase.
- **Pipeline.py as the primary authoring path.** The node schema is the primary composition model. `pipeline.py` exists only as an escape hatch for workflows that genuinely need imperative logic. The Director does not author `pipeline.py` files.
- **Full eval suite (Phase 14).** Phase 7b builds the pre-activation dry run foundation. The self-improving eval suite with regression accumulation, context optimization, and automated test case generation is Phase 14 scope.
- **Compound workflows.** A workflow that chains multiple workflow types (auto-research → auto-code) is Phase 11 scope.
- **Parallel execution within dry runs.** Dry runs execute sequentially. Parallel batch execution is Phase 8b scope.
- **Context optimizer integration.** The dry run does not optimize context. Context optimization is Phase 14 scope.
- **Automated workflow rollback.** Previous workflow versions are preserved for manual recovery but automated rollback (one-click revert to prior version) is not in scope.
- **Node-specific failure handling.** Runtime node failures during production execution follow the standard deliverable retry/escalate path (PR-12). No node-specific failure semantics are introduced in this phase.

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-7b.01–05a | PR-6 (Director composes workflows) | Workflow Management |
| FR-7b.03 | NFR-4b (project-scope agents type: llm only) | Agent Governance |
| FR-7b.06–09 | PR-8 (resource validation before execution) | Execution |
| FR-7b.07 | NFR-4 (credentials never logged) | Security |
| FR-7b.10–13 | NFR-4 (tool isolation, secure defaults) | Security |
| FR-7b.14–19 | PR-8 (resource validation), PR-4 (plugins install via WORKFLOW.yaml) | Workflow Management |
| FR-7b.20–23 | PR-6 (CEO retains activation authority), PR-17 (CEO queue) | Workflow Management, CEO Queue |
| FR-7b.24–30 (incl. 24a) | PR-6 (workflows model composability), PR-8 (validation) | Workflow Management |
| FR-7b.31–35 | PR-6 (Director composes workflows), PR-28 (workflow memory) | Workflow Management, Memory |
| FR-7b.36–39 (incl. 39a) | PR-31 (Agent Skills standard), PR-32 (deterministic activation) | Skills |
| FR-7b.40–49 (incl. 43a) | PR-4 (stage schema), PR-5 (per-stage agent config), PR-5a (instruction assembly) | Workflow Management |
| FR-7b.50–53 | PR-22 (three-layer verification), PR-11 (mandatory gates) | Completion Reporting |
| FR-7b.54–57 | PR-22 (three-layer verification) | Completion Reporting |
| FR-7b.58–63 (incl. 62a) | PR-6 (CEO retains deactivation/deletion authority), NFR-4 (secure defaults) | Workflow Management |
| FR-7b.64–68 | PR-6 (curated default workflow plugins) | Workflow Management |
| FR-7b.69–72 | PR-6 (curated default workflow plugins) | Workflow Management |
| FR-7b.73–78 | Engineering quality (no PRD requirement — naming clarity) | Engineering |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | Director can compose a new workflow through conversation with CEO | CAP-1: FR-7b.01–05 |
| 2 | Five resource discovery tools operational (never expose credential values) | CAP-2: FR-7b.06–09 |
| 3 | Director writes to staging directory, not active registry | CAP-3: FR-7b.10–13 |
| 4 | CEO approval required to activate a workflow (activation gate) | CAP-5: FR-7b.20–23 |
| 5 | Validation runs L1-L4 before activation (schema, references, parse, structural) | CAP-4: FR-7b.14–19 |
| 6 | Director-authored agents restricted to `type: llm` only | CAP-1: FR-7b.03 |
| 7 | Workflow improvement loop triggers on CEO request and post-completion review | CAP-7: FR-7b.31–35 |
| 8 | Three Director authoring skills operational (director-workflow-composition, software-development-patterns, research-patterns) | CAP-8: FR-7b.36–39 |
| 8a | Research worker skills (source-evaluation, citation-standards) available at runtime for auto-research/auto-writer workflows | CAP-8: FR-7b.39a |
| 9 | Import-level sandboxing validates dynamically imported pipeline definitions before execution | CAP-9: FR-7b.48 |
| 10 | INTEGRATE stage gates (integration_tests, architecture_conformance) produce real evaluation results, replacing Phase 7a stubs | CAP-10: FR-7b.50–53 |

**New scope beyond current contract (roadmap update needed):**

| # | New Scope Item | Covered By | Rationale |
|---|---------------|------------|-----------|
| 11 | Node-based pipeline schema replaces pipeline.py as primary composition model | CAP-9: FR-7b.40–49 | Core value delivery mechanism — agreed in shaping |
| 12 | auto-research workflow authored through Director pipeline | CAP-13: FR-7b.64–68 | Proves cross-domain composability end-to-end |
| 13 | auto-writer workflow authored through Director pipeline | CAP-14: FR-7b.69–72 | Proves cross-domain composability end-to-end |
| 14 | Pre-activation dry run with full E2E simulation | CAP-6: FR-7b.24–30 | Workflow quality foundation |
| 15 | Gate rename (validator → gate) | CAP-15: FR-7b.73–78 | Naming clarity on agentic platform |
| 16 | Workflow deactivation and deletion with CEO authority | CAP-12: FR-7b.58–63 | Workflow lifecycle completeness |
| 17 | Standard research gates (source_verification, citation_check, content_review) | CAP-11: FR-7b.54–57 | Required by auto-research/auto-writer workflows |
