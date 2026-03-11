# Phase 5b Spec: Supervision & Integration
*Generated: 2026-03-11*

## Overview

Phase 5b wires the supervision hierarchy and makes AutoBuilder an interactive, supervised autonomous system. Before this phase, agents and pipelines exist (5a) but nobody supervises them and the CEO can't interact. This phase delivers:

1. **State key authorization** — Tier-based write access enforced on every state delta. Director-prefixed keys writable only by Director-tier; PM-prefixed by PM+ tier; worker-prefixed and non-prefixed by all. Atomic rejection on violation with audit event.
2. **CEO queue operations** — Gateway routes for queue query, resolution, and dismissal. Approval resolution writes back to session state so the PM discovers it during batch selection and resumes suspended paths.
3. **Director formation & system reminders** — Three structured artifacts (`user:director_identity`, `user:ceo_profile`, `user:operating_contract`) formed through a dedicated Settings conversation. Ephemeral system reminders injected via `before_model_callback` for token budget warnings and state change notifications.
4. **Supervision callbacks** — Director observes PM execution through `before_agent_callback` (limit checks) and `after_agent_callback` (status capture, escalation detection). Pipeline callbacks: `checkpoint_project` (after each deliverable) and `verify_batch_completion` (after batch).
5. **Director-PM delegation** — Director as stateless root_agent delegates to PM via `transfer_to_agent`. PM escalates back. Hard limits cascade from CEO → Director → PM → Workers.
6. **PM autonomous loop** — Sequential batch execution: select → dispatch → checkpoint → verify → reason → repeat. Failed deliverables don't block independent work. PM returns or escalates when done.
7. **Director queue processing** — Dual-path: inline check during work sessions (after PM turns) + ARQ cron for idle periods.
8. **Chat integration** — Wire real Director into existing chat routes. Per-message invocation. Auto-create "Main" project session.
9. **Context recreation** — 4-step pipeline (persist → seed → fresh session → reassemble) triggered by ContextRecreationRequired. Degraded mode (no real MemoryService). Pipeline resumes from correct stage.

Aligns with FRD capabilities CAP-1 through CAP-7. No parallel execution (Phase 8), no real SkillLibrary (Phase 6), no real MemoryService (Phase 9).

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 5a: Agent Definitions & Pipeline | UNMET (PLANNED) | Spec complete; build pending. Agents, AgentRegistry, InstructionAssembler, DeliverablePipeline, ContextBudgetMonitor, DB tables (ceo_queue, director_queue, project_configs), enums all required. |
| Phase 4: Core Toolset | MET | 42 FunctionTools, GlobalToolset with role-based vending. `escalate_to_ceo`, `escalate_to_director`, `select_ready_batch`, `update_deliverable`, `query_deliverables` all available. |
| Phase 3: ADK Engine Integration | MET | LlmRouter, DatabaseSessionService, EventPublisher, anti-corruption layer, 4-scope state operational. |

## Design Decisions

### DD-1: ADK transfer_to_agent for Director↔PM

Director is the `root_agent` of the ADK App. PM agents are `sub_agents` of the Director. When the Director decides to delegate, it calls `transfer_to_agent` targeting the PM — ADK moves execution to the PM sub_agent within the same runner session. When the PM completes or escalates, it calls `transfer_to_agent` back to the Director.

For work sessions: Director is root with PM(s) as sub_agents. For chat sessions: Director is root with no sub_agents (direct conversation only).

The `run_work_session` task builds the Director with the project's PM as a sub_agent. The `run_director_turn` task builds the Director with no sub_agents (chat-only context).

### DD-2: State Key Authorization — Event Loop Enforcement

State key authorization is enforced in the worker event loop during `runner.run_async()` iteration. For each event with a `state_delta`, the EventPublisher validates key prefixes against the author agent's tier. On violation:

1. The entire delta is logged as rejected (no partial application to DB)
2. An error event is published to the Redis Stream
3. A corrective state delta is written to the session, reverting the unauthorized keys

**Tier determination**: Agent name → tier mapping using a simple dict:
- `"director"` → `"director"`
- Names starting with `"pm"` → `"pm"`
- Everything else → `"worker"`

**Authorization matrix** (write access):

| Key Prefix | Director | PM | Worker |
|---|:---:|:---:|:---:|
| `director:*` | ✓ | ✗ | ✗ |
| `pm:*` | ✓ | ✓ | ✗ |
| `worker:*` | ✓ | ✓ | ✓ |
| `app:*` | ✓ | ✓ | ✗ |
| `user:*` | ✓ | ✓ | ✓ |
| No prefix | ✓ | ✓ | ✓ |
| `temp:*` | ✓ | ✓ | ✓ |

Reads are always unrestricted (ADK state reads happen before event emission — no interception needed).

**Why event loop, not session service wrapper**: The EventPublisher already inspects every event via getattr ACL (zero ADK imports). Adding authorization checking fits the existing pattern. A session service wrapper would require ADK imports and complex interception of internal persistence calls. The event loop approach has a brief in-memory inconsistency window (between ADK applying the delta and our corrective write), which is acceptable for Phase 5b — agents follow their instructions as the primary control; authorization is a safety net.

### DD-3: Approval Writeback Pattern

When the CEO resolves an approval via `PATCH /ceo/queue/{id}`, the gateway:

1. Updates the queue item status to `RESOLVED` with resolution details
2. Writes a resolution key to the originating project's session state: `approval:{queue_item_id}` → resolution payload
3. If no active work session exists for the project, enqueues a new `run_work_session` job to resume

The PM discovers resolutions during batch selection. The `select_ready_batch` tool checks for `approval:*` keys matching pending deliverables' blockers. This is a pull model — the PM polls state, no active push.

The gateway writes to session state via `DatabaseSessionService` directly. This is safe because:
- The write targets a well-known approval key, not arbitrary state
- The PM reads this key only during batch selection (between turns), not mid-LLM-call
- Concurrent access is handled by PostgreSQL-backed session storage

### DD-4: PM Loop as ADK Agent Conversation

The PM loop is not a custom Python loop — it's the PM LlmAgent reasoning across multiple turns within a single ADK runner session. Each "batch cycle" is a turn:

1. PM uses `select_ready_batch` tool → gets ready deliverables
2. PM dispatches each deliverable through DeliverablePipeline (sub_agent execution)
3. After each deliverable: `checkpoint_project` callback fires automatically
4. After batch: `verify_batch_completion` callback fires
5. PM reads results via `query_deliverables` tool
6. PM reasons about next action: select next batch, escalate, or complete

The `run_work_session` task starts `runner.run_async()` which runs until the Director (and thus PM) finishes. The PM's conversation history grows with each batch cycle. ContextBudgetMonitor (5a) triggers recreation when the context fills up.

### DD-5: Director Queue Dual-Path Processing

Per Decision #67:

**Inline path** (zero latency for active sessions): The `after_agent_callback` on the PM checks the Director Queue after each PM turn. If pending items exist, the Director processes them inline before deciding its next action. This is a lightweight DB query — zero Director invocation cost for empty queues.

**Cron path** (for idle projects): An ARQ cron job `process_director_queue` runs at configurable intervals (default: 60s via `AUTOBUILDER_DIRECTOR_QUEUE_INTERVAL`). It scans for projects with pending Director Queue items and no active work sessions. For each, it enqueues a `run_director_turn` job. The cron function is a lightweight DB query — no Director invocation for empty queues.

**Deduplication**: Active work sessions set a Redis key `director:work_session:{project_id}` with TTL. The cron job skips projects with this key present.

### DD-6: Director Formation via Settings Conversation (Decision #68)

The Director's personality and working relationship with the CEO are established through a dedicated Settings conversation. Three structured artifacts define the relationship.

**State keys:**
- `user:director_identity` — Director name (optional), personality traits, communication style, working metaphor, decision approach, team management philosophy
- `user:ceo_profile` — CEO name, working style, communication preferences, domain expertise, collaboration patterns, autonomy comfort, decision-making style, strengths to leverage
- `user:operating_contract` — Proactivity level, escalation sensitivity, decision-making autonomy, feedback style, notification preferences, working hours, when to push back, when to just execute
- `user:formation_status` — `PENDING` | `IN_PROGRESS` | `COMPLETE`

**Settings session:** A new `ChatType.SETTINGS` value. One Settings session per user, auto-created on first system access (like "Main"). Uses per-message invocation model (same as chat). Director built with formation-mode instructions when `formation_status != COMPLETE`.

**Formation trigger:** When `user:formation_status` is missing or `PENDING`, the Director enters formation mode in the Settings session. Formation is a conversational exchange of ~5-10 professional but warm questions. The Director proposes structured artifact values; the CEO approves/edits in conversation. When all three artifacts are written, `formation_status` is set to `COMPLETE`.

**Instruction template integration:**
- `{user:director_identity}` → IDENTITY fragment (who the Director is for this user)
- `{user:ceo_profile}` → PROJECT fragment (user context available to all project work)
- `{user:operating_contract}` → GOVERNANCE fragment (behavioral parameters)
- `{user:director_identity?}` optional template — empty when key absent, formation instruction block engages

**Artifact update from any session:** Director proposes update via CEO queue `APPROVAL` item. On approval, artifact written to `user:` scope. Settings session always available for direct editing.

**Reset:** CEO requests reset in Settings session → Director clears three artifact keys + `formation_status` → re-enters formation on next message.

**Storage:** Database only — artifacts persist in `user:` scope state via DatabaseSessionService (PostgreSQL). No file export/import.

### DD-7: Context Recreation File Placement

New file `app/agents/context_recreation.py` contains the 4-step recreation logic:
- `recreate_context(session_service, old_session, pipeline_state)` — orchestrates the 4 steps
- `persist_important_state(old_session, memory_service)` — step 1
- `seed_critical_keys(old_session, new_session)` — step 2
- `rebuild_reduced_pipeline(registry, completed_stages)` — step 4

Called from the worker's pipeline execution when `ContextRecreationRequired` is caught. The worker creates a fresh session (step 3) and delegates reconstruction to this module.

### DD-8: Supervision Callback Signatures

ADK callbacks use specific signatures. Phase 5b callbacks:

```python
# Director supervision — set on PM sub_agent
async def before_pm_execution(ctx: CallbackContext) -> Content | None:
    """Check hard limits. Return Content to block, None to proceed."""

async def after_pm_execution(ctx: CallbackContext) -> Content | None:
    """Capture PM status, detect escalation signals, check Director Queue inline."""

# Pipeline callbacks — set on DeliverablePipeline sub_agents
async def checkpoint_project(ctx: CallbackContext) -> Content | None:
    """Persist deliverable completion status after each pipeline run."""

async def verify_batch_completion(ctx: CallbackContext) -> Content | None:
    """Validate all batch deliverables reached terminal state."""
```

All callbacks are async, receive `CallbackContext`, and return `Content | None`. They read/write state via `ctx.state` (callback state writes DO persist, unlike direct `ctx.session.state` writes in `_run_async_impl`). Verify this in `.dev/.knowledge/adk/` during implementation.

### DD-9: Work Session vs Chat Session vs Settings Session Agent Construction

| Concern | Work Session (`run_work_session`) | Chat Session (`run_director_turn`) | Settings Session (`run_director_turn`) |
|---|---|---|---|
| Root agent | Director | Director | Director |
| Sub agents | PM for the project | None | None |
| Supervision callbacks | Yes (before/after PM) | No | No |
| Session type | Long-running (ARQ job, multiple turns) | Per-message (one turn per message) | Per-message (one turn per message) |
| Formation artifacts | Used for behavior | Used for behavior | Formation or evolution mode based on `formation_status` |
| Hard limits | Loaded from project_configs | N/A | N/A |
| Director Queue | Inline check after PM turns | Not checked | Not checked |

Both use `AgentRegistry.build("director", ctx)` but with different sub_agent configurations.

---

## Deliverables

### P5b.D1: State Key Authorization
**Files:** `app/events/publisher.py`
**Depends on:** —
**Description:** Add tier-based state key authorization to EventPublisher. For each event with a state_delta, validate that the author agent's tier has write permission for every key prefix. On violation, reject the entire delta atomically: publish an error event with details (rejected key, author tier, required tier) and write a corrective state delta reverting unauthorized keys. Reads remain unrestricted. Non-prefixed keys writable by all tiers.
**BOM Components:**
- [x]`A79` — State key authorization (tier prefixes, EventPublisher ACL)
**Requirements:**
- [x]`EventPublisher.validate_state_delta(event, author_tier)` returns list of unauthorized key names (empty = authorized)
- [x]Agent-to-tier mapping: `"director"` → director, names matching `pm*` → pm, all others → worker
- [x]Authorization matrix matches DD-2 (director:* = director-only, pm:* = pm+director, worker:* and non-prefixed = all, app:* = pm+director, user:* and temp:* = all)
- [x]On violation: entire state_delta rejected — corrective delta written removing all unauthorized keys
- [x]On violation: error event published with `PipelineEventType.ERROR` containing rejected keys, author, tier mismatch
- [x]Reads unrestricted — validation only on state_delta writes, never on state reads
- [x]Non-prefixed keys always pass validation for any tier
- [x]Validation adds ≤ 1ms overhead per state delta (synchronous prefix check, no DB lookup)
- [x]Zero new ADK imports (uses existing getattr ACL pattern)
**Validation:**
- `uv run pyright app/events/publisher.py`
- `uv run pytest tests/events/test_publisher.py -v`

---

### P5b.D2: CEO Queue Gateway Routes & Approval Writeback
**Files:** `app/gateway/routes/ceo_queue.py`, `app/gateway/models/ceo_queue.py`, `app/gateway/main.py`, `app/db/models.py`, `app/db/migrations/versions/NNN_ceo_queue_resolution_fields.py`
**Depends on:** —
**Description:** Add gateway routes for CEO queue operations: list/filter queue items and resolve/dismiss items. Add resolution columns (`resolution`, `resolver`, `resolved_at`) to `CeoQueueItem` model via Alembic migration -- the 5a model has status but no fields to record resolution details. When an approval-type item is resolved, write the resolution to the originating project's session state so the PM can discover it. When no active work session exists, enqueue a new work session to resume. Handle edge cases: conflict on double-resolve, stale session references.
**BOM Components:**
- [x]`G12` — `GET /ceo/queue` route
- [x]`G13` — `PATCH /ceo/queue/{id}` route
- [x]`V18` — CEO resolved approval → session state writeback
**Requirements:**
- [x]`GET /ceo/queue` returns queue items filtered by optional query params: `type` (CeoItemType), `priority` (EscalationPriority), `status` (CeoQueueStatus). Ordered by priority descending then created_at ascending
- [x]`GET /ceo/queue` completes within 200ms for up to 1000 items
- [x]`CeoQueueItem` model extended with nullable columns: `resolution` (str), `resolver` (str), `resolved_at` (datetime). Alembic migration adds these three columns to the existing `ceo_queue` table (sequential NNN numbering)
- [x]`PATCH /ceo/queue/{id}` accepts resolution payload: `status` (RESOLVED or DISMISSED), `resolution` (str), `resolver` (str)
- [x]On resolve: updates item status, records resolution text, resolver identity, and resolution timestamp (`resolved_at` set server-side to `datetime.now(timezone.utc)`)
- [x]On resolve of approval-type item: writes `approval:{queue_item_id}` key to originating project's session state via DatabaseSessionService
- [x]On resolve with no active work session: enqueues `run_work_session` ARQ job to resume execution
- [x]On dismiss: updates item status to DISMISSED, records dismissal. No writeback triggered
- [x]Conflict: resolving/dismissing an already-resolved/dismissed item returns HTTP 409 with ConflictError
- [x]Stale reference: if source session no longer exists, resolution succeeds (item marked resolved) but writeback skipped with warning event
- [x]All CEO queue state transitions (resolve, dismiss) publish audit events to Redis Stream with item ID, action, resolver, and project context (NFR-5b.07)
- [x]Pydantic request/response models in `ceo_queue.py` with proper types (no Any, no magic strings)
- [x]Route registered in `main.py` create_app()
**Validation:**
- `uv run alembic upgrade head` — migration applies without error
- `uv run pyright app/gateway/routes/ceo_queue.py app/gateway/models/ceo_queue.py app/db/models.py`
- `uv run pytest tests/gateway/test_ceo_queue.py -v`

---

### P5b.D3: Director Formation & System Reminders
**Files:** `app/agents/formation.py` (new), `app/agents/state_helpers.py`
**Depends on:** —
**Description:** Add Director formation logic: on first system access for a user, auto-create a Settings session (`ChatType.SETTINGS`) and set `user:formation_status` to `PENDING`. When the Director enters a Settings session with `formation_status != COMPLETE`, it operates in formation mode — a conversational exchange that produces three structured artifacts (`user:director_identity`, `user:ceo_profile`, `user:operating_contract`). Formation instructions are a dedicated instruction fragment, not a YAML file. Add system reminder injection callback (`before_model_callback`) that inserts ephemeral governance nudges — context budget usage, state change notifications, progress summaries — before each LLM call. No injection when no relevant reminders exist. Reminders are transient (not persisted, lost during recreation).
**BOM Components:**
- [x]`A08` — Director formation artifacts (`user:` scope — three structured keys + formation status)
- [x]`A09` — Director formation logic (Settings conversation)
- [x]`A58` — System reminder injection (`before_model_callback`)
**Requirements:**
- [x]`FormationStatus` enum: `PENDING`, `IN_PROGRESS`, `COMPLETE` in `app/models/enums.py`
- [x]State key constants: `DIRECTOR_IDENTITY_KEY`, `CEO_PROFILE_KEY`, `OPERATING_CONTRACT_KEY`, `FORMATION_STATUS_KEY` in `app/models/constants.py`
- [x]`ensure_formation_state(session_service, user_id)` checks if `user:formation_status` exists. If missing, sets to `PENDING`. Returns current `FormationStatus`.
- [x]`write_artifact(session_service, user_id, key, value)` writes a formation artifact to `user:` scope. Updates `formation_status` to `COMPLETE` when all three artifacts exist.
- [x]`reset_formation(session_service, user_id)` clears all three artifact keys and resets `formation_status` to `PENDING`.
- [x]Formation conversation instructions defined as a formation instruction fragment in `app/agents/formation.py` — loaded by InstructionAssembler when `formation_status != COMPLETE` in Settings sessions
- [x]`ChatType.SETTINGS` enum value added to `app/models/enums.py`
- [x]Settings session auto-created on first system access (like "Main") with `type=ChatType.SETTINGS`
- [x]Director built with formation-mode or evolution-mode instructions based on `user:formation_status` when entering Settings session
- [x]Director can propose artifact updates from any session via CEO queue `APPROVAL` item
- [x]`system_reminder_callback(ctx, llm_request)` matches `before_model_callback` signature
- [x]Injects current `context_budget_used_pct` from state as a context budget warning (e.g., "Context usage: 73%")
- [x]Injects state change notifications from other agents when relevant state keys changed since last call
- [x]When no relevant reminders exist, callback returns None without modifying the request
- [x]System reminders are NOT persisted to durable state — they reflect transient conditions
- [x]System reminders are acceptable to lose during context recreation (by design)
- [x]Callback integrates into the `compose_callbacks` chain from Phase 5a (added after context injection, before budget monitor)
**Validation:**
- `uv run pyright app/agents/formation.py app/agents/state_helpers.py`
- `uv run pytest tests/agents/test_formation.py tests/agents/test_state_helpers.py -v`

---

### P5b.D4: Supervision Callbacks
**Files:** `app/agents/supervision.py`
**Depends on:** —
**Description:** Implement 4 supervision callbacks as standalone async functions. Director supervision: `before_pm_execution` checks project hard limits (cost ceiling, retry budget) and blocks if exceeded; `after_pm_execution` captures PM completion status, detects escalation signals, and checks Director Queue inline. Pipeline safety: `checkpoint_project` persists deliverable completion status after each pipeline run; `verify_batch_completion` validates all batch deliverables reached terminal state.
**BOM Components:**
- [x]`A14` — `before_agent_callback` (Director supervision)
- [x]`A15` — `after_agent_callback` (Director supervision)
- [x]`A40` — `verify_batch_completion` (`after_agent_callback`)
- [x]`A41` — `checkpoint_project` (`after_agent_callback`)
**Requirements:**
- [x]`before_pm_execution(ctx)` reads project hard limits from `project_configs` via state, checks current retry count and cost against limits
- [x]When a limit is exceeded, `before_pm_execution` returns `Content` blocking PM execution with exceeded-limit details
- [x]`before_pm_execution` publishes supervision event to Redis Stream (PM invocation with project context)
- [x]`after_pm_execution(ctx)` reads PM completion status from session state, publishes status event to Redis Stream
- [x]`after_pm_execution` detects escalation signals in state (e.g., PM wrote escalation context) — makes them observable, does not resolve
- [x]`after_pm_execution` checks Director Queue for pending items (inline path per DD-5)
- [x]`checkpoint_project(ctx)` persists deliverable completion status and pipeline output to durable state after each deliverable — fires regardless of success or failure
- [x]`verify_batch_completion(ctx)` validates all batch deliverables reached terminal state (completed or failed), logs batch result
- [x]All callbacks match ADK callback signature: `async (CallbackContext) -> Content | None`
- [x]All callbacks add ≤ 5ms overhead per invocation (lightweight state checks + event publishes, no LLM calls)
- [x]All significant state transitions produce audit events in Redis Stream
**Validation:**
- `uv run pyright app/agents/supervision.py`
- `uv run pytest tests/agents/test_supervision.py -v`

---

### P5b.D5: Director-PM Delegation & Hard Limits
**Files:** `app/workers/tasks.py`, `app/workers/adk.py`
**Depends on:** P5b.D3, P5b.D4
**Description:** Implement `run_work_session` task function that builds Director as root_agent with PM as sub_agent, ensures formation state, loads hard limits from project_configs, wires supervision callbacks, and starts the ADK runner. Director delegates to PM via `transfer_to_agent`. PM escalates back. Hard limits (retry_budget, cost_ceiling) cascade: Director cannot exceed global limits, PM cannot exceed project limits. Handle delegation/escalation failures with error events and CEO queue items.
**BOM Components:**
- [x]`A05` — Director → PM delegation (`transfer_to_agent`)
- [x]`A06` — PM → Director escalation (`transfer_to_agent`)
- [x]`A07` — Hard limits cascade (CEO → Director → PM → Workers)
**Requirements:**
- [x]`run_work_session(ctx, project_id, params)` builds Director from AgentRegistry with PM as sub_agent
- [x]Director built as stateless root_agent — fresh build on each invocation, no in-memory state carried
- [x]PM built via `AgentRegistry.build(f"PM_{project_id}", ctx, definition="pm")` with project-specific session
- [x]Supervision callbacks (from D4) wired onto PM sub_agent: `before_agent_callback=before_pm_execution`, `after_agent_callback=after_pm_execution`
- [x]Formation state ensured on first invocation for user (calls `ensure_formation_state` from D3)
- [x]Hard limits loaded from `project_configs` table and written to session state for PM access
- [x]When project has no config entry, default limits created from global defaults (new `AUTOBUILDER_DEFAULT_RETRY_BUDGET`, `AUTOBUILDER_DEFAULT_COST_CEILING` settings)
- [x]Director cannot set limits exceeding global limits; PM cannot set worker constraints exceeding project limits (validated at write time)
- [x]When retry budget depleted: escalation to tier above
- [x]When cost ceiling hit: hard stop + escalation to tier above
- [x]On delegation failure (PM build fails, session creation fails): publish error event, create CEO queue item with failure context
- [x]On escalation failure (PM→Director transfer fails): publish error event, PM escalation context preserved in session state
- [x]Successful delegation and escalation publish audit events to Redis Stream with project ID, agent names, and direction (NFR-5b.07)
- [x]Active work session sets Redis key `director:work_session:{project_id}` with TTL for deduplication
- [x]`run_work_session` registered in WorkerSettings.functions
**Validation:**
- `uv run pyright app/workers/tasks.py app/workers/adk.py`
- `uv run pytest tests/workers/ -v`

---

### P5b.D6: PM Autonomous Loop (Sequential)
**Files:** `app/workers/tasks.py`
**Depends on:** P5b.D4, P5b.D5
**Description:** Wire the PM's autonomous batch loop within the work session. The PM reasons across multiple turns: selects batch via tool, dispatches each deliverable through DeliverablePipeline sequentially, receives checkpoint/verification callbacks, reasons about results, and decides the next batch or escalation. No parallel execution (Phase 8). The PM discovers approval resolutions from session state during batch selection.
**BOM Components:** *(None unique — emergent behavior from PM agent (5a) + callbacks (D4) + delegation (D5))*
**Requirements:**
- [x]PM receives project with pre-seeded deliverables in session state and uses `select_ready_batch` tool to compose batches
- [x]Each deliverable dispatches through DeliverablePipeline sequentially (no ParallelAgent — Phase 8)
- [x]`checkpoint_project` callback fires automatically after each deliverable completes — persists status and output
- [x]`verify_batch_completion` callback fires after all batch deliverables complete — validates terminal states
- [x]PM reasons between batches: queries results via `query_deliverables`, assesses failures, decides next batch composition
- [x]Inter-batch reasoning maintains coherence across batch boundaries (verified with 2+ deliverable test)
- [x]Failed deliverable marked failed, PM continues with unblocked deliverables (failed doesn't block independent work)
- [x]PM returns control to Director on project completion (all deliverables complete or failed with no unblocked work)
- [x]PM escalates to Director when unable to make progress (all blocked, no retries, no reordering possible) with context
- [x]PM discovers approval resolutions via `approval:*` keys in session state during `select_ready_batch`
- [x]When PM suspended (waiting for approvals, no unblocked work), PM returns to Director with suspended status. ARQ job completes. New work session enqueued on approval resolution (D2).
**Validation:**
- `uv run pytest tests/workers/test_pm_loop.py -v`

---

### P5b.D7: Director Queue Processing
**Files:** `app/workers/tasks.py`, `app/workers/settings.py`
**Depends on:** P5b.D5
**Description:** Implement dual-path Director Queue processing. Inline path: the `after_pm_execution` callback (D4) already checks the queue after PM turns. Cron path: add `process_director_queue` ARQ cron job that scans for pending items in projects without active work sessions and enqueues `run_director_turn` jobs. Add `AUTOBUILDER_DIRECTOR_QUEUE_INTERVAL` setting.
**BOM Components:**
- [x]`A16` — Director queue consumption (reads pending escalations, resolves or forwards to CEO queue)
**Requirements:**
- [x]`process_director_queue` cron function: queries `director_queue` for pending items, groups by project, skips projects with active work sessions (Redis key check)
- [x]For each project with pending items and no active session: enqueues `run_director_turn` job
- [x]Cron function is lightweight DB query — zero Director invocation or token cost for empty queues
- [x]Cron interval configurable via `AUTOBUILDER_DIRECTOR_QUEUE_INTERVAL` setting (default: 60 seconds)
- [x]Cron registered in `WorkerSettings.cron_jobs`
- [x]Director processes queue items during work sessions via inline path (after_pm_execution callback in D4) and during idle periods via cron path
- [x]Director evaluates each item: resolves locally (writes resolution to state) or forwards to CEO queue via `escalate_to_ceo`
- [x]Items forwarded to CEO queue updated to `FORWARDED_TO_CEO` status
- [x]New setting added to `app/config/settings.py`: `director_queue_interval: int = 60`
**Validation:**
- `uv run pyright app/workers/tasks.py app/workers/settings.py app/config/settings.py`
- `uv run pytest tests/workers/test_director_queue.py -v`

---

### P5b.D8: Chat Integration & Director "Main"
**Files:** `app/gateway/routes/chat.py`, `app/workers/tasks.py`, `app/workers/settings.py`
**Depends on:** P5b.D5
**Description:** Wire the real Director agent into existing chat routes. Modify `run_director_turn` to build Director from AgentRegistry (replacing the echo stub), with per-message invocation model — one worker call per message, fresh Director build each time. Director has access to chat session history, `user:` scope state (formation artifacts), and `app:` scope state (project status). Add auto-creation of "Main" chat session and Settings session when CEO sends first message. Settings session routes Director into formation or evolution mode based on `user:formation_status`. Chat invocations do not block or modify active work sessions.
**BOM Components:**
- [x]`G10` — `POST /chat/{session_id}/messages` route
- [x]`G11` — `GET /chat/{session_id}/messages` route
- [x]`A70` — Chat session model (per-message `runner.run_async`)
- [x]`A13` — Director "Main" project (permanent chat session)
**Requirements:**
- [x]`run_director_turn` builds Director from `AgentRegistry.build("director", ctx)` replacing echo stub
- [x]Director built with no sub_agents for chat context (no PM delegation in chat)
- [x]Per-message invocation: one `runner.run_async` call per user message, fresh Director each time
- [x]Director accesses chat session conversation history via ADK session events
- [x]Director accesses `user:` scope state (formation artifacts: director_identity, ceo_profile, operating_contract) and `app:` scope state (project status, deliverable summaries)
- [x]Chat invocation does not block, interrupt, or modify running work sessions
- [x]When CEO sends message without specifying a project, system routes to "Main" chat session
- [x]If "Main" session does not exist for the user, it is created automatically with `type=ChatType.DIRECTOR`
- [x]Settings session (`ChatType.SETTINGS`) auto-created on first system access for a user (like "Main")
- [x]When CEO sends message to Settings session, Director built with formation-mode instructions (when `user:formation_status != COMPLETE`) or evolution-mode instructions (when `COMPLETE`)
- [x]Settings session is user-scoped (not project-scoped) and always available
- [x]Chat message send and Director response publish audit events to Redis Stream (NFR-5b.07)
- [x]On Director processing failure (agent build error, worker unavailable): error response persisted in chat message history, error event published
- [x]Chat message routing completes within 30 seconds under normal LLM latency
- [x]`run_director_turn` registered in `WorkerSettings.functions` (in `settings.py`)
- [x]`POST /chat/{session_id}/messages` and `GET /chat/{session_id}/messages` routes already exist — verify they work correctly with real Director (may need minor adjustments)
**Validation:**
- `uv run pyright app/gateway/routes/chat.py app/workers/tasks.py app/workers/settings.py`
- `uv run pytest tests/gateway/test_chat.py tests/workers/test_director_turn.py -v`

---

### P5b.D9: Context Recreation Pipeline
**Files:** `app/agents/context_recreation.py`, `app/agents/pipeline.py`
**Depends on:** P5b.D4, P5b.D6
**Description:** Implement the 4-step context recreation pipeline triggered when ContextRecreationRequired is raised during pipeline execution. Step 1 (persist): save important state to memory service. Step 2 (seed): copy critical state keys to new session. Step 3 (fresh session): create new ADK session with seeded state. Step 4 (reassemble): reconstruct agent context via InstructionAssembler, SkillLoaderAgent, and MemoryLoaderAgent. Rebuild pipeline with only remaining stages. Degraded mode: proceed without cross-session memory (Phase 9).
**BOM Components:**
- [x]`A59` — Context recreation mechanism
- [x]`CT05` — Context recreation pipeline (persist → seed → fresh session → reassemble)
**Requirements:**
- [x]`recreate_context(session_service, old_session, pipeline_context)` orchestrates the 4-step process
- [x]When ContextRecreationRequired raised during pipeline execution, worker catches it at pipeline level and initiates recreation
- [x]**Persist step**: saves progress markers, accumulated decisions, current plan, learnings to memory service. State keys already durable via DatabaseSessionService are not re-persisted
- [x]**Seed step**: copies critical keys from old session to new session: deliverable status, batch position, hard limits, loaded_skill_names, agent output_keys from completed stages. Conversation history intentionally NOT seeded
- [x]**Fresh session step**: creates new ADK session with seeded state. Old session preserved in DB (not deleted), no longer active
- [x]**Reassemble step**: InstructionAssembler recomposes instructions from fragments (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL). SkillLoaderAgent reloads skills. MemoryLoaderAgent attempts memory restore
- [x]When MemoryService unavailable (degraded mode — expected in Phase 5b): proceeds with state + skills + instruction fragments only. System reminder injected noting memory context unavailable
- [x]After recreation: pipeline rebuilt containing only remaining (not-yet-completed) stages. Completion determined from persisted deliverable state keys, not ADK events
- [x]No completed stages re-execute. No state is lost
- [x]On recreation failure (session creation error, seed failure, reassembly error): error event published, pipeline fails with clear error. No silent continuation with corrupted session
- [x]Context recreation initiation and completion (success or failure) publish audit events to Redis Stream with session IDs, stage reached, and outcome (NFR-5b.07)
- [x]Context recreation completes within 10 seconds (excluding LLM calls during reassembly)
- [x]`rebuild_reduced_pipeline(registry, completed_stages, ctx)` constructs a DeliverablePipeline with only remaining stages
- [x]`app/agents/pipeline.py` modified to support partial pipeline construction (accepts list of stages to include)
**Validation:**
- `uv run pyright app/agents/context_recreation.py app/agents/pipeline.py`
- `uv run pytest tests/agents/test_context_recreation.py -v`
- `uv run ruff check . && uv run pyright && uv run pytest` (full quality gates)

---

## Build Order

```
Batch 1 (parallel): P5b.D1, P5b.D2, P5b.D3, P5b.D4
  D1: State key authorization — app/events/publisher.py
  D2: CEO queue routes — app/gateway/routes/ceo_queue.py, models/ceo_queue.py, db/models.py, main.py
  D3: Director formation + system reminders — app/agents/formation.py, app/agents/state_helpers.py
  D4: Supervision callbacks — app/agents/supervision.py

Batch 2 (sequential): P5b.D5
  D5: Director-PM delegation & hard limits — app/workers/tasks.py, adk.py (depends on D3, D4)

Batch 3 (parallel): P5b.D6, P5b.D7, P5b.D8
  D6: PM autonomous loop — app/workers/tasks.py (depends on D4, D5)
  D7: Director queue processing — app/workers/tasks.py, settings.py (depends on D5)
  D8: Chat integration & "Main" — app/gateway/routes/chat.py, workers/tasks.py, settings.py (depends on D5)

Batch 4 (sequential): P5b.D9
  D9: Context recreation pipeline — app/agents/context_recreation.py, pipeline.py (depends on D4, D6)
```

## Completion Contract Traceability

### FRD Coverage

| Capability | FRD Requirement | Deliverable(s) |
|---|---|---|
| CAP-1: Hierarchical Delegation & Governance | FR-5b.01 | P5b.D5 |
| *(same)* | FR-5b.02 | P5b.D5 |
| *(same)* | FR-5b.03 | P5b.D5 |
| *(same)* | FR-5b.04 | P5b.D7 |
| *(same)* | FR-5b.05 | P5b.D3 |
| *(same)* | FR-5b.06 | P5b.D3 |
| *(same)* | FR-5b.06a | P5b.D3, P5b.D8 |
| *(same)* | FR-5b.06b | P5b.D3 |
| *(same)* | FR-5b.06c | P5b.D3 |
| *(same)* | FR-5b.07 | P5b.D8 |
| *(same)* | FR-5b.08 | P5b.D5 |
| *(same)* | FR-5b.08a | P5b.D5 |
| *(same)* | FR-5b.09 | P5b.D5 |
| *(same)* | FR-5b.10 | P5b.D5 |
| *(same)* | FR-5b.10a | P5b.D7 |
| *(same)* | FR-5b.10b | P5b.D7 |
| *(same)* | FR-5b.11 | P5b.D5 |
| CAP-2: PM Autonomous Loop | FR-5b.12 | P5b.D6 |
| *(same)* | FR-5b.13 | P5b.D6 |
| *(same)* | FR-5b.14 | P5b.D6 |
| *(same)* | FR-5b.15 | P5b.D6 |
| *(same)* | FR-5b.16 | P5b.D6 |
| *(same)* | FR-5b.17 | P5b.D6 |
| *(same)* | FR-5b.18 | P5b.D6 |
| *(same)* | FR-5b.19 | P5b.D6 |
| CAP-3: CEO Queue Operations | FR-5b.20 | P5b.D2 |
| *(same)* | FR-5b.21 | P5b.D2 |
| *(same)* | FR-5b.22 | P5b.D2 |
| *(same)* | FR-5b.23 | P5b.D2, P5b.D6 |
| *(same)* | FR-5b.24 | P5b.D2, P5b.D6 |
| *(same)* | FR-5b.25 | P5b.D2 |
| *(same)* | FR-5b.26 | P5b.D2 |
| *(same)* | FR-5b.27 | P5b.D2 |
| CAP-4: Director Chat Interface | FR-5b.28 | P5b.D8 |
| *(same)* | FR-5b.29 | P5b.D8 |
| *(same)* | FR-5b.30 | P5b.D8 |
| *(same)* | FR-5b.31 | P5b.D8 |
| *(same)* | FR-5b.32 | P5b.D8 |
| *(same)* | FR-5b.33 | P5b.D8 |
| CAP-5: Context Recreation Pipeline | FR-5b.34 | P5b.D9 |
| *(same)* | FR-5b.35 | P5b.D9 |
| *(same)* | FR-5b.36 | P5b.D9 |
| *(same)* | FR-5b.37 | P5b.D9 |
| *(same)* | FR-5b.38 | P5b.D9 |
| *(same)* | FR-5b.39 | P5b.D9 |
| *(same)* | FR-5b.40 | P5b.D9 |
| *(same)* | FR-5b.41 | P5b.D9 |
| CAP-6: State Key Authorization | FR-5b.42 | P5b.D1 |
| *(same)* | FR-5b.43 | P5b.D1 |
| *(same)* | FR-5b.44 | P5b.D1 |
| *(same)* | FR-5b.45 | P5b.D1 |
| *(same)* | FR-5b.46 | P5b.D1 |
| CAP-7: Supervision & Reminders | FR-5b.47 | P5b.D4 |
| *(same)* | FR-5b.48 | P5b.D4 |
| *(same)* | FR-5b.49 | P5b.D4 |
| *(same)* | FR-5b.50 | P5b.D4 |
| *(same)* | FR-5b.51 | P5b.D3 |
| *(same)* | FR-5b.52 | P5b.D3 |
| *(same)* | FR-5b.53 | P5b.D3 |

*59 FRD requirements, 59 mapped. Zero uncovered.*

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| A79 | State key authorization (tier prefixes, EventPublisher ACL) | P5b.D1 |
| G12 | `GET /ceo/queue` route | P5b.D2 |
| G13 | `PATCH /ceo/queue/{id}` route | P5b.D2 |
| V18 | CEO resolved approval → session state writeback | P5b.D2 |
| A08 | Director formation artifacts (`user:` scope) | P5b.D3 |
| A09 | Director formation logic (Settings conversation) | P5b.D3 |
| A58 | System reminder injection (`before_model_callback`) | P5b.D3 |
| A14 | `before_agent_callback` (Director supervision) | P5b.D4 |
| A15 | `after_agent_callback` (Director supervision) | P5b.D4 |
| A40 | `verify_batch_completion` (`after_agent_callback`) | P5b.D4 |
| A41 | `checkpoint_project` (`after_agent_callback`) | P5b.D4 |
| A05 | Director → PM delegation (`transfer_to_agent`) | P5b.D5 |
| A06 | PM → Director escalation (`transfer_to_agent`) | P5b.D5 |
| A07 | Hard limits cascade (CEO → Director → PM → Workers) | P5b.D5 |
| A16 | Director queue consumption | P5b.D7 |
| G10 | `POST /chat/{session_id}/messages` route | P5b.D8 |
| G11 | `GET /chat/{session_id}/messages` route | P5b.D8 |
| A70 | Chat session model (per-message `runner.run_async`) | P5b.D8 |
| A13 | Director "Main" project (permanent chat session) | P5b.D8 |
| A59 | Context recreation mechanism | P5b.D9 |
| CT05 | Context recreation pipeline | P5b.D9 |

*21 BOM components, 21 mapped. Zero unmapped.*

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | Director agent operates as root_agent (stateless config, recreated per invocation) | P5b.D5 | `pytest tests/workers/ -k director_stateless` |
| 2 | PM agent manages a project autonomously via tools + deterministic callbacks (`checkpoint_project`, `verify_batch_completion`), escalating only when necessary | P5b.D4, P5b.D6 | `pytest tests/workers/test_pm_loop.py` |
| 3 | PM loop (sequential mode): PM reasons correctly between batches — queries results, decides next batch composition, maintains coherent state across batch boundaries (2+ deliverables); Phase 8 adds parallel execution | P5b.D6 | `pytest tests/workers/test_pm_loop.py -k multi_batch` |
| 4 | Director → PM delegation and PM → Director escalation via transfer_to_agent | P5b.D5 | `pytest tests/workers/ -k delegation` |
| 5 | Context recreation produces a functional session with equivalent agent context (persist → fresh session → reassemble end-to-end) in degraded mode | P5b.D9 | `pytest tests/agents/test_context_recreation.py -k end_to_end` |
| 6 | State key writes with tier prefix rejected when author tier does not match prefix | P5b.D1 | `pytest tests/events/test_publisher.py -k tier_auth` |
| 7 | CEO queue items created, queried, and resolved via gateway routes | P5b.D2 | `pytest tests/gateway/test_ceo_queue.py` |
| 8 | CEO queue approval resolution written back to session state | P5b.D2 | `pytest tests/gateway/test_ceo_queue.py -k approval_writeback` |
| 9 | Chat messages routed to Director via worker and response persisted | P5b.D8 | `pytest tests/gateway/test_chat.py -k director_response` |
| 10 | Director formation via Settings conversation produces three structured artifacts in user: scope state | P5b.D3 | `pytest tests/agents/test_formation.py` |

*10 contract items, 10 covered. Zero uncovered.*

## Research Notes

### ADK transfer_to_agent Semantics
The Director's `sub_agents` list contains the PM agent. When the Director instruction says to delegate, it uses `transfer_to_agent` targeting the PM by name. ADK moves execution context to the PM within the same runner. The PM can transfer back to the Director. Verify in `.dev/.knowledge/adk/` whether `transfer_to_agent` preserves the full session state across transfers or if there are state scope restrictions.

### ADK Callback State Writes
Callback functions (`before_agent_callback`, `after_agent_callback`) receive `CallbackContext` which has a `state` property. Verify in `.dev/.knowledge/adk/ERRATA.md` whether `ctx.state["key"] = val` in callbacks persists (unlike `_run_async_impl` where it doesn't). The Phase 1 finding says direct writes in `_run_async_impl` don't persist, but callbacks may use a different code path.

### ADK LoopAgent Termination (from 5a)
The ReviewCycle termination mechanism depends on the ADK LoopAgent API. If LoopAgent doesn't support custom termination functions, Phase 5a wraps it in a CustomAgent. Phase 5b's context recreation (D9) needs to know the actual pipeline shape to rebuild reduced pipelines. Implementer must verify the pipeline shape established by 5a before implementing `rebuild_reduced_pipeline`.

### CEO Queue Concurrent Session Access
When the gateway writes approval resolution to session state, the PM may be mid-execution. DatabaseSessionService uses PostgreSQL — concurrent reads/writes are handled by database-level isolation. The approval key pattern (`approval:{id}`) targets a dedicated namespace that the PM only reads during batch selection (between turns), not during active LLM calls. This timing avoids read-during-write conflicts.

### Director Queue ARQ Cron Configuration
ARQ cron jobs use `arq.cron(func, second=N)` for minute-level scheduling. For configurable intervals, use `arq.cron(func, second={0, interval, 2*interval, ...})` to approximate the desired frequency, or use a single cron entry that checks elapsed time internally. The simpler approach: run cron every 60s (default) and make the function check a settings-driven interval internally.

### Existing Chat Route Stubs
The chat routes (`POST /chat/{session_id}/messages`, `GET /chat/{session_id}/messages`) already exist and work — they enqueue `run_director_turn` which uses an echo stub. D8 replaces the stub with the real Director agent. The route logic itself may not need changes; the modification is primarily in `run_director_turn` in `tasks.py`.

### System Reminder Injection Mechanism
The `before_model_callback` receives `LlmRequest` which contains the conversation messages. System reminders can be injected by appending a system message to the request's messages list. Verify in `.dev/.knowledge/adk/` whether `LlmRequest.messages` is mutable and whether injecting additional messages breaks ADK's internal tracking. Alternative: use a `{system_reminders}` state template in the agent's instructions (simpler but less dynamic).

---

*Document Version: 1.0.0*
*Phase: 5b — Supervision & Integration*
*Last Updated: 2026-03-11*
