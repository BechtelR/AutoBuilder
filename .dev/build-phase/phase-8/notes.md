# Phase 8 Pre-Shaping Research Notes

Research date: 2026-04-12
Focus: What Phase 8 should become now that Phase 7 (Workflow Composition) has absorbed capabilities Phase 8 originally claimed. Brain-dump for `/shape-phase 8`.

---

## 1. What Phase 7 Owns (vs. What Phase 8 Claimed)

Phase 8 was written as "Spec Pipeline & Autonomous Loop" before Phase 7's full design. Phase 7 ended up absorbing significant chunks of what Phase 8 claimed to own. Here's the gap analysis.

### Phase 8's Original Claims (from `08-ROADMAP.md`)

Goal: "The core thesis — specification to parallel deliverable execution with autonomous continuation under hierarchical supervision. PM IS the outer loop."

Claimed scope:
- Spec submission endpoint + spec-to-deliverable decomposition
- Deliverable model with status tracking and dependency declaration
- PM batch execution upgraded sequential → parallel (ParallelAgent + `select_ready_batch()`)
- Autonomous continuation with inter-batch PM reasoning (retry/skip/reorder/escalate)
- Director-level cross-project management
- Human-in-the-loop pause at batch boundary
- Partial failure handling
- Git worktree isolation per deliverable
- Concurrency limit enforcement (deferred from Phase 5b)

9 acceptance criteria, 20 BOM components (G02-G08, V19, A62-A63, X01-X11).

### What Phase 7 Now Owns

| Phase 8 Claim | Phase 7 Reality | Who Owns It Now |
|---|---|---|
| Stage schema with per-stage scoping | `WORKFLOW.yaml` stages field with agents/tools/skills/validators/completion_criteria/approval | **Phase 7** |
| PM-driven stage transitions | PM reconciliation loop with `pm:current_stage`, `pm:stage_index`, state-driven reconfiguration | **Phase 7** |
| Spec-to-deliverable decomposition *pattern* | PLAN stage in auto-code defines this; DeliverableDef in manifest guides it | **Phase 7** (pattern); Phase 8 (runtime) |
| Deliverable status tracking *model* | Validators + completion criteria + `deliverable_status_check` standard validator | **Phase 7** (framework); Phase 8 (DB entities) |
| Batch execution *architecture* | `batch_parallel` pipeline type defined; `select_ready_batch` pattern in stage schema notes | **Phase 7** (architecture); Phase 8 (implementation) |
| Inter-batch PM reasoning | PM reconciliation already enables observe → reason → act per batch | **Phase 7** (reasoning pattern); Phase 8 (retry/skip/reorder) |
| Completion criteria composition | Three-type AND: deliverable + validator + approval. Three-layer reports (functional/architectural/contract) | **Phase 7** |
| TaskGroup/stage close conditions | `verify_taskgroup_completion()`, `verify_stage_completion()` — hard gates PM can't override | **Phase 7** |
| Validator framework (6 standard) | lint_check, test_suite, regression_tests, dependency_validation, deliverable_status_check, code_review | **Phase 7** |
| Director workflow authoring | 6-phase lifecycle, staging directory, CEO approval, L1-L5 validation, filesystem tools | **Phase 7b** |
| CEO resource discovery tools | list_available_tools, list_mcp_servers, list_configured_credentials, list_workflows, list_available_skills | **Phase 7b** |

### What Phase 8 Still Exclusively Owns

| Capability | Why It's New |
|---|---|
| **Parallel batch execution runtime** (ParallelAgent instantiation) | Phase 7 designed it; Phase 8 wires the ADK agents |
| **Git worktree isolation** (create/merge/cleanup per deliverable) | No prior phase touches worktrees |
| **Brief/spec submission gateway endpoint** (`POST /specs`) | Gateway route + project creation + work session enqueueing |
| **Concurrency limits** (max parallel pipelines, cascaded) | Deferred from Phase 5b; no phase owns it yet |
| **Autonomous failure handling** (retry/skip/reorder/escalate heuristics) | PM reasoning pattern exists; specific failure strategies don't |
| **Human-in-the-loop intervention API** (`POST /workflows/{id}/intervene`) | New gateway route + batch-boundary pause |
| **Director execution turn** (cross-project orchestration) | Director's batch-of-PMs management |
| **Batch failure threshold** (consecutive failures → Director suspension) | Safety mechanism, no prior implementation |
| **Deliverable DB entities expansion** (status lifecycle, dependency graph) | Phase 7 added StageExecution/TaskGroupExecution/ValidatorResult tables; deliverables table exists but management tools are all placeholders |
| **Backlog queue orchestration** | CEO submits brief → Director triages → PM executes. DB tables exist (Phase 5b) but the entire orchestration layer is unbuilt |
| **`escalate_to_director` real implementation** | Tool exists as Phase 4 FunctionTool but returns a placeholder string — does NOT write to director_queue DB table |
| **Director queue gateway routes** | No CRUD routes for director_queue exposed via API |
| **Management tool DB wiring** | 10+ management tools (select_ready_batch, update_deliverable, query_deliverables, etc.) are all placeholder strings with no DB access |
| **Three-layer completion report wiring** | Phase 7 built CompletionReport model + verify_stage_completion; Phase 8 wires into INTEGRATE stage |
| **Brief validation against `brief_template`** | WorkflowManifest BriefTemplateDef exists (Phase 7); runtime validation of incoming briefs is Phase 8 |
| **Pre-execution resource validation** | ResourcesDef parsed at manifest level (Phase 7); runtime credential/service/knowledge checks are Phase 8 |

### Critical Finding: Backlog Queue Gap

Phase 5b built the **communication channels** (CEO queue gateway routes, Director queue DB table + cron scanner). But the **backlog flow** is entirely unbuilt:

| What Exists (Phase 5b) | What's Missing (Phase 8) |
|---|---|
| `ceo_queue` table + CRUD routes | `POST /specs` — no way to submit work |
| `director_queue` table + `DirectorQueueItem` model | No Director queue gateway routes (no CRUD) |
| `process_director_queue` ARQ cron (scans pending items) | `escalate_to_director` tool is placeholder string |
| CEO queue approval → session state writeback | No Director execution turn (X03) to process escalations |
| `run_work_session` ARQ job | No project backlog model (brief → triage → delegation) |

The Director execution turn described in `architecture/execution.md` §Director Execution Turn — CEO submits spec → Gateway enqueues decomposition → Director assigns PM → PM drives batch loop — requires Phase 8 to actually connect these pieces.

Additionally, the codebase audit reveals **10+ management tools in `app/tools/management.py` are placeholder strings** returning hardcoded text with no DB access:
- `select_ready_batch`, `update_deliverable`, `query_deliverables`, `reorder_deliverables`, `manage_dependencies`, `query_dependency_graph` (PM tools)
- `escalate_to_director`, `escalate_to_ceo` (tool version), `list_projects`, `query_project_status`, `override_pm` (Director tools)
- `task_create`, `task_update`, `task_query` (shared task tools)

Only `reconfigure_stage` has a real implementation (writes state deltas via ToolContext).

**Summary**: Phase 7 owns the *framework* (stage schema, validators, completion criteria, PM reasoning pattern). Phase 8 owns the *runtime* (parallel execution, worktree isolation, failure handling, gateway endpoints, DB entities).

---

## 2. The Manual Build Process

AutoBuilder's own build process — observable in `.claude/commands/` and `.claude/agents/` — is the reference implementation of the "auto-code" thesis. This IS what Phase 8 automates.

### The 5-Phase Manual Loop

```
/shape-phase {N}  → frd.md   (Functional Requirements Document)
/spec-phase {N}   → spec.md  (Buildable Specification)
/model-phase {N}  → model.md (Architecture Model — optional)
/build-phase {N}  → Code     (Implementation + 3-layer verification)
/update-phase {N} → delta    (Propagate upstream changes — reactive)
```

### Mapping to auto-code Stages

| Manual Phase | auto-code Stage | Match Quality | Notes |
|---|---|---|---|
| `/shape-phase` | **SHAPE** | **Clean match** | Brief → frd.md. Manual has user-in-the-loop for capability review; auto-code uses planner + reflector |
| `/spec-phase` | **DESIGN** | **Mostly clean** | Produces spec.md with deliverable decomposition, traceability matrices, build order. Manual has 10-step process; DESIGN stage covers architecture + design |
| `/model-phase` | **DESIGN** | **Absorbed** | model.md is a reference artifact. In auto-code, architecture decisions fold into design artifacts. No separate stage needed |
| `/build-phase` Step 1 (plan) | **PLAN** | **Clean match** | Survey code, map deliverables, confirm build order, create verification layers. Deterministic topological sort |
| `/build-phase` Step 2 (implement) | **BUILD** | **Clean match** | Batch-by-batch parallel subagent delegation. Context per subagent = deliverable spec + model interfaces |
| `/build-phase` Steps 3-4 (quality + review) | **BUILD** (validators) | **Structural divergence** | Manual runs test-gates then reviewer sequentially. auto-code integrates validators per-deliverable/per-batch |
| `/build-phase` Step 5 (completion) | **INTEGRATE** | **Partial match** | Manual has 3-layer verification (FRs + Deliverables + Contract). INTEGRATE stage adds integration testing. Not identical |
| `/update-phase` | None | **No match** | Reactive upstream propagation — not part of auto-code's forward pipeline |

### Key Divergences

**1. Human gates become agent gates.** Manual SHAPE requires user approval of capabilities. In auto-code, reflector critiques and planner validates — no human loop unless escalated. The CEO queue handles this: escalation-on-ambiguity, not approval-by-default.

**2. Spec and model collapse into DESIGN.** Manual produces three separate artifacts (frd.md, spec.md, model.md). Auto-code collapses these into one DESIGN stage producing design artifacts. This is simpler — but the traceability rigor (every FR → deliverable → contract item) must survive the collapse.

**3. Completion protocol is not just integration testing.** Manual Step 5 runs three independent verification layers (FRs, Deliverables, Contract items) with evidence tables. INTEGRATE stage is described as "integration testing and final verification" but doesn't detail the three-layer structure. Phase 8 must wire the three-layer completion report (already designed in Phase 7's architecture) into the INTEGRATE stage.

**4. Build order is an explicit planning artifact.** The manual `/spec-phase` produces a topological build order (parallel batches). In auto-code, this is the PLAN stage's job. PLAN must be deterministic — dependency graph resolution, not LLM reasoning.

### Quality Gates in the Manual Process

| Gate | Phase | Enforcer | Phase 8 Equivalent |
|---|---|---|---|
| Capability review | SHAPE | User | Reflector agent (auto) or CEO queue (escalation) |
| Reviewer verification | SPEC | reviewer agent | DESIGN stage validators |
| Reviewer verification | MODEL | reviewer agent | Absorbed into DESIGN |
| User plan approval | BUILD Step 1 | User | Auto (or CEO queue if ambiguous) |
| ruff + pyright + pytest | BUILD Step 3 | test-gates agent | lint_check + test_suite validators |
| Dual independent review | BUILD Step 4 | 2-6 reviewer agents | code_review validator (per_batch schedule) |
| 3-layer verification | BUILD Step 5 | test-gates agent | Three-layer completion report (Phase 7 design) |

---

## 3. Phase 8 Vision

### Phase Split: 8a + 8b

Phase 8 was split into two phases based on a clean dependency boundary:

**Phase 8a: "Autonomous Execution Engine"** (`L`) — End-to-end autonomous execution with sequential batches. Proves the core thesis: brief in → verified code out → minimal human intervention. Owns: brief submission, management tool DB wiring, Director backlog orchestration, sequential PM batch loop, failure handling, three-layer completion wiring, Director queue routes.

**Phase 8b: "Parallel Execution & Isolation"** (`M`) — Upgrades sequential to parallel. Owns: ParallelAgent composition, git worktree lifecycle, merge conflict strategy, state key namespacing, concurrency limits, proactive intervention API.

**Justification**: Sequential loop must work before adding filesystem concurrency. The manual `.claude/` build process works sequentially and produces verified code — parallel is a throughput optimization, not a correctness requirement. Git worktree merge conflicts (the biggest implementation risk) are isolated from the critical "make tools actually work" infrastructure.

Phase 9 and 10 depend on 8a (not 8b) — memory ingestion and event streaming need completed sessions, not parallel execution.

### Core Thesis (Unchanged)

**Spec in → verified working code out → minimal human intervention.**

Phase 8 is where this stops being architecture and starts being real. Everything before Phase 8 is infrastructure. Phase 8 is the proof.

### Minimum Thesis Proof

What is the minimum Phase 8 must deliver to prove the core thesis works?

**The demo**: Submit a brief to the auto-code workflow. Watch it SHAPE → DESIGN → PLAN → BUILD → INTEGRATE autonomously. Get back verified, tested, reviewed code with a three-layer completion report. Human touches nothing after submission (unless escalated).

**Minimum viable components:**

1. **Spec submission endpoint** (`POST /specs`) — accepts a brief, resolves workflow, creates project, enqueues work
2. **Deliverable model** — DB entities for deliverables with status + dependencies
3. **PLAN stage implementation** — deterministic spec-to-deliverable decomposition, dependency graph, batch composition
4. **Parallel batch executor** — ParallelAgent composition for concurrent deliverable pipelines
5. **Git worktree isolation** — create worktree per deliverable, merge on completion, cleanup on failure
6. **Autonomous PM loop** — retry/skip/reorder/escalate heuristics within BUILD stage
7. **Three-layer completion** — wire Phase 7's completion report framework into INTEGRATE validators
8. **Batch intervention API** — pause/resume at batch boundaries for CEO override

What can be deferred:
- Director cross-project orchestration (can run single-project first)
- Concurrency limits (hardcode a reasonable default; configurability later)
- Batch failure threshold Director suspension (PM escalation is sufficient initially)

### What Phase 8 is NOT

- **Not a new pipeline framework** — Phase 7 built that
- **Not new validators** — Phase 7 built those (Phase 8 wires them)
- **Not stage schema** — Phase 7 built that
- **Not workflow authoring** — Phase 7b built that
- **Not the PM reasoning loop** — Phase 5b built that; Phase 8 extends it

Phase 8 is the **runtime engine** that connects all prior infrastructure into the autonomous loop.

---

## 4. Key Tensions and Open Questions

### T1: Parallel Execution + Stage Reconfiguration

**Tension**: Phase 7's stage reconfiguration is state-driven — PM writes `pm:stage_agents`, `pm:stage_tools`, `pm:stage_skills` to session state, and the pipeline reads these at deliverable dispatch. But parallel batch execution means multiple deliverables dispatching simultaneously. Do they all read the same state? Is there a race condition?

**Probable resolution**: State reconfiguration happens at stage boundaries, not during execution. Within a stage, all deliverables share the same agent/tool/skill configuration. ParallelAgent workers read stage config once at batch start. No race condition because reconfiguration is between stages, not between deliverables.

**What `/shape-phase` must confirm**: Is the state snapshot model sufficient, or does each parallel worker need its own state scope?

### T2: Git Worktree Isolation + Session/State Model

**Tension**: Each deliverable executes in a git worktree (filesystem isolation). But ADK sessions and state are database-backed. How does the worktree boundary interact with session state?

**Key insight**: Worktrees isolate *filesystem* — code, tests, build artifacts. They do NOT isolate session state. All deliverables in a batch share the PM session and can write to session state via `state_delta` events. The isolation is physical (git branches) not logical (state).

**Implications**:
- Worktree create = `git worktree add` on a branch derived from current HEAD
- Worktree merge = fast-forward merge (or PR creation if conflicts)
- State writes from parallel workers must use distinct keys (e.g., `worker:{deliverable_id}:status`)
- Merge conflicts between worktrees are the biggest risk — need a deterministic merge strategy

**What `/shape-phase` must resolve**: Merge conflict strategy. Options: (a) sequential merge in dependency order, (b) rebase on merge, (c) conflict → escalate to PM for resolution. Probably (a) — merge in the same order as the dependency graph.

### T3: Spec Submission → WorkflowRegistry Wiring

**What the API needs**: `POST /specs` accepts a brief (or structured spec). The gateway must:
1. Resolve which workflow handles it (WorkflowRegistry.match() or explicit workflow_name)
2. Validate the brief against the workflow's `brief_template` (if any)
3. Create a Project record
4. Enqueue the work session via ARQ

**Open question**: Is "spec submission" the right framing? The manual process starts with a *brief* (unstructured intent), not a *spec* (structured requirements). The SHAPE stage *creates* the spec from the brief. So the endpoint should accept a **brief**, not a spec.

**Proposed**: Rename from "spec submission" to "brief submission". `POST /briefs` or `POST /projects` with a brief payload. The auto-code SHAPE stage transforms the brief into a spec. Cleaner conceptually — you submit intent, the system produces the spec.

### T4: PLAN Stage — Deterministic or LLM?

**The manual process**: `/spec-phase` step 8 produces a topological build order. This is deterministic — dependency graph resolution, not creative reasoning.

**The auto-code stage schema**: PLAN stage lists `agents: [planner]`. But if decomposition is deterministic, should it be a CustomAgent, not an LlmAgent?

**Resolution**: It's both. Spec-to-deliverable *decomposition* requires LLM judgment (understanding what the spec means, what work items emerge). Dependency ordering and batch composition are deterministic. So PLAN = LlmAgent (planner) for decomposition → CustomAgent for batching. This matches the "deterministic enforcement, probabilistic execution" design tension.

### T5: Parallel Batch Composition

**How does `select_ready_batch()` work?**

The PM needs to:
1. Query deliverable status (which are complete, which are blocked, which are ready)
2. Identify the next batch of deliverables whose dependencies are all met
3. Return those deliverables for parallel execution

This is a **tool** (FunctionTool) the PM calls, not a separate agent. It reads from DB state (deliverable records with status + dependency edges) and returns the ready set. The PM then dispatches them via ParallelAgent.

**Key design question**: Does the PM dispatch one batch at a time (wait for completion, then select next)? Or can it dispatch multiple batches if dependency-ready items span multiple levels?

**Probably one batch at a time.** The PM's reconciliation loop is: select_ready_batch → dispatch → wait for completion → observe results → reason (retry/skip/reorder?) → select_ready_batch again. Multiple concurrent batches would require tracking multiple in-flight sets, which adds complexity without clear benefit in the first version.

### T6: What is a "Deliverable" in the DB?

Phase 8 introduces deliverable DB entities. What's the schema?

**Minimum fields**: id, project_id, name, description, status (PLANNED/IN_PROGRESS/COMPLETE/FAILED/SKIPPED), dependencies (list of deliverable IDs), worktree_branch, validation_results, created_at, updated_at.

**Open question**: Is a deliverable the same granularity as a PR? The manual process maps 1 deliverable = 1 unit of reviewable work. Git worktree isolation suggests 1 deliverable = 1 branch = 1 merge. This feels right.

### T7: Rename Phase 8? — RESOLVED

**Decision**: Split into two phases:
- **Phase 8a: "Autonomous Execution Engine"** — sequential end-to-end proof
- **Phase 8b: "Parallel Execution & Isolation"** — parallel upgrade with worktree isolation

See "Phase Split: 8a + 8b" in section 3 for full justification.

---

## 5. Additional Design Ideas

### Spec Steering (from `.claude/specflow/`)

The manual process has a "spec steering" concept — an iterative loop where specs are refined through feedback. Phase 8's SHAPE stage should incorporate this: brief → draft spec → reflector critique → revised spec → approval (or escalation). Not just one-shot generation.

### Hard Iteration Limits (from external systems research)

Stripe caps at 2 CI rounds. Factory.ai uses multi-trajectory selection (try N approaches, pick best). AutoBuilder should have hard limits:
- Max review cycles per deliverable (e.g., 3)
- Max retry attempts per failed deliverable (e.g., 2)
- Max total batches per stage (e.g., 10 for safety)
- Consecutive failures → PM escalates to Director

These prevent unbounded LLM loops that burn tokens without progress.

### Deterministic-First Quality Gates (from Shopify Roast)

Roast's cog pipeline: `sed → autocorrect → LLM`. The cheapest check runs first. Phase 8 should enforce:
1. Lint (instant, free) → 2. Type check (fast, free) → 3. Unit tests (medium, free) → 4. LLM review (slow, expensive)

This is already the test-gates pipeline. Just ensure validators schedule in this order.

### Trace Recording (from OpenAI Codex)

Every prompt, tool call, agent transition must be inspectable. Phase 7's Redis Streams event bus already publishes events. Phase 8 should ensure batch execution produces a complete, replayable trace.

### Dynamic Batch Composition (from Airflow `expand()`)

Airflow's dynamic task mapping generates tasks at runtime from previous output. This IS `select_ready_batch()` — PM inspects deliverable state, computes ready set, dispatches dynamically. Not a static DAG.

---

## 6. References

### Architecture & Design
- `.dev/08-ROADMAP.md` — Phase 8 scope, acceptance criteria, BOM assignments
- `.dev/07-COMPONENTS.md` — Phase 8a + 8b BOM components (filter by phase)
- `.dev/architecture/workflows.md` — Phase 7 workflow composition system (the framework Phase 8 runs on)

### Design Notes (Phase 7 foundation)
- `.dev/.notes/260312_stage-schema-design.md` — Stage schema system, PM-driven transitions, state-driven reconfiguration, completion criteria
- `.dev/.notes/260312_manifest-design.md` — WORKFLOW.yaml format, progressive disclosure, three manifest tiers
- `.dev/.notes/260312_director-authoring-design.md` — Director authoring lifecycle, staging/activation, L1-L5 validation
- `.dev/.notes/260312_authoring-skills-design.md` — Skills taxonomy, quality framework, validator catalog

### Research
- `.dev/.research/260312_external-agentic-systems.md` — Stripe Minions, Shopify Roast, Devin, Factory.ai, Codex, Jules, Amazon Q, MetaGPT
- `.dev/.research/260312_workflow-composition-patterns.md` — N8N, Temporal, Prefect, Airflow, Dagster, GH Actions, K8s, Kestra, Argo
- `.dev/.research/260307_agent-framework-patterns-2026.md` — Dynamic system prompts, agent composition, skills progressive disclosure
- `.dev/.research/260311_claude-code-skills-system.md` — Agent Skills open standard, Claude Code implementation

### Manual Build Process (the reference implementation)
- `.claude/commands/shape-phase.md` — SHAPE phase: brief → frd.md
- `.claude/commands/spec-phase.md` — SPEC phase: frd.md → spec.md (10-step process)
- `.claude/commands/model-phase.md` — MODEL phase: architecture assembly → model.md
- `.claude/commands/build-phase.md` — BUILD phase: implement + quality gates + 3-layer verification
- `.claude/commands/update-phase.md` — UPDATE phase: propagate upstream changes
- `.claude/agents/reviewer.md` — Code review agent (finds AND fixes)
- `.claude/agents/reflector.md` — Critique agent (evaluate only, never fix)
- `.claude/agents/test-gates.md` — Quality validation (ruff/pyright/pytest pipeline)

### Auto-Code Workflow
- `app/workflows/auto-code/WORKFLOW.yaml` — 5-stage manifest
- `app/workflows/auto-code/pipeline.py` — Pipeline implementation
- `app/workflows/auto-code/agents/` — planner.md, coder.md, reviewer.md

### Key Decisions
- Decision #40 — Director as root_agent (stateless, recreated)
- Decision #50 — InstructionAssembler (6 typed fragments)
- Decision #52 — Context recreation (persist → seed → fresh session → reassemble)
- Decision #68 — Director formation via Settings conversation
- Decision #74 — Standard validators
- Decision #75 — Three-layer completion reports

---

## 7. Summary: The Phase 8 Picture

**Phase 7 built the orchestra pit.** Stage schema, validators, completion criteria, PM reasoning pattern, WorkflowRegistry, WORKFLOW.yaml — all infrastructure.

**Phase 8 conducts the orchestra.** It takes a brief, creates a project, runs it through auto-code's 5 stages autonomously with parallel batch execution, git worktree isolation, failure recovery, and three-layer verification. The human submits intent. The system delivers verified code.

**The minimum proof**: Submit a brief → auto-code SHAPE/DESIGN/PLAN/BUILD/INTEGRATE → verified deliverables with completion report. No human touch after submission (unless escalated). One project, one workflow, sequential batches first (parallel as the upgrade within Phase 8).

**Biggest risk**: Git worktree merge conflicts during parallel execution. This is the one thing that can't be solved by better prompting — it's a fundamental concurrency problem that needs a deterministic strategy (merge in dependency order, rebase, or escalate).

**Recommended rename**: "Autonomous Execution Engine"

---

## 8. Shaping Decisions (2026-04-12)

Decisions captured during the Phase 8a FRD shaping conversation. These refine and extend the pre-shaping research above.

### D1: Director-Mediated Entry (All Work Through Director)

All work enters through the Director following the supervision hierarchy (CEO → Director → PM → Workers). There is no raw API endpoint that bypasses the Director. The "brief submission endpoint" means the Director has validated a Brief and creates a Project. The Director mediates all entry modes through chat sessions using tools and sub-agents.

### D2: Seven Universal Entry Modes

Entry modes are workflow-agnostic (not specific to auto-code). All workflows support:

1. **New** — no prior work, Director shapes from scratch (PRD: Collaborative shaping)
2. **New with Materials** — user brings artifacts, Director evaluates and incorporates (PRD: Direct execution)
3. **Extend** — add new scope to existing project (PRD: Extension)
4. **Edit** — modify existing deliverables within a project (PRD: Extension subset)
5. **Re-run** — same process template, new inputs for repeatable workflows (PRD: Process run)
6. **Direct Execution** — completed Brief submitted directly, skip shaping conversation
7. **Workstream** — bounded task within a known project, scoped Brief without full project initialization

Entry mode is captured in the Brief; the workflow type (auto-code, auto-research, etc.) is constant regardless of entry mode. Greenfield/brownfield are auto-code-specific framings of New/Extend.

### D3: Projects as First-Order Entities

A new `projects` table is needed as a first-order DB entity. `ProjectConfig` and `Workflow` are related entities, not replacements. A project tracks: workflow type, current stage, active TaskGroup, queued/completed deliverables, pending escalations, accumulated cost, and status.

### D4: TaskGroup as Checkpoint/Resume Boundary

Context recreation and resume happens at TaskGroup boundaries (not stage — too coarse at hours-days; not deliverable — too fine). When context budget is exceeded, the system saves critical state at the current TaskGroup boundary, creates a fresh session, and resumes from the next unfinished TaskGroup. Mid-work batches within a TaskGroup are rediscovered during resume.

### D5: Living Projects with Workflow-Defined Edits

Projects persist after initial completion as living entities. Each workflow defines available edit operations in its manifest (e.g., auto-code: add/remove feature, fix bug, refactor; auto-research: add question, update sources). Edit requests flow through the Director, creating new TaskGroups within the existing project. Project memory and conventions carry forward.

### D6: Phase 8a/8b Split Confirmed

- **Phase 8a**: Sequential execution only. All batches/deliverables execute one at a time. Proves the core thesis.
- **Phase 8b**: Parallel execution upgrade. `batch_parallel` workflows get actual concurrency + git worktree isolation.
- Stages always sequential (can't BUILD before PLAN). Within-stage parallelism is Phase 8b.

### D7: Terminology Hierarchy Confirmed

Stage → TaskGroup(s) → Batch(es) → Deliverable(s). TaskGroup ≠ Batch. A TaskGroup is a PM-created runtime planning unit (~1h). A Batch is a group of deliverables dispatched together within a TaskGroup. Director approves at TaskGroup completion.

### D8: 15 Capabilities Defined

- **CAP-1**: Director-Mediated Project Creation & Brief Submission
- **CAP-2**: Brief Validation & Pre-Execution Resource Checks
- **CAP-3**: Durable Management Operations (foundation — all roles)
- **CAP-4**: Director Queue Operations & Observability
- **CAP-5**: Director Backlog Orchestration
- **CAP-6**: Autonomous Stage-Driven Execution Loop (Stage→TaskGroup→Batch→Deliverable)
- **CAP-7**: Failure Handling & Independent Progress
- **CAP-8**: Batch Failure Threshold & Director Suspension
- **CAP-9**: Three-Layer Completion Reporting (TaskGroup + Stage level)
- **CAP-10**: Project Lifecycle Tracking (first-order DB entity)
- **CAP-11**: Execution & System Observability
- **CAP-12**: Context Recreation & TaskGroup Resume
- **CAP-13**: Artifact Storage
- **CAP-14**: Project Continuity & Workflow-Defined Edit Operations
- **CAP-15**: Work Layer Pause & Resume Lifecycle

### D9: Scope Hierarchy

CEO + Director = full-system scope. PM = project scope. Escalation: Worker → PM → Director → CEO. All queue items flow upward through this hierarchy.

### D10: New Director Tools Identified

Phase 8a introduces new Director tools not yet in the codebase:

- `create_project` — create project entity in DB
- `validate_brief` — validate brief against workflow's brief_template
- `check_resources` — verify credentials, services, knowledge availability
- `delegate_to_pm` — enqueue PM work session for project

### D11: Appetite

L (Large) — ~2-3 weeks focused effort. 15 capabilities, ~30 BOM components. Can split further (8a/8b/8c) if scope exceeds budget.
