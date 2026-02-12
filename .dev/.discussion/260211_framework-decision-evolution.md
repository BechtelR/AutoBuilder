# AutoBuilder: Framework Decision Evolution

**Date**: 2026-02-11
**Status**: Active Research
**Supersedes/Amends**: Sections 6, 7, 10, 11, 12 of `260114_plan-shaping.md`

---

## 1. What Changed Since Initial Planning

The initial plan (Jan 14) made several decisions that need revision based on deeper research and ecosystem evolution:

### 1a. Language Decision: Python, Not TypeScript

The initial architecture (Sections 5, 7) was written entirely in TypeScript. After evaluation, **Python is the correct choice for the core orchestration engine**.

**Why Python wins for AutoBuilder:**
- Every serious agent framework lives in Python (Pydantic AI, Google ADK, LangGraph, CrewAI, AutoGen)
- Pydantic AI — the leading lean framework — is Python-native
- Google ADK's most mature implementation is Python
- The agent ecosystem's tooling, examples, and community are overwhelmingly Python
- Async Python (asyncio) handles concurrent agent execution well

**TypeScript remains appropriate for:**
- Dashboard/web UI layer (if/when built)
- Any browser-based agent tools (Playwright, accessibility tree testing)
- These are separate concerns from the core orchestration engine

**Impact:** Sections 5 and 7 architecture diagrams should be re-read as conceptual, not literal. Implementation will be Python.

### 1b. Don't Build a Custom Provider Abstraction Layer

Section 6 designed a custom provider abstraction with four separate provider implementations (ClaudeProvider, AnthropicProvider, OpenAIProvider, OllamaProvider). This is **unnecessary engineering**.

Both Pydantic AI and Google ADK already solve multi-model routing natively:
- **Pydantic AI** supports 20+ providers out of the box via built-in model connectors
- **Google ADK** supports multi-model via LiteLLM integration and direct SDK wrappers

Building our own provider layer means writing wrapper code around wrapper code. The framework handles this — our energy should go toward the novel orchestration patterns that make AutoBuilder unique.

**Impact:** Section 6's "Provider Abstraction Layer" decision is superseded. The chosen framework's built-in multi-model support will be used instead. Capability-based routing logic remains valid but will be implemented within the framework's patterns, not as a standalone abstraction.

### 1c. Framework Selection Needs Final Resolution

The initial plan assumed Claude Agent SDK as the primary, with provider abstraction bolted on. Research shows this is wrong:
- Claude Agent SDK is an **agent harness** (powers a single Claude agent), not a **workflow orchestrator**
- It's Claude-only, TypeScript-only, and provides no workflow/graph primitives
- It's the wrong tool for multi-agent, multi-model, autonomous orchestration

Two strong candidates have emerged for serious evaluation:
1. **Pydantic AI** (+ pydantic-graph)
2. **Google ADK**

See `260211_technical-spike-adk-vs-pydantic.md` for the full comparison.

### 1d. MVP Scope Must Be Ruthless

The capability comparison table (Section 8) targets ✅ on 15+ major capabilities simultaneously. oh-my-opencode attempted similar breadth and hit 117k LOC. AutoBuilder's < 100k LOC target requires phased delivery.

**MVP (Phase 1) — Core Loop:**
1. Framework integration (chosen SDK) with multi-model support
2. Plan/Execute agent separation
3. Autonomous continuation loop ("run until done")
4. Git worktree isolation for parallel execution
5. Spec-to-deliverable pipeline (from Autocoder patterns)
6. Basic CLI interface

**Phase 2 — Production Hardening:**
7. Durable execution / checkpointing
8. Cost/token tracking per deliverable and agent
9. Agent role-based tool restrictions
10. Context budget management

**Phase 3 — Scale & Polish:**
11. Web dashboard
12. Additional workflow types (auto-design, auto-market)
13. Self-learning / self-correcting patterns
14. Advanced memory (vector DB + graph)

---

## 2. Updated Decisions Log

Appended to Section 11 of the original document:

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 9 | Python for core engine, TS for UI only | Agent ecosystem is Python-first; all candidate frameworks are Python-native | 2026-02-11 |
| 10 | Use framework-native multi-model support, not custom provider abstraction | Both Pydantic AI and Google ADK handle this natively; building our own is unnecessary engineering | 2026-02-11 |
| 11 | Claude Agent SDK rejected as primary framework | It's an agent harness, not a workflow orchestrator; Claude-only, TS-only, no workflow primitives | 2026-02-11 |
| 12 | Phased MVP delivery required | Targeting all 15+ capabilities simultaneously risks bloat; MVP focuses on 6 core capabilities | 2026-02-11 |
| 13 | Final framework choice: Pydantic AI vs Google ADK (pending spike) | Both are model-agnostic, Python-first, code-first; need head-to-head evaluation | 2026-02-11 |

---

## 3. Updated Open Questions

Supersedes/amends Section 10:

| # | Question | Status |
|---|----------|--------|
| 1 | Lib sharing strategy (monorepo vs copy) | Open — less relevant now that core is Python, not TS |
| 2 | Feature file format | Open |
| 3 | Spec parsing sophistication | Open |
| 4 | Regression strategy | Open |
| 5 | UI priority | **Resolved: CLI-first, dashboard is Phase 3** |
| 6 | Workflow packaging | Open |
| 7 | Agent role system granularity | Open — Phase 2 |
| 8 | Context budget strategy | Open — Phase 2 |
| 9 | Cost tracking | **Resolved: Yes, Phase 2** |
| 10 | **NEW: Pydantic AI vs Google ADK** | **Active research — see technical spike** |
| 11 | **NEW: Google ADK privacy/telemetry concerns** | Active research — Apache 2.0 licensed but "optimized for Gemini" |
| 12 | **NEW: Reuse Automaker TS libs or rewrite in Python?** | Open — language change affects lib reuse strategy |
| 13 | **NEW: Durable execution strategy** | Open — Pydantic AI has Temporal/DBOS; ADK has DatabaseSessionService |

---

## 4. Updated Next Steps

Supersedes Section 12:

1. [x] Identify candidate frameworks (Pydantic AI, Google ADK)
2. [ ] **Complete technical spike comparison** (see `260211_technical-spike-adk-vs-pydantic.md`)
3. [ ] Make final framework selection
4. [ ] Prototype: basic agent loop with chosen framework + Claude model
5. [ ] Prototype: parallel agent execution with git worktree isolation
6. [ ] Prototype: plan/execute agent separation
7. [ ] Design spec-to-deliverable pipeline (adapt Autocoder patterns to Python)
8. [ ] Build MVP CLI
9. [ ] Evaluate Automaker lib reuse vs Python rewrite for git-utils, dependency-resolver

---

## 5. References

- Technical spike: `260211_technical-spike-adk-vs-pydantic.md`
- Original plan: `260114_plan-shaping.md`
- Prior SDK research: Claude project chat history (Agent SDK research conversations, Jan 2026)
