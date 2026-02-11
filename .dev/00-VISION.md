# AutoBuilder Vision & Strategy

## Pitch

AutoBuilder is an autonomous agentic workflow system built on Google ADK that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. It supports pluggable workflow composition (auto-code, auto-design, auto-research, etc.), dynamic LLM routing across providers via LiteLLM, six-level progressive memory architecture, skill-based knowledge injection, and git worktree isolation for parallel execution. The system runs continuously from specification to verified output with optional human-in-the-loop intervention points. Built as a Python engine with TypeScript UI.

Unlike chat-based coding assistants that require constant human steering, AutoBuilder is a standalone orchestrator that runs autonomously from spec to verified software. It treats deterministic tools (linters, test runners, formatters) as first-class workflow participants alongside LLM agents, guaranteeing that quality gates execute at the right time regardless of LLM judgment.

---

## Core Differentiators

1. **Autonomous completion** -- "run until done" loop, not session-based human interaction
2. **Deterministic + probabilistic composition** -- LLM agents and deterministic tools are equal workflow participants
3. **Spec-to-software pipeline** -- specification to feature decomposition to parallel implementation to verified output
4. **Multi-model orchestration** -- route tasks to optimal models by capability
5. **Structured quality gates** -- linting, testing, review cycles are guaranteed workflow steps, not LLM suggestions

---

## What AutoBuilder Is Not

- **Not a plugin for an existing editor/CLI** -- AutoBuilder is a standalone orchestrator that owns the full execution loop
- **Not a chat-based coding assistant** -- it is an autonomous executor, not a conversation partner requiring constant human prompting
- **Not a single-agent harness** -- it coordinates multi-agent teams with specialized roles across parallel and sequential workflows

---

## Problems Being Solved

| # | Problem | Description |
|---|---------|-------------|
| 1 | **Excessive human-in-the-loop** | Existing tools (Claude Code, Cursor, chat LLMs) require constant human steering |
| 2 | **No intelligent orchestration** | Lack of sequential vs parallel process coordination across agent teams |
| 3 | **Expensive autonomous alternatives** | Tools like Blitzy cost $10k+ per project |
| 4 | **Fragmented ecosystem** | Agent harnesses that do specific things instead of orchestrating multi-agent teams |
| 5 | **Insufficient quality control** | Too little reflection, verification, and structured review in autonomous workflows |
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

- **Monolithic files** -- max ~300 lines per module
- **Hook/plugin systems as primary extension** -- prefer explicit workflow phases
- **Magic keyword triggers** -- structured config, not prompt keyword detection
- **Platform-specific binaries** -- pure Python, no native dependencies
- **Plugin coupling to host tools** -- standalone system, no external CLI dependency

---

## Architecture Decisions Log

All major decisions recorded with rationale and date.

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | SDK over headless CLI | Less overhead, better parallelism, native streaming, multi-model support | 2026-01-14 |
| 2 | New app, not modified Automaker | Reuse architectural patterns, skip complexity debt | 2026-01-14 |
| 3 | Multi-workflow architecture | Future-proof for auto-design, auto-market, etc. | 2026-01-14 |
| 4 | Standalone orchestrator, not plugin | Plugin coupling is fragile; autonomous loop needs full control | 2026-01-14 |
| 5 | Plan/Execute phase separation | Strict role boundaries proven by oh-my-opencode's Prometheus/Atlas | 2026-01-14 |
| 6 | Agent role-based tool restrictions | Read-only exploration agents prevent scope creep | 2026-01-14 |
| 7 | Provider fallback chains | 3-step resolution (user, chain, default) is proven and pragmatic | 2026-01-14 |
| 8 | Python for core engine | Agent ecosystem is Python-first; all candidate frameworks are Python-native | 2026-02-11 |
| 9 | TypeScript only for UI | Dashboard/web UI layer, separate concern from orchestration engine | 2026-02-11 |
| 10 | No custom provider abstraction | Both Pydantic AI and Google ADK handle multi-model natively; building our own is unnecessary | 2026-02-11 |
| 11 | Claude Agent SDK rejected | It is an agent harness (single Claude agent), not a workflow orchestrator; Claude-only, TS-only | 2026-02-11 |
| 12 | Google ADK selected as framework | Unified composition of LLM agents + deterministic tools; first-class workflow primitives | 2026-02-11 |
| 13 | Phased MVP delivery | Targeting all 15+ features simultaneously risks bloat; MVP focuses on 6 core capabilities | 2026-02-11 |
| 14 | Skills system as Phase 1 component | Agents without skills are generic; skills produce project-appropriate output from day one | 2026-02-11 |
| 15 | Workflow composition system as Phase 1 | Workflows must be pluggable from day one; hardcoding auto-code then bolting on others later would require ripping out assumptions | 2026-02-11 |
| 16 | MCP used sparingly | MCPs add significant context bloat; prefer lightweight FunctionTools; use agent-browser for browser automation | 2026-02-11 |
| 17 | LLM Router for dynamic model selection | Different tasks benefit from different models; route by capability/cost/speed, not hardcoded model strings | 2026-02-11 |
| 18 | ADK App class as application container | App provides lifecycle management, context compression, resumability, plugin registration -- use as the top-level container | 2026-02-11 |
| 19 | Multi-level memory as Phase 1 | Agents must accumulate learnings across features and sessions; without memory, feature 47 cannot know what patterns features 1-10 established | 2026-02-11 |

---

*Document Version: 1.0*
*Last Updated: February 2026*
