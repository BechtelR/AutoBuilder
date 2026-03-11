# Phase 1 Delta Report
*Generated: 2026-02-27*
*Phase status: DONE*
*Sources compared: PRD v6.0, Architecture v2.0, BOM v1.2.3*

## Summary

Phase 1 is an ADK validation phase — its deliverables (5 prototype tests, go/no-go decision) are insulated from most PRD and architecture changes. No PRD requirements affecting Phase 1's validation domain have changed. No BOM components are affected.

Four documentation gaps were identified, all in spec.md and model.md code examples that were not updated when the ADK state-write quirk was resolved during implementation. The actual code correctly uses `state_delta` throughout; the spec and model still show the pre-fix direct-write pattern. An additional test count inconsistency exists across the project status record, the decision doc, and the actual test suite.

All findings are documentation-only. No code changes are required.

---

## PRD Delta

### New Requirements (in scope)

| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|
| — | None | Phase 1's domain (validate ADK as orchestration engine) has no new PRD requirements. | No action |

*Evaluation*: Phase 1 covers NFR-3 (reliability/crash recovery, LLM provider fallback) and NFR-5 (framework choice validated). Both are present and unchanged in PRD v6.0 for Phase 1's purposes.

### Changed Requirements

| PR-N | What Changed | FR Affected | Action |
|------|-------------|-------------|--------|
| NFR-3 | PRD v6.0 added explicit language: "LLM reliability is AutoBuilder's responsibility — handled through heartbeats, retry hooks, and provider fallback." | None | No action — Phase 1 already validated provider fallback (P1.D7). Heartbeats and retry hooks are Phase 11 scope. |
| NFR-5 | PRD v6.0 added "Agent Skills standard skills install without code changes." | None | No action — Agent Skills is Phase 6 scope. Phase 1 validates framework choice only. |

### Dropped Requirements

| FR | Formerly traced to | Disposition |
|----|-------------------|-------------|
| — | None | No Phase 1 requirements trace to dropped PRD IDs. |

### Contract Drift

| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|
| All 4 contract items | No drift detected. All items (P1-P4 pass, P5 pass, go/no-go documented, ADK quirks documented) still aligned with current PRD. | No action |

---

## Architecture Delta

### Architecture Decisions That Supersede This Phase

| Architecture Section | Issue | Component Affected | Action |
|---------------------|-------|-------------------|--------|
| ERRATA.md #1 (state writes) | spec.md P1.D3 code example (lines 127-129) shows `ctx.session.state["lint_results"] = ...` + empty `state_delta={}`. Actual implementation uses populated `state_delta` dict (confirmed in `tests/phase1/test_p2_mixed_agents.py` lines 35-42). | spec.md P1.D3 | Update spec.md code example to reflect actual implementation. |
| ERRATA.md #1 (state writes) | spec.md P1.D5 code example (lines 231-235) shows direct `ctx.session.state["all_completed"] = ...` etc. Actual implementation uses `Event(actions=EventActions(state_delta={...}))` for all three keys (confirmed in `tests/phase1/test_p4_outer_loop.py` lines 106-115). | spec.md P1.D5 | Update spec.md code example to reflect actual implementation. |
| ERRATA.md #1 (state writes) | spec.md Research Notes "State Access in CustomAgent" (lines 389-398) documents "Write (direct)" as a valid pattern, contradicting Decision D9 (.decision-log.md, line 39) which was **REVISED** to say direct writes do NOT persist. | spec.md Research Notes | Mark "Write (direct)" as deprecated with note. |
| `_run_async_impl` type ignore (confirmed in test files) | model.md CustomAgent pattern (lines 99-102) shows `_run_async_impl` without `# type: ignore[override]`. Actual code uses this annotation (confirmed in both `test_p2_mixed_agents.py` line 28 and `test_p4_outer_loop.py` line 68). | model.md CustomAgent pattern | Add `# type: ignore[override]` to `_run_async_impl` signature. |

### New BOM Components

| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|
| — | — | — | Phase 1 has no BOM-assigned production components. It is a validation-only phase using prototype tests. |

### Dropped BOM Components

| Component ID | Deliverable | Status |
|-------------|-------------|--------|
| — | — | No BOM components dropped from Phase 1 scope. |

### Model Strings Verification

spec.md P1.D7 model strings verified against `06-PROVIDERS.md`:
- `openai/gpt-5-nano` — confirmed present in `06-PROVIDERS.md`
- `gemini/gemini-2.5-flash-lite` — confirmed present in `06-PROVIDERS.md`
- No drift detected.

### FunctionTool Import Path

spec.md Research Notes (line 337) documents `from google.adk.tools import FunctionTool`. ERRATA.md #7 documents the correct import as `from google.adk.tools.function_tool import FunctionTool`. Both forms are valid via re-export; Phase 4 production code uses the correct direct path. Flagged as a documentation note — minor.

---

## Additional Findings

### Test Count Inconsistency

Three artifacts report different test counts:
- **Project status record**: "11/11 tests pass with live LLM" — predates P1.D7 (P5 alternate providers, added as Batch 5)
- **phase1-decision.md**: "13 passed in 38.2s" — reflects P1-P4 (11) + partial P5 run (only one of two providers available at run time: 11 + 3 = 14, or possibly one test skipped = 13)
- **Actual test suite**: 17 test functions total (P1: 3, P2: 2, P3: 3, P4: 3, P5: 6)

The "11/11" in the project status record is the correct count for the core P1-P4 validation. "13 passed" reflects one P5 provider being available. The full suite has 17 functions, with P5 tests auto-skipping when provider keys are absent.

**Recommendation**: The project status record should be updated to clarify "11 core tests + up to 6 P5 provider tests (auto-skip when keys absent)."

---

## Artifact Changes Made

| Artifact | Section | Change | Rationale |
|----------|---------|--------|-----------|
| `spec.md` | P1.D3 code example | LinterAgent state writes corrected from direct assignment + empty `state_delta` to populated `EventActions(state_delta={...})` | Aligns documentation with actual implementation; removes misleading code example |
| `spec.md` | P1.D5 code example | OuterLoopAgent final state writes corrected from direct `ctx.session.state["key"] = ...` to `Event(actions=EventActions(state_delta={...}))` | Aligns documentation with actual implementation |
| `spec.md` | Research Notes "State Access in CustomAgent" | "Write (direct)" pattern marked as deprecated with ADK quirk note | Resolves internal contradiction with Decision D9; prevents future implementers from using the wrong pattern |
| `model.md` | State Keys Table (P1.D5 rows) | "Written By" column changed from "OuterLoopAgent direct write" to "OuterLoopAgent via `state_delta`" | Factually incorrect — actual code uses `state_delta`; the table documents what the code does |
| `model.md` | CustomAgent pattern | Added `# type: ignore[override]` to `_run_async_impl` signature | Aligns model with actual code (confirmed in test files) |

---

## Remediation Required (Code)

| # | Scope | What | Why |
|---|-------|------|-----|
| — | None | All Phase 1 code is correct. The findings are documentation drift only — the actual test implementations already use the correct `state_delta` pattern. | — |

---

## No Action Required

| Finding | Rationale |
|---------|-----------|
| FunctionTool import path (`from google.adk.tools` vs `from google.adk.tools.function_tool`) | Both forms work via re-export. Production code (Phase 4) uses the direct path. Phase 1 Research Notes import is a minor documentation imprecision that doesn't affect test execution. No update applied — the notes section covers both. |
| OuterLoopAgent superseded by PM-as-outer-loop | Already documented in model.md: "In production, PM (LlmAgent) absorbs this orchestration role." No further update needed. |
| NFR-3, NFR-5 text expansion | Both additions (heartbeats/retry hooks for NFR-3; Agent Skills standard for NFR-5) are Phase 6+ scope. Phase 1's validation of provider fallback and framework viability is complete and unaffected. |
| Model strings in P1.D7 spec | `openai/gpt-5-nano` and `gemini/gemini-2.5-flash-lite` confirmed against `06-PROVIDERS.md`. No drift. |
