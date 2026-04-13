# Phase 7 FRD: Workflow Composition
*Generated: 2026-04-11*

## Objective

Transform AutoBuilder from a single-pipeline system into a multi-workflow platform where each workflow is a self-contained, discoverable unit with its own stage schema, agent configuration, quality gates, and completion reports. After Phase 7, adding a new workflow means adding a directory with a manifest file -- zero registration code, zero core changes. Traces to PR-4 (workflows as plugins), PR-5 (per-stage agent configuration), PR-7 (user-level overrides), PR-8 (resource validation), PR-11 (mandatory validators), PR-22 (three-layer verification), PR-23 (deterministic close conditions), PR-31 (infrastructure skills), NFR-5 (plugin install without code changes).

## Consumer Roles

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| **PM System** | The PM agent driving stage transitions, TaskGroup lifecycle, and completion criteria evaluation within a workflow | Manifest loaded -> stages initialized -> deliverables executed within stages -> validators evaluated -> completion reports generated -> stage transitions driven -> workflow completes |
| **Workflow Author** | Developer or Director creating a manifest and pipeline definition to define a new workflow type | Manifest written -> directory placed -> system discovers on startup -> validates -> pipeline instantiates on request -> workflow executes end-to-end |
| **Gateway/Operator** | System bootstrapping, registry initialization, cache management, workflow listing and resolution | Startup -> registry scans directories -> caches index -> serves workflow metadata -> resolves workflow requests -> instantiates pipelines |
| **Worker Pipeline** | The deliverable pipeline consuming stage-scoped agent, tool, and skill configuration during execution | Stage config read -> agents filtered to stage roster -> tools scoped per stage -> skills merged across three tiers -> pipeline executes within stage constraints |

## Appetite

**L** -- per roadmap. Full pluggable workflow architecture including registry, manifest system, stage schema, validator framework, completion reports, auto-code workflow, three-tier skill/agent integration, and infrastructure skills.

---

## Capabilities

### CAP-1: Workflow Discovery and Registry

The system discovers workflow definitions by scanning configured directories for manifest files, indexes them by name, and makes them available for selection and instantiation. Two tiers of directories are scanned: built-in (shipped with the platform) and user-level (configurable location). User-level workflows override built-in workflows with the same name. The registry is populated at system startup and cached for fast access.

**Requirements:**

- [x] **FR-7.01**: When the system starts, it scans the built-in workflows directory for manifest files, parses each one, validates required fields, and builds an in-memory index keyed by workflow name. *(PR-4)*
- [x] **FR-7.02**: When both a built-in and a user-level workflow directory are configured, the system scans the built-in directory first, then the user-level directory. A user-level workflow with the same name as a built-in workflow replaces the built-in entirely in the index. *(PR-4, NFR-5)*
- [x] **FR-7.03**: When a user-level workflow has a unique name not present in the built-in set, it is added to the index alongside built-in workflows. *(PR-4, NFR-5)*
- [x] **FR-7.04**: When the user-level workflows directory does not exist or is not configured, the system operates with built-in workflows only and does not emit errors. *(PR-4, NFR-5)*
- [x] **FR-7.05**: When a consumer requests a workflow by explicit name, the system returns the workflow entry if it exists in the index, or reports a clear not-found error if it does not. *(PR-4)*
- [x] **FR-7.06**: When a consumer requests all available workflows, the system returns a list of every discovered workflow with its name, description, and pipeline type. *(PR-4)*
- [x] **FR-7.07**: When the registry index is built, it is cached so that subsequent requests retrieve the index without re-scanning the filesystem. When the cache is unavailable, the system falls back to a filesystem scan -- cache failure does not prevent workflow discovery. *(PR-4)*
- [x] **FR-7.08**: When a new workflow directory containing a valid manifest is placed in any scanned location, the system discovers it on the next startup or cache rebuild -- no code changes, no registration calls, no configuration edits are required. *(PR-4, NFR-5)*

---

### CAP-2: Manifest Progressive Disclosure

Workflow manifests validate with only two required fields: name and description. All other fields -- stages, validators, tools, models, resources, completion reports, conventions, triggers, and MCP server declarations -- layer in progressively with sensible defaults. A minimal manifest is fully valid; a comprehensive manifest provides the complete operating manual for the workflow.

**Requirements:**

- [x] **FR-7.09**: When a manifest contains only a name and description, the system accepts it as valid. Default values apply: no triggers (explicit name selection only), no required tools, single-pass pipeline type, no stages, no validators, generic completion report structure. *(PR-4)*
- [x] **FR-7.09b**: When a manifest declares `config`, `brief_template`, or `director_guidance` fields, their contents are validated against their respective type schemas and stored alongside the parsed manifest. *(PR-4)*
- [x] **FR-7.10**: When a manifest declares stages, each stage validates independently: stage names must be present and unique within the manifest. *(PR-4)*
- [x] **FR-7.11**: When a manifest declares validators, each validator must have a name, type, and schedule. Validator names must be unique across the entire manifest (workflow-level and stage-level combined). *(PR-4, PR-11)*
- [x] **FR-7.12**: When a manifest declares resources (credentials, services, knowledge dependencies), they are recorded for pre-execution validation by the Director. *(PR-8)*
- [x] **FR-7.13**: When a manifest declares MCP server references, each entry records the server name and whether it is required or optional. *(PR-4)*
- [x] **FR-7.14**: When a manifest's name is not in kebab-case, the system rejects it with a clear validation error. *(PR-4)*
- [x] **FR-7.15**: When a manifest's name or description is missing, the system rejects it with a clear validation error identifying the missing field. *(PR-4)*
- [x] **FR-7.16**: When a manifest contains a field that is structurally invalid (e.g., a stage with a duplicate name, a pipeline type that is not one of the recognized values), the system rejects the entire manifest with a diagnostic message and excludes it from the index. *(PR-4)*
- [x] **FR-7.17**: When a manifest declares stages but uses a single-pass pipeline type, the system logs a non-blocking warning (manifest is still indexed). When a validator references an agent not listed in any stage's agent roster, the system logs a non-blocking warning. *(PR-4)*

---

### CAP-3: Stage Schema and Transitions

Workflows optionally declare an ordered sequence of stages. Each stage specifies which agents, tools, skills, models, validators, and completion criteria apply. The PM drives stage transitions by evaluating completion criteria and invoking a reconfiguration action. Stages are organizational groupings within a single PM session -- they do not create separate execution contexts. Stages with automatic approval advance without PM reasoning when completion criteria are satisfied.

**Requirements:**

- [x] **FR-7.18**: When a workflow with stages begins execution, the system initializes stage state: the first declared stage becomes the current stage with a pending status, and the full stage schema is available in session state for PM reasoning. *(PR-4, PR-5)*
- [x] **FR-7.19**: When the PM evaluates that a stage's completion criteria are met, the PM invokes a stage reconfiguration action specifying the next stage. The system updates the current stage, marks the previous stage as completed, and makes the new stage's configuration active. *(PR-5)*
- [x] **FR-7.20**: When the PM attempts to skip a stage (advance to a non-sequential stage), the system rejects the action with a clear message. Stages must advance sequentially. *(PR-5)*
- [x] **FR-7.21**: When the PM attempts to revisit an already-completed stage, the system rejects the action. Stage progression is forward-only. *(PR-5)*
- [x] **FR-7.22**: When a stage declares an agent roster (e.g., only planner and reviewer), only those agents participate in deliverable execution during that stage. Omitting the agent roster makes all available agents eligible. *(PR-5)*
- [x] **FR-7.23**: When a stage declares tool scoping (additions and removals relative to the workflow baseline), the effective tool set for that stage reflects the workflow's required tools modified by the stage's additions and removals. *(PR-5)*
- [x] **FR-7.24**: When a stage declares additional skills to force-load, those skills are loaded alongside context-matched and role-bound skills during that stage. Stage skill declarations are additive. *(PR-5)*
- [x] **FR-7.25**: When a stage declares model overrides, they merge with the workflow's default model assignments for that stage. Stage-level overrides take precedence. *(PR-5)*
- [x] **FR-7.26**: When a stage has `approval: auto` and the system's completion verification returns success, the stage advances automatically without PM reasoning. PM reasoning is only involved for stages requiring Director or CEO approval. *(PR-5)*
- [x] **FR-7.27**: When a workflow has no stages declared (empty stage list), stage reconfiguration is a no-op and stage completion verification always succeeds. The workflow operates as a flat, single-stage pipeline. *(PR-4)*
- [x] **FR-7.28**: When a stage transition occurs, a stage lifecycle event is published to the event stream indicating the stage name, transition direction (started or completed), and timestamp. *(PR-4)*

---

### CAP-4: TaskGroup Lifecycle

The PM creates TaskGroups as runtime planning artifacts within stages. A TaskGroup is a bounded unit of work (roughly one work session) containing a batch of related deliverables. TaskGroups have deterministic close conditions that the PM cannot override -- they are hard gates enforced by the system regardless of PM reasoning.

**Requirements:**

- [x] **FR-7.29**: When the PM creates a TaskGroup within a stage, the system records the TaskGroup with its parent stage, sequence number, and initial status. *(PR-23)*
- [x] **FR-7.30**: When the PM attempts to close a TaskGroup, the system evaluates close conditions deterministically: all deliverables within the TaskGroup must be at their required completion status, all scheduled validators for the TaskGroup's scope must be passing, and no unresolved escalations may exist. If any condition fails, the close is rejected with the specific failure reasons. *(PR-23)*
- [x] **FR-7.31**: When a TaskGroup's close conditions are not met, the PM cannot override or bypass the gate. The rejection is absolute -- it is a hard gate, not a recommendation. *(PR-23)*
- [x] **FR-7.32**: When a TaskGroup completes successfully, the system records the completion timestamp and generates a completion report scoped to that TaskGroup's deliverables and validator results. *(PR-22, PR-23)*

---

### CAP-5: Completion Criteria Composition

Completion criteria for stages and TaskGroups compose from three independent dimensions, all of which must be satisfied (AND composition). Each dimension is evaluated independently: deliverable status is checked against the database, validator results are checked against recorded evidence, and approval status is checked against the approval authority. No single dimension passing is sufficient for completion.

**Requirements:**

- [x] **FR-7.33**: When a stage's completion criteria are evaluated, the system checks three dimensions simultaneously: (1) all deliverables are at the required status (default: all verified), (2) all required validators for that stage have passed, and (3) the required approval authority has approved. All three must be true for the stage to be considered complete. *(PR-11)*
- [x] **FR-7.34**: When a stage uses the default completion criteria (all deliverables verified), every deliverable associated with that stage must have completed with all its validators passed. *(PR-11)*
- [x] **FR-7.35**: When a stage uses a planning-specific completion criteria (all deliverables planned), every deliverable must have an implementation plan recorded, even if not yet executed. *(PR-11)*
- [x] **FR-7.36**: When a required validator has not yet been evaluated (the agent that produces its input has not run), the completion check treats the validator as failing. Missing evidence is never treated as passing. *(PR-11)*
- [x] **FR-7.37**: When a validator is declared as advisory (not required), its result is recorded but does not block completion. Only required validators participate in the AND composition. *(PR-11)*

---

### CAP-6: Validator Framework and Evidence Collection

Validators are mandatory quality gates declared in the workflow manifest. They evaluate existing agent output (state keys, database records) and record structured evidence. Validators do not perform the work -- they assess what agents have already produced. Three validator types exist: deterministic (check state keys or query data), LLM-based (invoke LLM reasoning against state), and approval (check approval status). Each validator produces a result with pass/fail status and machine-generated evidence.

**Requirements:**

- [x] **FR-7.38**: When a validator is evaluated, it produces a structured result containing: the validator name, pass/fail status, machine-generated evidence (structured data supporting the determination), a human-readable message, and the evaluation timestamp. *(PR-22)*
- [x] **FR-7.39**: When a deterministic validator evaluates, it reads a specific state key or queries a data source. No LLM call is involved. The result is fully reproducible given the same input state. *(PR-22)*
- [x] **FR-7.40**: When the lint validator evaluates, it reads the lint results from the pipeline's output state. It passes if no errors are reported. Its evidence includes the error count and error details. *(PR-22)*
- [x] **FR-7.41**: When the test suite validator evaluates, it reads test results from the pipeline's output state. It passes if all tests pass. Its evidence includes pass and fail counts. *(PR-22)*
- [x] **FR-7.42**: When the regression test validator evaluates, it reads regression test results from the pipeline's output state. It passes if all regression tests pass. Its evidence includes individual test names and their results. *(PR-22)*
- [x] **FR-7.43**: When the code review validator evaluates, it reads the review-passed indicator from the pipeline's output state. It passes if the indicator is true. This is a deterministic check, not an LLM call. Its evidence includes the review cycle count and the reviewer's final assessment. *(PR-22)*
- [x] **FR-7.44**: When the dependency validation validator evaluates, it checks the deliverable dependency graph for cycles and validity. It passes if the graph is acyclic and all referenced dependencies exist. Its evidence includes a summary of the dependency graph. *(PR-22)*
- [x] **FR-7.45**: When the deliverable status check validator evaluates, it queries all deliverables at the relevant scope (TaskGroup, stage, or workflow). It passes if every deliverable is at the required completion status. Its evidence includes the per-deliverable status list. *(PR-22)*
- [x] **FR-7.46**: When a batch of validators is evaluated at a given schedule (per-deliverable, per-batch, per-TaskGroup, or per-stage), only validators matching that schedule are executed. Validators at other schedules are not evaluated. *(PR-11)*
- [x] **FR-7.47**: When a validator's required input state key is missing (the producing agent has not yet run), the validator returns a failing result with a clear message indicating what input is missing. *(PR-11)*
- [x] **FR-7.48**: When validator results are produced, they are persisted to the database for audit trail and completion report assembly. *(PR-22)*
- [x] **FR-7.49**: When two stub validators (integration tests [required] and architecture conformance [advisory, required: false] for the INTEGRATE stage) are evaluated, they return passing results. These are Phase 7b placeholders -- the system records their presence in evidence but does not perform real evaluation. *(PR-22)*

---

### CAP-7: Completion Reports

Stage and TaskGroup completions produce structured reports with configurable verification layers. Each layer requires machine-generated evidence from validators -- assertion alone is never sufficient. Three default layers (functional, architectural, contract) apply when a manifest does not specify custom layers. Workflows add domain-specific sections for additional reporting dimensions.

**Requirements:**

- [x] **FR-7.50**: When a stage completes, the system generates a completion report scoped to that stage. The report assembles evidence from all validator results evaluated during the stage's lifecycle. *(PR-22)*
- [x] **FR-7.51**: When a completion report is generated and the manifest does not specify custom verification layers, three default layers are used: functional (does it work as specified?), architectural (does the implementation match the documented design?), and contract (were all deliverables completed?). *(PR-22)*
- [x] **FR-7.52**: When a manifest specifies custom verification layers, the report uses those layers instead of the defaults. Each layer references specific validators as its evidence sources. *(PR-22)*
- [x] **FR-7.53**: When a completion report layer references a validator, the layer's pass/fail status is derived from that validator's recorded results. The layer does not independently re-evaluate -- it aggregates existing evidence. *(PR-22)*
- [x] **FR-7.54**: When a manifest declares additional report sections (domain-specific metadata beyond the standard layers), those sections appear in the completion report alongside the verification layers. *(PR-22)*
- [x] **FR-7.55**: When a completion report is generated, it includes the scope identifier (which stage or TaskGroup it covers) and the generation timestamp. *(PR-22)*

---

### CAP-8: Pipeline Composition

Workflows define how agents compose into executable pipelines via a standard interface. A single context object bundles all shared infrastructure (agent registry, instruction context, manifest, skill library, tool set, model callbacks) so pipeline definitions remain clean and decoupled. Three standard composition patterns cover common use cases. Custom pipeline logic remains possible for advanced workflows.

**Requirements:**

- [x] **FR-7.56**: When a workflow's pipeline is instantiated, the system dynamically loads the workflow's pipeline definition from its directory and invokes it with a context object containing all shared infrastructure. The pipeline definition returns a composed agent tree ready for execution. *(PR-4)*
- [x] **FR-7.57**: When a workflow's pipeline definition is missing from the workflow directory, the system reports a clear not-found error. When the definition is present but structurally invalid (cannot be loaded, does not export the expected interface), the system reports a clear configuration error. *(PR-4)*
- [x] **FR-7.58**: When a workflow declares a single-pass pipeline type, a standard single-pass composition pattern is available for the pipeline definition to use. *(PR-4)*
- [x] **FR-7.59**: When a workflow declares a sequential pipeline type, a standard sequential composition pattern is available for the pipeline definition to use. *(PR-4)*
- [x] **FR-7.60**: When a workflow declares a batch-parallel pipeline type, a standard batch-parallel composition pattern is available for the pipeline definition to use. This pattern supports the select-batch, execute-parallel, validate, checkpoint cycle. *(PR-4)*
- [x] **FR-7.61**: When a pipeline definition needs agents, it obtains them through the context's agent registry, which resolves agent definitions through the three-scope cascade (global, workflow, project). The pipeline definition does not directly reference agent definition files. *(PR-5)*

---

### CAP-9: auto-code Workflow

The auto-code workflow is the first concrete workflow implementation. It defines autonomous software development from specification to verified output using a 5-stage schema (SHAPE, DESIGN, PLAN, BUILD, INTEGRATE). Each stage specifies its agent roster, tool scoping, validator pipeline, and approval authority. The auto-code manifest serves as both the production workflow and a reference example for workflow authors.

**Requirements:**

- [x] **FR-7.62**: When auto-code is selected, its manifest validates successfully and declares a batch-parallel pipeline type. *(PR-4)*
- [x] **FR-7.63**: When the auto-code manifest is loaded, it declares five stages in order: SHAPE (refine brief into specification), DESIGN (architecture and contracts), PLAN (decompose into deliverables), BUILD (implement and verify), and INTEGRATE (integration testing and final verification). *(PR-4, PR-5)*
- [x] **FR-7.64**: When the SHAPE stage is active, only the planner agent is eligible. An LLM-type validator evaluates specification completeness at stage end. Director approval is required to advance. *(PR-5)*
- [x] **FR-7.65**: When the DESIGN stage is active, the planner and reviewer agents are eligible. An LLM-type validator evaluates design consistency at stage end. Director approval is required to advance. *(PR-5)*
- [x] **FR-7.66**: When the PLAN stage is active, only the planner agent is eligible. A deterministic dependency validation validator runs at stage end. The completion criteria require all deliverables to have plans. The stage uses automatic approval -- it advances without Director or CEO involvement when criteria are met. *(PR-5)*
- [x] **FR-7.67**: When the BUILD stage is active, the full implementation agent roster is eligible (coder, reviewer, fixer, formatter, linter, tester, diagnostics). Per-deliverable validators run for lint, test, and code review. Per-batch regression tests run after each batch completes. *(PR-5, PR-11)*
- [x] **FR-7.68**: When the INTEGRATE stage is active, the tester, reviewer, and diagnostics agents are eligible. Integration tests and architecture conformance validators run at stage end (Phase 7b stubs returning passed). A final approval validator requires CEO approval. *(PR-5, PR-11)*
- [x] **FR-7.69**: When the auto-code manifest is loaded, it declares required tools for file operations, shell execution, and version control. It declares default model assignments for planning and implementation roles. *(PR-4)*
- [x] **FR-7.70**: When the auto-code workflow's pipeline is instantiated, it composes the agent tree using the standard batch-parallel pattern (or equivalent custom composition) and wires workflow-scope agent definitions from the registry. *(PR-4)*
- [x] **FR-7.71**: When the auto-code workflow directory is scanned, the system discovers it automatically alongside any other workflows in the same parent directory. No special registration or hardcoded reference is needed. *(PR-4, NFR-5)*
- [x] **FR-7.72**: When the auto-code workflow is active, workflow-scope agent definitions (planner, coder, reviewer with auto-code-specific instructions) override the global agent definitions of the same name for that workflow's execution. *(PR-5)*

---

### CAP-10: Three-Tier Agent and Skill Integration

Agent definitions and skills merge across three tiers when a workflow is active: global (shipped with the platform), workflow-specific (inside the workflow directory), and project-specific (in the user's repository). Each higher tier overrides the lower tier by name. This extends the existing two-tier override model from Phase 6 by adding the workflow tier in the middle.

**Requirements:**

- [x] **FR-7.73**: When a workflow is active and it contains workflow-specific skill definitions, the skill index is built from three tiers: global skills first, then workflow skills (overriding global by name), then project skills (overriding both by name). *(PR-5, PR-31)*
- [x] **FR-7.74**: When a workflow skill has a unique name not present in the global set, it is added alongside global skills (additive, not just override). *(PR-5, PR-31)*
- [x] **FR-7.75**: When an agent registry builds agents for a workflow pipeline, it scans agent definition files from three scopes: global definitions, then workflow-scope definitions (overriding global by name), then project-scope definitions (overriding both by name). *(PR-5)*
- [x] **FR-7.76**: When a project-scope agent definition would grant tool access beyond what the workflow manifest's declared tool set allows, the system logs a warning. The workflow manifest's tool declarations serve as a ceiling for project-scope tool access. *(PR-5)*

---

### CAP-11: Workflow Trigger Matching

Workflows declare triggers that enable deterministic matching against user requests. Two trigger types exist: keyword (user request contains any declared keyword) and explicit (user names the workflow directly). Matching is deterministic -- no LLM call is involved. When multiple workflows match, explicit triggers take precedence over keyword triggers.

**Requirements:**

- [x] **FR-7.77**: When a user request contains a keyword declared in a workflow's trigger list, that workflow is matched. *(PR-4)*
- [x] **FR-7.78**: When a user explicitly names a workflow (matching the workflow's explicit trigger), that workflow is matched with highest precedence. *(PR-4)*
- [x] **FR-7.79**: When a workflow declares no triggers, it is only selectable by explicit name -- it never matches via keyword. *(PR-4)*
- [x] **FR-7.80**: When multiple workflows match a user request via keywords, the system returns all matching workflows for the caller to resolve. *(PR-4)*
- [x] **FR-7.81**: When both an explicit match and keyword matches exist for the same request, the explicit match takes precedence. *(PR-4)*

---

### CAP-12: Infrastructure Skills

Five infrastructure skills are operational and teach workflow authoring patterns, validator design, and testing approaches. Three skills (workflow-authoring, agent-definition, skill-authoring) already exist from Phase 6. Two new skills (workflow-quality and workflow-testing) are added. Additionally, one workflow-specific skill (test-generation) ships with auto-code.

**Requirements:**

- [x] **FR-7.82**: When the workflow-quality skill is loaded, it provides guidance on validator types, scheduling strategies, evidence requirements, completion criteria composition, and three-layer verification report design. It applies to planner and reviewer agents. *(PR-31)*
- [x] **FR-7.83**: When the workflow-testing skill is loaded, it provides guidance on workflow validation approaches, stage transition testing, manifest validation, and pipeline verification. It applies to tester and coder agents. *(PR-31)*
- [x] **FR-7.84**: When a pipeline for auto-code scans the workflow's skill directory, the test-generation skill is discovered and available for deliverables involving test creation or test-related file patterns. *(PR-31)*
- [x] **FR-7.85**: When the skill index is rebuilt, the two new infrastructure skills (workflow-quality, workflow-testing) are present in the index, each with valid frontmatter and body content under 3000 words in imperative style. The three existing Phase 6 skills (workflow-authoring, agent-definition, skill-authoring) remain operational and indexed. *(PR-31)*

---

## Non-Functional Requirements

- [x] **NFR-7.01**: Manifest validation (parsing and field validation of a single manifest) completes in under 100 milliseconds. Full registry scan (all manifests in both directories) completes in under 2 seconds for up to 50 workflows.
- [x] **NFR-7.02**: Workflow trigger matching against the full registry completes in under 10 milliseconds per user request -- matching is O(n) in the number of indexed workflows with constant-time per-trigger evaluation.
- [x] **NFR-7.03**: Stage completion verification (deliverable status + validator results + approval status) completes in under 500 milliseconds, including any database queries.
- [x] **NFR-7.04**: The workflow composition system introduces no new external dependencies -- it uses only the filesystem, Redis (already available), and existing database infrastructure.
- [x] **NFR-7.05**: Registry cache invalidation is atomic -- at no point does a request see a partially rebuilt index. The old index serves requests until the new index is fully built.
- [x] **NFR-7.06**: Validator evidence is structured data (not free-form text) so that completion reports can aggregate it mechanically. Evidence schemas are consistent across all validators of the same type.
- [x] **NFR-7.07**: All stage state keys use the `pm:` tier prefix per the established state key authorization model. Only PM-tier agents can write stage state.

---

## Rabbit Holes

- **Stage vs. TaskGroup disambiguation**: "Stage" is a manifest-declared structural grouping (DESIGN, BUILD). "TaskGroup" is a PM-created runtime planning unit (~1 hour of work within a stage). Requirements, state keys, and completion gates exist for both. Confusing them during implementation leads to gates that check the wrong scope -- e.g., evaluating stage-level validators when a TaskGroup closes, or checking TaskGroup deliverables at stage boundaries.

- **Validator type confusion**: The code review validator is deterministic (reads a boolean from state), not an LLM call. The distinction matters because deterministic validators are fully reproducible and fast, while LLM validators introduce non-determinism and latency. Misclassifying a validator type in the manifest changes its execution model.

- **Pipeline definition dynamic import**: Instantiating a pipeline requires dynamically loading and executing a module from a user-level directory. Phase 7 trusts user-placed files; import-level sandboxing is deferred to Phase 7b. The security boundary is the file system -- only files the user placed in the workflows directory are loaded.

- **Manifest field collision with YAML reserved constructs**: Fields like `version` and `name` are common YAML keys. Manifest parsing must handle YAML anchors, aliases, and edge cases (e.g., `true`/`false` string values) gracefully without misinterpreting manifest intent.

- **Stage reconfiguration is state-only**: Stage transitions update session state keys -- they do not rebuild agent trees or create new sessions. If implementation accidentally introduces agent tree rebuilds on stage transitions, it couples stages to execution contexts, violating the organizational-not-executional design principle.

- **Three-tier skill merge ordering**: The middle tier (workflow skills) is new in Phase 7. If the scan order is wrong (e.g., project before workflow), override semantics break. The correct order is global -> workflow -> project, where each later tier overwrites earlier entries by name.

- **Stub validators returning true**: The INTEGRATE stage's integration tests and architecture conformance validators are Phase 7b stubs. They must be explicitly documented as stubs in their evidence output so that completion reports do not misrepresent the verification depth. A passing stub is not the same as a passing real validator.

---

## No-Gos

- **Director workflow authoring** -- Phase 7b. The Director's ability to compose new workflows through conversation is a separate capability requiring the staging area, CEO approval gate, and authoring skill suite.
- **Compound workflows** -- Phase 11. Workflows that span multiple workflow types (e.g., research + code) require registry orchestration not yet built.
- **Project-scoped workflows** -- Decision #72. Workflows are selected for a project, not customized within one. Project-scope overrides apply to agents and skills, not to the workflow itself.
- **Dashboard and CLI workflow routes** -- Phase 10/12. User-facing workflow selection, listing, and status display are client concerns, not workflow engine concerns.
- **Custom validators** -- Custom validators require deploying new evaluation logic. The Director composes existing standard validators in novel combinations via the manifest; it cannot create new validator types.
- **Real MemoryService integration** -- Phase 9. Context recreation uses degraded-mode stubs; real memory persistence is a future capability.
- **Stage overlap and concurrency** -- Phase 8+. The `allow_stage_overlap` concurrency model (multiple stages active simultaneously) is not part of Phase 7.
- **Import-level sandboxing for pipeline definitions** -- Phase 7b. Dynamic import of user-level pipeline definitions executes arbitrary code; L4 import validation is deferred.

---

## Traceability

### PRD Coverage

> **Note (PRD v7.3 back-propagation):** PR-4 was expanded to include "available edit operations" in workflow plugin definitions. The `edit_operations` manifest field is a Tier 3 optional field covered by existing FR-7.09b (additional fields validated against type schemas). No new FRD requirement is needed -- the field follows the same progressive disclosure pattern as `mcp_servers`, `brief_template`, and `director_guidance`. The runtime behavior (accepting and routing edit requests) is Phase 8a scope (BOM X27). See `delta-report.md` for full analysis.

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-7.01, FR-7.05, FR-7.06, FR-7.07, FR-7.08 | PR-4 (Workflows are plugins with zero core code changes) | Discovery & registry |
| FR-7.02, FR-7.03, FR-7.04 | PR-4 (Workflows are plugins), NFR-5 (Plugin install without code changes) | User-level discovery |
| FR-7.09, FR-7.10, FR-7.11, FR-7.14, FR-7.15, FR-7.16, FR-7.17 | PR-4 (WORKFLOW.yaml with zero core code changes) | Manifest validation |
| FR-7.12 | PR-8 (Director validates all resources required by the workflow stage) | Resource validation |
| FR-7.13 | PR-4 (Workflow manifest defines infrastructure) | MCP servers |
| FR-7.18, FR-7.19, FR-7.20, FR-7.21, FR-7.27, FR-7.28 | PR-4 (Stage schema), PR-5 (Per-stage agent config) | Stage schema |
| FR-7.22, FR-7.23, FR-7.24, FR-7.25, FR-7.26 | PR-5 (PM assembles appropriate agent configuration per stage) | Per-stage scoping |
| FR-7.29, FR-7.30, FR-7.31 | PR-23 (TaskGroup cannot close while conditions unmet) | TaskGroup lifecycle |
| FR-7.32 | PR-22, PR-23 (TaskGroup completion report + close conditions) | TaskGroup lifecycle |
| FR-7.33, FR-7.34, FR-7.35, FR-7.36, FR-7.37 | PR-11 (Validators are mandatory; cannot be skipped by agent judgment) | Completion criteria |
| FR-7.38, FR-7.39, FR-7.40, FR-7.41, FR-7.42, FR-7.43, FR-7.44, FR-7.45, FR-7.46, FR-7.47, FR-7.48, FR-7.49 | PR-22 (Three verification layers; machine-generated evidence) | Validators & evidence |
| FR-7.50, FR-7.51, FR-7.52, FR-7.53, FR-7.54, FR-7.55 | PR-22 (Completion reports with three verification layers) | Completion reports |
| FR-7.56, FR-7.57, FR-7.58, FR-7.59, FR-7.60, FR-7.61 | PR-4 (Workflows are plugins), PR-5 (Agent configuration per stage) | Pipeline composition |
| FR-7.62 through FR-7.72 | PR-4 (Stage schema), PR-5 (Per-stage agent/tool/skill config), PR-11 (Validator scheduling), NFR-5 (Plugin install) | auto-code workflow |
| FR-7.73, FR-7.74, FR-7.75, FR-7.76 | PR-5 (Agent and skill scoping per stage), PR-31 (Skills open standard) | Three-tier integration |
| FR-7.77, FR-7.78, FR-7.79, FR-7.80, FR-7.81 | PR-4 (Workflows are plugins with deterministic matching) | Trigger matching |
| FR-7.82, FR-7.83, FR-7.84, FR-7.85 | PR-31 (Skills implement Agent Skills open standard) | Infrastructure skills |
| NFR-7.01, NFR-7.02 | NFR-2 (System overhead is not a meaningful contributor to stage duration) | Performance |
| NFR-7.04 | NFR-6 (Runs fully on a single machine with no cloud dependencies) | Dependencies |
| NFR-7.05 | NFR-3 (Crash recovery; reliability) | Cache atomicity |
| NFR-7.07 | NFR-4c (State key authorization enforces tier-based write access) | Security |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | WorkflowRegistry discovers auto-code on startup via directory scan | CAP-1: FR-7.01, FR-7.08; CAP-9: FR-7.71 |
| 2 | `POST /workflows/run {"workflow": "auto-code"}` resolves and instantiates pipeline. Gateway route wiring deferred to Phase 10; Phase 7 delivers the underlying resolution and instantiation capability. | CAP-1: FR-7.05; CAP-8: FR-7.56; CAP-9: FR-7.62, FR-7.70 |
| 3 | Adding a new workflow = adding a directory + manifest (zero registration code) | CAP-1: FR-7.08; CAP-2: FR-7.09 |
| 4 | User-level workflows at `~/.autobuilder/workflows/` override built-in by name | CAP-1: FR-7.02, FR-7.03, FR-7.04 |
| 5 | WORKFLOW.yaml validates with progressive disclosure (2-field minimum is valid) | CAP-2: FR-7.09, FR-7.15, FR-7.16 |
| 6 | auto-code manifest includes 5-stage schema with per-stage agent/tool/skill config | CAP-9: FR-7.63, FR-7.64, FR-7.65, FR-7.66, FR-7.67, FR-7.68, FR-7.69 |
| 7 | Stage completion criteria compose as AND (deliverables + validators + approval) | CAP-5: FR-7.33, FR-7.34, FR-7.36 |
| 8 | Standard validators (lint, test, regression, review) produce machine evidence | CAP-6: FR-7.38, FR-7.40, FR-7.41, FR-7.42, FR-7.43 |
| 9 | Completion reports generated (configurable verification layers) | CAP-7: FR-7.50, FR-7.51, FR-7.52, FR-7.53, FR-7.54 |
| 10 | TaskGroup/stage close conditions enforced deterministically (hard gates) | CAP-4: FR-7.30, FR-7.31; CAP-5: FR-7.33, FR-7.36 |
| 11 | Five infrastructure skills operational | CAP-12: FR-7.82, FR-7.83, FR-7.84, FR-7.85 |
