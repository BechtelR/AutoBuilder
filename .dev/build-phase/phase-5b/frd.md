# Phase 5b FRD: Supervision & Integration
*Generated: 2026-03-10*

## Objective

Make the supervision hierarchy operational and connect the CEO to the system. Before this phase, agents and pipelines exist (5a) but nobody supervises them and the CEO can't interact. Phase 5b wires Director<>PM delegation, the CEO queue, chat interface, context recreation, and state key authorization -- making AutoBuilder an interactive, supervised autonomous system. Traces to PR-13, PR-14, PR-15, PR-15a, PR-17, PR-18, PR-20, NFR-4c.

## Consumer Roles

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| CEO (End User) | The human user who interacts as ultimate authority -- chats with Director, resolves escalations, observes project status | Chat message sent -> Director response received and persisted; CEO queue item viewed -> resolved -> suspended execution path resumes |
| System (Supervision Runtime) | The AutoBuilder runtime that manages agent hierarchy, enforces governance limits, handles context lifecycle, and bridges chat/work sessions | Director created per invocation -> delegates to PM -> PM executes autonomously -> escalation flows correctly; context budget exceeded -> recreation succeeds -> agent resumes with equivalent context (excluding cross-session memory) |
| Developer (Operator) | The person who seeds Director personality, configures project limits, and inspects diagnostic/supervision state | Personality config seeded -> Director exhibits personality in CEO interactions; hard limits in project config -> enforced at every tier via supervision callbacks |

## Appetite

M size: ~3-5 days. 21 BOM components. Most are thin wiring -- gateway routes, callbacks, delegation plumbing. Critical path: context recreation pipeline (CAP-5) and PM loop (CAP-2). The CEO queue routes and chat routing are straightforward CRUD + job enqueueing.

## Prerequisites

- Phase 5a complete: all agents defined as declarative files, AgentRegistry and InstructionAssembler operational, DeliverablePipeline executes a single deliverable end-to-end, ContextBudgetMonitor raises ContextRecreationRequired, NullSkillLibrary and InMemoryMemoryService stubs in place
- DB tables created in 5a: `ceo_queue`, `director_queue`, `project_configs` (with Alembic migrations)
- CEO queue enums (type, priority, status) defined in 5a; Director queue enums defined in Phase 4

## Capabilities

### CAP-1: Hierarchical Delegation & Governance

The Director operates as the root agent -- stateless configuration, recreated fresh on each invocation. It delegates projects to PMs via agent transfer and receives escalations back. The Director processes its own queue (Director Queue) on a regular interval, resolving PM escalations or forwarding them to the CEO queue. Hard limits cascade from CEO through Director to PM to Workers, enforced at each tier. The Director's personality is seeded from a configuration file into cross-session state and evolves over time. A permanent "Main" chat session provides the CEO's portfolio-level conversation context.

**Requirements:**

- [ ] **FR-5b.01**: When the system invokes the Director, it builds the Director agent from its definition file with a stateless configuration -- no in-memory state carried from prior invocations. All continuity comes from database-backed session state.
- [ ] **FR-5b.02**: When the Director receives a project delegation, it delegates execution authority to the project's PM agent. The PM receives full execution authority for that project.
- [ ] **FR-5b.03**: When the PM encounters a condition it cannot resolve, it returns execution authority to the Director with escalation context in session state. The Director evaluates the escalation and either resolves it locally or forwards it to the CEO queue.
- [ ] **FR-5b.04**: When the Director processes its queue (Director Queue), it reads pending items written by PMs via the escalation tool, evaluates each, and either resolves the item (writes resolution to session state) or forwards it to the CEO queue via the CEO escalation tool. Items marked as forwarded are updated to reflect forwarding status.
- [ ] **FR-5b.05**: When the system starts the Director for the first time for a given user, it seeds the Director's personality from a configuration file into the user-scoped state. The personality persists across all sessions for that user and is available via state template injection in the Director's instructions.
- [ ] **FR-5b.06**: When the personality has already been seeded (user-scoped state exists), the system does not re-seed from the configuration file. The existing personality is preserved, allowing it to evolve through interactions.
- [ ] **FR-5b.07**: When the CEO initiates a chat without specifying a project, the system routes the message to the "Main" chat session -- the Director's permanent portfolio-level conversation context. If the "Main" session does not exist, it is created automatically.
- [ ] **FR-5b.08**: When the Director delegates a project to a PM, it writes hard limits (retry budget, cost ceiling) to the project configuration. The PM reads these limits at session start and operates within them. The Director cannot set limits that exceed global limits. The PM cannot set worker constraints that exceed project limits.
- [ ] **FR-5b.08a**: When the Director creates a new project, a project configuration entry is created with default hard limits derived from global limits. If the Director does not explicitly set limits during delegation, the defaults apply. The PM always has a valid configuration to read at session start.
- [ ] **FR-5b.09**: When any tier exhausts a limit dimension (retry budget depleted, cost ceiling hit), the system escalates to the tier above. Retry budget exhaustion triggers escalation. Cost ceiling exhaustion triggers a hard stop and escalation.
- [ ] **FR-5b.10**: When agent transfer from Director to PM fails (PM agent cannot be built, session creation fails), the system publishes an error event and creates a CEO queue item with the failure context. The Director does not silently drop the delegation.
- [ ] **FR-5b.10a**: When no work session is active for a project with pending Director Queue items, an ARQ cron job (`process_director_queue`, configurable interval via `AUTOBUILDER_DIRECTOR_QUEUE_INTERVAL`, default 60s) detects pending items and enqueues a `run_director_turn` job for processing. The cron job skips projects with active work sessions (inline path handles those). The cron function itself is a lightweight DB check — no Director invocation or token cost for empty queues.
- [ ] **FR-5b.10b**: When the Director's supervision callback fires after a PM turn (after_agent_callback), the Director checks the Director Queue inline for pending items before deciding its next action. Queue items are loaded into context alongside PM completion status. This is the fast path — zero additional latency for active work sessions.
- [ ] **FR-5b.11**: When agent transfer from PM back to Director fails, the system publishes an error event. The PM's escalation context is preserved in session state for recovery.

---

### CAP-2: PM Autonomous Loop (Sequential Mode)

The PM manages a project autonomously with reliable inter-batch reasoning, tools, and deterministic safety callbacks. The loop executes a multi-deliverable sequence with tool-driven batch selection, callback-driven checkpointing after each deliverable, and batch verification after completion. The PM reasons between batches -- assessing results, deciding composition for the next batch -- without losing context. Phase 5b runs batches sequentially; Phase 8 extends the same loop with parallel execution and git worktrees.

**Requirements:**

- [ ] **FR-5b.12**: When the PM receives a project with pre-seeded deliverables in session state, it uses the batch selection tool to identify dependency-ready deliverables and composes a batch for execution.
- [ ] **FR-5b.13**: When the PM dispatches a batch, each deliverable in the batch executes through the DeliverablePipeline sequentially. Parallel intra-batch execution is not in scope (Phase 8).
- [ ] **FR-5b.14**: After each deliverable completes in the pipeline, the checkpoint callback fires automatically. The callback persists the deliverable's completion status and pipeline output to durable state. This is not discretionary -- the callback fires regardless of success or failure.
- [ ] **FR-5b.15**: After all deliverables in a batch complete, the batch verification callback fires. It validates that all deliverables reached a terminal state (completed or failed) and logs the batch result.
- [ ] **FR-5b.16**: After a batch completes, the PM reasons about the results using its tools -- querying deliverable statuses, assessing failures, and deciding the composition of the next batch or whether to escalate. This inter-batch reasoning maintains coherence across batch boundaries.
- [ ] **FR-5b.17**: When a deliverable fails and exhausts its retry budget, the PM marks it as failed and continues with unblocked deliverables. The failed deliverable does not block independent work.
- [ ] **FR-5b.18**: When all deliverables are complete (or failed with no remaining unblocked work), the PM transfers control back to the Director with the project result in session state.
- [ ] **FR-5b.19**: When the PM is unable to make progress (all remaining deliverables blocked, no retries available, no reordering possible), it escalates to the Director with context describing the blockage.

---

### CAP-3: CEO Queue Operations

The CEO queue is the single point of contact between the CEO and the system. Items are created by the Director (escalations, approvals, notifications, tasks), queried and filtered by the CEO, and resolved via the gateway. When an approval is resolved, the resolution is written back to the relevant session state so the PM can discover it on its next batch selection and resume the previously blocked path.

**Requirements:**

- [ ] **FR-5b.20**: When the CEO queries the queue, the system returns all items matching the requested filters (type, priority, status). Items are ordered by priority (descending) then creation time (ascending).
- [ ] **FR-5b.21**: When the CEO resolves a queue item, the system updates the item's status and records the resolution, the resolver identity, and the resolution timestamp.
- [ ] **FR-5b.22**: When the CEO resolves an approval-type queue item, the system writes the resolution to a dedicated approval resolution key in the originating project's session state. The write targets a well-known key pattern that the PM polls during batch selection — it does not mutate arbitrary state while the PM may be mid-turn. The queue item's source project reference locates the correct session.
- [ ] **FR-5b.23**: When the PM next selects a batch after an approval resolution, the previously blocked deliverable becomes eligible if its only blocker was the pending approval. The PM discovers the resolution through session state -- there is no active push.
- [ ] **FR-5b.24**: When the PM has no unblocked work remaining and is waiting for an approval, the PM returns control to the Director with a suspended status indicating pending approvals. The work session's ARQ job completes. When the CEO resolves the approval, the system enqueues a new work session to resume execution.
- [ ] **FR-5b.25**: When the CEO dismisses a queue item, the system updates the item's status to dismissed and records the dismissal. Dismissed items do not trigger writeback.
- [ ] **FR-5b.26**: When the CEO attempts to resolve a queue item that is already resolved or dismissed, the system rejects the request with a conflict indication.
- [ ] **FR-5b.27**: When a queue item references a session that no longer exists (project deleted, session expired), the resolution succeeds (item marked resolved) but the state writeback is skipped with a warning event.

---

### CAP-4: Director Chat Interface

The CEO communicates with the Director through chat sessions -- sending messages, receiving responses, and observing project status. Messages are routed to the Director agent via a worker, and the Director's response is persisted for retrieval. Multiple chat sessions exist per project. The Director in a chat session can access work session data through shared state scopes (cross-session bridge), enabling accurate status reporting without interrupting autonomous execution.

**Requirements:**

- [ ] **FR-5b.28**: When the CEO sends a chat message, the system persists the message, routes it to the Director agent via a worker invocation, and persists the Director's response. The response is retrievable via the message history.
- [ ] **FR-5b.29**: When the CEO retrieves message history for a chat session, the system returns all messages in chronological order, including both CEO messages and Director responses.
- [ ] **FR-5b.30**: When the Director handles a chat message, it has access to the chat session's conversation history, user-scoped state (personality, preferences), and app-scoped state (project status, deliverable summaries, batch progress). This enables the Director to answer status questions using data written by active work sessions without interrupting them.
- [ ] **FR-5b.31**: When a chat message is sent for a project that has an active work session, the Director can read work session status from shared state. The chat invocation does not block, interrupt, or modify the running work session.
- [ ] **FR-5b.32**: When the system routes a chat message to the Director, it uses per-message invocation -- one worker call per message, not a long-running session. Each invocation builds a fresh Director agent from its definition file.
- [ ] **FR-5b.33**: When the Director cannot process a message (agent build failure, worker unavailable), the system persists an error response in the chat message history and publishes an error event.

---

### CAP-5: Context Recreation Pipeline

When a long-running agent session approaches its context window limit, the system recreates the session from durable state rather than applying lossy compaction. The ContextBudgetMonitor (from 5a) raises the signal; Phase 5b catches it and executes the 4-step recreation: persist important state, seed critical keys to a new session, create a fresh session, and reassemble context from durable stores. In Phase 5b, recreation operates in degraded mode -- cross-session memory is unavailable (no real MemoryService until Phase 9). Equivalence is defined as: state keys + skills + instruction fragments preserved. Full equivalence (including cross-session memory) is verified in Phase 9.

**Requirements:**

- [ ] **FR-5b.34**: When the ContextRecreationRequired exception is raised during pipeline execution, the worker catches it at the pipeline level and initiates the 4-step recreation process. The pipeline does not crash or abort.
- [ ] **FR-5b.35**: During the persist step, the system identifies and saves important state to the memory service -- progress markers, accumulated decisions, current plan, and learnings. State keys that are already durable via the database-backed session service are not re-persisted.
- [ ] **FR-5b.36**: During the seed step, the system copies critical state keys from the old session to the new session. Critical keys include: deliverable status, batch position, hard limits, loaded skill names, and agent output keys from all completed pipeline stages. Conversation history is intentionally not seeded -- this is the purpose of recreation.
- [ ] **FR-5b.37**: During the fresh session step, the system creates a new session with the seeded state. The old session is preserved in the database (not deleted) but is no longer the active session for the pipeline.
- [ ] **FR-5b.38**: During the reassemble step, the system reconstructs the agent's context: the InstructionAssembler composes instructions from fragments (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL), the SkillLoaderAgent reloads skills, and the MemoryLoaderAgent attempts to restore cross-session context.
- [ ] **FR-5b.39**: When the MemoryService is unavailable during reassembly (degraded mode -- the expected state in Phase 5b), the system proceeds with state + skills + instruction fragments only. A system reminder is injected noting that memory context is unavailable. The pipeline continues without cross-session memory.
- [ ] **FR-5b.40**: After recreation completes, the system reconstructs the pipeline containing only the stages that have not yet completed. Completion status is determined from persisted deliverable state keys, not from ADK agent state (which is lost with the old session's events). No completed stages re-execute. No state is lost.
- [ ] **FR-5b.41**: When recreation fails (session creation error, seed failure, reassembly error), the system publishes an error event with the failure context and the pipeline fails with a clear error. It does not silently continue with a corrupted session.

---

### CAP-6: State Key Authorization

State writes are governed by tier-based access control. Keys with tier prefixes (director:, pm:, worker:) are writable only by agents at or above the matching tier. Non-prefixed keys are shared workspace accessible by all tiers. Reads are unrestricted -- any tier can read any key. Violations reject the entire state delta atomically and produce a visible error event.

**Requirements:**

- [ ] **FR-5b.42**: When an agent yields a state delta containing a key with a tier prefix, the system validates that the agent's tier has write permission for that prefix. Director-prefixed keys are writable only by Director-tier agents. PM-prefixed keys are writable by PM-tier and Director-tier agents. Worker-prefixed keys are writable by all tiers.
- [ ] **FR-5b.43**: When a state delta contains a key that violates tier authorization, the system rejects the entire state delta -- no partial application. None of the keys in the delta are applied, including valid ones.
- [ ] **FR-5b.44**: When a state delta is rejected, the system publishes an error event to the event stream. The event includes: the rejected key, the author agent's tier, the required tier, and the full list of keys in the rejected delta. The originating agent receives an error indication.
- [ ] **FR-5b.45**: When an agent reads a state key with any tier prefix, the read succeeds regardless of the agent's tier. Reads are unrestricted. A worker reading a director-prefixed key to understand governance constraints is correct behavior.
- [ ] **FR-5b.46**: When a state delta contains only non-prefixed keys (shared workspace), the write succeeds for any tier. Non-prefixed keys are the primary communication mechanism within a pipeline.

---

### CAP-7: Supervision Callbacks & System Reminders

The Director observes PM execution through supervision callbacks attached to PM agents. A before-execution callback checks governance constraints and can block PM execution if limits are exceeded. An after-execution callback captures PM completion status and detects escalation signals. System reminders inject ephemeral governance nudges into the conversation before each LLM call -- token budget warnings, state change notifications, progress notes. Reminders are acceptable to lose during context recreation.

**Requirements:**

- [ ] **FR-5b.47**: Before the PM agent executes, a supervision callback checks the project's hard limits (cost ceiling, retry budget) against current usage. If a limit is exceeded, the callback blocks PM execution and returns a response indicating the exceeded limit and required escalation.
- [ ] **FR-5b.48**: Before the PM agent executes, the supervision callback logs a supervision event to the event stream, recording the PM invocation with project context.
- [ ] **FR-5b.49**: After the PM agent completes a turn, a supervision callback captures the PM's completion status from session state and publishes a status event to the event stream.
- [ ] **FR-5b.50**: After the PM agent completes a turn, the supervision callback detects escalation signals in session state (e.g., the PM wrote escalation context indicating it cannot proceed). The callback does not resolve escalations -- it makes them observable.
- [ ] **FR-5b.51**: Before each LLM call for any agent, the system injects ephemeral system reminders into the conversation. Reminders include: current context budget usage percentage, state change notifications from other agents, and progress summaries.
- [ ] **FR-5b.52**: When the system has no relevant reminders to inject, the before-call hook executes without modification -- it does not inject empty or placeholder content.
- [ ] **FR-5b.53**: System reminders are transient and are not persisted to durable state. During context recreation, reminders from the old session are lost. This is by design -- reminders reflect transient conditions, not durable governance rules.

## Non-Functional Requirements

- [ ] **NFR-5b.01**: Chat message routing (CEO sends message -> Director response persisted) completes within 30 seconds under normal LLM latency. The system does not add meaningful overhead beyond LLM call time.
- [ ] **NFR-5b.02**: CEO queue query operations complete within 200ms for up to 1000 queue items.
- [ ] **NFR-5b.03**: State key authorization validation adds no more than 1ms overhead per state delta. The validation is a synchronous prefix check, not a database lookup.
- [ ] **NFR-5b.04**: Context recreation completes within 10 seconds (excluding LLM calls during reassembly). The 4-step process is dominated by session creation and state seeding, not computation.
- [ ] **NFR-5b.05**: All quality gates pass (ruff check, pyright strict, pytest) with the complete supervision system. Zero type: ignore exceptions without documented rationale.
- [ ] **NFR-5b.06**: Supervision callbacks (before/after agent) add no more than 5ms overhead per PM invocation. Callbacks are lightweight state checks and event publishes, not LLM calls.
- [ ] **NFR-5b.07**: All significant state transitions produce an immutable audit event in the event stream: CEO queue item creation/resolution/dismissal, chat message send/receive, state key authorization violations, context recreation initiation/completion, Director-PM delegation/escalation, and supervision callback outcomes. No state change is silent.

## Rabbit Holes

- **ADK transfer_to_agent semantics**: The exact mechanism for Director->PM delegation depends on ADK's `transfer_to_agent` behavior. Verify: does transfer_to_agent work across different agent types (LlmAgent to LlmAgent)? Does it preserve session state? Does it work within a SequentialAgent or only at the root level? Test this early -- delegation is the critical path.

- **CEO queue writeback timing**: When the gateway writes an approval resolution to session state via DatabaseSessionService, the PM may be mid-execution in the same session. Verify: does DatabaseSessionService handle concurrent reads and writes safely? Does a state write from the gateway appear in the PM's next state read, or does the PM have a cached copy? If the PM caches state, the writeback pattern needs adjustment.

- **Context recreation resumption point**: After creating a fresh session and reassembling context, the pipeline must resume from the correct logical point. ADK's SequentialAgent tracks stage progress via events in the session — a fresh session has no events, so SequentialAgent restarts from the beginning. The correct approach is to rebuild the pipeline containing only the remaining stages, determined from persisted deliverable state keys. This is architecturally sound but requires the recreation handler to construct a reduced pipeline dynamically.

- **PM loop statefulness across batches**: The PM is an LlmAgent reasoning across multiple batch cycles within a single work session. Its conversation history grows with each batch. The ContextBudgetMonitor will eventually trigger recreation mid-PM-loop. Verify: after recreation, can the PM resume its loop coherently? Does it need special "where was I" state keys beyond deliverable statuses?

- **System reminder injection mechanism**: ADK's before_model_callback receives the LlmRequest. Verify: can you inject additional content (system reminders) into the request without breaking ADK's internal state tracking? Or should reminders be injected via a different mechanism (e.g., writing to a state key that's referenced via {key} template)?

- **Pipeline stage list discrepancy (5a FRD vs architecture)**: The 5a FRD pipeline includes FormatterAgent in the stage list, but the architecture reference (agents.md) does not. Context recreation (FR-5b.40) must rebuild the pipeline with only remaining stages — it needs to know the canonical stage list. Resolve the discrepancy during 5a build or early in 5b. The correct pipeline shape is the single source of truth for recreation.

- **Director Queue processing trigger (Resolved — Decision #67)**: Hybrid: inline check during work sessions (after PM turns via supervision callback — zero latency, zero token cost for empty queue) + ARQ cron fallback for idle periods (configurable interval, default 60s, only invokes Director if pending items exist). Both paths converge on the same `run_director_turn` mechanism. Deduplication: if a work session is already active for a project, cron skips it (use Redis lock `director:work_session:{project_id}`). Settings: `AUTOBUILDER_DIRECTOR_QUEUE_INTERVAL`.

## No-Gos

- **No parallel batch execution**: Phase 5b runs deliverables sequentially within batches. ParallelAgent for intra-batch parallelism is Phase 8.
- **No spec decomposition**: Phase 5b uses pre-seeded deliverables. Spec parsing and deliverable decomposition is Phase 8.
- **No git worktree isolation**: Filesystem isolation for parallel execution is Phase 8.
- **No real MemoryService**: Context recreation runs in degraded mode. PostgresMemoryService with tsvector/pgvector is Phase 9. Full equivalence verification is a Phase 9 contract item.
- **No real SkillLibrary**: Skills load via NullSkillLibrary (empty results). Trigger matching, two-tier scan, and Redis cache are Phase 6.
- **No SSE streaming for CEO queue**: The SSE endpoint for real-time CEO queue push notifications (G14) is Phase 10. Phase 5b provides polling via the query route.
- **No webhook notifications**: Notification delivery for unresolved CEO queue items via webhooks/email/Slack is Phase 10.
- **No tool_role ceiling validation**: Requires WORKFLOW.yaml which is Phase 7.
- **No RegressionTestAgent integration**: Agent definition exists from 5a, but batch-level regression testing is Phase 8.
- **No Director governance tools**: Advanced governance tooling (tool authoring, CEO approval gates) is Phase 13+.
- **No adaptive LLM routing**: Cost/latency-aware model selection is Phase 11.
- **No batch failure threshold (PR-16)**: Requires real batch execution to trigger consecutive failure counting. The supervision callback infrastructure is wired (FR-5b.47–50); the batch failure counter and threshold logic are entirely Phase 8.

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-5b.01, FR-5b.02, FR-5b.03, FR-5b.10, FR-5b.11 | PR-13: Director as executive partner | Supervision |
| FR-5b.04, FR-5b.10a, FR-5b.10b | PR-18: Director Queue for PM escalations | Supervision |
| FR-5b.05, FR-5b.06 | PR-13: Director as executive partner — personality enables the Director's distinct identity and conversational continuity | Personality |
| FR-5b.07 | PR-13: Primary Director session for portfolio-level conversation | Chat |
| FR-5b.08, FR-5b.08a, FR-5b.09 | PR-15: Bounded authority -- retry budget, decision scope, cost ceiling; limits cascade | Governance |
| FR-5b.12, FR-5b.13, FR-5b.14, FR-5b.15, FR-5b.16 | PR-10: PM execution loop -- select batch, dispatch, collect, repeat; PR-14: PM owns delivery loop | PM Loop |
| FR-5b.17, FR-5b.18, FR-5b.19 | PR-14: PM escalates only when necessary; PR-12: Failed deliverable escalation chain | PM Loop |
| FR-5b.20, FR-5b.21, FR-5b.25, FR-5b.26, FR-5b.27 | PR-17: CEO queue -- single point of contact | CEO Queue |
| FR-5b.22, FR-5b.23, FR-5b.24 | PR-20: Resolving CEO queue item resumes suspended path | CEO Queue |
| FR-5b.28, FR-5b.29, FR-5b.30, FR-5b.31, FR-5b.32, FR-5b.33 | PR-13: Director maintains per-project chat sessions | Chat |
| FR-5b.34, FR-5b.35, FR-5b.36, FR-5b.37, FR-5b.38, FR-5b.39, FR-5b.40, FR-5b.41 | PR-15a: Context recreation -- persist, fresh session, reassemble, no lossy summarization | Context |
| FR-5b.42, FR-5b.43, FR-5b.44, FR-5b.45, FR-5b.46 | NFR-4c: State key authorization -- tier-based write access | Security |
| FR-5b.47, FR-5b.48, FR-5b.49, FR-5b.50 | PR-15: Bounded authority enforced at each tier; PR-14: PM under Director supervision | Supervision |
| FR-5b.51, FR-5b.52, FR-5b.53 | PR-15: Bounded authority -- context budget awareness | Context |
| NFR-5b.01 | NFR-2: System overhead not meaningful contributor | Performance |
| NFR-5b.02 | NFR-1: Status queries feel instantaneous | Performance |
| NFR-5b.03 | NFR-2: System overhead not meaningful contributor | Performance |
| NFR-5b.04 | PR-15a: Context recreation without lossy summarization | Performance |
| NFR-5b.05 | NFR-5: Quality gates | Engineering |
| NFR-5b.06 | NFR-2: System overhead not meaningful contributor | Performance |
| NFR-5b.07 | NFR-4: All state transitions produce an immutable audit event; PR-35: Immutable audit log | Auditability |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | Director agent operates as root_agent (stateless config, recreated per invocation) | CAP-1: FR-5b.01 |
| 2 | PM agent manages a project autonomously via tools + deterministic safety mechanisms (`checkpoint_project`, `verify_batch_completion`), escalating only when necessary | CAP-2: FR-5b.12, FR-5b.14, FR-5b.15, FR-5b.17, FR-5b.19 |
| 3 | PM loop (sequential mode): PM reasons correctly between batches — queries results, decides next batch composition, maintains coherent state across batch boundaries (2+ deliverables); Phase 8 adds parallel execution | CAP-2: FR-5b.12, FR-5b.13, FR-5b.14, FR-5b.15, FR-5b.16, FR-5b.18 |
| 4 | Director -> PM delegation and PM -> Director escalation via transfer_to_agent | CAP-1: FR-5b.02, FR-5b.03 |
| 5 | Context recreation produces a functional session with equivalent agent context (persist -> fresh session -> reassemble end-to-end) in degraded mode | CAP-5: FR-5b.34, FR-5b.35, FR-5b.36, FR-5b.37, FR-5b.38, FR-5b.39, FR-5b.40 |
| 6 | State key writes with tier prefix rejected when author tier does not match prefix | CAP-6: FR-5b.42, FR-5b.43, FR-5b.44 |
| 7 | CEO queue items created, queried, and resolved via gateway routes | CAP-3: FR-5b.20, FR-5b.21, FR-5b.25 |
| 8 | CEO queue approval resolution written back to session state | CAP-3: FR-5b.22, FR-5b.23 |
| 9 | Chat messages routed to Director via worker and response persisted | CAP-4: FR-5b.28, FR-5b.29, FR-5b.32 |
| 10 | Director personality seeded from config into user: scope state | CAP-1: FR-5b.05, FR-5b.06 |

---

*Document Version: 1.3.0*
*Phase: 5b -- Supervision & Integration*
*Last Updated: 2026-03-11*
