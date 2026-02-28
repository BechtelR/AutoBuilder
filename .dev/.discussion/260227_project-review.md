# Project Review — AutoBuilder

*Date: 2026-02-27*
*Status: CONCLUDED*

---

## Context

End-to-end review of the AutoBuilder architecture and implementation state following completion of Phase 4 (Core Toolset). 273 tests passing, all quality gates clean.

---

## Findings & Discussion

### Strengths (confirmed)

- **ADK Anti-Corruption Layer** — best architectural decision in the codebase. ADK fully contained in `app/workers/adk.py`; swappable without cascading changes.
- **Real infrastructure in tests** — PostgreSQL and Redis are real, not mocked. Skip-when-unavailable is the right compromise.
- **Type safety chain** — SQLAlchemy → Pydantic → OpenAPI → hey-api → TypeScript is complete and correct.
- **Redis Streams for events** — persistence + consumer groups + replay-on-reconnect solves real production problems.
- **Stateless agents + DB-backed sessions** — correct use of ADK; enables crash recovery without bespoke state.
- **Enum convention (values = names)** — prevents OpenAPI serialization breakage.

---

### Point 1: PM outer loop is probabilistic

**Raised**: The PM is an `LlmAgent` controlling the execution outer loop. Batch selection, dependency ordering, retry decisions are all LLM-mediated — most critical orchestration path trusted to the least reliable component.

**Proposed**: A deterministic `CustomAgent` for the outer loop, with PM as a *policy advisor* (not a controller).

**Response**: The PM must be intelligent and dynamic. Deterministic guardrails on an LLM-controlled loop would still require the LLM to make the decisions.

**Resolved**: The PM stays LLM-controlled. Deterministic safety is already addressed via `after_agent_callback` (`verify_batch_completion`, `checkpoint_project`) and the `RegressionTestAgent` (CustomAgent) wired into each pipeline. These enforce invariants without removing PM intelligence. Decision #38/#39 already cover this correctly. Point withdrawn.

---

### Point 2: Tools built before agents exist

**Raised**: 42 tools built in Phase 4 before any agents exist in Phase 5 — tools may need redesigned signatures when agents are actually composed.

**Response**: Defining the full tool surface before composing agents is intentional — it establishes the vocabulary agents work in. Phase 4 validates this vocabulary.

**Resolved**: Valid architectural sequence. Point withdrawn.

---

### Point 3: Memory deferred to Phase 9

**Raised**: Cross-session searchable memory is a core differentiator but agents run without it for phases 5–8.

**Response**: The agent framework and workflows must be operational before the memory system can function end-to-end.

**Resolved**: Infrastructure-first sequencing is correct. Point withdrawn.

---

### Point 4: Long runway to first useful output

**Raised**: First user-facing workflow (auto-code) is Phase 7 — significant investment before proving the value proposition.

**Response**: Delayed gratification is how robust systems are built. E2E workflow tests can validate the vertical path earlier.

**Resolved**: Accepted. E2E workflow integration tests should be added between phases to provide early validation without compromising phase sequencing.

---

### Point 5: LLM verification framed as "mandatory gates"

**Raised**: Three-layer verification (functional correctness, architectural conformance, contract completion) — layers 2 and 3 are LLM-judged, not deterministic. Framing them as "mandatory gates" implies guarantees the system can't provide.

**Response**: Intelligent verification requires LLMs. There is no alternative for architectural conformance checks.

**Resolved**: LLM verification is the right tool. The framing concern stands but is a documentation issue, not an architectural one. "Mandatory quality gates" should distinguish between deterministic gates (linting, tests — hard pass/fail) and probabilistic checks (LLM review — signal, not guarantee). Update verification documentation to reflect this distinction.

**Action**: Update `architecture/agents.md` verification section to clarify deterministic vs. probabilistic gate semantics.

---

### Point 6: Cost controls deferred to Phase 11

**Raised**: With 42 tools, multiple LLM calls per deliverable, and parallel batch execution — cost can spiral before Phase 11 instrumentation arrives.

**Response**: This is the inherent cost of a system of this nature.

**Resolved**: Accepted in principle. Lightweight token logging (model + token count per call) should be added as part of Phase 5 agent setup, not deferred to full Langfuse integration in Phase 11. No new infrastructure required — structured log fields are sufficient for early cost visibility.

**Action**: Add structured token logging to LlmRouter and ARQ task context in Phase 5.

---

### Point 7: Gateway reads as a pure work-queue

**Raised**: The implemented gateway (`POST /workflows/run → 202 Accepted`) reads as a fire-and-forget work queue. The Director requires a conversational, session-oriented interface — a fundamentally different interaction model not visible in the implementation.

**Response**: Spec-shaping precedes all execution processes and is a separate interaction model. The concern is valid but misread as a concurrent-process issue.

**Resolved**: The concern is correct. The gateway needs to implement the Director chat interface as a distinct interaction model from the workflow queue. This is a gap between the architecture docs (which already define `/chat/{session_id}/messages` in `architecture/gateway.md`) and the current implementation.

**Decision #49**: The gateway implementation must reflect both interaction models:
1. **Work-queue model** (`/workflows`, `/specs`) — fire-and-forget, async execution
2. **Conversational model** (`/chat`) — session-oriented, streaming Director responses via SSE

These are not equivalent and must not be conflated. New DB models (`Chat`, `ChatMessage`) and gateway routes (`/chat`) are required. See `.todo/260228_pre-phase-5.md`.

---

## Decisions Recorded

| # | Decision | Date |
|---|----------|------|
| 49 | Gateway implements two distinct interaction models: work-queue (`/workflows`) and conversational (`/chat`); Director interface requires session-oriented routes with SSE streaming, distinct from job enqueueing | 2026-02-27 |

---

## Open Actions

| Action | Owner | Phase |
|--------|-------|-------|
| Implement `/chat` gateway routes, `Chat`/`ChatMessage` DB models, Pydantic contracts | — | Phase 5 pre-work |
| Update `architecture/agents.md` verification section: deterministic gates vs. probabilistic LLM checks | — | Phase 5 pre-work |
| Add structured token logging (model + token count) to LlmRouter and worker task context | — | Phase 5 |
| Add E2E workflow integration test (smoke test) between Phase 5 and 6 | — | Phase 5 exit |
