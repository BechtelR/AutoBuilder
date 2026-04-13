# Phase 8a Spec: Autonomous Execution Engine
*Generated: 2026-04-12*

## Overview

Phase 8a connects all prior infrastructure — workflow composition (Phase 7), supervision hierarchy (Phase 5b), toolset (Phase 4), and skills (Phase 6) — into a working autonomous execution loop. A user expresses project intent to the Director via chat, the Director validates the brief, creates a project, and delegates to a PM that drives sequential execution through Stage → TaskGroup → Batch → Deliverable. Management tools write to real database tables. Escalations flow PM → Director → CEO. Context recreation at TaskGroup boundaries enables long-running projects. Edit operations and pause/resume lifecycle make projects living entities.

This phase proves the core thesis: specification to verified deliverables under hierarchical supervision with minimal human intervention. All execution is sequential (one deliverable at a time) — parallel execution is Phase 8b.

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 7: Workflow Composition | MET | WorkflowRegistry, WorkflowManifest, stage schema, validators, PipelineContext all operational. 897 tests pass. |
| Phase 5b: Supervision & Integration | MET | Director/PM hierarchy, supervision callbacks, CEO queue, formation, context recreation (degraded mode). |
| Phase 4: Tool System | MET | GlobalToolset with 42 FunctionTools, role-based vending, management tool stubs in place. |
| Phase 6: Skill System | MET | SkillLibrary, parser, matchers, SkillLoaderAgent operational. |
| Phase 3: Data Layer | MET | SQLAlchemy models, Alembic migrations, deliverables/workflows/stage_executions/taskgroup_executions/director_queue/ceo_queue/project_configs tables. |

## Design Decisions

### DD-1: ToolContext DB Session + ARQ Pool Injection
Management tools access the database via an async session factory and the ARQ pool injected into session state (`_db_session_factory`, `_arq_pool`) at session creation in `tasks.py`. Each tool call gets its own transaction. See [spec-research.md §RN-1](spec-research.md).

### DD-2: State Boundary — ADK Session vs Database
ADK session state holds ephemeral execution context (`pm:*` keys). Database tables hold durable entity state (deliverable status, queue items, project records). Checkpointing syncs critical session state to database. See [spec-research.md §RN-3](spec-research.md).

### DD-3: Director Tools in All Session Types
All Director tools are available in both chat and work sessions via GlobalToolset. Behavior is instruction-guided, not session-type-gated. See [spec-research.md §RN-4](spec-research.md).

### DD-4: Artifact Storage — Filesystem + DB Metadata
Per execution.md and the architecture's artifact storage design: actual content stored on filesystem organized by project/entity. DB `artifacts` table stores metadata (path, content_type, size, entity association via polymorphic `entity_type` + `entity_id`). ADK `save_artifact` is session-scoped internal; a post-pipeline step copies session artifacts to the persistent filesystem store. See [spec-research.md §RN-5](spec-research.md).

### DD-5: Pause as State Transition
Pause is a project status transition (ACTIVE → PAUSED) observed by the PM between deliverables. PM checkpoints and exits. Resume enqueues a new work session from checkpoint. See [spec-research.md §RN-8](spec-research.md).

### DD-6: Edit Operations as New TaskGroups
Edit requests create new TaskGroups within the existing project, not new projects. Same execution loop, same validation. Accumulated context carries forward. See [spec-research.md §RN-7](spec-research.md).

### DD-7: Two-Tier Checkpointing (Not FunctionTools)
Per tools.md: `checkpoint_project` and `run_regression_tests` are **not FunctionTools** — they must not be skippable by LLM judgment. Tier 1: `after_agent_callback` on DeliverablePipeline (per-deliverable, automatic). Tier 2: PM-triggered at TaskGroup boundary via callback. `RegressionTestAgent` is a CustomAgent wired into the pipeline after each batch.

## Deliverables

### P8a.D1: Projects Table, Artifacts Table & Enum Updates
**Files:** `app/db/models.py`, `app/models/enums.py`, `app/db/migrations/NNN_add_projects_and_artifacts.py`
**Depends on:** —
**Description:** Add `Project` as a first-order DB entity. Add `artifacts` table with polymorphic entity association (per execution.md). Add `ProjectStatus` enum. Extend `DeliverableStatus` with PLANNED and SKIPPED values. Establish foreign key relationships from existing tables to projects. Migration is additive.
**BOM Components:**
- [ ] `X20` — `projects` table (first-order entity)
**Requirements:**
- [ ] `Project` model: id (UUID), name, workflow_type, brief (text), status (ProjectStatus), current_stage, current_taskgroup_id (nullable FK), accumulated_cost (Numeric), created_at, updated_at, started_at, completed_at, error_message
- [ ] `ProjectStatus` enum added to `app/models/enums.py`: SHAPING, ACTIVE, PAUSED, SUSPENDED, COMPLETED, ABORTED
- [ ] `DeliverableStatus` enum extended with PLANNED and SKIPPED (existing values PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED preserved)
- [ ] `Artifact` model: id (UUID), entity_type (str), entity_id (UUID), path (str), content_type (str), size_bytes (int), created_at. Polymorphic via entity_type + entity_id (deliverable, taskgroup_execution, stage_execution)
- [ ] FK columns added: deliverables.project_id, stage_executions.project_id, taskgroup_executions.project_id. Existing `source_project_id` columns in director_queue and ceo_queue converted to FK references to projects table. project_configs gains project_id FK
- [ ] `deliverables` table gains `retry_count` int (default 0), `execution_order` int
- [ ] `taskgroup_executions` gains `checkpoint_data` JSONB (nullable)
- [ ] Migration is sequential numbered (NNN format), additive, non-destructive
- [ ] All models pass pyright strict
**Validation:**
- `uv run alembic upgrade head`
- `uv run pyright app/db/models.py app/models/enums.py`

---

### P8a.D2: Management Tool DB & ARQ Infrastructure
**Files:** `app/tools/management.py`, `app/workers/tasks.py`
**Depends on:** P8a.D1
**Description:** Establish the DB session + ARQ pool injection pattern for management tools. Inject `_db_session_factory` and `_arq_pool` into session state at session creation time in `tasks.py` (both `run_work_session` and `run_director_turn`). Convert all management tool stubs from sync to async and add `tool_context: ToolContext` parameter. Create `_get_db_session` and `_get_arq_pool` helpers. Implement `escalate_to_ceo` as the reference DB-writing tool. Add role-scoped tool access violation logging (NFR-8a.08).
**BOM Components:**
- [ ] `X12` — Management tool DB wiring (replace placeholder strings with real persistence)
**Requirements:**
- [ ] `_db_session_factory` and `_arq_pool` keys injected into session state at session creation in `run_work_session()` and `run_director_turn()` in `app/workers/tasks.py`
- [ ] All management tool functions converted from `def` to `async def` with `tool_context: ToolContext` parameter added
- [ ] `_get_db_session(tool_context)` async context manager yields session from factory; raises structured error if unavailable
- [ ] `_get_arq_pool(tool_context)` returns ARQ pool from state; raises structured error if unavailable
- [ ] `escalate_to_ceo` writes a real `CeoQueueItem` record to the database (reference implementation)
- [ ] All tool stubs gain consistent error response: `{"error": {"code": "...", "message": "..."}}`
- [ ] Tool access scope violations (e.g., PM invoking Director-only tool) logged as security events via EventPublisher (NFR-8a.08)
- [ ] Pattern documented in module docstring
**Validation:**
- `uv run pytest tests/tools/test_management.py -v`
- `uv run pyright app/tools/management.py`

---

### P8a.D3: PM Management Tools (Real DB)
**Files:** `app/tools/management.py`
**Depends on:** P8a.D1, P8a.D2
**Description:** Implement PM FunctionTools with real database persistence. `select_ready_batch` performs topological sort (Kahn's algorithm). `update_deliverable` writes status changes. `query_deliverables` queries with filters. `reorder_deliverables` updates execution order. `manage_dependencies` manages edges with cycle detection. `escalate_to_director` writes real DirectorQueueItem rows. Note: `checkpoint_project` is NOT a FunctionTool (see DD-7) — it is implemented as a callback in D9.
**BOM Components:**
- [ ] `X02` — Deliverable status tracking (lifecycle management via management tools)
- [ ] `X13` — `escalate_to_director` real implementation (write to `director_queue` table)
**Requirements:**
- [ ] `select_ready_batch` queries deliverables by project_id, filters by status (PENDING + retryable FAILED), builds dependency graph, returns frontier set via topological sort; completes within 500ms for 100 deliverables
- [ ] `update_deliverable` writes status + optional notes + timestamp; validates status transitions (PENDING→IN_PROGRESS→COMPLETED|FAILED|SKIPPED); rejects invalid transitions with error
- [ ] `query_deliverables` returns records filtered by project_id, status, stage, taskgroup; includes dependency info
- [ ] `reorder_deliverables` updates execution_order column within a TaskGroup
- [ ] `manage_dependencies` adds/removes dependency edges; rejects circular dependencies with specific error message identifying the cycle
- [ ] `escalate_to_director` creates DirectorQueueItem with type, priority, context, source_project_id, source_agent; item immediately visible via DB query
- [ ] All tools return structured JSON strings (not plain text placeholders)
- [ ] All DB writes within a single tool call execute in one transaction; on failure, transaction rolls back and no partial state is visible (NFR-8a.03)
**Validation:**
- `uv run pytest tests/tools/test_management.py -v`
- `uv run pyright app/tools/management.py`

---

### P8a.D4: Director Management Tools (Real DB)
**Files:** `app/tools/management.py`, `app/tools/_toolset.py`
**Depends on:** P8a.D1, P8a.D2
**Description:** Implement Director management tools with real database persistence. These are **new functions** added to management.py (not modifications of existing stubs): `create_project`, `validate_brief`, `check_resources`, `delegate_to_pm`. Plus convert existing stubs: `list_projects`, `query_project_status`, `override_pm`, `query_dependency_graph`. Register new tools in `_toolset.py`. Note: `escalate_to_ceo` is already implemented in D2 as the reference tool.
**BOM Components:**
- [ ] `X21` — Director `create_project` tool
- [ ] `X22` — Director `validate_brief` tool
- [ ] `X23` — Director `check_resources` tool
- [ ] `X24` — Director `delegate_to_pm` tool
- [ ] `X18` — Brief validation against workflow `brief_template`
- [ ] `X19` — Pre-execution resource validation
**Requirements:**
- [ ] `create_project` creates Project record with workflow_type, brief, entry_mode, status=SHAPING; returns project_id
- [ ] `validate_brief` resolves workflow via WorkflowRegistry, validates brief fields against `brief_template`; returns structured pass/fail with per-field details
- [ ] `check_resources` reads workflow manifest `resources` field, validates: credentials (env var present and non-empty), services (reachable via health check), knowledge (file/dir exists); returns structured result per resource
- [ ] `delegate_to_pm` enqueues ARQ `run_work_session` job via `_get_arq_pool(tool_context)`; transitions project status SHAPING→ACTIVE
- [ ] `list_projects` returns project records with optional status filter, including workflow_type, stage, cost summary
- [ ] `query_project_status` returns comprehensive status: deliverable counts by status, current stage, active TaskGroup, pending escalations, accumulated cost, duration
- [ ] `override_pm` applies pause/resume/reorder/correct action; records override as audit event
- [ ] `query_dependency_graph` returns full dependency graph with node statuses and cycle detection
- [ ] When workflow resolution is ambiguous, `validate_brief` returns available matches for Director to present to user
- [ ] When no workflow matches, `validate_brief` returns error listing available workflow types
- [ ] New tools registered in `GlobalToolset` via `_toolset.py` with Director role scope
**Validation:**
- `uv run pytest tests/tools/test_management.py -v`
- `uv run pyright app/tools/management.py app/tools/_toolset.py`

---

### P8a.D5: Director Queue Gateway Routes
**Files:** `app/gateway/routes/director_queue.py`, `app/gateway/models/director_queue.py`
**Depends on:** P8a.D1
**Description:** Add gateway routes for querying and resolving Director queue items. Mirrors existing CEO queue route pattern (`app/gateway/routes/ceo_queue.py`).
**BOM Components:**
- [ ] `G28` — `GET /director/queue` (list Director queue items)
- [ ] `G29` — `PATCH /director/queue/{id}` (resolve/forward Director queue item)
**Requirements:**
- [ ] `GET /director/queue` returns DirectorQueueItem records filtered by type, priority, status; sorted by priority desc then created_at asc
- [ ] `PATCH /director/queue/{id}` supports RESOLVE (with resolution text) and FORWARD_TO_CEO (creates CeoQueueItem with original context + rationale, marks original as FORWARDED_TO_CEO)
- [ ] Response models use Pydantic; no ADK types exposed
- [ ] Routes registered in gateway app factory
**Validation:**
- `uv run pytest tests/gateway/ -v -k director_queue`
- `uv run pyright app/gateway/routes/director_queue.py`

---

### P8a.D6: Project & Deliverable Gateway Routes
**Files:** `app/gateway/routes/projects.py`, `app/gateway/routes/deliverables.py`, `app/gateway/models/projects.py`, `app/gateway/models/deliverables.py`
**Depends on:** P8a.D1
**Description:** Add gateway routes for project lifecycle and deliverable queries. Enhance existing workflow routes to reference project entities.
**BOM Components:**
- [ ] `G02` — `POST /specs` (brief submission)
- [ ] `G03` — `POST /workflows/{id}/run`
- [ ] `G04` — `GET /workflows/{id}/status`
- [ ] `G07` — `GET /deliverables`
- [ ] `G08` — `GET /deliverables/{id}`
**Requirements:**
- [ ] `POST /projects` accepts brief content and optional workflow_type; enqueues Director turn for project creation; returns 202
- [ ] `GET /projects/{id}` returns project record with status, stage, deliverable counts, cost, timestamps
- [ ] `GET /deliverables` returns records filtered by project_id, status, stage; includes dependency info
- [ ] `GET /deliverables/{id}` returns full record including dependencies, validator results, artifact references (from `artifacts` table), retry count
- [ ] `POST /workflows/{id}/run` and `GET /workflows/{id}/status` enhanced to reference project entities
- [ ] All response models use Pydantic with proper typing
**Validation:**
- `uv run pytest tests/gateway/ -v -k "project or deliverable"`
- `uv run pyright app/gateway/routes/projects.py app/gateway/routes/deliverables.py`

---

### P8a.D7: Pause/Resume Gateway Routes
**Files:** `app/gateway/routes/projects.py`, `app/gateway/routes/director_lifecycle.py`
**Depends on:** P8a.D1, P8a.D6
**Description:** Add gateway routes for the three-layer pause/resume lifecycle.
**BOM Components:**
- [ ] `G30` — `POST /projects/{id}/pause`
- [ ] `G31` — `POST /projects/{id}/resume`
- [ ] `G32` — `POST /director/pause`
- [ ] `G33` — `POST /director/resume`
**Requirements:**
- [ ] `POST /projects/{id}/pause` accepts reason; validates project is ACTIVE; enqueues pause action; returns 202
- [ ] `POST /projects/{id}/resume` validates project is PAUSED; enqueues resume action; returns 202
- [ ] `POST /director/pause` accepts reason; cascades pause to all active projects; returns 202
- [ ] `POST /director/resume` resumes Director backlog processing; resumes paused projects in priority order; returns 202
- [ ] All routes return 409 on invalid state transitions
**Validation:**
- `uv run pytest tests/gateway/ -v -k "pause or resume"`
- `uv run pyright app/gateway/routes/`

---

### P8a.D8: Director Execution Loop
**Files:** `app/workers/tasks.py`, `app/workers/adk.py`
**Depends on:** P8a.D3, P8a.D4
**Description:** Enhance `run_director_turn` to support the seven entry modes. Enhance `process_director_queue` to process backlog: read pending items, resolve within authority, forward unresolvable to CEO queue.
**BOM Components:**
- [ ] `X01` — Director-mediated project entry (seven entry modes)
- [ ] `X03` — Director execution loop (backlog processing, PM delegation, escalation forwarding)
**Requirements:**
- [ ] Director chat sessions support all seven entry modes via natural conversation — Director determines mode from user intent and uses appropriate tools
- [ ] Director validates brief via `validate_brief` before project creation
- [ ] Director checks resources via `check_resources` before PM delegation
- [ ] Director creates project via `create_project` and delegates via `delegate_to_pm`
- [ ] For extend/edit/workstream modes, Director identifies existing project and creates scoped work within it
- [ ] `process_director_queue` reads pending DirectorQueueItems prioritized by escalation priority (CRITICAL > HIGH > NORMAL > LOW)
- [ ] Director resolves items within its authority: status reports (auto-acknowledge), resource requests with known resolution (apply fix), pattern alerts with prior precedent (apply same resolution)
- [ ] Director forwards items beyond authority to CEO queue with assessment and recommended resolution options
- [ ] When 2+ projects escalate the same failure type within a configurable window (default: 1 hour), Director surfaces a cross-project pattern alert to CEO queue with aggregated evidence
- [ ] When backlog is empty, loop yields until new items arrive via existing cron mechanism
**Validation:**
- `uv run pytest tests/workers/ -v -k "director"`
- `uv run pyright app/workers/tasks.py`

---

### P8a.D9: PM Autonomous Batch Loop & Pipeline Infrastructure
**Files:** `app/workers/tasks.py`, `app/workers/adk.py`, `app/agents/supervision.py`
**Depends on:** P8a.D3, P8a.D8
**Description:** Implement the PM's autonomous Stage → TaskGroup → Batch → Deliverable execution loop within `run_work_session`. Two-tier checkpointing per DD-7: Tier 1 `after_agent_callback` on DeliverablePipeline persists per-deliverable state automatically; Tier 2 PM-triggered at TaskGroup boundary. `RegressionTestAgent` (CustomAgent) wired into pipeline after each batch. Stage transitions gated by `verify_stage_completion`.
**BOM Components:**
- [ ] `X04` — PM batch loop (autonomous, stage-driven, sequential)
- [ ] `A63` — PM outer loop (sequential batch management)
- [ ] `X25` — PM checkpoint_project (after_agent_callback, NOT a FunctionTool)
**Requirements:**
- [ ] PM initializes from workflow stage schema; determines starting point (first stage for new, checkpoint for resume)
- [ ] PM creates TaskGroups as bounded planning units within each stage
- [ ] Within each TaskGroup, PM calls `select_ready_batch` and executes deliverables sequentially (one at a time)
- [ ] Each deliverable passes through full pipeline: skill loading → planning → execution → validation → review
- [ ] **Tier 1 checkpoint**: `after_agent_callback` on DeliverablePipeline fires after each deliverable, persists deliverable status and result to DB via `CallbackContext`. A checkpointed deliverable never re-executes after crash (FR-8a.48)
- [ ] **Tier 2 checkpoint**: At TaskGroup completion, persist critical PM state (stage progress, cost, loaded skills) to `taskgroup_executions.checkpoint_data`. Checkpoint writes execute in a single DB transaction; on failure, rolls back completely (NFR-8a.03)
- [ ] **RegressionTestAgent** (CustomAgent) wired into pipeline after each batch — reads PM's regression policy from session state, runs tests when policy requires, no-ops otherwise. Always present, not LLM-discretionary
- [ ] Validators run at configured schedules: PER_DELIVERABLE, PER_BATCH, PER_TASKGROUP, PER_STAGE. Validators are mandatory — PM cannot skip or defer
- [ ] At TaskGroup completion: verify all batches done, generate completion report, publish event
- [ ] Stage transitions: forward-only, sequential, gated by `verify_stage_completion` + approval
- [ ] PM publishes batch completion events to Redis Streams
- [ ] Loop continues autonomously until all stages complete or escalation required
- [ ] Between batches, PM evaluates execution state and selects one action: retry failed deliverable (if retries remain), reorder to prioritize unblocked work, skip blocked deliverable (mark SKIPPED), or escalate to Director. Decision logged as event
- [ ] PM enforces per-project cost ceiling from `project_configs`; escalates to Director when exceeded
**Validation:**
- `uv run pytest tests/workers/ -v -k "work_session"`
- `uv run pyright app/workers/tasks.py app/agents/supervision.py`

---

### P8a.D10: Failure Handling & Batch Failure Threshold
**Files:** `app/agents/supervision.py`, `app/tools/management.py`
**Depends on:** P8a.D9
**Description:** Implement autonomous failure handling and batch failure threshold. Extend supervision callbacks.
**BOM Components:**
- [ ] `X08` — Autonomous failure handling (retry/reorder/skip)
- [ ] `X11` — Batch failure threshold (consecutive failures → Director suspension)
**Requirements:**
- [ ] PM retries failed deliverables up to per-deliverable retry limit (default: 2, configurable per project via NFR-8a.07); each retry logged as event
- [ ] On retry exhaustion, PM marks deliverable FAILED and evaluates dependency graph for blocked vs independent work
- [ ] Failed deliverables do not block deliverables with no dependency path through the failure
- [ ] PM reorders remaining work to maximize progress — independent deliverables first
- [ ] When PM cannot resolve, escalates to Director with context, validator evidence, and remediation history
- [ ] When CEO resolves escalation, resolution applies to work queue; suspended path resumes without restarting
- [ ] Remediation re-executes only failed deliverable and direct dependents — verified independent work never re-executed
- [ ] Consecutive batch failure counter tracked in session state (`pm:consecutive_batch_failures`)
- [ ] When counter exceeds threshold (default: 3, configurable per project), PM escalates to Director
- [ ] Director suspends project, diagnoses failure pattern, surfaces findings to CEO queue
- [ ] Director does not attempt autonomous repair beyond threshold — CEO must resolve
- [ ] CEO resolution resumes project from last checkpoint; verified deliverables not re-executed
- [ ] Successful batch resets consecutive failure counter to zero
**Validation:**
- `uv run pytest tests/agents/test_supervision.py tests/tools/test_management.py -v`
- `uv run pyright app/agents/supervision.py`

---

### P8a.D11: Three-Layer Completion Reports
**Files:** `app/workflows/completion.py`, `app/workflows/validators.py`
**Depends on:** P8a.D9
**Description:** Implement completion report generation at TaskGroup and Stage boundaries with three verification layers backed by validator evidence. Reports stored in execution record JSONB.
**BOM Components:**
- [ ] `X14` — Three-layer completion report wiring into INTEGRATE validators
**Requirements:**
- [ ] `CompletionReportBuilder` collects validator results, maps to verification layers, adds metrics
- [ ] TaskGroup completion report generated when all deliverables complete and validators pass
- [ ] Stage completion report aggregates TaskGroup reports within the stage
- [ ] Each layer contains machine evidence from validators — assertion without evidence marked as unverified
- [ ] TaskGroup cannot close while: any deliverable outstanding, any scheduled validator failing, any escalation unresolved
- [ ] Reports include: per-deliverable evidence, cost/token usage by agent tier, duration, decision log
- [ ] INTEGRATE stage CEO approval gate requires all three layers to pass
- [ ] Reports stored in `taskgroup_executions.completion_report` and `stage_executions.completion_report` JSONB
**Validation:**
- `uv run pytest tests/workflows/ -v -k completion`
- `uv run pyright app/workflows/completion.py`

---

### P8a.D12: Artifact Storage (Filesystem + DB)
**Files:** `app/agents/artifacts.py`, `app/workers/tasks.py`
**Depends on:** P8a.D1, P8a.D9
**Description:** Implement persistent artifact storage per execution.md: content stored on filesystem organized by project/entity, metadata in `artifacts` DB table. Post-pipeline step copies session artifacts to persistent store with DB association. Query API returns artifact references (path, content_type, size) — not inline content.
**BOM Components:**
- [ ] `CT03` — Artifact storage (`save_artifact`/`load_artifact`)
- [ ] `X31` — Deliverable artifact association
- [ ] `X32` — Completion report artifact association
**Requirements:**
- [ ] `ArtifactStore` class with `save(entity_type, entity_id, filename, content, content_type)` → writes file to `{project_dir}/{entity_type}/{entity_id}/{filename}`, creates `Artifact` DB record
- [ ] `ArtifactStore.load(artifact_id)` → reads file from path stored in DB record
- [ ] `ArtifactStore.list(entity_type, entity_id)` → queries `artifacts` table for entity
- [ ] Post-pipeline callback copies ADK session artifacts to persistent store via `ArtifactStore.save()`
- [ ] Artifact records include: entity_type, entity_id, path, content_type, size_bytes, created_at
- [ ] Deliverable and execution record query responses include artifact references
- [ ] Arbitrary file types supported (code, test results, reports)
**Validation:**
- `uv run pytest tests/agents/test_artifacts.py -v`
- `uv run pyright app/agents/artifacts.py`

---

### P8a.D13: Context Recreation at TaskGroup Boundary
**Files:** `app/agents/context_recreation.py`, `app/workers/tasks.py`
**Depends on:** P8a.D9, P8a.D12
**Description:** Enhance existing context recreation for TaskGroup-aware resume. When ContextRecreationRequired fires mid-TaskGroup, complete current deliverable, checkpoint, create fresh session, resume.
**BOM Components:**
- [ ] `CT04b` — Context recreation resume at TaskGroup boundary
**Requirements:**
- [ ] On ContextRecreationRequired, system completes current deliverable then checkpoints
- [ ] Seeded state includes: deliverable statuses, stage progress, current_taskgroup_id, accumulated cost, loaded skill names, project config
- [ ] Fresh session created; conversation history dropped; context reconstructed from durable stores
- [ ] Verified deliverables within completed TaskGroups never re-executed
- [ ] Mid-work batches rediscovered via `select_ready_batch` on resume
- [ ] Context recreation publishes events: initiation (old session ID) and completion (new session ID, seeded keys, remaining stages)
- [ ] Recreation completes within 30 seconds (NFR-8a.04)
**Validation:**
- `uv run pytest tests/agents/test_context_recreation.py -v`
- `uv run pyright app/agents/context_recreation.py`

---

### P8a.D14: Batch & Project Event Publishing
**Files:** `app/events/publisher.py`, `app/models/enums.py`
**Depends on:** P8a.D1
**Description:** Extend EventPublisher with new lifecycle event types. Add `publish_batch_completed`, `publish_stage_completed`, `publish_project_status_changed` methods alongside existing `publish_lifecycle`.
**BOM Components:**
- [ ] `V19` — Batch completion event publishing
**Requirements:**
- [ ] `BATCH_COMPLETED` event published after each batch with deliverable statuses and validator results
- [ ] `STAGE_COMPLETED` event published on stage transitions
- [ ] `PROJECT_STATUS_CHANGED` event published on any project status change
- [ ] `CONTEXT_RECREATED` event published on context recreation with old/new session IDs
- [ ] Events publish within 2 seconds of state change (NFR-8a.02)
- [ ] Event types added to `PipelineEventType` enum in `app/models/enums.py`
- [ ] Events include project_id, workflow_type, and timestamp
**Validation:**
- `uv run pytest tests/events/ -v`
- `uv run pyright app/events/publisher.py`

---

### P8a.D15: Workflow Edit Operations & Living Projects
**Files:** `app/workflows/manifest.py`, `app/workflows/auto-code/WORKFLOW.yaml`, `app/workers/tasks.py`, `app/tools/management.py`
**Depends on:** P8a.D8, P8a.D9
**Description:** Add `edit_operations` field to WorkflowManifest. Update `auto-code` WORKFLOW.yaml with edit operations and `resources` entries. Implement project edit flow.
**BOM Components:**
- [ ] `X26` — Workflow-defined edit operations manifest field (`edit_operations` in WORKFLOW.yaml)
- [ ] `X27` — Project edit request flow (Director receives edit → creates new TaskGroup)
**Requirements:**
- [ ] `EditOperationDef` added to manifest.py: name, description, entry_stage (optional), requires_approval (bool, default false)
- [ ] Existing manifests without `edit_operations` remain valid (default: empty list)
- [ ] `auto-code` WORKFLOW.yaml updated with: edit_operations (add-feature, remove-feature, fix-bug, refactor) and resources (at minimum one credential entry for testability of D4's `check_resources`)
- [ ] Projects modifiable in any state (SHAPING, ACTIVE, PAUSED, SUSPENDED, COMPLETED)
- [ ] Single edit creates one new TaskGroup; batch edit creates ordered TaskGroups respecting inter-edit dependencies
- [ ] PM incorporates new TaskGroups via `select_ready_batch` without interrupting current deliverable
- [ ] Edit work follows same execution loop with same validation, checkpointing, and reporting
- [ ] Project's accumulated context carries forward into edit work
**Validation:**
- `uv run pytest tests/workflows/ -v -k "edit or manifest"`
- `uv run pyright app/workflows/manifest.py`

---

### P8a.D16: Pause/Resume Lifecycle Mechanism
**Files:** `app/workers/lifecycle.py`, `app/workers/tasks.py`, `app/agents/supervision.py`
**Depends on:** P8a.D7, P8a.D9, P8a.D13
**Description:** Implement the three-layer pause/resume lifecycle per DD-5.
**BOM Components:**
- [ ] `X28` — Project-level pause/resume mechanism
- [ ] `X29` — Director work layer pause/resume mechanism
- [ ] `X30` — System-wide pause/resume
**Requirements:**
- [ ] Project pause: PM completes current deliverable, checkpoints at next boundary, logs reason, stops; no inconsistent state
- [ ] Project resume: loads persisted state, rebuilds PM context (skills, instructions, stage config), resumes from checkpoint; verified deliverables never re-executed
- [ ] Project abort: terminates execution, preserves completed work and events, records reason, transitions to ABORTED
- [ ] System-wide pause: pauses every active project individually; each reaches safe checkpoint independently
- [ ] System-wide resume: resumes each project individually; projects resume independently
- [ ] Director pause: stops backlog queue processing, stops new project creation, cascades pause to active projects
- [ ] Director resume: rebuilds Director context, loads pending queue state, resumes backlog processing, resumes paused projects in priority order
- [ ] All pause/resume operations publish lifecycle events with layer scope, actor, timestamp, reason
**Validation:**
- `uv run pytest tests/workers/test_lifecycle.py -v`
- `uv run pyright app/workers/lifecycle.py`

---

## Build Order

```
Batch 1 (independent): P8a.D1
  D1: Projects table, artifacts table, enum updates — app/db/models.py, app/models/enums.py, migration

Batch 2 (depends on D1): P8a.D2, P8a.D5, P8a.D6, P8a.D14
  D2: Tool DB + ARQ infrastructure — app/tools/management.py, app/workers/tasks.py
  D5: Director queue routes — app/gateway/routes/director_queue.py
  D6: Project & deliverable routes — app/gateway/routes/projects.py, deliverables.py
  D14: Event publishing — app/events/publisher.py, app/models/enums.py

Batch 3 (depends on D2): P8a.D3, P8a.D4
  D3: PM management tools — app/tools/management.py (PM section)
  D4: Director management tools — app/tools/management.py, app/tools/_toolset.py

Batch 4 (depends on D3, D4, D6): P8a.D7, P8a.D8
  D7: Pause/resume routes — app/gateway/routes/
  D8: Director execution loop — app/workers/tasks.py

Batch 5 (depends on D3, D8): P8a.D9
  D9: PM batch loop + pipeline infrastructure — app/workers/tasks.py, adk.py, supervision.py

Batch 6 (depends on D9): P8a.D10, P8a.D11, P8a.D12, P8a.D15
  D10: Failure handling — app/agents/supervision.py
  D11: Completion reports — app/workflows/completion.py
  D12: Artifact storage — app/agents/artifacts.py
  D15: Edit operations — app/workflows/manifest.py, WORKFLOW.yaml

Batch 7 (depends on D9, D12): P8a.D13
  D13: Context recreation — app/agents/context_recreation.py

Batch 8 (depends on D7, D9, D13): P8a.D16
  D16: Pause/resume lifecycle — app/workers/lifecycle.py
```

## Completion Contract Traceability

### FRD Coverage

| Capability | FRD Requirements | Deliverable(s) |
|---|---|---|
| CAP-1: Director-Mediated Project Creation | FR-8a.01, .05–.09 | P8a.D8 |
| *(same)* | FR-8a.02–.04, .10a, .10b | P8a.D4, P8a.D8 |
| CAP-2: Brief Validation & Resource Checks | FR-8a.10–.12 | P8a.D4 |
| *(same)* | FR-8a.13 | P8a.D4, P8a.D14 |
| CAP-3: Durable Management Operations | FR-8a.14–.18, .20, .25 | P8a.D3 |
| *(same)* | FR-8a.19 | P8a.D3, P8a.D4 |
| *(same)* | FR-8a.21 | P8a.D2, P8a.D4 |
| *(same)* | FR-8a.22–.24, .28–.32 | P8a.D4 |
| *(same)* | FR-8a.26–.27 | P8a.D2 |
| CAP-4: Director Queue Operations | FR-8a.33–.35 | P8a.D5 |
| *(same)* | FR-8a.36 | P8a.D3, P8a.D5 |
| *(same)* | FR-8a.37 | P8a.D2, P8a.D5 |
| CAP-5: Director Backlog Orchestration | FR-8a.38–.42 | P8a.D8 |
| CAP-6: Autonomous Execution Loop | FR-8a.43–.45, .47, .50, .52–.54 | P8a.D9 |
| *(same)* | FR-8a.46, .49 | P8a.D9, P8a.D11 |
| *(same)* | FR-8a.48 | P8a.D9 |
| *(same)* | FR-8a.51 | P8a.D14 |
| CAP-7: Failure Handling | FR-8a.55–.61 | P8a.D10 |
| CAP-8: Batch Failure Threshold | FR-8a.62–.66 | P8a.D10 |
| CAP-9: Completion Reporting | FR-8a.67–.72 | P8a.D11 |
| CAP-10: Project Lifecycle Tracking | FR-8a.73–.75 | P8a.D1 |
| *(same)* | FR-8a.76 | P8a.D1, P8a.D14 |
| CAP-11: Observability | FR-8a.77–.79, .81 | P8a.D6 |
| *(same)* | FR-8a.80 | P8a.D5, P8a.D6 |
| CAP-12: Context Recreation | FR-8a.82–.84 | P8a.D13 |
| *(same)* | FR-8a.85 | P8a.D13, P8a.D14 |
| CAP-13: Artifact Storage | FR-8a.86–.88 | P8a.D12 |
| *(same)* | FR-8a.89 | P8a.D6, P8a.D12 |
| CAP-14: Edit Operations | FR-8a.90–.93, .92a | P8a.D15 |
| *(same)* | FR-8a.92b | P8a.D9, P8a.D15 |
| CAP-15: Pause/Resume Lifecycle | FR-8a.94–.100 | P8a.D16 |
| *(same)* | FR-8a.101 | P8a.D14, P8a.D16 |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| X20 | `projects` table | P8a.D1 |
| X12 | Management tool DB wiring | P8a.D2 |
| X02 | Deliverable status tracking | P8a.D3 |
| X13 | `escalate_to_director` real implementation | P8a.D3 |
| X21 | Director `create_project` tool | P8a.D4 |
| X22 | Director `validate_brief` tool | P8a.D4 |
| X23 | Director `check_resources` tool | P8a.D4 |
| X24 | Director `delegate_to_pm` tool | P8a.D4 |
| X18 | Brief validation against `brief_template` | P8a.D4 |
| X19 | Pre-execution resource validation | P8a.D4 |
| G28 | `GET /director/queue` | P8a.D5 |
| G29 | `PATCH /director/queue/{id}` | P8a.D5 |
| G02 | `POST /specs` (brief submission) | P8a.D6 |
| G03 | `POST /workflows/{id}/run` | P8a.D6 |
| G04 | `GET /workflows/{id}/status` | P8a.D6 |
| G07 | `GET /deliverables` | P8a.D6 |
| G08 | `GET /deliverables/{id}` | P8a.D6 |
| G30 | `POST /projects/{id}/pause` | P8a.D7 |
| G31 | `POST /projects/{id}/resume` | P8a.D7 |
| G32 | `POST /director/pause` | P8a.D7 |
| G33 | `POST /director/resume` | P8a.D7 |
| X01 | Director-mediated project entry | P8a.D8 |
| X03 | Director execution loop | P8a.D8 |
| X04 | PM batch loop | P8a.D9 |
| A63 | PM outer loop | P8a.D9 |
| X25 | PM checkpoint_project (after_agent_callback) | P8a.D9 |
| X08 | Autonomous failure handling | P8a.D10 |
| X11 | Batch failure threshold | P8a.D10 |
| X14 | Three-layer completion report wiring | P8a.D11 |
| CT03 | Artifact storage | P8a.D12 |
| X31 | Deliverable artifact association | P8a.D12 |
| X32 | Completion report artifact association | P8a.D12 |
| CT04b | Context recreation resume at TaskGroup boundary | P8a.D13 |
| V19 | Batch completion event publishing | P8a.D14 |
| X26 | Edit operations manifest field | P8a.D15 |
| X27 | Project edit request flow | P8a.D15 |
| X28 | Project-level pause/resume | P8a.D16 |
| X29 | Director work layer pause/resume | P8a.D16 |
| X30 | System-wide pause/resume | P8a.D16 |

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | Director creates projects through conversation supporting seven entry modes | P8a.D4, P8a.D8 | `uv run pytest tests/workers/ -v -k director` |
| 2 | Brief validated against workflow's `brief_template`; pre-execution resource validation | P8a.D4 | `uv run pytest tests/tools/test_management.py -v -k "validate_brief or check_resources"` |
| 3 | Projects are first-order DB entities | P8a.D1 | `uv run alembic upgrade head && uv run pyright app/db/models.py` |
| 4 | Management tools write to and read from the database — no placeholder strings | P8a.D2, P8a.D3, P8a.D4 | `uv run pytest tests/tools/test_management.py -v` |
| 5 | `escalate_to_director` writes real rows; Director queue routes operational | P8a.D3, P8a.D5 | `uv run pytest tests/tools/ tests/gateway/ -v -k "escalat or director_queue"` |
| 6 | Director execution loop processes backlog | P8a.D8 | `uv run pytest tests/workers/ -v -k "director_queue or director_turn"` |
| 7 | PM drives sequential execution through hierarchy | P8a.D9 | `uv run pytest tests/workers/ -v -k work_session` |
| 8 | Loop continues autonomously until all stages complete | P8a.D9 | `uv run pytest tests/workers/ -v -k work_session` |
| 9 | Failed deliverables don't block independent work | P8a.D10 | `uv run pytest tests/agents/test_supervision.py -v -k failure` |
| 10 | Consecutive batch failures trigger Director suspension | P8a.D10 | `uv run pytest tests/agents/test_supervision.py -v -k threshold` |
| 11 | Three-layer completion report generated | P8a.D11 | `uv run pytest tests/workflows/ -v -k completion` |
| 12 | Context recreation at TaskGroup boundaries | P8a.D13 | `uv run pytest tests/agents/test_context_recreation.py -v` |
| 13 | Deliverable outputs and reports stored as persistent artifacts | P8a.D12 | `uv run pytest tests/agents/test_artifacts.py -v` |
| 14 | Projects support workflow-defined edit operations | P8a.D15 | `uv run pytest tests/workflows/ -v -k edit` |
| 15 | Deliverable and workflow status query routes operational | P8a.D6 | `uv run pytest tests/gateway/ -v -k "project or deliverable"` |
| 16 | Every work layer supports Pause and Resume | P8a.D7, P8a.D16 | `uv run pytest tests/workers/test_lifecycle.py tests/gateway/ -v -k "pause or resume"` |

## Research & Extended Design → [spec-research.md](spec-research.md)

See companion document for: ToolContext DB injection pattern, topological sort algorithm, state boundary principles, artifact storage design, completion report schema, edit operations manifest, pause/resume state machine, context recreation enhancement, and existing code patterns.
