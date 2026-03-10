[← Architecture Overview](../02-ARCHITECTURE.md)

# The Autonomous Execution Loop

The execution loop operates at two levels within the hierarchy, across multiple sessions in two categories (chat and work):

## Multi-Session Architecture

The Director operates via **multiple ADK sessions** -- same agent definition, different session IDs:

| Session Type | Invocation Model | Purpose |
|-------------|-----------------|---------|
| **Chat session** | Per-message (`runner.run_async` per user message) | CEO interaction -- questions, directives, status checks. Multiple chats per project; "Main" is the permanent project chat. |
| **Work session** | Long-running ARQ job | Background autonomous execution -- PM delegation, monitoring, intervention. One active work session per project. |

**Cross-session bridge**: Chat and work sessions share context via `app:` state (project-scoped), `user:` state (CEO preferences/Director personality), `MemoryService` (searchable cross-session archive), and Redis Streams (real-time event observation). A chat session can inspect and influence a running work session without interrupting it.

## Director-Level Loop

```
1. Client submits spec via POST /specs
2. Gateway enqueues decomposition job -> ARQ worker decomposes -> deliverables in DB
3. Client triggers POST /workflows/{id}/run
4. Gateway enqueues work session (ARQ job) for the project
5. Director (root_agent, recreated from config) receives the workflow:
   a. Assigns project to a PM via sub_agents + transfer_to_agent
   b. Sets hard limits (cost, time, concurrency) in project_configs (DB entity)
   c. Delegates execution to PM
   d. Monitors PM progress via event stream
   e. Intervenes if cross-project patterns go wrong
   f. Pushes notifications/escalations to unified CEO queue
   g. Manages multiple concurrent projects via separate work sessions
6. Director publishes completion event when PM reports done
7. Client receives completion via SSE stream, CEO queue notification, or polls status
```

**CEO interaction (chat sessions)**: CEO sends messages via `POST /chat/{session_id}/messages`. Gateway calls `runner.run_async` with the Director agent and the chat session ID. Director responds using `app:`/`user:` state and `MemoryService` for project context. No ARQ job -- synchronous per-message invocation.

## PM-Level Loop (per project)

```
1. PM receives project delegation from Director
2. PM runs the autonomous execution loop:
   a. Load spec -> resolve dependencies (topological sort)
   b. While incomplete deliverables exist:
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
   c. Handle failures autonomously (retry, reorder, skip blocked deliverables)
   d. Escalate to Director only when PM cannot resolve
3. PM reports project completion to Director
```

Each tier runs autonomously. No human prompting is required between iterations. The Director monitors all PMs and can intervene at any point. Optional human-in-the-loop intervention points can be configured at the batch boundary (step 2b.vi), triggered via the intervention API endpoint.

Note: The specific deterministic agents in validation/verification steps vary by workflow. For auto-code: LinterAgent + TestRunnerAgent. For auto-research: SourceVerifierAgent + CitationCheckerAgent. The *pattern* (deterministic validation is mandatory) is universal; the *implementation* is workflow-specific.

---

## See Also

- [Agents](./agents.md) -- Agent hierarchy, Director, PM, and Worker architecture
- [Workers](./workers.md) -- ARQ worker processes and job execution
- [Events](./events.md) -- Redis Streams event bus and event distribution
- [Architecture Overview](../02-ARCHITECTURE.md) -- Full system architecture

---

*Extracted from 02-ARCHITECTURE.md v2.9*
*Last Updated: 2026-02-17*
