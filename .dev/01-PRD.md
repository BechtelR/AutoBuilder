# AutoBuilder — Product Requirements Document
*Version: 7.2 | Date: 2026-03-11 | Maps to: `00-VISION.md` v3.0*

---

## How AutoBuilder Works

AutoBuilder is built on two first-order ideas:

**Composable workflows.** Any structured knowledge process can be encoded as a workflow — a plugin that defines its own stage schema, agent configuration, skill requirements, validation logic, and output format. The auto-code workflow is the first; the platform is the product.

**Hierarchical autonomous execution.** All work flows through the same supervision hierarchy regardless of workflow type:

```
User (CEO) → Director → PM → Workers
```

The **Director** is the user's executive partner: it shapes raw ideas into documented Briefs, coordinates across all active projects, maintains a per-project chat alongside autonomous execution, and surfaces everything requiring user judgment to the CEO queue. Once a Brief is documented, the Director delegates to a **PM**. The PM owns the project end-to-end — it manages the execution loop (select batch → run in parallel → validate → checkpoint → repeat) using the agents, skills, and tools appropriate to each workflow stage. **Workers** execute individual deliverables under PM supervision.

The system is functionally stateful — projects accumulate memory, decisions persist, work resumes precisely from where it left off. Architecturally, agent objects are stateless: recreated per invocation, with all continuity in database-backed sessions.

**How work enters the pipeline:**

| Mode | What the User Brings |
|------|---------------------|
| **Collaborative shaping** | A raw idea, goal, or problem — the Director interviews, researches, and shapes it into a Brief |
| **Direct execution** | A completed Brief ready to run |
| **Extension** | An existing project or codebase — the Director establishes context, then plans incremental changes |
| **Workstream** | A bounded task within a known project — routed directly to the right PM |
| **Process run** | A new instance of a repeatable workflow — different inputs, same encoded process |

---

## 1. User Personas

### P-1: The Builder
Constructing something — a product, system, pipeline — that didn't fully exist before. May arrive with a vague idea or a detailed spec. May be building from scratch or extending an existing foundation.

What they want: define what done looks like and walk away. Returns to a verified completion report. Across multiple stages and TaskGroups, the system accumulates project context — conventions, architectural decisions, resolved ambiguities — so each benefits from the full history of the project without manual re-entry.

What they can't get elsewhere: trust. Today's autonomous tools produce drift without oversight. AutoBuilder's structural quality gates and three-layer verification let them actually walk away.

### P-2: The Lead
Manages delivery quality across a team that includes both humans and AutoBuilder. Delegates workstreams with explicit standards, expecting the same rigor from AutoBuilder as from a senior engineer: conform to the conventions, produce evidence of conformance, and escalate when genuinely stuck.

What they want: the completion report to function as a delegation receipt — a verifiable record of what was built, to what standards, with what decisions made autonomously vs. by the user. Accountable to stakeholders; needs an audit trail.

What they can't get elsewhere: accountability. No current tool produces verifiable evidence that standards were followed. "Done" is asserted, not proven.

### P-3: The Operator
Runs repeatable, high-value knowledge processes — due diligence, research synthesis, technical audits, investment screening. The expertise is in the process design. Encodes it once as a workflow; runs instances against new inputs without re-coordination. The system gets better at the process over time as workflow memory accumulates.

What they want: encode their best process once, then submit new instances without re-coordination. Judgment calls surface to the CEO queue; the operator resolves without entering the execution loop.

What they can't get elsewhere: process fidelity at scale. AI tools automate steps, not end-to-end processes with structural quality gates.

---

## 2. User Journeys

### J-1: Shape and Build a New Project
*Personas: P-1, P-2 | Modes: collaborative shaping, direct execution, extension*

The project may begin with a raw idea (Director interviews the user, conducts research, drafts the Brief collaboratively) or a completed Brief (Director validates it and proceeds directly). Either way, once the Brief is documented, the Director delegates to a PM.

The PM determines the appropriate workflow stage and configures accordingly — research and architecture agents for a design stage, coding and testing agents for a build stage. It selects a batch of dependency-ready deliverables, dispatches workers in parallel, validates results, checkpoints state, then selects the next batch. Genuine blockers escalate through the Director Queue to the CEO queue.

The user interacts only with the CEO queue: resolves decisions, reviews completion reports, approves stages. The Director approves TaskGroups autonomously within a stage. Each approval — TaskGroup or stage — writes to project memory; the next inherits full context.

*Failure*: Deliverable exhausts retries → CEO queue with validator evidence. User chooses: remediate the specific deliverable (re-executes it and dependents only), redirect, or abort.

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

### J-3: Direct, Intervene, or Converse
*Personas: any | Mode: any*

The Director maintains multiple active chat sessions — a primary session and per-project sessions — not a single monolithic interface. Users converse naturally: status questions get portfolio summaries sourced from the CEO queue and project memory; directives are assessed and routed to affected PMs; strategic priorities are applied across the portfolio.

Mid-execution intervention is evaluated for scope: if a directive would cancel verified work, the Director surfaces what would be lost to the CEO queue before proceeding. Otherwise it applies immediately and logs the intervention to the audit trail.

---

## 3. Functional Requirements

### 3.1 Project & Brief

| ID | Requirement |
|----|-------------|
| PR-1 | A **Brief** is the documented project intent — its structure defined by the workflow type. It may be authored collaboratively with the Director (via interviews and research) or submitted directly. At minimum it captures: objective, acceptance criteria, and scope constraints. The Director validates it before delegating to a PM. |
| PR-2 | Projects track status, active workflow stage, queued and completed deliverables, pending CEO queue items, and cumulative cost at all times. |
| PR-3 | Projects support pause, resume, and abort at any time. Pause suspends at the next deliverable checkpoint — within a TaskGroup, between deliverables — with full state persisted. Resume restores from that checkpoint; no verified work is re-executed. Abort terminates, preserves all completed work and events, and records the reason. |

### 3.2 Workflow Management

| ID | Requirement |
|----|-------------|
| PR-4 | Workflows are plugins. A workflow defines its own **stage schema** (e.g., SHAPE → DESIGN → PLAN → BUILD for software), the agents, skills, and tools active at each stage, its mandatory validator pipeline, its deliverable and output format definitions, and its completion report structure. Plugins install via WORKFLOW.yaml with zero core code changes. |
| PR-5 | At each workflow stage, the PM assembles the appropriate agent configuration: research and architecture agents for design stages, coding and verification agents for build stages. Skills and tool authorizations are scoped per stage. |
| PR-5a | Agent instructions are composed from 6 typed fragments (safety, identity, governance, project context, task context, domain skills) via an InstructionAssembler (see NFR-4a for constitutional SAFETY fragment). The Director controls agent behavior per-project through governance fragments stored in session state — it does not rewrite agent prompts directly. Skills load progressively based on deliverable context. The assembler filters loaded skills per agent using each skill's `applies_to` field — not all agents receive all skills. All fragments are auditable (source-tracked). |
| PR-5b | Agents are defined as **declarative definition files** (markdown with YAML frontmatter). Frontmatter carries structured metadata (name, type, model routing, tool access, output key). The markdown body provides instruction content. An AgentRegistry scans definition files and builds ADK agents on demand — the filesystem is the registry. No agent identity lives in Python code. |
| PR-5c | Agent definitions follow a **3-scope file cascade**: global (shipped with platform) → workflow-specific → project-specific. Later scopes override earlier scopes by filename match. A project-scope file with only frontmatter (no body) is a **partial override** — its fields merge over the parent scope, inheriting the parent's instruction body. This parallels the Skill override cascade. |
| PR-6 | A curated set of default workflow plugins ships with the platform — designed to be directly useful and to model how to compose new workflows, by users or by the Director itself. |
| PR-7 | Project-level conventions override workflow defaults. The workflow manifest is the execution contract for everything it defines. |

### 3.3 Execution & Work Queues

| ID | Requirement |
|----|-------------|
| PR-8 | The Director decomposes each submitted Brief into a dependency-ordered execution plan, determining the appropriate workflow stage to begin from. Before the first deliverable is dispatched, the system validates all resources required by the workflow stage — credentials, API access, tool authorizations, and input materials. Any missing or invalid resource surfaces to the CEO queue immediately; execution does not begin until resolved. Resource failures never occur mid-run. |
| PR-9 | All agent work is managed through **observable async work queues**. Every queued item — pending, in-progress, or blocked — is visible to the user at all times. Items can be promoted, demoted, paused, resumed, or cancelled without restarting the project. |
| PR-10 | The PM's execution loop operates on the work queue: select a Batch of dependency-ready deliverables → dispatch in parallel or sequentially → collect results → repeat until the TaskGroup is complete → run regression tests → fix until pass → checkpoint. |
| PR-11 | The workflow manifest defines when validators run — per-deliverable for lightweight checks, per-batch or per-TaskGroup for comprehensive validation. At minimum, all workflow validators run at TaskGroup completion. Scheduled validators are mandatory pipeline steps; they cannot be skipped or overridden by agent judgment. |
| PR-12 | Failed deliverable: auto-retry to configured limit → escalate to PM → escalate to Director → surface to CEO queue. State is checkpointed after each successful deliverable; a crash cannot cause a checkpointed deliverable to re-execute. When a CEO queue item is resolved, the resolution is applied back into the work queue and execution resumes. |

### 3.4 Agent Hierarchy

| ID | Requirement |
|----|-------------|
| PR-13 | The Director is the user's executive partner. It shapes Briefs through collaborative dialogue, coordinates across all active projects, and maintains per-project chat sessions alongside autonomous work sessions. Each project has its own Director chat session; there is also a primary Director session for portfolio-level conversation. A dedicated **Settings session** enables the CEO and Director to shape their working relationship through natural conversation. On first access, the Director initiates a formation conversation — a short, professional exchange (~5-10 questions) that produces three structured artifacts: Director Identity (personality, communication style), CEO Profile (working style, expertise, collaboration patterns), and Operating Contract (autonomy levels, escalation sensitivity, feedback style). These artifacts persist in `user:` scope and inform all Director behavior across sessions and projects. The Settings session remains available for evolving the relationship at any time. The Director receives role-bound skills (governance, oversight, brief-shaping, CEO communication) at build time via the same deterministic matching engine used by workers. |
| PR-14 | Each project has one dedicated PM for its lifetime. The PM owns the delivery loop, quality gate enforcement, and PM-level decisions. The PM receives role-bound skills (project management, task orchestration, quality gates) at build time via the same deterministic matching engine used by workers. Workers execute deliverables under PM supervision and escalate blockers upward — they do not surface directly to the user. |
| PR-15 | Each tier has bounded authority: a **retry budget** (max retries before escalating), a **decision scope** (categories it can resolve autonomously), and a **cost ceiling** (token/spend limit). Exhausting any dimension triggers escalation to the tier above. Limits cascade: user sets project ceiling → Director enforces across projects → PM enforces within the project → workers operate within per-deliverable budgets. |
| PR-15a | When an agent's context window approaches capacity, the system recreates the session: persisting important state to memory, creating a fresh session, and reassembling context from durable stores (memory, state, skills, instruction fragments). No lossy summarization. The agent resumes from the same logical point with full relevant context reconstructed. |
| PR-15b | Cross-session memory context is loaded as a **deterministic pipeline step** (MemoryLoaderAgent) at the start of each deliverable pipeline, not as an LLM-discretionary tool call. The agent searches the memory service for relevant context and writes results to session state before any LLM agent runs. This ensures memory context is always available and never skipped by LLM judgment. |
| PR-16 | When a PM's consecutive batch failures exceed the configured threshold (default: 3), the Director suspends the project and diagnoses the failure pattern — reviewing validator evidence, escalation history, and execution state. It surfaces findings and options to the CEO queue; it does not attempt autonomous repair. |

### 3.5 CEO Queue & Director Queue

| ID | Requirement |
|----|-------------|
| PR-17 | The CEO queue is the single point of contact between the user and the system: decisions, approvals, notifications, and tasks from all active projects — prioritized, real-time. |
| PR-18 | A parallel **Director Queue** handles PM-to-Director escalations (status reports, resource requests, pattern alerts). The Director resolves within its authority; items exceeding its authority elevate to the CEO queue. |
| PR-19 | Each CEO queue decision includes: what the blocker is, the options available, and a recommended resolution with rationale. When an escalation is active, unblocked work continues — only the directly blocked path suspends. |
| PR-20 | Resolving a CEO queue item resumes the suspended path immediately, without restarting the project. |
| PR-21 | Unresolved items trigger notifications via configured channels (webhook, email, Slack, Telegram, SMS) after a configurable timeout (default: 4 hours). Every item is logged with its resolution, who resolved it, and when. |

### 3.6 Completion Reporting

| ID | Requirement |
|----|-------------|
| PR-22 | Workflow Stages and TaskGroups each produce a completion report with three verification layers, scoped to their level. All layers require machine-generated evidence: **Functional correctness** (does it work as specified?), **Architectural conformance** (does the implementation match the documented architecture?), and **Contract completion** (were all deliverables at this level completed?). Assertion alone is never sufficient. |
| PR-23 | A TaskGroup cannot close while any deliverable is outstanding, any scheduled validator is failing, or any escalation is unresolved. These conditions hold regardless of workflow; workflow verification layers are additive. |
| PR-24 | Reports include: per-deliverable evidence, cost and token usage by agent tier, wall-clock duration, and a decision log — distinguishing system-autonomous from user-resolved decisions. |
| PR-25 | Remediation re-executes only failed deliverables and their dependents. Verified independent deliverables are not re-executed. |

### 3.7 Memory

| ID | Requirement |
|----|-------------|
| PR-26 | Memory is platform infrastructure — available to all workflows without configuration. Write triggers are explicit and predictable; LLM ingestion models handle summarization, deduplication, and relevance scoring at each checkpoint. Four scopes: |
| PR-27 | **Global** — system-wide standards and user preferences. Written by the Director with user approval. The structured CEO Profile artifact (from the Settings conversation) is the source of truth for user preferences; global memory indexes and makes it searchable. |
| PR-28 | **Workflow** — domain expertise accumulated across all projects using a workflow type: recurring failure patterns, quality signals, edge cases observed across runs. Proposed by the PM at project completion, written after Director approval. A new project using a workflow type with accumulated memory receives that expertise from its first deliverable. |
| PR-29 | **Project** — project-specific conventions, architecture decisions, and resolved escalations from prior TaskGroups and stages. Written by the PM on TaskGroup or stage approval. Automatically available to any subsequent TaskGroup or stage of the same project. |
| PR-30 | **Session** — ephemeral execution state for the current run only. At TaskGroup completion, the system explicitly extracts learnings and ingests them into the appropriate longer-lived scope via a memory ingestion step. Session state itself is not persisted. |

### 3.8 Skills

| ID | Requirement |
|----|-------------|
| PR-31 | Skills implement the Agent Skills open standard (agentskills.io): a `SKILL.md` file with YAML frontmatter and Markdown instructions, with optional `references/` and `assets/` subdirectories. Agents load only skill frontmatter (~100 tokens) by default — the full body loads on activation only, reference files on demand. |
| PR-32 | Skill activation is deterministic, using a three-layer model: (1) **role-bound** — skills with an `always` trigger load unconditionally for specified agent roles (e.g., Director governance skills, PM management skills); (2) **context-matched** — skills match against deliverable metadata (type, tags, file patterns) via structured trigger rules; (3) **explicit override** — skills requested by name via session state for edge cases metadata does not capture. The `applies_to` field is a delivery filter (which agents receive the skill), not a matching criterion. When no skill matches, execution continues and a warning event is emitted. |
| PR-33 | Third-party skills install without code changes. Skills without AutoBuilder-specific triggers fall back to deterministic keyword matching against the `description` field. AutoBuilder extensions use the `metadata.*` namespace per the standard's extension point. `scripts/` execution and `allowed-tools` pre-authorization are capabilities defined by the standard; support is phase-dependent. |
| PR-33a | Agents can autonomously create new skills during execution, encoding learned patterns as reusable knowledge. Created skills are validated against the same rules as manually authored skills and become available to subsequent pipeline executions after cache invalidation — no restart or manual registration required. |

### 3.9 Observability

| ID | Requirement |
|----|-------------|
| PR-34 | Every project has a persistent, replayable event stream (Redis Streams + SSE). Clients reconnect via `Last-Event-ID` with no events lost. The stream covers: agent tier changes, deliverable lifecycle, validator results, escalations, cost per deliverable, checkpoints, and errors. |
| PR-35 | Token usage and cost are tracked per deliverable, TaskGroup, stage, and project — in real-time, no manual calculation. An immutable audit log records all state transitions, decisions, escalations, and interventions. |
| PR-35a | Agent definition resolution is auditable. For each agent built, the system logs which scope (global, workflow, project) provided the definition, which file path was used, and whether a partial override was applied. The resolution map is available for diagnostic inspection. |

### 3.10 Interfaces

| ID | Requirement |
|----|-------------|
| PR-36 | The CLI covers the full operational surface: create project, submit spec, check status, stream live events, view CEO queue, send directive, resolve decision, view logs. JSON output for scripting. No dashboard required for any operation. |
| PR-37 | The dashboard is the CEO command center — not required for any operation, but designed to provide the richest possible view of the system: portfolio overview with real-time agent status, live event stream, work queue visualization (Kanban columns defined by the workflow's stage schema), CEO queue with inline resolution, completion reports, Director chat panels. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | API response time and SSE latency targets established in Phase 10. Design goal: status queries feel instantaneous locally; events appear within 2 seconds of state change. |
| NFR-2 | A standard workflow stage completes within a working day under normal conditions. System overhead is not a meaningful contributor to stage duration. |
| NFR-3 | Crash recovery: restarts from last checkpoint without re-executing verified deliverables. LLM reliability is AutoBuilder's responsibility — handled through heartbeats, retry hooks, and provider fallback before any user escalation. |
| NFR-4 | Gateway input validation via Pydantic at all boundaries. Credentials never logged or hardcoded. Tool execution isolated to worker processes. All state transitions produce an immutable audit event. |
| NFR-4a | A **constitutional SAFETY fragment** is hardcoded in the InstructionAssembler and prepended to every LLM agent's instructions. It cannot be overridden by any scope — not project-scope definitions, not Director session state, not skill content. It enforces core safety constraints: no data exfiltration, respect tool boundaries, follow escalation protocol. |
| NFR-4b | **Project-scope agent definitions** are restricted: only `type: llm` is permitted (no arbitrary `class` paths from user-controlled directories). The `tool_role` field is validated against the workflow's permitted tool ceiling — a project-scope override cannot grant tools the workflow does not permit. |
| NFR-4c | **State key authorization** enforces tier-based write access. Governance-sensitive state keys use tier prefixes (`director:`, `pm:`, `worker:`). The event system validates that the event author's tier matches the key prefix on state writes. Non-prefixed keys are shared workspace accessible by all tiers. |
| NFR-5 | Third-party workflow plugins and Agent Skills standard skills install without code changes. The gateway API is the sole external contract — internal engine changes do not require client updates. Codegen (OpenAPI → TypeScript via hey-api) maintains type safety across the gateway boundary. |
| NFR-6 | Runs fully on a single machine with no cloud dependencies. All configuration via environment variables. |

---

## 5. Information Architecture

| Entity | What It Is | User Can |
|--------|-----------|----------|
| **Project** | Top-level unit: workflow type, conventions, stage and TaskGroup history, accumulated project memory | Create, view, pause, resume, abort |
| **Brief** | Documented project intent — structure defined by workflow type. Produced collaboratively with the Director or submitted directly. Validated before PM delegation. | Submit, view status |
| **Workflow** | Plugin defining the complete execution process: stage schema, agent/skill/tool configuration per stage, validators, deliverable format, and completion report structure | Select, install third-party, view |
| **Workflow Stage** | Schema-defined execution stage (e.g., DESIGN, PLAN, BUILD). Contains one or more TaskGroups. Determines active agents, skills, and tools. Visible at portfolio level. CEO approves on completion. | Approve, view, remediate |
| **TaskGroup** | PM-created runtime planning artifact within a Workflow Stage (~1h work unit). Director approves on completion; produces a completion report scoped to TaskGroup deliverables and a project memory write. Visible at project level. | View |
| **Batch** | A group of Deliverables within a TaskGroup dispatched together by the PM — parallel or sequential. The PM instructs workers on execution mode based on dependency order. | View |
| **Deliverable** | Atomic unit of work: executed, validated, and checkpointed. Must have at least one agent-executable verification method defined: API call, batch command, agent evaluation, browser interaction, or LLM assessment. | View |
| **CEO Queue Item** | Decision, approval, notification, or task from any project | Resolve, dismiss |
| **Director Queue Item** | PM-to-Director escalation, resolved at Director tier or elevated | View |
| **Completion Report** | Three-layer evidence package with per-deliverable detail and cost | View, approve, remediate |
| **Event** | Immutable state change; replayable via Redis Streams | Subscribe, replay |
| **Memory** | Persistent context at four scopes; written at explicit checkpoints | View |
| **Skill** | Agent Skills standard module: instructions, references, assets. Can be authored by humans or created autonomously by agents. | View installed |
| **Agent** | Director / PM / Worker with current task; surfaced in event stream | Observe |

**Memory write triggers** (explicit, not ambient): Global ← Director (user approval required). Workflow ← PM proposes at project completion, Director approves. Project ← written on TaskGroup approval (Director) and Stage approval (CEO). Session ← ephemeral; content extracted to Project/Workflow scope at TaskGroup completion.

**Escalation path**: Worker → PM → Director Queue → Director → CEO Queue

---

## 6. Integrations

| Integration | Purpose |
|-------------|---------|
| LLM Providers (Anthropic, OpenAI, Google) via LiteLLM | Agent intelligence, routing, fallback chains, cost tracking, memory summarization |
| Redis | ARQ task queue, Redis Streams event bus, cache |
| PostgreSQL + Alembic | Persistent state, sequential schema migrations |
| Git + GitHub *(required by all workflows)* | Version control for all project artifacts; git worktrees for parallel execution |
| Filesystem (POSIX) | Local artifact storage, execution workspace |
| Google Drive *(and future cloud storage)* | Remote file storage and document input for knowledge workflows |
| OpenTelemetry + Langfuse | Distributed tracing, LLM observability, cost analytics |
| Webhook / Email / Slack / Telegram / SMS (Twilio) | CEO queue notifications via user-configured channels |
| React 19 SPA + hey-api codegen | Dashboard, TypeScript client generated from OpenAPI spec |
| Typer CLI | Terminal interface, pure gateway API consumer |

---

## 7. Constraints & Assumptions

**Constraints**: Local-first with no cloud orchestration dependencies initially. Execution strictly out-of-process — gateway never runs agent logic. All persistence through the gateway API. ADK is an internal engine — its types never appear in the external contract. All agents are stateless configuration objects; continuity lives in database-backed sessions.

**Assumptions**: The Director converts any form of user input — raw idea, rough goal, or structured Brief — into a valid project Brief. AutoBuilder maintains LLM execution reliability through internal mechanisms (heartbeats, retries, provider fallback); provider availability is not assumed. Single-user local deployment initially. Users can configure the local stack. Default workflow plugins model composability patterns for users and the Director when building custom workflows.

---

## 8. Out of Scope

Interactive pair programming, IDE plugins, LLM training/fine-tuning, proprietary workflow formats, and real-time human-AI co-editing are **never** in scope. AutoBuilder is a standalone system — it does not extend or embed in an editor, IDE, or other tool.

Multi-tenant SaaS, workflow marketplace, cross-project dependency orchestration, artifact deployment, mobile UX, and WCAG AA compliance are **deferred**. Note: basic semantic HTML and keyboard navigation are expected engineering standards from Phase 1, not features to be added later. The plugin install infrastructure (PR-4, NFR-5) is foundational to a future marketplace.

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Autonomous completion | ≥80% of standard workflow TaskGroups complete without CEO queue intervention |
| Escalation precision | ≥90% of CEO queue items are genuine blockers — not conditions the system could have resolved with another retry or alternative |
| Cross-TaskGroup retention | TaskGroup 3 completion report reflects conventions established in TaskGroup 1 without user re-entry, verified by report inspection |
| Workflow memory improvement | Escalations per deliverable decrease ≥20% between run 1 and run 5 of the same workflow type |
| Verification coverage | 100% of completion reports contain machine-generated evidence for all three layers — any missing layer is a failure |
| Plugin extensibility | A valid third-party WORKFLOW.yaml installs and executes a full project with zero core code changes |
| Time to first output | First deliverable output within 30 minutes of completing initial stack setup |
| Stage duration | A standard workflow stage completes within one working day of wall-clock time |
| Cost efficiency | Execution cost per completed workflow stage ≤5% of market-rate equivalent human output at comparable quality (validated on auto-code workflow by Phase 10) |

---

## 10. Traceability

| Vision Goal | Vision Section | Requirements |
|-------------|---------------|-------------|
| Autonomous execution | Product Vision | PR-1, 2, 7, 10, 15a, 20, 24, 36, NFR-2, 3 |
| Hierarchical supervision | Innovations | PR-7, 8, 13, 14, 15, 16, 18, 21, 37 |
| Guaranteed quality enforcement | Innovations | PR-9, 10, 11, NFR-4 |
| Agent governance and safety | Innovations | PR-5a, 5b, 5c, NFR-4a, NFR-4b, NFR-4c |
| Three-layer verification | Innovations | PR-9, 22, 23 |
| Brief-to-deliverable traceability | Innovations | PR-1, 22, 23, 24, 35 |
| Workflow composability | Innovations | PR-4, 5, 5b, 5c, 6, 31, 32, 33, 33a, NFR-5 |
| Cost efficiency | Success Criteria | PR-24, 35, §9 Cost efficiency metric |
| Transparency and trust | Strategic Advantages | PR-3, 34, 35, 35a, 36, 37 |
| Structured escalation | Product Vision | PR-10, 15, 16, 17, 18, 19, 20 |
| Memory accumulation | Strategic Advantages | PR-15b, 26–30 |
