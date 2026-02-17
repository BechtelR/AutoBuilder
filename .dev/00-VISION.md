# AutoBuilder Vision & Strategy

## Pitch

AutoBuilder is an autonomous agentic workflow system built on Google ADK that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. It supports pluggable workflow composition (auto-code, auto-design, auto-research, etc.), dynamic LLM routing across providers via LiteLLM, six-level progressive memory architecture, skill-based knowledge injection, and git worktree isolation for parallel execution. The system runs continuously from specification to verified output with optional human-in-the-loop intervention points.

The system exposes an API-first gateway (FastAPI) that owns the external contract. ADK runs behind an anti-corruption layer -- clients never see ADK internals. Workflow execution is out-of-process via ARQ workers backed by Redis. Interfaces (CLI and web dashboard) are pure API consumers over REST + SSE.

Unlike chat-based assistants that require constant human steering, AutoBuilder is a standalone orchestrator that runs autonomously from spec to verified deliverable. It treats deterministic tools (validators, test runners, formatters, etc.) as first-class workflow participants alongside LLM agents, guaranteeing that deterministic steps execute at prescribed pipeline stages regardless of LLM judgment.

---

## Core Differentiators

1. **Autonomous completion** -- "run until done" loop, not session-based human interaction
2. **Hierarchical agent supervision** -- CEO (user) → Director → PM → Workers; each tier autonomous with recursive problem-solving, mapped to ADK's native agent tree
3. **Deterministic + probabilistic composition** -- LLM agents and deterministic tools are equal workflow participants
4. **Spec-to-deliverable pipeline** -- specification to deliverable decomposition to parallel implementation to verified output
5. **Multi-model orchestration** -- route tasks to optimal models by capability
6. **Structured quality gates** -- validation, verification, and review cycles are guaranteed workflow steps, not LLM suggestions
7. **API-first architecture** -- gateway owns the contract; ADK is an internal implementation detail behind an anti-corruption layer
8. **Out-of-process execution** -- gateway enqueues work, ARQ workers execute pipelines, Redis Streams distribute events

---

## What AutoBuilder Is Not

- **Not a plugin for an existing editor/CLI** -- AutoBuilder is a standalone orchestrator that owns the full execution loop
- **Not a chat-based assistant** -- it is an autonomous executor, not a conversation partner requiring constant human prompting
- **Not a single-agent harness** -- it coordinates multi-agent teams with specialized roles across parallel and sequential workflows
- **Not an ADK wrapper** -- ADK is an internal engine behind the gateway's anti-corruption layer; clients never interact with ADK directly

---

## Problems Being Solved

| # | Problem | Description |
|---|---------|-------------|
| 1 | **Excessive human-in-the-loop** | Existing tools require constant human steering |
| 2 | **No intelligent orchestration** | Lack of hierarchical supervision and sequential vs parallel process coordination across agent teams |
| 3 | **Expensive autonomous alternatives** | Tools like Blitzy cost $10k+ per project |
| 4 | **Fragmented ecosystem** | Agent harnesses that do specific things instead of orchestrating multi-agent teams |
| 5 | **Insufficient quality control** | Too little verification and structured review in autonomous workflows |
| 6 | **Blocking on feedback** | Systems that halt entirely for human input when unrelated work could continue |
| 7 | **No shared memory architecture** | No multi-level context (business standards, project conventions, session state) |
| 8 | **Token waste** | Excessive human-friendly language when machine-formatted structures would suffice |
| 9 | **Over-reliance on LLM judgment** | Non-deterministic processing where scripts and tools should guarantee outcomes |
| 10 | **No progressive knowledge loading** | Agents either get everything or nothing, no task-appropriate context |

---

## Prior Art Analysis

### Frameworks Evaluated

| Framework | Key Strength | Key Weakness | Lesson for AutoBuilder |
|-----------|-------------|--------------|----------------------|
| **Autocoder** | Autonomous execution, spec to 150-400+ features, regression testing | Single agent, no parallelism, Claude-only | Spec-to-feature pipeline pattern; auto-continuation loop |
| **Automaker** | Git worktree isolation, dependency resolution, concurrent execution | Bloated (19 views, 32 themes, 150+ routes), no auto-continuation | Topological sorting; worktree isolation for parallel work |
| **SpecDevLoop** | Fresh context per iteration via ledger handoff | Subprocess overhead, Claude-only, single workflow | Ledger/handoff pattern (achievable without subprocess overhead) |
| **oh-my-opencode** | 11 specialized agents, multi-model fallback chains, plan/execute separation | 117k LOC, plugin coupling, no autonomous loop, no spec pipeline | Agent role restrictions; provider fallback chains; plan/execute boundary |

### Key Patterns Adopted from Prior Art

- **Provider fallback chains** (oh-my-opencode) -- 3-step resolution: user override, fallback chain, default
- **Plan/Execute separation** (oh-my-opencode) -- planning agents never write code; execution agents consume structured plans
- **Agent tool restrictions** (oh-my-opencode) -- read-only agents for exploration prevent scope creep
- **Git worktree isolation** (Automaker) -- true filesystem isolation for parallel code generation
- **Topological dependency sorting** (Automaker) -- features execute in dependency order
- **Spec-to-feature generation** (Autocoder) -- specification decomposed into 150-400+ implementable features
- **Auto-continuation loop** (Autocoder) -- run until all features complete, no human prompting needed

### Patterns Explicitly Avoided

- **Monolithic files** -- max ~500 per module
- **Hook/plugin systems as primary extension** -- prefer explicit workflow phases
- **Magic keyword triggers** -- structured config, not prompt keyword detection
- **Platform-specific binaries** -- pure Python, no native dependencies
- **Plugin coupling to host tools** -- standalone system, no external CLI dependency
- **GraphQL / gRPC at gateway layer** -- REST + SSE is sufficient; complexity not justified
- **Separate databases per interface** -- single database behind the gateway

---

## Terminology

Throughout this documentation, **deliverable** refers to any discrete, independently completable unit of work within a specification -- whether that's a software feature, a research report section, a design asset, or an investment strategy component. A specification is decomposed into deliverables, which are then executed in dependency-aware parallel batches.

---

*Document Version: 2.1*
*Last Updated: 2026-02-14*
