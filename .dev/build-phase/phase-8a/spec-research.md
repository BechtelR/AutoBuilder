# Phase 8a Spec: Research Notes & Extended Design
*Generated: 2026-04-12*

> Companion to [spec.md](spec.md). Contains research findings and extended design decisions.

## Research Notes

### RN-1: ToolContext DB Session Injection Pattern

**Problem:** All 16+ management tools in `app/tools/management.py` are currently stubs returning placeholder strings. They need real database access, but FunctionTools execute in worker context with no direct DB session.

**Existing Pattern:** `reconfigure_stage()` uses `ToolContext.state` for ADK session state writes via `state_delta`. `get_project_context()` uses filesystem access. Neither accesses the database.

**Solution (from FRD RH-1):** Inject an async session factory into ToolContext state from the worker context during pipeline construction. Each tool call gets its own session/transaction.

```python
# In worker context (adk.py), before pipeline execution:
session_state["_db_session_factory"] = async_session_factory

# In tool function:
async def select_ready_batch(project_id: str, tool_context: ToolContext) -> str:
    factory = tool_context.state["_db_session_factory"]
    async with factory() as session:
        # DB operations within transaction
        ...
```

**Transaction boundary:** Each tool call = one transaction. Tools that need atomicity across multiple DB operations use a single `async with` block. The `_db_session_factory` key uses underscore prefix (internal/infrastructure, not agent-visible).

**Verified:** ToolContext is available to all FunctionTool callbacks. The `state` dict is the same ADK session state dict, readable by tools. Writing via `tool_context.actions.state_delta` for persistence.

### RN-2: Topological Sort for select_ready_batch

**Problem:** `select_ready_batch` needs dependency-aware batch selection with cycle detection (FRD RH-3).

**Current state:** `deliverables` table has `depends_on` column (list type in SQLAlchemy model). The dependency graph is stored per-deliverable as a list of dependency IDs.

**Solution:** Kahn's algorithm for topological sort. Filter deliverables by project + status (PLANNED or FAILED with retries remaining). Build adjacency graph from `depends_on`. Return the frontier set (nodes with in-degree 0 among remaining work). Cycle detection at dependency creation time (`manage_dependencies` rejects circular deps per FR-8a.18).

### RN-3: ADK Session State vs Database State Boundary

**Principle (from FRD RH-2):**
- **ADK session state** (`pm:*` keys): Ephemeral execution context — what the PM is doing right now (current stage, batch position, retry counts, loaded skills)
- **Database tables**: Durable entity state — what has been completed (deliverable status, queue items, project status, stage/taskgroup executions)
- **Checkpoint operation** (`checkpoint_project`): Syncs critical session state to database, creating a durable recovery point

**State keys that already exist** (from `app/models/constants.py`):
- `pm:current_stage`, `pm:stage_index`, `pm:stage_status`, `pm:stages_completed`, `pm:workflow_stages`
- `pm:batch_position`, `pm:escalation_context`, `pm:pending_escalations`
- `deliverable_status:{id}`, `deliverable_statuses`

**New state keys needed for Phase 8a:**
- `pm:current_taskgroup_id` — active TaskGroup execution ID
- `pm:consecutive_batch_failures` — for batch failure threshold (X11)
- `pm:total_cost` — accumulated cost for ceiling enforcement
- `pm:retry_count:{deliverable_id}` — per-deliverable retry tracking

### RN-4: Director Execution in Chat vs Work Sessions

**Problem (FRD RH-4):** Director is root_agent in both chat sessions (project creation, CAP-1) and work sessions (backlog orchestration, CAP-5). Same agent definition, different tool requirements.

**Current implementation:** `run_director_turn()` handles both chat mode (chat_id + message_id) and queue mode (project_id). `build_chat_session_agent()` builds Director without sub_agents for chat/queue. `build_work_session_agents()` builds Director with PM as sub_agent.

**Solution:** All Director tools (create_project, validate_brief, check_resources, delegate_to_pm, etc.) are available in both session types via GlobalToolset. The tool authorization is role-based (Director tier), not session-type-based. Instructions guide behavior — in chat sessions the Director shapes briefs and creates projects; in work sessions the Director orchestrates PMs and processes backlog.

### RN-5: Artifact Storage Design

**Problem:** Deliverable outputs and completion reports need persistent, retrievable storage (CAP-13).

**Architecture reference** (execution.md §Artifact Storage): Content stored on filesystem, metadata in dedicated `artifacts` DB table with polymorphic `entity_type` + `entity_id` association. ADK's `save_artifact`/`load_artifact` is session-scoped internal only.

**Solution:** `ArtifactStore` class handles filesystem I/O + DB metadata. Path layout: `{artifacts_root}/{project_id}/{entity_type}/{entity_id}/{filename}`. DB record: `id`, `entity_type`, `entity_id`, `path`, `content_type`, `size_bytes`, `created_at`. A post-pipeline callback (`after_agent_callback` on DeliverablePipeline) copies session artifacts to persistent store. API responses include artifact references (path, type, size) — not inline content.

**ADK relationship:** ADK `save_artifact` is used within agent sessions for intermediate data. The persistent `ArtifactStore` is the cross-session, queryable layer. Post-pipeline step bridges the two.

### RN-6: Three-Layer Completion Report Structure

**Architecture reference** (workflows.md §7): Three verification layers — functional, architectural, contract. Each requires machine-generated evidence from validators.

**Implementation:** A `CompletionReportBuilder` utility that:
1. Collects validator results from the current TaskGroup/Stage execution
2. Maps results to verification layers based on validator type
3. Adds cost/token/duration metrics from session state
4. Produces a structured report stored in `taskgroup_executions.completion_report` or `stage_executions.completion_report` (JSONB)

**Report schema:**
```python
class CompletionReport(TypedDict):
    layers: dict[str, VerificationLayer]  # functional, architectural, contract
    metrics: ExecutionMetrics              # cost, tokens, duration
    decision_log: list[DecisionEntry]      # autonomous vs user-resolved
    generated_at: str                      # ISO timestamp
```

### RN-7: Edit Operations Manifest Extension

**Architecture reference** (workflows.md §3): `edit_operations` field in WORKFLOW.yaml.

**Design (from FRD RH-8):** Minimal schema — name + description + optional `entry_stage` (which stage to start from for this edit type) + `requires_approval` bool.

```yaml
edit_operations:
  - name: add-feature
    description: Add a new feature to the project
    entry_stage: plan    # Start from PLAN stage
    requires_approval: false
  - name: fix-bug
    description: Fix a reported bug
    entry_stage: build   # Skip planning, go straight to BUILD
    requires_approval: false
```

**Manifest model extension:** Add `EditOperationDef` to `app/workflows/manifest.py`. Progressive disclosure — existing manifests without this field remain valid (default: empty list).

### RN-8: Pause/Resume State Machine

**Three layers** (FRD CAP-15):

1. **Project-level** (X28): PM completes current deliverable → checkpoints at next boundary → sets project status to PAUSED → stops execution. Start: loads checkpoint → rebuilds context → resumes batch loop.

2. **Director work layer** (X29): Director stops backlog processing → cascades pause to all active projects → logs. Start: rebuilds Director context → resumes queue processing → starts paused projects.

3. **System-wide** (X30): Iterates project-level pause/resume for all active projects. Thin wrapper over project-level operations.

**Implementation:** Pause is a state transition (ACTIVE → PAUSED) that the PM observes between deliverables. The PM checks project status before each batch selection. If PAUSED, the PM checkpoints and exits the work session. Resume enqueues a new work session that continues from checkpoint.

### RN-9: Context Recreation Enhancement (CT04b)

**Existing implementation** (`app/agents/context_recreation.py`): 4-step pipeline (persist → seed → fresh session → reassemble). Currently handles ContextRecreationRequired exception in `run_work_session`.

**Phase 8a enhancement:** Resume at TaskGroup boundary, not just "somewhere in the pipeline."

**Key change:** When ContextRecreationRequired fires mid-TaskGroup:
1. Complete current deliverable (if in progress) — already handled by ADK completing the current agent step
2. Checkpoint at the deliverable boundary within the TaskGroup
3. Create fresh session with seeded state (including `pm:current_taskgroup_id`)
4. Resume the current TaskGroup — `select_ready_batch` rediscovers remaining work

**No new files needed** — extend existing `recreate_context()` in `context_recreation.py` with TaskGroup-aware state seeding.

### RN-10: Existing Code Patterns to Follow

**Worker task structure** (`app/workers/tasks.py`):
- `run_work_session()` already handles: session creation, agent building, pipeline execution, context recreation, failure escalation, lifecycle events
- Pattern: build agents → create/load session → execute with runner → handle exceptions → publish events

**Management tool pattern** (`app/tools/management.py`):
- `reconfigure_stage()` is the reference implementation for a real tool with state writes
- Pattern: validate inputs → perform operation → write state via ToolContext.actions.state_delta → return formatted string result

**Event publishing** (`app/events/publisher.py`):
- `publish_lifecycle()` for synthetic events (STARTED, COMPLETED, FAILED)
- Extend with: BATCH_COMPLETED, STAGE_COMPLETED, PROJECT_PAUSED, PROJECT_STARTED, CONTEXT_RECREATED

**Supervision callbacks** (`app/agents/supervision.py`):
- `create_before_pm_callback()` enforces limits (retry budget, cost ceiling)
- Extend with: batch failure threshold check, pause state check

---

*[Back to spec.md](spec.md)*
