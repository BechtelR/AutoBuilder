# Hierarchical Supervision Architecture

The references to `05-AGENTS.md` in this historical document now correspond to `architecture/agents.md`.

*Date: 2026-02-14*
*Status: DECIDED — fundamental architecture change*
*Supersedes: Flat pipeline model in 02-ARCHITECTURE.md and 05-AGENTS.md*

---

## Problem Statement

The original vision (260114_plan-shaping.md, Problem #9) explicitly called for "lightweight agentic-team coordination patterns; director->workers, specialists, reflectors, reviewers, security, etc." ADK was chosen specifically because it supports hierarchical agent composition via `App` → `root_agent` → `sub_agents` tree, with native primitives for Coordinator/Dispatcher patterns and Hierarchical Task Decomposition.

However, when the architecture was formalized into `02-ARCHITECTURE.md` and `05-AGENTS.md`, this hierarchy was flattened into a sequential pipeline model with no supervisory layer between the user (CEO) and the execution pipeline. This contradicts the original vision and underutilizes ADK's native hierarchy capabilities.

## Decision

Introduce a **three-tier hierarchical supervision model** that maps directly to ADK's native agent tree:

```
CEO (dev user / human)
  └── Director (LlmAgent, opus) — root_agent of App
        ├── PM: Project Alpha (LlmAgent, sonnet) — per-project autonomous manager (IS the outer loop)
        │     └── DeliverablePipeline(s) — workers execute deliverables
        ├── PM: Project Beta (LlmAgent, sonnet)
        │     └── DeliverablePipeline(s) — workers execute deliverables
        └── [cross-project agents as needed]
```

### Tier Definitions

| Tier | Agent Type | Model | Role | Scope |
|------|-----------|-------|------|-------|
| **Director** | `LlmAgent` | opus | Cross-project governance, CEO liaison, strategic decisions, resource allocation | All projects, global settings |
| **PM** | `LlmAgent` | sonnet | Autonomous project management, batch strategy, quality oversight, worker supervision | Single project |
| **Workers** | `LlmAgent` + `CustomAgent` | varies | Execution — planning, coding, reviewing, linting, testing, formatting | Single deliverable |

### Key Design Principles

**1. Recursive Autonomy**
Each tier handles problems autonomously. Escalation is the exception, not the norm:
- Workers handle execution problems (lint failures, test failures, review feedback)
- PMs handle project problems (batch reordering, deliverable failures, retries, quality gate failures)
- Director handles cross-project problems (resource conflicts, priority shifts, pattern propagation)
- CEO handles only what Director truly cannot resolve (rare, due to accumulated memory)

**2. Director as root_agent**
~~The Director is the **permanent** root_agent of the ADK `App`. It is NOT created per execution — it is the persistent governance layer. This changes DD-2 in Phase 3: the App container with Director as root_agent is created at worker startup, not per workflow execution.~~ **Superseded by decision #40 (260216)**: Director is a stateless config object recreated per invocation. All state lives in DB via DatabaseSessionService. Personality in `user:` scope.

**3. PMs Need LLM Reasoning**
PMs are `LlmAgent` (sonnet), NOT `CustomAgent`. They need reasoning to:
- Decide batch strategy based on project context
- Handle unexpected failures without escalating every issue to Director
- Reorder deliverables based on discovered dependencies
- Assess quality gate failures and decide retry vs. escalate vs. skip

**4. Director Capabilities**
- Full observability into all active projects
- Can intervene directly in any project when patterns go wrong
- Accumulates multi-level memory (standards, project patterns, CEO preferences)
- Intelligently decides when to pause for CEO input (rare)
- Uses all necessary tools to resolve issues autonomously
- Publishes full logs of decisions and actions

**5. Hard Limits Cascade**
```
CEO sets global limits → Director operates within globals, sets per-project limits
Director sets project limits → PM operates within project limits
PM sets worker constraints → Workers execute within constraints
```

**6. Memory at Each Tier**
Follows the original 6-level memory architecture (260211_plan-shaping.md §11), applied at each tier's scope:

| Level | Director Scope | PM Scope | Worker Scope |
|-------|---------------|----------|--------------|
| Invocation (temp:) | Current decision cycle | Current batch management cycle | Current deliverable execution |
| Pipeline (session) | Cross-project governance state | Project execution state | Deliverable pipeline state |
| Project (app: + Skills) | Global conventions, all project configs | Project conventions, project skills | Deliverable-specific skills |
| User (user:) | CEO preferences, global settings | N/A (inherits from Director) | N/A (inherits from PM) |
| Cross-session (MemoryService) | Historical decisions, pattern library | Project history, past batch outcomes | Past deliverable patterns |
| Business (Skills) | Global skills, governance rules | Project skills, workflow skills | Task-specific skills |

### ADK Mapping

| Concept | ADK Primitive | Notes |
|---------|--------------|-------|
| Director as root | `App(root_agent=director_agent)` | Permanent, not per-execution |
| Director → PM delegation | `transfer_to_agent` or `AgentTool` | Director spawns/delegates to PMs |
| PM → Workers | `sub_agents` on PM | Workers are PM's children in tree |
| Supervision hooks | `before_agent_callback` / `after_agent_callback` | Director monitors PM events |
| Cross-project state | `app:` scope prefix | Visible to Director and all PMs |
| Project-scoped state | `session` scope | PM and its workers |
| Observability | ADK event stream | Director sees all events via stream |

### Model Routing by Tier

| Tier | Default Model | Rationale |
|------|--------------|-----------|
| Director | `anthropic/claude-opus-4-6` | Strategic decisions, cross-project reasoning |
| PM | `anthropic/claude-sonnet-4-5-20250929` | Project management, batch strategy |
| Worker (plan) | `anthropic/claude-opus-4-6` | Complex planning benefits from strongest reasoning |
| Worker (code) | `anthropic/claude-sonnet-4-5-20250929` | Standard implementation |
| Worker (review) | `anthropic/claude-sonnet-4-5-20250929` | Quality assessment |
| Worker (classify) | `anthropic/claude-haiku-4-5-20251001` | Quick classification |

## Impact on Existing Architecture

### Phase 3 (ADK Engine Integration) — Current Phase
- **DD-2 changes**: ~~App container is NOT created per execution. Director is the permanent root_agent. App created at worker startup with Director as root_agent.~~ **Superseded by decision #40**: App created per invocation with Director as root_agent (stateless config object).
- `create_app_container()` in Phase 3 still uses EchoAgent for validation — but the pattern must accommodate the Director becoming root_agent in Phase 5.
- Phase 3 spec's "Future Phase Extensions" section for `create_app_container()` must note Director as the production root_agent.

### Phase 5 (Agent Definitions) — Major Impact
- Director agent definition (LlmAgent, opus, root_agent)
- PM agent definition (LlmAgent, sonnet, per-project)
- Worker agent definitions (existing plan/code/review/fix agents remain, scoped under PM)
- Agent communication now hierarchical: Director → PM → Workers, not flat pipeline
- `sub_agents` tree construction replaces flat `SequentialAgent` at the top level

### Phase 8 (Spec Pipeline & Autonomous Loop) — Restructured
- The PM IS the outer loop — no separate orchestrator agent
- The "outer loop" is now at Director level (cross-project) and PM level (per-project)
- Director manages multiple concurrent projects
- PM manages the "while incomplete deliverables exist" loop for its project

### Phase 1 (Completed) — Retrospective Note
- P4 (Dynamic Outer Loop) validated the dynamic batch construction pattern — this is now the PM-level pattern, not the root_agent pattern. P4 validation still holds; it just maps to PM, not Director.

## What This Is NOT

- Not deferring hierarchy to a future phase — this is MVP, built from Phase 5 onward
- Not adding unnecessary complexity — ADK natively supports this; we're using it as designed
- Not creating abstractions we don't need — each tier has clear, distinct responsibilities

## Decisions Summary

| # | Decision | Rationale |
|---|----------|-----------|
| 29 | Director (LlmAgent, opus) as root_agent | Cross-project governance requires LLM reasoning; ADK App.root_agent is the natural home. (Originally "permanent"; superseded by #40: stateless, recreated per invocation.) |
| 30 | PMs (LlmAgent, sonnet) for per-project management | Autonomous project supervision requires reasoning, not just programmatic orchestration |
| 31 | Recursive autonomy at every tier | Each tier handles its problems; escalation is the exception |
| 32 | Director has full project observability | Can intervene when patterns go wrong; not blind delegation |
| 33 | Hard limits cascade CEO → Director → PM | Resource governance follows the hierarchy |
| 34 | 6-level memory applied per tier scope | Original memory architecture maps naturally to hierarchical supervision |
| 35 | All hierarchy is MVP scope | Not deferred; Director + PMs built in Phase 5, not Phase 8+ |

---

*This discussion was the result of identifying that the original hierarchical vision (260114_plan-shaping.md §9) was inadvertently flattened during architecture formalization. The hierarchy maps directly to ADK's native primitives (App → root_agent → sub_agents tree, Coordinator/Dispatcher pattern, Hierarchical Task Decomposition pattern) and restores the intended design.*
