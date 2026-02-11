# AutoBuilder State & Memory Architecture

## Overview

AutoBuilder uses ADK's three-tier context management system -- Session, State, and Memory -- to provide six levels of progressively broader context to agents. This document covers what ADK provides natively, where the gaps are, and how AutoBuilder fills them.

---

## 1. What ADK Provides Natively

### 1.1 Session

A single conversation thread. Contains a chronological `Event` history and a `state` dict. Identified by the tuple `(app_name, user_id, session_id)`. Managed by a `SessionService`.

Every agent (LLM or deterministic) emits `Event` objects into the session's event stream. ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt.

### 1.2 State (4-Scope System)

Key-value scratchpad within a session, with four prefix-scoped tiers:

| Prefix | Scope | Lifetime | AutoBuilder Use |
|--------|-------|----------|----------------|
| *(none)* | This session only | Persists with session (via `DatabaseSessionService`) | Current batch, feature statuses, loaded skills, test/lint results, intermediate pipeline data |
| `user:` | All sessions for this user (within same app) | Persistent | User preferences, model selections, intervention settings, notification preferences |
| `app:` | All users and sessions for this app | Persistent | Project config, global conventions, skill index, workflow registry, shared templates |
| `temp:` | Current invocation only | Discarded after invocation completes | Intermediate LLM outputs, scratch calculations, data passed between tool calls within one invocation |

Key characteristics:

- **Event-sourced updates.** State changes happen via `Event.actions.state_delta` -- never direct mutation. All state changes are auditable in the event stream.
- **Serializable values only.** Strings, numbers, booleans, simple lists/dicts. No complex objects.
- **Template injection.** State values are injectable into agent instructions via `{key}` templating: `"Implement the feature: {current_feature_spec}"` auto-resolves from `session.state['current_feature_spec']`. Use `{key?}` for optional keys that may not exist.

### 1.3 Memory (MemoryService)

Searchable cross-session knowledge archive. Two operations:

- `add_session_to_memory(session)` -- ingests a completed session
- `search_memory(app_name, user_id, query)` -- retrieves relevant past context

Built-in tools for agent access:

| Tool | Behavior |
|------|----------|
| `PreloadMemoryTool` | Auto-loads relevant memories every turn |
| `LoadMemory` | Agent-decided retrieval (on-demand) |
| `tool.Context.search_memory()` | Programmatic search from within custom tools |

### 1.4 Session Rewind (v1.17+)

Revert to any previous invocation point. Session-level state and artifacts are restored. `app:` and `user:` state are NOT restored (by design -- those are cross-session). External systems (filesystem, git) are not managed by rewind -- AutoBuilder handles that via git worktree isolation.

### 1.5 Session Migration

CLI tool for `DatabaseSessionService` schema upgrades (v0 pickle to v1 JSON). Important for production maintenance when upgrading ADK versions.

---

## 2. SessionService Options

| Service | Persistence | Use Case |
|---------|------------|----------|
| `InMemorySessionService` | None (lost on restart) | Dev/testing only |
| **`DatabaseSessionService`** | **SQLite or Postgres** | **AutoBuilder production choice -- local, no GCP dependency** |
| `VertexAiSessionService` | Vertex AI managed | Skipping -- GCP dependency |

`DatabaseSessionService` requires async drivers: `sqlite+aiosqlite` for SQLite, `asyncpg` for Postgres.

```python
from google.adk.sessions import DatabaseSessionService

# AutoBuilder production configuration
session_service = DatabaseSessionService(
    db_url="sqlite:///./autobuilder_sessions.db"  # Or postgres://...
)
```

---

## 3. MemoryService Options

| Service | Search | Persistence | Limitations |
|---------|--------|-------------|-------------|
| `InMemoryMemoryService` | Basic keyword matching | None | Dev/testing only |
| `VertexAiMemoryBankService` | Semantic (LLM-powered extraction + search) | Managed by Vertex AI | GCP-only -- we are avoiding this |

ADK's `MemoryService` is an interface (`BaseMemoryService`) with two methods: `add_session_to_memory()` and `search_memory()`. The only production-ready implementation is `VertexAiMemoryBankService` (GCP-only). `InMemoryMemoryService` is keyword-only and non-persistent.

This is the primary gap AutoBuilder must fill.

---

## 4. The Gap: Local Semantic Memory

AutoBuilder needs a local, persistent, semantically-searchable memory service. Three options were evaluated:

### Option 1: SQLite FTS5

Full-text search built into SQLite. No additional dependencies. Good enough for keyword and phrase matching. Lightweight.

**Pros:** Zero-dependency (SQLite is already our session store), fast, battle-tested.
**Cons:** No true semantic similarity. Keyword-based matching only.

### Option 2: Local Embedding + Vector Store

Embed session content locally (via a small embedding model or API call), store in ChromaDB/FAISS/SQLite-VSS. True semantic search.

**Pros:** Semantic similarity, better recall for conceptual queries.
**Cons:** Additional dependencies, more complexity, embedding model cost/latency.

### Option 3: Hybrid

SQLite FTS5 for structured lookups + vector store for semantic similarity. Best of both worlds.

**Pros:** Most capable search.
**Cons:** Most moving parts, highest complexity.

### Phase 1 Recommendation: SQLite FTS5

Implement `BaseMemoryService` backed by SQLite FTS5. Rationale:

- Zero-dependency -- SQLite is already our session store
- Provides useful full-text search
- Sufficient for queries like "what architectural patterns did we establish in features 1-10?"
- Evaluate upgrading to vector-backed semantic search in Phase 2 if FTS5 proves insufficient

---

## 5. AutoBuilder's Multi-Level Memory Architecture

Mapping the original "multi-level memory" requirement (Problem #7 from plan-shaping) to ADK's native primitives:

| Memory Level | ADK Mechanism | What It Stores | Loaded How |
|---|---|---|---|
| **Invocation context** | `temp:` state | Scratch data for current tool chain | Auto-available, discarded after |
| **Pipeline context** | Session state (no prefix) | Feature spec, plan, code output, test results, lint results | Written by agents via `state_delta`, read via `{key}` templates |
| **Project conventions** | `app:` state + Skills | Coding standards, architecture decisions, framework patterns | SkillLoaderAgent + `InstructionProvider` |
| **User preferences** | `user:` state | Model preferences, notification settings, review strictness | Auto-merged into session at load |
| **Cross-session learnings** | `MemoryService` | Patterns discovered, mistakes made, architectural decisions from past runs | `PreloadMemoryTool` or `LoadMemory` tool |
| **Business knowledge** | Skills files (global + project-local) | Domain rules, compliance requirements, API conventions | SkillLoaderAgent (deterministic matching) |

This is six levels of progressively broader context, all using ADK-native mechanisms. No custom memory framework needed -- just proper use of state scopes + MemoryService + Skills.

---

## 6. How Memory Flows Through the Pipeline

```
Session starts
  --> DatabaseSessionService loads session with merged state
  |
  |   app:* state available (project config, conventions)
  |   user:* state available (preferences, settings)
  |   session state available (feature list, batch status from last run)
  |
  v
SkillLoaderAgent
  --> loads relevant skills into session state (deterministic matching)
  |
  v
PreloadMemoryTool
  --> searches MemoryService for relevant cross-session context
  |
  v
plan_agent reads:
  {current_feature_spec}, {loaded_skills}, {memory_context}, {app:coding_standards}
  |
  v
code_agent reads:
  {implementation_plan}, {loaded_skills}, {app:coding_standards}
  |
  v
LinterAgent writes: lint_results to session state
TestRunnerAgent writes: test_results to session state
  |
  v
review_agent reads:
  {code_output}, {lint_results}, {test_results}, {loaded_skills}
  |
  v
Session complete
  --> add_session_to_memory() ingests learnings for future runs
```

Each step reads from and writes to session state. Agents communicate via state, not direct message passing. The event stream captures every state mutation for observability and rewind support.

---

## 7. Key Implementation Details

### 7.1 State Updates Are Event-Sourced

Never mutate `session.state` directly. Always write via `EventActions(state_delta={...})`. This ensures all changes are captured in the event stream and are rewind-safe.

```python
from google.adk.events import Event, EventActions

yield Event(
    author=self.name,
    actions=EventActions(state_delta={
        "lint_results": {"passed": True, "warnings": 3, "errors": 0},
        "lint_status": "passed",
    })
)
```

### 7.2 Memory Ingestion Is Explicit

Call `memory_service.add_session_to_memory(session)` at appropriate points -- after feature completion, after batch completion, at session end. Not every invocation needs to be ingested.

The ingestion strategy (after each feature, each batch, or session end) is an open question for Phase 1. See consolidated planning doc, Open Questions #10.

### 7.3 Rewind Limitations

Session rewind restores session-level state and artifacts but NOT `app:` or `user:` state. Since AutoBuilder's project conventions live in `app:` state and skills, a rewind does not accidentally erase global learnings. This is the right behavior for our use case.

External filesystem state is not managed by rewind. AutoBuilder handles this via git worktree isolation -- each parallel feature executes in its own worktree, so rewind within a feature pipeline does not affect other features.

### 7.4 Multiple Memory Services

ADK allows agents to access more than one `MemoryService`. This could be useful if AutoBuilder later needs separate stores for different knowledge types (e.g., code patterns vs. project decisions). Phase 1 uses a single `SqliteFtsMemoryService`.

### 7.5 Context Window Management

ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt. Two built-in mechanisms manage growth:

- **Context compression** -- sliding window summarization of older events (config-driven, interval + overlap)
- **Context caching** -- caches static prompt parts server-side (system instructions, knowledge bases)

**Gap identified:** ADK has no built-in context-window usage metric. Agents cannot reactively respond to "you are at 80% capacity." Solution: `before_model_callback` that token-counts the assembled `LlmRequest`, writes percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). Approximately 50 lines of code.

**Pipeline design implication:** For longer pipelines, agents should not rely on reading raw event history from prior steps. Better to use SkillLoaderAgent + explicit state writes so each agent gets precisely the context it needs, not the full event log.

---

## 8. Scope Estimate

**`SqliteFtsMemoryService`**: ~200-300 lines implementing `BaseMemoryService` with SQLite FTS5 backing.

The rest of the state and memory architecture (state scopes, session management, event-sourced updates, template injection, context compression) is native ADK. AutoBuilder uses it correctly rather than rebuilding it.

---

## 9. Related Documents

- Consolidated planning doc: `.dev/.discussion/260211_plan-shaping.md` (Section 11)
- Skills system: `.dev/07-TOOLS.md` (tools and deterministic agents)
- ADK Sessions & Memory overview: https://google.github.io/adk-docs/sessions/
- ADK State management: https://google.github.io/adk-docs/sessions/state/
- ADK Memory service: https://google.github.io/adk-docs/sessions/memory/
- ADK Session rewind: https://google.github.io/adk-docs/sessions/session/rewind/

---

*Document Version: 1.0*
*Last Updated: 2026-02-11*
