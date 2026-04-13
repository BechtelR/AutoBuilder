[← Architecture Overview](../02-ARCHITECTURE.md)

# The Autonomous Execution Engine

The execution loop operates at two levels within the hierarchy, across multiple sessions in three categories (settings, chat, and work):

## Multi-Session Architecture

The Director operates via **multiple ADK sessions** -- same agent definition, different session IDs:

| Session Type | Invocation Model | Purpose |
|-------------|-----------------|---------|
| **Settings session** | Per-message (`runner.run_async` per user message) | Director formation and relationship evolution. One permanent session per user, auto-created on first access. |
| **Chat session** | Per-message (`runner.run_async` per user message) | CEO interaction -- questions, directives, status checks. Multiple chats per project; "Main" is the permanent project chat. |
| **Work session** | Long-running ARQ job | Background autonomous execution -- PM delegation, monitoring, intervention. One active work session per project. |

**Cross-session bridge**: Chat, settings, and work sessions share context via `app:` state (project-scoped), `user:` state (Director identity, CEO profile, operating contract), `MemoryService` (searchable cross-session archive), and Redis Streams (real-time event observation). A chat session can inspect and influence a running work session without interrupting it.

## Consumer Roles

Three roles interact with the execution engine:

| Role | Identity | Interaction Model |
|------|----------|-------------------|
| **CEO** | Human user | Chat sessions, CEO queue, dashboard |
| **Director Agent** | Root LlmAgent (opus) | Work sessions, settings sessions, chat sessions |
| **PM Agent** | Per-project LlmAgent (sonnet) | Work sessions (delegated from Director) |

There is no separate "API consumer" role. CLI and dashboard act as the CEO's interface to the gateway.

## Director-Mediated Entry

All work enters the system through the Director. There is no raw API endpoint that bypasses the supervision hierarchy (Decision D1). The entry flow:

```
1. CEO submits request via chat or CLI
2. Director receives request, validates it (validate_brief), resolves workflow type
3. Director creates project (create_project) with workflow binding
4. Director checks resource availability (check_resources)
5. Director delegates to PM (delegate_to_pm) via transfer_to_agent
6. PM receives project delegation and begins autonomous execution
```

### Seven Universal Entry Modes

Entry modes are workflow-agnostic. The Director determines the appropriate mode from the CEO's request:

| # | Mode | Description | Creates New Project? |
|---|------|-------------|---------------------|
| 1 | **New** | Shape from scratch -- no prior artifacts | Yes |
| 2 | **New with Materials** | Evaluate user-provided artifacts, then shape | Yes |
| 3 | **Extend** | Add scope to an existing project | No (new TaskGroup) |
| 4 | **Edit** | Modify existing deliverables within a project | No (new TaskGroup) |
| 5 | **Re-run** | Same workflow, new inputs (e.g., regenerate with updated spec) | Yes |
| 6 | **Direct Execution** | Completed Brief submitted directly -- skip shaping | Yes (starts at plan/build) |
| 7 | **Workstream** | Bounded task within a known project (e.g., "fix the login bug") | No (new TaskGroup) |

Modes 3, 4, and 7 operate on living projects (see [workflows.md](./workflows.md#living-projects)). Mode 6 bypasses the shaping stage when the Brief is already complete.

## Director-Level Loop

```
1. CEO submits request (chat, CLI, or dashboard)
2. Director validates Brief and resolves workflow type
3. Director creates project record (or selects existing project for extend/edit/workstream)
4. Gateway enqueues work session (ARQ job) for the project
5. Director (root_agent, recreated from config) executes:
   a. Assigns project to a PM via sub_agents + transfer_to_agent
   b. Sets hard limits (cost, time, concurrency) in project_configs (DB entity)
   c. Delegates execution to PM
   d. Monitors PM progress via event stream
   e. Intervenes if cross-project patterns go wrong
   f. Pushes notifications/escalations to unified CEO queue
   g. Manages multiple concurrent projects via separate work sessions
6. Director publishes completion event when PM reports done
7. CEO receives completion via SSE stream, CEO queue notification, or polls status
```

**CEO interaction (chat sessions)**: CEO sends messages via `POST /chat/{session_id}/messages`. Gateway calls `runner.run_async` with the Director agent and the chat session ID. Director responds using `app:`/`user:` state and `MemoryService` for project context. No ARQ job -- synchronous per-message invocation.

## PM-Level Loop (per project)

### Execution Hierarchy

The PM operates within a four-level hierarchy (Decision D7):

```
Stage → TaskGroup(s) → Batch(es) → Deliverable(s)
```

| Level | Defined By | Granularity | Example |
|-------|-----------|-------------|---------|
| **Stage** | Workflow manifest | Organizational grouping | SHAPE, DESIGN, PLAN, BUILD, INTEGRATE |
| **TaskGroup** | PM at runtime | ~1h work unit, checkpoint boundary | "Implement auth endpoints" |
| **Batch** | PM within TaskGroup | Parallel execution set | 3 deliverables with resolved deps |
| **Deliverable** | PM from spec decomposition | Single implementable unit | "Login API endpoint" |

TaskGroup is NOT the same as Batch. A TaskGroup may contain multiple Batches. TaskGroups are the checkpoint/resume boundary (Decision D4).

### Autonomous Execution

```
1. PM receives project delegation from Director
2. PM runs the autonomous execution loop within the current stage:
   a. Create TaskGroup (~1h planning unit, checkpoint boundary)
   b. Within TaskGroup:
      i.   Select next batch (respecting deps + concurrency limits)
      ii.  For each deliverable in batch (parallel):
           - Load relevant skills (deterministic: SkillLoaderAgent)
           - Plan implementation (LLM: planner)
           - Execute plan (LLM: coder)
           - Validate output (deterministic: workflow-specific, e.g. LinterAgent)
           - Verify output (deterministic: workflow-specific, e.g. TestRunnerAgent)
           - Review quality (LLM: reviewer)
           - Loop review-fix-validate-verify if review fails (max N)
      iii. Merge completed deliverables
      iv.  Run regression checks
      v.   Publish batch completion event -> Redis Streams
      vi.  Optional: pause for human review (intervention via API)
   c. Close TaskGroup (deterministic gate: verify_taskgroup_completion)
   d. Save checkpoint at TaskGroup boundary (context recreation snapshot)
   e. Handle failures autonomously (retry, reorder, skip blocked deliverables)
   f. Escalate to Director only when PM cannot resolve
   g. Repeat (new TaskGroup) until stage completion criteria met
3. PM advances to next stage (gated by verify_stage_completion + approval)
4. PM reports project completion to Director after final stage
```

Each tier runs autonomously. No human prompting is required between iterations. The Director monitors all PMs and can intervene at any point. Optional human-in-the-loop intervention points can be configured at the batch boundary (step 2b.vi), triggered via the intervention API endpoint.

Note: The specific deterministic agents in validation/verification steps vary by workflow. For auto-code: LinterAgent + TestRunnerAgent. For auto-research: SourceVerifierAgent + CitationCheckerAgent. The *pattern* (deterministic validation is mandatory) is universal; the *implementation* is workflow-specific.

**Stage-scoped execution:** The PM operates within the current stage's constraints -- agent configuration, tool authorization, and skill sets are scoped per stage. Stage transitions are PM-driven via `reconfigure_stage` and gated by `verify_stage_completion`. See [workflows.md §Stage Schema](./workflows.md#stage-schema).

### Context Recreation at TaskGroup Boundaries (Decision D4)

Context recreation saves and restores at TaskGroup boundaries -- not at stage (too coarse, loses mid-stage progress) or deliverable (too fine, excessive overhead). On resume:

1. Load project state from database
2. Restore session to last completed TaskGroup checkpoint
3. Rediscover incomplete batches within the current TaskGroup (if interrupted mid-TaskGroup)
4. Rebuild agent context via InstructionAssembler + SkillLoaderAgent + MemoryLoaderAgent

This enables crash recovery, pause/resume, and long-running project continuation across worker restarts.

### Pause/Start Lifecycle (Decision D11)

Three layers of pause/start control:

| Layer | Pause | Start |
|-------|-------|-------|
| **Project-level** | Save state at TaskGroup checkpoint, log reason, stop PM execution | Load resources, rebuild context from checkpoint, resume PM loop |
| **All-projects** | System-wide pause cascading to all active projects | System-wide resume cascading to all paused projects |
| **Director layer** | Stop backlog processing, cascade pause to all active projects | Rebuild Director context, resume CEO queue processing |

Pause is always safe -- it waits for the current deliverable to reach a safe point (batch boundary or TaskGroup boundary), then saves state. Start rebuilds context from the last checkpoint and resumes. Paused projects retain their state indefinitely.

---

## See Also

- [Agents](./agents.md) -- Agent hierarchy, Director, PM, and Worker architecture
- [Workflows](./workflows.md) -- Workflow composition, stages, pipeline instantiation
- [Workers](./workers.md) -- ARQ worker processes and job execution
- [Events](./events.md) -- Redis Streams event bus and event distribution
- [Architecture Overview](../02-ARCHITECTURE.md) -- Full system architecture

---

*Extracted from 02-ARCHITECTURE.md v2.9*
*Last Updated: 2026-04-12*
