# AutoBuilder — Product Requirements Document
*Version: 5.0 | Date: 2026-02-21 | Maps to: `00-VISION.md` v3.0*

---

## How AutoBuilder Works

All work flows through the same pipeline:

```
User → Director → PM → Workers
```

The **Director** is the user's executive interface. It receives work, coordinates across all active projects, and routes to the right PM. The **PM** owns a project end-to-end: plans deliverables, manages the execution loop (select batch → run in parallel → validate → checkpoint → repeat), and escalates genuine blockers. **Workers** execute individual deliverables. Everything that surfaces to the user comes through a single unified queue — the CEO queue.

What varies is how work is initiated. Users arrive at the Director with different starting conditions:

| Mode | Starting Condition |
|------|--------------------|
| **Open-ended** | An idea or goal — the Director shapes it into a structured plan |
| **Spec-driven** | A defined specification ready to execute |
| **Continuation** | An existing project or codebase — the Director establishes context, then executes changes |
| **Delegation** | A bounded task within a known project — routes to the appropriate PM |
| **Process run** | An instance of an encoded repeatable workflow — new inputs, same rigor |

---

## 1. User Personas

### P-1: The Builder
Constructing something — a product, a system, a tool — that didn't exist before. May start with a rough idea or a polished spec. Might have an existing codebase to build on top of.

What they want: define the objective and acceptance criteria, then step away. Return to a verified completion report. Work that spans multiple phases accumulates project memory automatically — conventions established in Phase 1 are in context for Phase 8 without re-entry.

What they can't get elsewhere: trust. Today's autonomous tools produce drift without oversight. AutoBuilder's structural quality gates and three-layer verification let them actually walk away.

### P-2: The Lead
Manages delivery quality across a team. Delegates workstreams — implementation, review, technical analysis — to AutoBuilder the same way they'd delegate to a senior engineer: with standards, acceptance criteria, and an expectation of proof, not assertion.

What they want: a completion report that functions as a delegation receipt — per-deliverable evidence of conformance with defined standards, a decision audit trail, and a clear record of what the system decided autonomously vs. what required human judgment.

What they can't get elsewhere: accountability. No current tool produces verifiable evidence that standards were followed. "Done" is asserted, not proven.

### P-3: The Operator
Runs repeatable, high-value knowledge processes — due diligence, research synthesis, technical audits — where the expertise is in the process design, not the execution of individual instances.

What they want: encode their best process once, then submit new instances without re-coordination. The system gets better at the process over time as workflow memory accumulates — the tenth due diligence run handles edge cases the first run escalated.

What they can't get elsewhere: process fidelity at scale. AI tools automate steps, not end-to-end processes with structural quality gates.

---

## 2. User Journeys

### J-1: Build a New Project
*Personas: P-1, P-2 | Modes: open-ended, spec-driven, continuation*

1. User creates a project: workflow type, objective or spec, acceptance criteria, conventions (coding standards, architecture constraints, model preferences).
2. Director decomposes into a phased execution plan. PM for Phase 1 selects dependency-ready deliverables and dispatches workers in parallel.
3. Workers execute. After each deliverable: mandatory validators run, state checkpoints, regression tests fire per PM policy. PM selects the next batch; repeats until phase complete.
4. A genuine blocker escalates from PM → Director Queue → CEO queue with context, options, and a recommendation.
5. User resolves from the CEO queue. Execution resumes on the blocked path without restart.
6. Phase completes. Completion report: three-layer evidence (correctness, conformance, contract), per-deliverable detail, cost and decision summary.
7. User approves. Project memory persists conventions and decisions for subsequent phases.

*Failure*: Deliverable exhausts retries → CEO queue with validator evidence. User chooses: remediate the specific deliverable (re-executes it and dependents only), redirect the phase, or abort.

---

### J-2: Run a Repeatable Process
*Persona: P-3 | Mode: process run*

1. Operator submits a new project instance: workflow type, input materials, instance-specific overrides.
2. Director routes to a PM. The workflow's encoded agent topology, skill set, and validators apply automatically — no reconfiguration per run.
3. Execution draws on accumulated workflow memory: edge cases from prior runs, domain-specific patterns, quality signals.
4. Ambiguous judgment call → CEO queue. Operator resolves without entering the execution loop.
5. Output delivered in the workflow-defined format. Workflow memory updated with learnings from this run.

*Failure*: Invalid input materials → rejected before execution with a structured error. Mid-run failure → CEO queue with context and options.

---

### J-3: Intervene or Direct Mid-Execution
*Personas: any | Mode: any*

User sends a directive to the Director (via chat or API). Director evaluates scope: if the directive cancels verified work, it surfaces what would be lost to the CEO queue before applying. Otherwise applies immediately, routes updated direction to affected PMs, and logs the intervention to the audit trail.

Director chat is conversational and multi-turn: "Status across active projects" → portfolio summary. "Prioritize Alpha over Beta this week" → Director routes to affected PMs. Chat sessions and autonomous work sessions coexist without interference.

---

## 3. Functional Requirements

### 3.1 Project & Specification

| ID | Requirement |
|----|-------------|
| PR-1 | Projects are created with: workflow type, objective (open-ended or structured), conventions, and acceptance criteria. A **Specification** is a distinct entity — the formal project objective — validated against the workflow's input schema before execution begins. |
| PR-2 | Projects can be paused (suspends at next checkpoint, full state persisted), resumed (restores from checkpoint, no re-execution of verified work), or aborted (terminates, preserves completed work and events, records reason). |
| PR-3 | Project and phase status, active agent tier and current task, event history, pending CEO queue items, and cumulative cost are all accessible at any time. |

### 3.2 Workflow Management

| ID | Requirement |
|----|-------------|
| PR-4 | Workflow plugins install via a WORKFLOW.yaml manifest that defines: agent topology, required skills, mandatory validators, deliverable schema, output format, and memory configuration. Installation requires no core code changes. |
| PR-5 | Project-level conventions override workflow defaults. The workflow manifest is the execution contract — everything the PM needs to run a project of that type. |
| PR-6 | The auto-code workflow ships pre-installed as the platform's reference implementation. |

### 3.3 Execution

| ID | Requirement |
|----|-------------|
| PR-7 | The Director decomposes each submitted specification into a dependency-ordered execution plan without user input. |
| PR-8 | The PM runs a batch execution loop: select dependency-ready deliverables → dispatch in parallel → collect results → run regression tests per PM policy → checkpoint → select next batch → repeat until phase complete. |
| PR-9 | After every deliverable, all validators in the workflow manifest run as mandatory pipeline steps. Validators cannot be skipped or overridden by agent judgment. |
| PR-10 | Failed deliverable: auto-retry to configured limit → escalate to PM → escalate to Director → surface to CEO queue. State is checkpointed after each successful deliverable; a crash cannot cause double-execution of a checkpointed deliverable. |

### 3.4 Agent Hierarchy

| ID | Requirement |
|----|-------------|
| PR-11 | The Director is the user's executive interface: receives work, coordinates across projects, surfaces all items requiring user attention to the CEO queue, and maintains conversational chat alongside autonomous execution. All agents are stateless configuration objects — continuity lives in database-backed sessions, not process memory. |
| PR-12 | Each project has one dedicated PM for its lifetime. The PM owns the delivery loop, quality gate enforcement, and PM-level decisions. Workers execute deliverables under PM supervision and escalate blockers upward — they do not surface directly to the user. |
| PR-13 | Each tier has bounded authority: a **retry budget** (max retries before escalating), a **decision scope** (categories it can resolve autonomously), and a **cost ceiling** (token/spend limit). Exhausting any dimension triggers escalation to the tier above. Limits cascade: user sets project ceiling → Director enforces across projects → PM enforces within the project → workers operate within per-deliverable budgets. |
| PR-14 | When a PM's consecutive batch failures exceed the configured threshold (default: 3), the Director suspends the project and surfaces a diagnostic to the CEO queue. The Director does not attempt autonomous repair. |

### 3.5 CEO Queue & Escalation

| ID | Requirement |
|----|-------------|
| PR-15 | The CEO queue is the single point of contact between the user and the system: decisions, approvals, notifications, and tasks from all active projects — prioritized, real-time. |
| PR-16 | A parallel **Director Queue** handles PM-to-Director escalations (status reports, resource requests, pattern alerts). The Director resolves within its authority; items exceeding its authority elevate to the CEO queue. |
| PR-17 | Each CEO queue decision includes: what the blocker is, the options available, and a recommended resolution with rationale. When an escalation is active, unblocked work continues — only the directly blocked path suspends. |
| PR-18 | Resolving a CEO queue item resumes the suspended path immediately, without restarting the project. |
| PR-19 | Unresolved items trigger a notification via configured channels (webhook, email, Slack) after a configurable timeout (default: 4 hours). Every item is logged with its resolution, who resolved it, and when. |

### 3.6 Completion Reporting

| ID | Requirement |
|----|-------------|
| PR-20 | Completion reports contain three independent verification layers, each requiring machine-generated evidence: **Functional correctness** (validator and test output), **Architectural conformance** (linter, type-checker, or workflow-defined check output), **Contract completion** (deliverable checklist vs. specification acceptance criteria). Assertion alone is insufficient for any layer. |
| PR-21 | Reports include: per-deliverable evidence, cost and token usage by agent tier, wall-clock duration, and a full decision log distinguishing system-autonomous decisions from user-resolved ones. |
| PR-22 | Remediation re-executes only the failed deliverable and its dependents. Verified independent deliverables are not touched. |

### 3.7 Memory

| ID | Requirement |
|----|-------------|
| PR-23 | The system maintains four memory scopes. Write triggers are explicit — memory is not accumulated ambiguously: |
| PR-24 | **Global** — system-wide standards and user preferences. Written by the Director with user approval. |
| PR-25 | **Workflow** — domain expertise accumulated across all projects using a workflow type: recurring failure patterns, quality signals, edge cases observed across runs. Proposed by the PM at project completion, written after Director approval. A new project using a workflow type with accumulated memory receives that expertise from its first deliverable. |
| PR-26 | **Project** — project-specific conventions, architecture decisions, and resolved escalations from prior phases. Written by the PM on phase approval. Automatically available to any subsequent phase of the same project. |
| PR-27 | **Session** — ephemeral execution state for the current run only. At phase completion, the system explicitly extracts learnings and ingests them into the appropriate longer-lived scope via a memory ingestion step. Session state itself is not persisted. |

### 3.8 Skills

| ID | Requirement |
|----|-------------|
| PR-28 | Skills implement the Agent Skills open standard (agentskills.io): a `SKILL.md` file with YAML frontmatter and Markdown instructions, with optional `references/` and `assets/` subdirectories. Skill metadata (~100 tokens) is always available; the full body loads only on activation; reference files load on demand. |
| PR-29 | Skill activation is automatic, matched in priority order: (1) exact `metadata.triggers` match, (2) `metadata.applies_to` pattern match, (3) keyword match against `description`. When no skill matches, execution continues and a warning event is emitted. |
| PR-30 | Third-party skills install without code changes. AutoBuilder extensions use the `metadata.*` namespace per the standard's extension point. `scripts/` execution and `allowed-tools` pre-authorization are capabilities defined by the standard; support is phase-dependent. |

### 3.9 Observability

| ID | Requirement |
|----|-------------|
| PR-31 | Every project has a persistent, replayable event stream (Redis Streams + SSE). Clients reconnect via `Last-Event-ID` with no events lost. The stream covers: agent tier changes, deliverable lifecycle, validator results, escalations, cost per deliverable, checkpoints, and errors. |
| PR-32 | Token usage and cost are tracked per deliverable, phase, and project — in real-time, no manual calculation. An immutable audit log records all state transitions, decisions, escalations, and interventions. |

### 3.10 Interfaces

| ID | Requirement |
|----|-------------|
| PR-33 | The CLI covers the full operational surface: create project, submit spec, check status, stream live events, view CEO queue, send directive, resolve decision, view logs. JSON output for scripting. No dashboard required for any operation. |
| PR-34 | The dashboard provides: project portfolio overview with real-time agent status, live event stream per project (SSE), CEO queue with inline resolution, completion reports with three-layer detail, Director chat panel. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | API response time and SSE latency targets established in Phase 10. Design goal: status queries feel instantaneous locally; events appear within 2 seconds of state change. |
| NFR-2 | A standard workflow phase completes within a working day under normal LLM availability. System overhead is not a meaningful contributor to phase duration. |
| NFR-3 | Crash recovery: worker restarts from last checkpoint without re-executing verified deliverables. LLM provider outages handled via backoff and provider fallback before surfacing as an escalation. |
| NFR-4 | Gateway input validation via Pydantic at all boundaries. Credentials never logged or hardcoded. Tool execution isolated to worker processes. All state transitions produce an immutable audit event. |
| NFR-5 | Third-party workflow plugins and Agent Skills standard skills install without code changes. The gateway API is the sole external contract — internal engine changes do not require client updates. |
| NFR-6 | Runs fully on a single machine with no cloud dependencies. All configuration via environment variables. |

---

## 5. Information Architecture

| Entity | What It Is | User Can |
|--------|-----------|----------|
| **Project** | Top-level unit: workflow type, conventions, phase history, accumulated project memory | Create, view, pause, resume, abort |
| **Specification** | Formal project objective validated before execution | Submit, view status |
| **Workflow** | Plugin defining the complete execution process | Select, install third-party, view |
| **Phase** | Execution segment containing dependency-ordered deliverables (run in parallel batches) | View, approve, remediate |
| **Deliverable** | Atomic work unit: executed, validated, checkpointed | View |
| **CEO Queue Item** | Decision, approval, notification, or task from any project | Resolve, dismiss |
| **Director Queue Item** | PM-to-Director escalation, resolved at Director tier or elevated | View |
| **Completion Report** | Three-layer evidence package with per-deliverable detail and cost | View, approve, remediate |
| **Event** | Immutable state change; replayable via Redis Streams | Subscribe, replay |
| **Memory** | Persistent context at four scopes; written at explicit checkpoints | View |
| **Skill** | Agent Skills standard module: instructions, references, assets | View installed |
| **Agent** | Director / PM / Worker with current task; surfaced in event stream | Observe |

**Memory write triggers** (explicit, not ambient): Global ← Director (user approval required). Workflow ← PM proposes at project completion, Director approves. Project ← PM writes on phase approval. Session ← ephemeral; content extracted to Project/Workflow scope at phase completion.

**Escalation path**: Worker → PM → Director Queue → Director → CEO Queue

---

## 6. Integrations

LLM providers (Anthropic, OpenAI, Google) via LiteLLM — routing, fallback, cost tracking. Redis — ARQ task queue, Redis Streams event bus, cache. PostgreSQL + Alembic — persistent state, sequential schema migrations. Filesystem + Git — artifacts, worktrees, VCS operations. OpenTelemetry + Langfuse — distributed tracing, LLM observability. Notification channels (webhook, email, Slack) — CEO queue alerts. Gateway API — consumed by React 19 SPA dashboard (HTTP + SSE) and Typer CLI (HTTP).

---

## 7. Constraints & Assumptions

**Constraints**: Local-first with no cloud orchestration dependencies initially. Execution strictly out-of-process — gateway never runs agent logic. All persistence through the gateway API. ADK is an internal engine — its types never appear in the external contract. All agents are stateless configuration objects; continuity lives in database-backed sessions.

**Assumptions**: Users supply structured objectives — not raw conversational prompts. LLM providers maintain sufficient reliability for multi-hour executions. Single-user local deployment initially. Users can set up the local stack (Redis, Postgres, API keys). Workflow plugins are authored externally or by a technical partner; the system executes workflows, it does not author them in the initial release.

---

## 8. Out of Scope

Interactive pair programming, IDE plugins, LLM training/fine-tuning, proprietary workflow formats, and real-time human-AI co-editing are **never** in scope.

Multi-tenant SaaS, workflow marketplace, cross-project dependency orchestration, artifact deployment, mobile UX, and WCAG AA compliance are **deferred**. Note: basic semantic HTML and keyboard navigation are expected engineering standards from Phase 1, not features to be added later. The plugin install infrastructure (PR-4, NFR-5) is foundational to a future marketplace.

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Autonomous completion | ≥80% of standard phases (2–20 deliverables, no external API dependencies) complete without CEO queue intervention |
| Escalation precision | ≥90% of CEO queue items are genuine blockers — not conditions the system could have resolved with another retry or alternative |
| Cross-phase retention | Phase 3 completion report reflects conventions established in Phase 1 without user re-entry, verified by report inspection |
| Workflow memory improvement | Escalations per deliverable decrease ≥20% between run 1 and run 5 of the same workflow type |
| Verification coverage | 100% of completion reports contain machine-generated evidence for all three layers — any missing layer is a failure |
| Plugin extensibility | A valid third-party WORKFLOW.yaml installs and executes a full project with zero core code changes |
| Time to first output | First deliverable output within 30 minutes of completing initial stack setup |

---

## 10. Traceability

*Note: `00-VISION.md` v3.0 describes three memory scopes (global, project, session). This PRD adds workflow-scoped memory to serve V-10 more completely. Vision and `architecture/state.md` should be updated accordingly.*

| Vision Goal | Requirements |
|-------------|-------------|
| V-1 Autonomous execution | PR-1, 2, 7, 10, 18, 22, 33, NFR-2, 3 |
| V-2 Hierarchical supervision | PR-7, 8, 11, 12, 13, 14, 16, 19, 34 |
| V-3 Guaranteed quality enforcement | PR-9, 10, NFR-4 |
| V-4 Three-layer verification | PR-9, 20 |
| V-5 Spec-to-deliverable traceability | PR-1, 19, 20, 21, 32 |
| V-6 Workflow composability | PR-4, 5, 6, 28, 30, NFR-5 |
| V-7 Cost efficiency | PR-21, 32, NFR-1 |
| V-8 Transparency | PR-3, 31, 32, 33, 34 |
| V-9 Structured escalation | PR-10, 13, 14, 15, 16, 17, 18, 29 |
| V-10 Memory accumulation | PR-23–27, 29 |
