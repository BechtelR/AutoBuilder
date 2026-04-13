# Phase 8a FRD: Autonomous Execution Loop
*Generated: 2026-04-12*

## Objective

Phase 8a connects all prior infrastructure — workflow composition (Phase 7), supervision hierarchy (Phase 5b), toolset (Phase 4), and skills (Phase 6) — into a working autonomous execution loop. For the first time, a user can express project intent to the Director and receive verified deliverables without manual intervention during execution. This phase proves the core thesis: specification to verified output under hierarchical supervision. Derives from PR-1, PR-8, PR-10, PR-13, PR-14, PR-22.

## Consumer Roles

| Role | Description | E2E Boundary | Scope |
|------|-------------|--------------|-------|
| **CEO (User)** | Human operator who directs the system via Director chat sessions, resolves escalations, approves stage completions, and monitors execution via CLI/dashboard | Chat message → Director response; CEO queue item → resolution; status query → system state | Full system, all projects |
| **Director Agent** | Root agent mediating all work entry — creates projects, manages queues, delegates to PMs, monitors execution | Brief → Project → PM delegation; Queue item → triage → resolve or forward | Full system, all projects |
| **PM Agent** | Per-project agent driving stage execution using management tools against persistent storage | Tool call → DB read/write → autonomous Stage → TaskGroup → Batch → Deliverable loop | Single project |

## Appetite

**L (Large)** — ~2-3 weeks of focused effort. Fixed time, variable scope. 15 capabilities, ~30 components. If scope exceeds budget, split further into 8a/8b/8c. Capabilities ordered by priority; lower-priority capabilities are the first candidates for deferral.

---

## Capabilities

### CAP-1: Director-Mediated Project Creation & Brief Submission

All work enters through the Director following the supervision hierarchy (CEO → Director → PM → Workers). The Director handles seven entry modes through chat sessions: new (shape from scratch), new-with-materials (evaluate and incorporate user artifacts), extend (add scope to existing project), edit (modify existing deliverables), re-run (same workflow, new inputs), direct execution (completed Brief submitted directly), and workstream (bounded task within a known project). Once a Brief is complete, the Director validates it, creates a Project, and delegates to a PM.

**Requirements:**
- [ ] **FR-8a.01**: When the CEO initiates a new project through a Director chat session, the Director conducts an intake conversation to understand the project intent, determines the entry mode, and shapes the conversation toward producing a validated Brief according to the target workflow's template.
- [ ] **FR-8a.02**: When the Director determines the Brief is complete, it validates the Brief against the target workflow's `brief_template` definition. If the Brief fails validation, the Director communicates the specific deficiencies to the CEO and continues the conversation.
- [ ] **FR-8a.03**: When a Brief passes validation and resources are verified, the Director creates a Project entity in the database with workflow type, brief content, initial status, and project configuration.
- [ ] **FR-8a.04**: After project creation, the Director delegates to a PM by enqueuing a work session. The CEO is notified via the CEO queue that autonomous execution has begun.
- [ ] **FR-8a.05**: When the CEO submits pre-existing artifacts (new-with-materials mode), the Director evaluates the submitted artifacts against workflow requirements and produces a Brief that incorporates them — proceeding to project creation without requiring a full shaping conversation.
- [ ] **FR-8a.06**: When the CEO requests an extension or edit of an existing project, the Director analyzes the existing project state (deliverables, conventions, memory) and produces a Brief scoped to the requested changes, creating new work within the existing project rather than a new project.
- [ ] **FR-8a.07**: When the CEO requests a re-run of a workflow with new inputs, the Director creates a new project using the same workflow type with the new input parameters.
- [ ] **FR-8a.08**: When the CEO submits a completed Brief directly (direct execution mode), the Director validates it against the workflow template without requiring a shaping conversation. If valid, the Director proceeds directly to project creation.
- [ ] **FR-8a.09**: When the CEO routes a bounded task within a known project (workstream mode), the Director identifies the target project and PM, and creates a scoped Brief for the specific task without full project initialization.
- [ ] **FR-8a.10a**: When workflow resolution is ambiguous (multiple workflows match the user's intent), the Director presents the options to the CEO and waits for clarification before proceeding.
- [ ] **FR-8a.10b**: When no matching workflow can be resolved for the Brief, the Director surfaces an error to the CEO listing available workflow types and their descriptions.

---

### CAP-2: Brief Validation & Pre-Execution Resource Checks

Before execution begins, the system validates the Brief against the workflow's template and verifies all required resources. Validation failures surface immediately. Execution never begins with missing resources.

**Requirements:**
- [ ] **FR-8a.10**: When a Brief is submitted for execution, the system validates all required fields defined in the workflow's `brief_template`. Missing or invalid fields produce a structured validation error listing each deficiency.
- [ ] **FR-8a.11**: Before the first deliverable is dispatched, the system validates all resources declared in the workflow manifest's `resources` field: credentials are present and non-empty, services are reachable, and knowledge files or directories exist.
- [ ] **FR-8a.12**: When any pre-execution resource check fails, the system surfaces the failure to the CEO queue immediately with specific details of what is missing and how to resolve it. Execution does not begin until all resources are validated.
- [ ] **FR-8a.13**: When all resource checks pass, the system records the validation results as audit events. Resource failures declared in the manifest never occur mid-run.

---

### CAP-3: Durable Management Operations

All PM and Director management operations persist durably and produce consistent results. No operation returns placeholder responses. The following management operations are available to each role:

- **Director**: create project, validate brief, check resources, delegate to PM, escalate to CEO, list projects, query project status, override PM, query dependency graph
- **PM**: select ready batch, update deliverable, query deliverables, reorder deliverables, escalate to Director, manage dependencies, checkpoint project, reconfigure stage (already operational)
- **Shared**: create task, update task, query tasks

**Requirements:**
- [ ] **FR-8a.14**: When the PM calls `select_ready_batch`, the system queries deliverable records in the database, evaluates the dependency graph, and returns the set of deliverables whose dependencies are all satisfied, ordered by topological sort.
- [ ] **FR-8a.15**: When the PM calls `update_deliverable`, the system writes the status change and optional result data to the deliverable's database record. Valid statuses: PLANNED, IN_PROGRESS, COMPLETE, FAILED, SKIPPED.
- [ ] **FR-8a.16**: When the PM calls `query_deliverables`, the system returns deliverable records from the database filtered by requested criteria (status, project, stage, TaskGroup).
- [ ] **FR-8a.17**: When the PM calls `reorder_deliverables`, the system updates the execution order of deliverables within a TaskGroup in the database.
- [ ] **FR-8a.18**: When the PM calls `manage_dependencies`, the system adds, removes, or queries dependency edges between deliverables in the database. Circular dependencies are detected and rejected.
- [ ] **FR-8a.19**: When the PM or Director calls `query_dependency_graph`, the system returns the full dependency graph for a project's deliverables including the status of each node and any cycles detected.
- [ ] **FR-8a.20**: When a PM or Worker calls `escalate_to_director`, the system creates a `DirectorQueueItem` record in the database with escalation type, priority, context, and source information. The item is immediately visible via Director queue routes.
- [ ] **FR-8a.21**: When the Director calls `escalate_to_ceo`, the system creates a `CeoQueueItem` record in the database with item type, priority, context, and source information. The item is immediately visible via existing CEO queue routes.
- [ ] **FR-8a.22**: When the Director calls `list_projects`, the system returns all project records with current status, workflow type, stage, and cost summary.
- [ ] **FR-8a.23**: When the Director calls `query_project_status`, the system returns comprehensive project status: deliverable counts by status, current stage, active TaskGroup, pending escalations, accumulated cost, and wall-clock duration.
- [ ] **FR-8a.24**: When the Director calls `override_pm`, the system applies the requested action (pause, resume, reorder, correct) to the PM's execution state for the specified project and records the override as an audit event.
- [ ] **FR-8a.25**: When any agent calls `task_create`, `task_update`, or `task_query`, the system creates, updates, or queries task records in the database.
- [ ] **FR-8a.26**: All management tools access persistent storage through a uniform mechanism. No tool uses an alternative persistence path.
- [ ] **FR-8a.27**: When a management tool's database operation fails, the tool returns a structured error with an error code and description. No tool returns placeholder strings or succeeds silently on failure.
- [ ] **FR-8a.28**: When the Director calls `create_project`, the system creates a project record in the database with workflow type, brief content, initial configuration, and SHAPING status.
- [ ] **FR-8a.29**: When the Director calls `validate_brief`, the system validates the brief content against the resolved workflow's `brief_template` and returns a structured pass/fail result with per-field details.
- [ ] **FR-8a.30**: When the Director calls `check_resources`, the system verifies all resource requirements from the workflow manifest and returns a structured result indicating which resources passed and which failed.
- [ ] **FR-8a.31**: When the Director calls `delegate_to_pm`, the system enqueues a work session for the specified project. The project status transitions from SHAPING to ACTIVE.
- [ ] **FR-8a.32**: When the PM calls `checkpoint_project`, the system persists critical state (deliverable statuses, stage progress, accumulated cost) at the current TaskGroup boundary as a durable checkpoint.

---

### CAP-4: Director Queue Operations & Observability

The CEO can list and resolve Director queue items. Escalation tools create real queue records. The Director manages its own queue during standard operations. The CEO has override access for oversight.

**Requirements:**
- [ ] **FR-8a.33**: When the CEO requests the Director queue listing, the system returns all `DirectorQueueItem` records filtered by status and sorted by priority descending then creation time ascending.
- [ ] **FR-8a.34**: When the CEO resolves a Director queue item, the system updates the item's status to RESOLVED, records the resolution text and resolver identity, and timestamps the action.
- [ ] **FR-8a.35**: When the CEO forwards a Director queue item to the CEO queue, the system creates a corresponding `CeoQueueItem` with the original context preserved plus the forwarding rationale, and marks the Director queue item as FORWARDED_TO_CEO.
- [ ] **FR-8a.36**: When `escalate_to_director` is called, the created `DirectorQueueItem` is visible via the Director queue gateway route immediately after the database transaction commits.
- [ ] **FR-8a.37**: When `escalate_to_ceo` is called, the created `CeoQueueItem` is visible via the existing CEO queue gateway routes immediately after the database transaction commits.

---

### CAP-5: Director Backlog Orchestration

The Director execution loop triages the backlog: reads pending Director queue items, resolves items within its authority, and forwards items beyond its authority to the CEO queue. The Director monitors all active projects and can intervene at any point.

**Requirements:**
- [ ] **FR-8a.38**: When the Director execution loop runs, it reads all pending `DirectorQueueItem` records, prioritized by escalation priority (CRITICAL > HIGH > NORMAL > LOW) then creation time.
- [ ] **FR-8a.39**: When the Director encounters an item within its decision scope (status reports, resource requests within its authority, pattern alerts with known resolution), it resolves the item autonomously and records the resolution.
- [ ] **FR-8a.40**: When the Director encounters an item beyond its authority (CEO-level decisions, cost ceiling overrides, project abort requests), it forwards the item to the CEO queue with its assessment and recommended resolution options.
- [ ] **FR-8a.41**: When the Director detects cross-project patterns (multiple projects escalating similar failures, systemic resource issues), it surfaces a pattern alert to the CEO queue with aggregated evidence.
- [ ] **FR-8a.42**: When the Director backlog loop completes with no pending items, the loop yields until new items arrive via the existing `process_director_queue` cron mechanism.

---

### CAP-6: Autonomous Stage-Driven Execution Loop

The PM drives execution through workflow stages following the hierarchy: Stage → TaskGroup → Batch → Deliverable. Within each stage, the PM creates TaskGroups, selects dependency-ordered batches, executes deliverables sequentially (Phase 8a), runs validators at configured schedules, and checkpoints at TaskGroup completion. Stage transitions are PM-driven and gated by completion verification.

**Requirements:**
- [ ] **FR-8a.43**: When a work session begins, the PM initializes from the workflow's stage schema and determines the starting point — either the first stage for new projects, or the stage and TaskGroup from a resumed checkpoint for continuing projects.
- [ ] **FR-8a.44**: Within each stage, the PM creates TaskGroups as runtime planning units. Each TaskGroup represents a bounded scope of autonomous work and contains one or more batches of deliverables.
- [ ] **FR-8a.45**: Within each TaskGroup, the PM calls `select_ready_batch` to obtain the next set of dependency-ready deliverables and executes them sequentially — one deliverable at a time. Each deliverable passes through the full pipeline: skill loading → memory loading → planning → execution → validation → review.
- [ ] **FR-8a.46**: After each deliverable completes, the system runs validators at the `PER_DELIVERABLE` schedule. After each batch completes, the system runs validators at the `PER_BATCH` schedule. At TaskGroup completion, all `PER_TASKGROUP` validators run. At stage completion, all `PER_STAGE` validators run.
- [ ] **FR-8a.47**: Scheduled validators are mandatory pipeline steps. The PM cannot skip, defer, or override validator execution regardless of deliverable outcome.
- [ ] **FR-8a.48**: After each successful deliverable, the system checkpoints state. A system crash cannot cause a checkpointed deliverable to re-execute.
- [ ] **FR-8a.49**: When all deliverables in a TaskGroup are complete and all scheduled validators pass, the PM signals TaskGroup completion. The Director approves the TaskGroup (or escalates to CEO if required), a TaskGroup-scoped completion report is generated, and project-scope context is written.
- [ ] **FR-8a.50**: When a stage's completion criteria are met and `verify_stage_completion` passes, the PM calls `reconfigure_stage` to advance to the next stage. Stage transitions are forward-only and sequential — no skipping, no backtracking.
- [ ] **FR-8a.51**: The PM publishes a batch completion event to Redis Streams after each batch completes, including deliverable statuses and validator results.
- [ ] **FR-8a.52**: The execution loop continues autonomously — selecting batches, executing, validating, checkpointing — until all stages complete or work is escalated beyond the PM's authority.
- [ ] **FR-8a.53**: Between batches, the PM reasons about execution state: retry a failed deliverable, reorder remaining work, skip a blocked deliverable, or escalate. This inter-batch reasoning is observable in the event stream.
- [ ] **FR-8a.54**: The PM enforces per-project cost ceilings. When accumulated cost exceeds the project's configured cost ceiling, execution pauses and escalates to the Director.

---

### CAP-7: Failure Handling & Independent Progress

Failed deliverables do not block independent work. The PM retries within limits, skips blocked paths, reorders around failures, and escalates when budget is exhausted. Only the directly blocked path suspends; unblocked work continues.

**Requirements:**
- [ ] **FR-8a.55**: When a deliverable fails, the PM retries it up to the configured per-deliverable retry limit. Each retry is logged as an event with the attempt number and failure reason.
- [ ] **FR-8a.56**: When a deliverable exhausts its retry budget, the PM marks it as FAILED and evaluates the dependency graph to identify which remaining deliverables are blocked vs. independent.
- [ ] **FR-8a.57**: Failed deliverables do not block deliverables that have no dependency path through the failed one. The PM continues execution with all unblocked work.
- [ ] **FR-8a.58**: The PM reorders remaining work to maximize progress — executing independent deliverables before returning to blocked paths.
- [ ] **FR-8a.59**: When the PM cannot resolve a failure autonomously, it escalates to the Director via `escalate_to_director` with failure context, validator evidence, and attempted remediation history.
- [ ] **FR-8a.60**: When a CEO queue escalation is resolved, the resolution is applied back into the work queue and the suspended path resumes immediately without restarting the project or re-executing verified deliverables.
- [ ] **FR-8a.61**: Remediation re-executes only the failed deliverable and its direct dependents. Verified independent deliverables are never re-executed.

---

### CAP-8: Batch Failure Threshold & Director Suspension

When consecutive batch failures exceed a configured threshold, the Director suspends the project and surfaces findings to the CEO queue. No autonomous repair beyond the threshold.

**Requirements:**
- [ ] **FR-8a.62**: The system tracks consecutive batch failures per project. When the count exceeds the configured threshold, the PM escalates to the Director and the Director suspends the project.
- [ ] **FR-8a.63**: When the Director suspends a project, it diagnoses the failure pattern — reviewing validator evidence, escalation history, and execution state — and surfaces findings and recommended options to the CEO queue.
- [ ] **FR-8a.64**: The Director does not attempt autonomous repair beyond the batch failure threshold. The CEO must resolve the suspension via the CEO queue.
- [ ] **FR-8a.65**: When the CEO resolves the suspension, the Director resumes the project from the last checkpoint. Verified deliverables are not re-executed.
- [ ] **FR-8a.66**: A successful batch resets the consecutive failure counter to zero.

---

### CAP-9: Three-Layer Completion Reporting

At TaskGroup and Stage completion, the system generates completion reports with three verification layers backed by machine-generated evidence from validators. All validator tools must be operational for reporting to be valid.

**Requirements:**
- [ ] **FR-8a.67**: At TaskGroup completion, the system generates a completion report with three verification layers: functional correctness (do deliverables work as specified?), architectural conformance (do deliverables match the documented architecture?), and contract completion (were all scoped deliverables completed?).
- [ ] **FR-8a.68**: At Stage completion, the system generates a stage-scoped completion report with the same three layers, aggregating evidence from all TaskGroups within the stage.
- [ ] **FR-8a.69**: Each verification layer contains machine-generated evidence from validator results. Assertion without evidence is never sufficient — a layer with no validator results is marked as unverified.
- [ ] **FR-8a.70**: A TaskGroup cannot close while any deliverable is outstanding, any scheduled validator is failing, or any escalation is unresolved. These are hard gates regardless of workflow type.
- [ ] **FR-8a.71**: Completion reports include: per-deliverable evidence, cost and token usage by agent tier, wall-clock duration, and a decision log distinguishing system-autonomous decisions from user-resolved decisions.
- [ ] **FR-8a.72**: The INTEGRATE stage's CEO approval gate requires all three verification layers to pass before the stage (and project, if final) can be marked complete.

---

### CAP-10: Project Lifecycle Tracking

Projects are first-order persistent entities. All deliverables, queue items, stage executions, and configurations relate to a project. The project is the anchor for the entire execution lifecycle.

**Requirements:**
- [ ] **FR-8a.73**: The system maintains projects as first-order persistent entities. Each project record tracks: unique identifier, name, workflow type, brief content, current status, current stage, active TaskGroup, accumulated cost, and timestamps (created, updated, started, completed).
- [ ] **FR-8a.74**: Project status values include: SHAPING (Director is creating the Brief), ACTIVE (PM is executing), PAUSED (user-initiated suspension at next checkpoint), SUSPENDED (Director-initiated due to batch failure threshold), COMPLETED (all stages passed), ABORTED (terminated with reason recorded).
- [ ] **FR-8a.75**: All deliverables, stage executions, TaskGroup executions, Director queue items, CEO queue items, and project configs reference their parent project.
- [ ] **FR-8a.76**: When a project's status changes, the system publishes a status change event to Redis Streams and updates the project record's timestamp.

---

### CAP-11: Execution & System Observability

The CEO can query project status, workflow execution, deliverable details, queue state, and system health. This is the monitoring surface for tracking autonomous execution.

**Requirements:**
- [ ] **FR-8a.77**: When the CEO queries a project's execution status, the system returns the current stage, active TaskGroup, deliverable progress counts (by status), pending escalation count, and accumulated cost.
- [ ] **FR-8a.78**: When the CEO queries deliverables, the system returns deliverable records with status filtering (by status, project, stage, TaskGroup) and includes dependency information.
- [ ] **FR-8a.79**: When the CEO queries a specific deliverable, the system returns the full record including dependencies, validator results, execution history, artifact references, and retry count.
- [ ] **FR-8a.80**: The Director queue state is queryable via API (pending, in-progress, and resolved items with filtering). The CEO queue state is queryable via existing API routes.
- [ ] **FR-8a.81**: Every queued work item — pending, in-progress, or blocked — is visible to the CEO at all times. No work executes invisibly.

---

### CAP-12: Context Recreation & TaskGroup Resume

When context budget is exceeded during execution, the system saves critical state at the TaskGroup boundary, creates a fresh session, and resumes without re-executing verified work. The checkpoint/resume boundary is the TaskGroup.

**Requirements:**
- [ ] **FR-8a.82**: When context budget exceeds the configured threshold during execution, the system saves critical state (deliverable statuses, PM-tier state, project config, stage progress, loaded skill names) at the current TaskGroup boundary.
- [ ] **FR-8a.83**: The system creates a fresh execution context seeded with the critical state and resumes execution from the next unfinished TaskGroup. No lossy summarization occurs — context is reconstructed from durable stores (state, skills, instruction fragments).
- [ ] **FR-8a.84**: Verified deliverables within completed TaskGroups are never re-executed after context recreation. Mid-work batches within an interrupted TaskGroup are rediscovered during resume via `select_ready_batch`.
- [ ] **FR-8a.85**: Context recreation publishes observable events (at initiation and completion) including the old session ID, new session ID, seeded keys, and remaining stages.

---

### CAP-13: Artifact Storage

Deliverable outputs and completion reports are stored as persistent, retrievable artifacts associated with their execution context. Artifacts support arbitrary file types.

**Requirements:**
- [ ] **FR-8a.86**: Deliverable outputs (code files, test results, review reports, build artifacts) are stored as persistent artifacts associated with the deliverable record.
- [ ] **FR-8a.87**: Completion reports are stored as persistent artifacts associated with the TaskGroup or Stage execution record.
- [ ] **FR-8a.88**: Artifacts support storage and retrieval of arbitrary file types produced during execution.
- [ ] **FR-8a.89**: When the CEO queries a deliverable or execution record, the response includes artifact references (identifiers and metadata) for retrieval.

---

### CAP-14: Workflow-Defined Edit Operations

Each workflow defines permitted edit operations. Edits are a continuous, any-time capability — not limited to post-completion. The CEO issues edits (single or batch) through the Director at any time, regardless of project state. The Director propagates edits down to the project, where they queue as new TaskGroups alongside any in-progress work. The PM handles newly queued work arriving mid-execution. Accumulated project context carries forward into edit work.

**Requirements:**
- [ ] **FR-8a.90**: Projects are living entities — queryable, observable, and modifiable through the Director at any time, in any project state (SHAPING, ACTIVE, PAUSED, SUSPENDED, COMPLETED).
- [ ] **FR-8a.91**: Each workflow defines its permitted edit operations in the workflow manifest. For auto-code: add feature, remove feature, fix bug, refactor. For other workflows: operations appropriate to the domain.
- [ ] **FR-8a.92**: When the CEO requests an edit through the Director, the Director creates new TaskGroups within the existing project. Edits issued during active execution queue alongside in-progress work. Edits issued during paused or suspended state queue for when execution resumes.
- [ ] **FR-8a.92a**: When the CEO issues a batch edit (multiple edit operations at once), the Director processes them as a single coordinated action, creating appropriately ordered TaskGroups that respect inter-edit dependencies.
- [ ] **FR-8a.92b**: The PM handles new TaskGroups arriving mid-execution. Newly queued edit work is incorporated into the PM's batch selection via `select_ready_batch` without interrupting the current deliverable.
- [ ] **FR-8a.93**: Edit operations follow the same execution loop (Stage → TaskGroup → Batch → Deliverable) with the same validation, checkpointing, and completion reporting as initial project execution. The project's accumulated context (conventions, architectural decisions, resolved escalations) carries forward into edit work.
---

### CAP-15: Work Layer Pause & Start Lifecycle

Every work layer — individual project, all projects, and the Director — supports explicit Pause and Start operations. Pause saves state, logs the action, and stops work cleanly. Start loads resources, rebuilds context, and resumes work from where it left off. This is a first-class lifecycle, not an edge case.

**Requirements:**

**Project-level:**
- [ ] **FR-8a.94**: When the CEO pauses a project, the PM completes the current deliverable (if in progress), saves all critical state at the next checkpoint boundary, logs the pause reason, and stops execution. No work is left in an inconsistent state.
- [ ] **FR-8a.95**: When the CEO starts a paused project, the system loads the project's persisted state, rebuilds the PM's execution context (skills, instruction fragments, stage configuration), and resumes the batch loop from the checkpointed position. Verified deliverables are never re-executed.
- [ ] **FR-8a.96**: When the CEO aborts a project, the system terminates execution, preserves all completed work and events, records the abort reason, and transitions the project to ABORTED status.

**All-projects (system-wide):**
- [ ] **FR-8a.97**: When the CEO pauses all projects, the system pauses every active project individually using the same project-level pause mechanism. Each project reaches its own safe checkpoint independently.
- [ ] **FR-8a.98**: When the CEO starts all paused projects, the system starts each project individually using the same project-level start mechanism. Projects resume independently and do not block each other.

**Director work layer:**
- [ ] **FR-8a.99**: When the CEO pauses the Director, the Director stops processing the backlog queue, stops accepting new project creation requests, and logs the pause. Active project PMs continue executing until they reach their next checkpoint, then pause.
- [ ] **FR-8a.100**: When the CEO starts the Director, the Director rebuilds its context, loads pending queue state, and resumes backlog processing. Projects paused by the Director pause are started in priority order.
- [ ] **FR-8a.101**: Pause and start at any layer publish lifecycle events with the layer scope (project, all-projects, director), the actor (CEO), the timestamp, and the reason.

---

## Non-Functional Requirements

- [ ] **NFR-8a.01**: Management tool single-record database operations complete within 200ms under normal load. `select_ready_batch` with dependency graph evaluation completes within 500ms for projects with up to 100 deliverables.
- [ ] **NFR-8a.02**: Batch completion events publish to Redis Streams within 2 seconds of state change. Project status change events publish within 1 second.
- [ ] **NFR-8a.03**: Project checkpoint (state persistence at TaskGroup boundary) completes atomically. A partial checkpoint is never visible to consumers — either all state is persisted or none is.
- [ ] **NFR-8a.04**: Context recreation (save critical state + create fresh session + resume) completes within 30 seconds. The pipeline resumes from the correct TaskGroup without manual intervention.
- [ ] **NFR-8a.05**: All management tool failures produce structured error responses with error codes and human-readable descriptions. No tool returns raw exceptions, placeholder strings, or empty results on failure.
- [ ] **NFR-8a.06**: Brief validation and resource checks complete before any work session is enqueued. The system never begins autonomous execution with known missing or invalid resources.
- [ ] **NFR-8a.07**: The batch failure threshold is configurable per project via project configuration (default: 3). The per-deliverable retry limit is configurable (default: 2).
- [ ] **NFR-8a.08**: Tool access is role-scoped per the supervision hierarchy. Director tools are not accessible to PM or Worker agents. PM tools are not accessible to Worker agents. Scope violations are logged as security events.
- [ ] **NFR-8a.09**: Adding the project entity is non-destructive — existing data in all related entities (project configs, workflows, deliverables, queue items) is preserved and relationships are established without data loss.

---

## Rabbit Holes

*Note: Rabbit holes intentionally reference implementation details — they exist to flag technical risks for the spec and build phases.*

### RH-1: ToolContext Database Session Injection
Management tools are currently plain functions with no database access path. The only tool using ToolContext for state writes is `reconfigure_stage` (which writes to ADK session state, not to the database). Wiring 14+ tools to the database requires a consistent pattern — likely injecting a session factory via ToolContext state from the worker context. Risk: inconsistent patterns per tool, unclear transaction boundaries (does each tool call get its own transaction?), error handling divergence. **Navigate by**: defining the pattern once for a reference tool, then applying uniformly.

### RH-2: ADK Session State vs Database State Duality
Some state lives in ADK session state (e.g., `pm:retry_count`, `pm:current_stage`, `pm:stage_status`). Other state lives in database tables (deliverable status, queue items, project status). The PM reads from both stores. If the boundary is unclear, the PM will read stale data from one store while the other has been updated. **Navigate by**: establishing a clear principle — ADK session state for ephemeral execution context (what the PM is doing right now), database for durable entity state (what has been completed). The checkpoint operation syncs them.

### RH-3: Deliverable Dependency Topological Sort
`select_ready_batch` needs correct topological sort with cycle detection. Cycles in the dependency graph would deadlock the PM loop (nothing is ever "ready"). The dependency graph may also need soft dependencies (preferred ordering) vs. hard dependencies (must complete first). **Navigate by**: implementing cycle detection at dependency creation time (FR-8a.18 rejects circular dependencies) so the sort is guaranteed acyclic at query time.

### RH-4: Director Tool Access Across Session Types
The Director is the root_agent in both chat sessions and work sessions. For project creation (CAP-1), the Director needs tools (`create_project`, `validate_brief`) that run in chat sessions. For backlog orchestration (CAP-5), the Director runs in work sessions. The same agent definition serves both contexts but with different tool requirements. **Navigate by**: tool authorization scoped by session type (chat vs. work) or by providing all Director tools in both contexts and relying on instruction-based behavior.

### RH-5: TaskGroup Granularity Discovery
The PM must determine how to partition deliverables into TaskGroups. This requires estimating work size — an LLM judgment call that could be wrong. Over-splitting creates checkpoint overhead and Director approval bottlenecks. Under-splitting defeats the checkpoint benefit and risks context budget exhaustion. **Navigate by**: starting with a simple heuristic (batches-per-TaskGroup count or deliverable count), allowing PM discretion, and tuning based on observed context recreation frequency.

### RH-6: Context Recreation Mid-TaskGroup
The context budget monitor fires based on token usage, which can happen mid-TaskGroup (between deliverables within a TaskGroup). The shaping decision says "TaskGroup boundary" but the trigger may fire at an arbitrary point. **Navigate by**: when context budget is hit mid-TaskGroup, completing the current deliverable (if in progress) then checkpointing at that deliverable boundary. The "TaskGroup boundary" is the logical resume point — the system resumes the current TaskGroup, rediscovering mid-work batches via `select_ready_batch`.

### RH-7: Projects Table Migration & Foreign Key Restructure
Introducing a `projects` table requires restructuring foreign keys across multiple existing tables. `project_configs`, `workflows`, `deliverables`, `stage_executions`, `taskgroup_executions`, `director_queue`, and `ceo_queue` all reference projects — some by name, some by ID, some not at all. **Navigate by**: making the migration additive (new table + new FK columns) before migrating references, rather than attempting a single destructive migration.

### RH-8: Workflow Edit Operations Schema Design
Adding `edit_operations` to WORKFLOW.yaml extends the manifest schema. The schema must support progressive disclosure — existing manifests without this field remain valid. The definition of an edit operation needs design: is it a name + description, or does it include stage routing (which stages run for an edit vs. a new project)? **Navigate by**: starting minimal (name + description + optional starting_stage) and expanding based on actual usage in the auto-code workflow.

---

## No-Gos

- **Parallel batch execution** — Phase 8b. All execution in Phase 8a is sequential (one deliverable at a time within a batch, one batch at a time).
- **Git worktree isolation** — Phase 8b. No filesystem concurrency or branch-per-deliverable isolation.
- **Concurrency limits configuration** — Phase 8b. Phase 8a hardcodes single-deliverable sequential execution.
- **Memory service integration** — Phase 9. Memory writes at checkpoints use the degraded in-memory mode from Phase 5b. Real MemoryService with search, summarization, and cross-session retrieval is Phase 9.
- **Real-time SSE streaming to clients** — Phase 10. Events publish to Redis Streams in Phase 8a; SSE endpoint consumption is Phase 10.
- **Dashboard UI** — Phase 10. All observability is via API routes and CLI only.
- **Notification channels** — Phase 10. CEO queue notifications (webhook, email, Slack, Telegram, SMS) are Phase 10.
- **Multi-project concurrent orchestration** — Phase 8a executes single projects. The Director queue handles items from multiple projects, but true concurrent PM orchestration (multiple PMs running simultaneously) is beyond 8a scope.
- **Human-in-the-loop intervention API** — Phase 8b. Proactive pause/resume at batch boundaries via a dedicated intervention endpoint is deferred.
- **Cross-project dependency orchestration** — Out of scope per PRD §8. Projects are independent.
- **Workflow marketplace** — Out of scope per PRD §8.

---

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-8a.01–10b | PR-1 (Brief), PR-8 (Decomposition), PR-13 (Director) | Project & Brief, Execution, Agent Hierarchy |
| FR-8a.10–13 | PR-8 (Resource validation) | Execution & Work Queues |
| FR-8a.14–32 | PR-10 (PM execution loop), PR-14 (PM ownership), PR-18 (Director Queue) | Execution & Work Queues, Agent Hierarchy |
| FR-8a.33–37 | PR-14 (PM ownership), PR-18 (Director Queue) | Agent Hierarchy, CEO & Director Queue |
| FR-8a.38–42 | PR-14 (Director), PR-18 (Director Queue) | Agent Hierarchy, CEO & Director Queue |
| FR-8a.43–54 | PR-10 (PM execution loop), PR-11 (Validators), PR-14 (PM ownership), PR-15 (Bounded authority) | Execution & Work Queues, Agent Hierarchy |
| FR-8a.55–61 | PR-12 (Failure handling), PR-19 (CEO queue decisions), PR-20 (Resume on resolution), PR-25 (Remediation) | Execution, CEO Queue, Completion |
| FR-8a.62–66 | PR-16 (Batch failure threshold) | Agent Hierarchy |
| FR-8a.67–72 | PR-22 (Three-layer verification), PR-23 (TaskGroup close conditions), PR-24 (Report contents) | Completion Reporting |
| FR-8a.73–76 | PR-2 (Project tracking) | Project & Brief |
| FR-8a.77–81 | PR-9 (Observable work queues — partial: visibility covered; item promote/demote/cancel deferred to Phase 10), PR-34 (Event stream) | Observability, Execution |
| FR-8a.82–85 | PR-15a (Context recreation) | Agent Hierarchy |
| FR-8a.86–89 | PR-24 (Report contents, per-deliverable evidence) | Completion Reporting |
| FR-8a.90–93 | PR-4 (Workflow plugins — edit operations) | Workflow Management |
| FR-8a.94–101 | PR-3 (Pause/resume/abort — all work layers) | Project & Brief |
| NFR-8a.01–02 | NFR-1 (Response time), NFR-2 (Stage completion time) | Performance |
| NFR-8a.03–04 | NFR-3 (Crash recovery) | Reliability |
| NFR-8a.05 | NFR-4 (Input validation) | Security |
| NFR-8a.06 | PR-8 (Resource validation before execution) | Execution |
| NFR-8a.07 | PR-15 (Configurable limits) | Agent Hierarchy |
| NFR-8a.08 | NFR-4c (State key authorization) | Security |
| NFR-8a.09 | NFR-3 (Crash recovery — data preservation) | Reliability |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | Director creates projects through conversation supporting seven entry modes (new, new-with-materials, extend, edit, re-run, direct execution, workstream) — validates brief, checks resources, creates project entity, delegates to PM via work session | CAP-1: FR-8a.01–10b, CAP-3: FR-8a.28–31 |
| 2 | Brief validated against workflow's `brief_template` before acceptance; pre-execution resource validation checks credentials, services, and knowledge availability | CAP-2: FR-8a.10–13 |
| 3 | Projects are first-order DB entities tracking workflow type, status, stage, deliverables, escalations, and cost | CAP-10: FR-8a.73–76 |
| 4 | Management tools (all PM, Director, and shared tools) write to and read from the database — no placeholder strings remain | CAP-3: FR-8a.14–27 |
| 5 | `escalate_to_director` writes real `DirectorQueueItem` rows; `escalate_to_ceo` writes real `CeoQueueItem` rows; Director queue gateway routes operational | CAP-4: FR-8a.33–37, CAP-3: FR-8a.20–21 |
| 6 | Director execution loop processes backlog: reads Director queue, triages items within authority, forwards unresolvable items to CEO queue | CAP-5: FR-8a.38–42 |
| 7 | PM drives sequential execution through Stage → TaskGroup → Batch → Deliverable hierarchy: creates TaskGroups, selects dependency-ordered batches, executes one batch at a time, stage transitions gated by `verify_stage_completion` | CAP-6: FR-8a.43–54 |
| 8 | Loop continues autonomously until all stages complete or work escalated | CAP-6: FR-8a.52 |
| 9 | Failed deliverables don't block independent work — PM skips/reorders around failures | CAP-7: FR-8a.55–61 |
| 10 | Consecutive batch failures trigger Director suspension of project (batch failure threshold) | CAP-8: FR-8a.62–66 |
| 11 | Three-layer completion report generated at TaskGroup and Stage completion with machine evidence from validators | CAP-9: FR-8a.67–72 |
| 12 | Context recreation at TaskGroup boundaries — save critical state, create fresh session, resume without re-executing verified work | CAP-12: FR-8a.82–85 |
| 13 | Deliverable outputs and completion reports stored as persistent, retrievable artifacts | CAP-13: FR-8a.86–89 |
| 14 | Projects support workflow-defined edit operations at any time regardless of project state — single and batch edits queue as new TaskGroups | CAP-14: FR-8a.90–93, FR-8a.92a–92b |
| 15 | Deliverable and workflow status query routes operational; Director queue, PM queue, and system observability accessible via API | CAP-11: FR-8a.77–81 |
| 16 | Every work layer (project, all-projects, Director) supports explicit Pause (save state, log, stop) and Start (load resources, rebuild context, resume) lifecycle operations | CAP-15: FR-8a.94–101 |
