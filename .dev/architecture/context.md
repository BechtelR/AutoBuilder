[← Architecture Overview](../02-ARCHITECTURE.md)

# Context Management

**AutoBuilder Platform**
**Context Assembly, Budgeting & Recreation Reference**

---

## Table of Contents

1. [Overview](#overview)
2. [InstructionAssembler Pipeline](#instructionassembler-pipeline)
3. [Context Assembly Lifecycle](#context-assembly-lifecycle)
4. [Knowledge Loading Layers](#knowledge-loading-layers)
5. [Context Loaders](#context-loaders)
6. [Context Budget Monitoring](#context-budget-monitoring)
7. [Context Recreation](#context-recreation)
8. [System Reminders](#system-reminders)
9. [Context Caching](#context-caching)
10. [Pipeline Design Implications](#pipeline-design-implications)

---

## Overview

Context management is a first-class architectural concern because LLM agents operate within finite context windows, and AutoBuilder runs long-lived autonomous pipelines. A deliverable pipeline that exhausts its context window mid-execution cannot simply fail -- it must gracefully recreate its working context and continue. Meanwhile, every token of context capacity is a scarce resource: irrelevant context dilutes agent attention and degrades output quality.

AutoBuilder's context strategy rests on three pillars:

1. **Structured assembly** -- the `InstructionAssembler` composes typed fragments from auditable sources, ensuring agents receive precisely the instructions they need (Decision #50)
2. **Progressive disclosure** -- skills and knowledge load only when relevant to the current task, not unconditionally (see [skills.md](./skills.md))
3. **Lossless recreation** -- when context fills up, the system persists durable state and rebuilds from scratch rather than using lossy summarization (Decision #52)

---

## InstructionAssembler Pipeline

All LLM agent instructions are composed from **typed fragments** by the `InstructionAssembler` (~100 lines). Each fragment carries a category, content, and audit source (Decision #50).

### Fragment Types

| Category | Source | Content | Lifecycle |
|----------|--------|---------|-----------|
| **SAFETY** | Hardcoded in InstructionAssembler | Core safety constraints, tool boundary enforcement, escalation protocol | Immutable, always prepended (Decision #55) |
| **IDENTITY** | Agent definition file body | Role, persona, behavioral boundaries | Static per agent role |
| **GOVERNANCE** | Agent definition file body | Hard limits, escalation rules, safety constraints | Static per agent role |
| **PROJECT** | Database (project entity) | Coding standards, conventions, project-specific patterns | Dynamic per invocation |
| **TASK** | Session state or node prompt file | Current deliverable spec, implementation plan, review feedback. In the node-based pipeline model (Phase 7b), loaded from the node's external prompt file. | Dynamic per invocation |
| **SKILL** | SkillLoaderAgent output | Loaded skill content, filtered by `applies_to` per agent role | Dynamic per invocation |

### Assembly Interface

```python
@dataclass
class InstructionFragment:
    fragment_type: str              # "safety", "identity", "governance", "project", "task", "skill"
    content: str
    source: str = ""                # Audit: where this came from

class InstructionAssembler:
    """Composes typed fragments into agent instructions."""

    def assemble(self, agent_name: str, body: str, ctx: InstructionContext) -> str:
        """Assemble full instructions from file body + dynamic context + skills.
        SAFETY fragment is always prepended (hardcoded, non-overridable).
        The body provides IDENTITY + GOVERNANCE base content.
        Filters skills by applies_to per agent role."""
```

### Constitutional Safety Layer (Decision #55)

The SAFETY fragment is hardcoded in the InstructionAssembler and cannot be overridden by any scope -- not by project-scope definition files, not by Director session state, not by skill content. It is the non-negotiable floor. The GOVERNANCE fragment in definition files carries agent-specific behavioral rules and CAN be overridden via the 3-scope cascade. SAFETY is the floor; GOVERNANCE is the ceiling.

### Source Auditability

Every fragment carries a `source` field. At any point you can trace exactly where every piece of an agent's instruction came from -- which definition file, which skill, which database entity, or "hardcoded" for SAFETY.

### Coexistence with ADK Layers

The assembler replaces ADK instruction layers 1 and 2 (static instruction string). Two ADK mechanisms coexist unchanged:

| Mechanism | Role | Status |
|-----------|------|--------|
| `before_model_callback` | Heavyweight runtime injection (file contents, codebase analysis, budget monitoring) | Coexists |
| `{key}` state templates | Direct state value injection within assembled output | Coexists -- ADK resolves at runtime |

The assembled instruction string may contain `{key}` placeholders (e.g., `{current_deliverable_spec}`). The assembler does NOT resolve these -- ADK resolves them at runtime from session state. The assembler escapes literal curly braces in SKILL and PROJECT fragments to prevent code syntax from being misinterpreted as state templates.

---

## Context Assembly Lifecycle

A complete picture of how an agent's context window goes from empty to fully assembled at invocation time:

```
Pipeline start
  │
  ├── 1. AgentRegistry.build()
  │     └── Scans definition files (3-scope cascade: global → workflow → project)
  │     └── Resolves frontmatter (name, type, model_role, tool_role, output_key)
  │     └── Extracts body content (IDENTITY + GOVERNANCE base)
  │
  ├── 2. InstructionAssembler.assemble()
  │     └── Prepends SAFETY fragment (hardcoded, Decision #55)
  │     └── Inserts IDENTITY + GOVERNANCE from definition file body
  │     └── Injects PROJECT fragment from database entity
  │     └── Injects TASK fragment from session state
  │     └── Filters and injects SKILL fragments by applies_to per agent role
  │     └── Escapes literal curly braces in SKILL/PROJECT content
  │     └── Result: assembled instruction string with {key} placeholders
  │
  ├── 3. SkillLoaderAgent (deterministic CustomAgent, workers only)
  │     └── Matches skills against current deliverable context (trigger matching)
  │     └── Resolves cascaded skill dependencies
  │     └── Writes loaded_skills (with applies_to metadata), loaded_skill_names to state
  │     └── (Director/PM receive skills at build time via SkillLibrary.match())
  │
  ├── 4. MemoryLoaderAgent (deterministic CustomAgent, runs second)
  │     └── Searches MemoryService for relevant cross-session context
  │     └── Writes memory_context to session state
  │
  ├── 5. ADK resolves {key} templates from session state
  │     └── {memory_context}, {current_deliverable_spec}, etc.
  │     └── (Skills are NOT injected via {loaded_skills} template -- they are composed
  │          directly into instructions as SKILL fragments by the assembler in step 2)
  │
  ├── 6. before_model_callback fires (right before each LLM call)
  │     └── ContextBudgetMonitor: token-counts LlmRequest, writes usage % to state
  │     └── System reminders: injects ephemeral nudges (Decision #53)
  │     └── File context, codebase analysis, test results (heavyweight injection)
  │
  └── 7. LLM receives: system instructions + session event history + tools
```

**Workflow variance (Phase 7a+):** The pipeline steps shown above reflect the auto-code workflow. Pipeline composition varies by workflow -- each workflow defines its own agent topology and stage schema. The context recreation mechanism is shared; the pipeline stages it recreates are workflow-provided.

State is populated in execution order before LLM agents read it:

```
SkillLoaderAgent    → state["loaded_skills"]              # deterministic, runs first
MemoryLoaderAgent   → state["memory_context"]              # searches MemoryService
PM writes           → state["current_deliverable_spec"]    # from batch selection
```

---

## Knowledge Loading Layers

AutoBuilder's knowledge loading is layered across six mechanisms, each serving a distinct role in context assembly:

| Layer | Mechanism | What It Loads | When |
|-------|-----------|---------------|------|
| 1 | `InstructionAssembler` base fragments | Safety constraints, identity, and governance instructions (SAFETY, IDENTITY, GOVERNANCE types; Decisions #50, #55) | Agent build time |
| 2 | `InstructionAssembler` dynamic fragments | Project context, task spec, matched skills (PROJECT, TASK, SKILL types; assembled at invocation time) | Invocation start |
| 3 | `before_model_callback` | File context, codebase analysis, test results (right before LLM call) | Each LLM call |
| 4 | `BaseToolset.get_tools()` | Different tools per deliverable type | Agent build time |
| 5 | Artifacts (`save_artifact`/`load_artifact`) | Large data (full file contents, generated code) | On demand |
| 6 | Context recreation | Persist to memory, fresh session, reassemble via InstructionAssembler (Decision #52) | Budget threshold hit |

### Relationship to InstructionAssembler Fragments

Layers 1-2 map directly to the 6 fragment types:

- **Layer 1** (base fragments): SAFETY, IDENTITY, GOVERNANCE -- static per agent role, determined at build time
- **Layer 2** (dynamic fragments): PROJECT, TASK, SKILL -- resolved per invocation from database, state, and skill matching

Layers 3-6 operate outside the assembler: callbacks inject at the LLM call boundary, tools are vended separately, artifacts bypass the instruction system entirely, and recreation is a lifecycle event that triggers a full reassembly.

No built-in RAG or vector store. For AutoBuilder, knowledge is deterministic lookup -- conventions from files, codebase via tools, specs via state, patterns from local directory. `InstructionAssembler` + callbacks are sufficient.

---

## Context Loaders

Two deterministic `CustomAgent` implementations guarantee context loading as pipeline steps, not LLM-discretionary tool calls.

### SkillLoaderAgent (Workers Only)

Runs as the first step in every `DeliverablePipeline` (worker tier only). Matches skills against the current deliverable context using deterministic pattern matching (exact string, glob, set intersection -- no LLM call). Writes loaded skill content with `applies_to` metadata to session state so the `InstructionAssembler` can filter per-agent at assembly time.

Director and PM receive skills at agent build time via direct `SkillLibrary.match()` calls, not via `SkillLoaderAgent`. See [skills.md](./skills.md) for full skill format, trigger matching, supervision-tier resolution, and three-tier library architecture.

### MemoryLoaderAgent (Decision #57)

Runs as the second step in every pipeline. Searches the `MemoryService` (PostgreSQL tsvector + pgvector) for relevant cross-session context -- project learnings, workflow expertise, past patterns. Writes results to session state.

This replaces the earlier `PreloadMemoryTool` design. As a deterministic CustomAgent, memory loading is guaranteed to execute and cannot be skipped by LLM judgment. Both loaders write to session state, making their output available to all downstream agents via `{key}` template injection.

---

## Context Budget Monitoring

ADK has no built-in context-window usage metric. Agents cannot reactively respond to "you are at 80% capacity."

**Solution**: `ContextBudgetMonitor` -- a `before_model_callback` (~50 lines) that:

1. Token-counts the assembled `LlmRequest` using LiteLLM's `token_counter(model, text)` for pre-call estimation
2. Compares against the model's context window limit (from LiteLLM's model registry)
3. Writes usage percentage to session state
4. When usage exceeds the configured threshold (default: 80%), triggers **Context Recreation** (see below)

Post-call, the LLM response's `usage.prompt_tokens` and `usage.completion_tokens` provide actual token counts. These are recorded for cost tracking and observability (see [observability.md §1](./observability.md)) but are not used for budget decisions -- by the time actuals arrive, the call has already been made. Budget decisions use pre-call estimates exclusively.

### Token Counting Mechanism

| Phase | Source | Method | Purpose |
|-------|--------|--------|---------|
| Pre-call | `LlmRequest` content | `litellm.token_counter(model, text)` | Budget threshold check |
| Post-call | LLM response | `response.usage.prompt_tokens`, `response.usage.completion_tokens` | Cost tracking, observability |

LiteLLM handles provider-specific tokenizer selection (tiktoken for OpenAI, Anthropic's tokenizer for Claude, etc.) behind a unified API. No direct tokenizer dependency needed.

### Trigger Mechanics

The `before_model_callback` fires synchronously before each LLM call. When the budget threshold is exceeded:

1. The callback raises a `ContextRecreationRequired` exception (custom, not an ADK type)
2. The worker's pipeline runner catches this exception at the pipeline level (not inside ADK's agent loop)
3. The runner executes the 4-step recreation process (see below)
4. After recreation, the pipeline resumes from the current agent step with a fresh session

This happens between turns -- the LLM call that would have exceeded the budget never fires. The `before_model_callback` is the gatekeeper.

The monitor fires before every LLM call, providing continuous visibility into context utilization. Budget warnings are surfaced as system reminders (Decision #53) before the threshold is hit.

---

## Context Recreation

**Decision #52** -- the primary strategy for managing context growth in long-running sessions.

### Why Recreation Over Compaction

Compaction (sliding window summarization) is inherently lossy -- a summary inevitably drops details. Context recreation is lossless reconstruction from durable state. The agent gets a full context window with precisely the information it needs, not a compressed approximation.

ADK's built-in `EventsCompactionConfig` remains as a fallback safety net, but it is not the primary strategy.

### The 4-Step Process

1. **Persist** -- progress markers, accumulated decisions, current plan, and learnings are saved to the memory service (durable storage). Session state keys (deliverable status, batch position, hard limits) are already durable via `DatabaseSessionService`.

2. **Seed** -- critical session state keys (deliverable status, batch position, hard limits, loaded skill names, project config) are copied from the old session to the new session before the old session is discarded. This is a key-by-key copy of durable state, not a full session clone -- conversation history is intentionally dropped.

3. **Fresh session** -- a new ADK session is created with the seeded state, discarding the bloated conversation history.

4. **Reassemble** -- `InstructionAssembler` reconstructs the system prompt from fragments; `SkillLoaderAgent` reloads skills; `MemoryLoaderAgent` restores cross-session context.

The agent picks up where it left off because everything that matters lives in durable stores (session state, memory service, skills).

### Dynamic Content Drift

Dynamic content (skill versions, memory search results) may differ if underlying data changed between sessions. This is correct behavior, not data loss -- the recreated context reflects the current state of the world.

### Degraded Mode

If `MemoryService` is unavailable during recreation, the agent proceeds with degraded context (state + skills + instructions, no cross-session memory). A system reminder is injected noting memory context is unavailable. This is strictly better than halting the pipeline.

---

## System Reminders

**Decision #53** -- ephemeral governance nudges injected into the conversation as tagged messages via `before_model_callback`. Inspired by Claude Code's `<system-reminder>` pattern.

System reminders are for **soft nudges**, not hard governance:

| Use Case | Example |
|----------|---------|
| Token budget warnings | "Context usage at 78%. Consider persisting important state." |
| State change notifications | "Deliverable D-003 status changed to BLOCKED by another worker." |
| Progress notes | "3 of 5 deliverables in current batch complete." |

Hard governance (safety constraints, escalation rules, behavioral boundaries) lives in IDENTITY and GOVERNANCE instruction fragments via `InstructionAssembler`. System reminders are **ephemeral by design** -- they are acceptable to lose during context recreation because they reflect transient conditions, not durable rules.

---

## Context Caching

ADK's `App` container supports `context_cache_config` to cache static prompt parts server-side. AutoBuilder uses this to cache:

- System instructions (the assembled instruction string, which is static within a session)
- Skill content (loaded once per pipeline, static thereafter)

This reduces token costs for repeated LLM calls within the same session by avoiding retransmission of static content. The cache is provider-dependent (e.g., Anthropic prompt caching, Google context caching).

See [engine.md](./engine.md) for `App` container configuration.

---

## Pipeline Design Implications

For longer pipelines, agents should NOT rely on reading raw event history from prior steps. The event log grows unboundedly and will eventually trigger context recreation, at which point conversation history is discarded.

**Instead**: use `SkillLoaderAgent` + explicit state writes so each agent gets precisely the context it needs, not the full event log. State keys survive context recreation (they are seeded into the new session). Event history does not.

This is also why agent communication flows through session state (`output_key`, `{key}` templates) rather than message passing -- state is durable and survives recreation; messages are transient.

---

## See Also

- [State & Memory](./state.md) -- ADK 4-scope state, multi-level memory, session persistence, `PostgresMemoryService`
- [Agents](./agents.md) -- agent hierarchy, definition files, `AgentRegistry`, instruction composition details
- [Skills](./skills.md) -- skill file format, trigger matching, progressive disclosure, three-tier library
- [Engine](./engine.md) -- `App` container, `EventsCompactionConfig`, `context_cache_config`
- [Observability](./observability.md) -- tracing, logging, event stream monitoring

---

*Document Version: 1.4*
*Last Updated: 2026-04-12*
