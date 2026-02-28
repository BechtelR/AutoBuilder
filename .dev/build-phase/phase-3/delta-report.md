# Phase 3 Delta Report
*Generated: 2026-02-27*
*Phase status: DONE*
*Sources compared: PRD v6.0, Architecture v2.0, BOM v1.2.3*

## Summary

Phase 3 is the ADK integration phase. Its 35 BOM components are explicitly mapped in the spec's BOM Coverage table, and the spec's Research Notes document verified ADK import paths against the installed package. The PRD requirements in Phase 3's domain (PR-9, PR-34, NFR-3, NFR-4, NFR-5) have not materially changed.

Three categories of drift were identified:

1. **Undocumented utility consolidation**: `parse_redis_settings` was consolidated into `app/config/settings.py` and exported from `app.config` during Phase 3 (documented in Phase 3 spec P3.D1 delta note). The function originated in Phase 2 as a private worker helper; Phase 3's DD-8 (ArqRedis gateway integration) required the gateway to also parse Redis URLs, motivating the move to shared config. Not documented in Phase 3's spec requirements.

2. **Undocumented constants**: `SYSTEM_USER_ID`, `INIT_SESSION_ID`, and `APP_NAME` were added to `app/models/constants.py` (documented in Phase 3 spec P3.D6 delta note). Phase 3's spec P3.D6 uses string literals (`"system"`, `"autobuilder"`) without referencing these constants. `INIT_SESSION_ID = "__init__"` is specifically used for `app:` scope initialization (DD-12) but is not mentioned in the spec.

3. **Undocumented worker startup DB engine**: Worker startup creates `db_engine` and `db_session_factory` (SQLAlchemy) for direct Workflow table access by `run_workflow`. Phase 3's spec worker startup requirements (lines ~293–296) only list `DatabaseSessionService` and `LlmRouter` initialization — the SQLAlchemy engine/session factory is absent.

All findings are documentation-only. No code changes are required.

---

## PRD Delta

### New Requirements (in scope)

| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|
| — | None | No new product requirements fall in Phase 3's ADK integration domain. | No action |

*Evaluation*: Phase 3 satisfies PR-9 (observable async work queues — Redis Streams publishing established), PR-34 (persistent replayable event stream — per-workflow Redis Streams via `workflow:{id}:events`), NFR-3 (crash recovery — ResumabilityConfig + DatabaseSessionService for session persistence), NFR-4 (credentials never logged — EventPublisher ACL, structured logging), NFR-5 (gateway API as sole external contract — ADK types never in gateway models). All are unchanged in PRD v6.0.

### Structural PRD Changes (No Phase 3 Impact)

| Change | Scope Impact |
|--------|-------------|
| "Specification" renamed to "Brief" throughout PRD | None — Phase 3 does not implement any spec/brief routes. |
| New PR-8 inserted (resource pre-flight validation), renumbering old PR-8→PR-9 | None — roadmap already uses current PRD IDs. |
| Information Architecture: new entities (WorkflowStage, Phase, Batch, Completion Report) | None — all new entities are Phase 5–8 scope. |

### Changed Requirements

| PR-N | What Changed | FR Affected | Action |
|------|-------------|-------------|--------|
| NFR-3 | PRD v6.0 added: "LLM reliability is AutoBuilder's responsibility — handled through heartbeats, retry hooks, and provider fallback." | None | No action — heartbeats in Phase 2 (W09), retry hooks and provider fallback are Phase 11 scope. Phase 3's ResumabilityConfig and 3-step fallback chain address the provider fallback requirement. |

### Contract Drift

| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|
| All 5 contract items | No drift. All items verified against current architecture (gateway enqueues ADK jobs, LLM Router selects models, Claude responds via LiteLLM, session state persists, ADK events published to Redis Streams). | No action |

---

## Architecture Delta

### Architecture Decisions That Supersede This Phase

| Architecture Section | Issue | Component Affected | Action |
|---------------------|-------|-------------------|--------|
| Phase 3 spec DD-8 (ArqRedis integration): `parse_redis_settings` consolidation | Phase 3's spec doesn't mention this utility. It originated as a private `_parse_redis_settings()` in `app/workers/settings.py` (Phase 2). Phase 3's DD-8 (ArqRedis gateway integration) required the gateway to also parse Redis URLs, so the function was made public, moved to `app/config/settings.py`, and exported from `app.config`. Undocumented in Phase 3's spec requirements. | spec.md Research Notes | Add note documenting `parse_redis_settings()` consolidation. |
| Phase 3 spec P3.D6: constants `SYSTEM_USER_ID`, `INIT_SESSION_ID`, `APP_NAME` | Phase 3's spec P3.D6 uses string literals `user_id="system"` and `app_name="autobuilder"`. Actual implementation uses `SYSTEM_USER_ID` and `APP_NAME` constants from `app.models.constants`. `INIT_SESSION_ID = "__init__"` is used for the `app:` scope initialization session (DD-12) but not mentioned in the spec. | spec.md P3.D6 | Delta note added to spec P3.D6. |
| Worker startup implementation | Worker `on_startup` creates `db_engine` and `db_session_factory` (SQLAlchemy) in worker context for `run_workflow` to read/write `Workflow` records directly. Phase 3's spec worker startup requirements (~line 293–296) only list `DatabaseSessionService` and `LlmRouter` initialization — the SQLAlchemy session factory is absent from the spec. | spec.md P3.D6 | Add delta note to P3.D6 worker startup requirements. |
| ~~`search_provider` field~~ | ~~Phase 0 delta-report incorrectly attributed `search_provider` to Phase 3.~~ **Correction**: `search_provider` is a Phase 4 addition (explicitly documented in Phase 4's spec P4.D2). No Phase 3 action. Phase 0 delta-report corrected. | N/A | No action for Phase 3. |

### New BOM Components

| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|
| — | — | — | No new BOM components have been added to Phase 3's domain. |

### Dropped BOM Components

| Component ID | Deliverable | Status |
|-------------|-------------|--------|
| — | — | No BOM components assigned to Phase 3 have been dropped. |

### BOM Coverage Verification

All 35 Phase 3 BOM components explicitly mapped in spec.md's BOM Coverage table (line ~387–427): G21, D04, D11, E01, E04-E07, E09, E12-E15, W03-W08, V01-V02, R01-R04, A44, A71, M01-M04, M22, M25-M26, O04. No coverage gaps.

### Model String Verification

Phase 3 model strings verified against `06-PROVIDERS.md`:
- `"anthropic/claude-sonnet-4-6"` — confirmed (CODE, REVIEW roles)
- `"anthropic/claude-opus-4-6"` — confirmed (PLAN role / Director)
- `"anthropic/claude-haiku-4-5-20251001"` — confirmed (FAST role, LlmEventSummarizer)
- No drift detected.

### ADK Import Path Verification

Phase 3 spec Research Notes (lines ~431–468) explicitly document verified ADK import paths against the installed package. No import path drift identified. The more specific paths (e.g., `from google.adk.apps.app import EventsCompactionConfig, ResumabilityConfig`) supersede the shorthand shown in engine.md (which is architecturally illustrative, not implementation-verified).

---

## Artifact Changes Made

| Artifact | Section | Change | Rationale |
|----------|---------|--------|-----------|
| `spec.md` | P3.D1 requirements | Added delta note: `parse_redis_settings()` consolidated to `app/config/settings.py` and exported from `app.config` during Phase 3 (DD-8 ArqRedis integration). Phase 4 also adds `search_provider` to Settings — that is Phase 4's change, not Phase 3's. | Aligns Research Notes with Phase 3 implementation. |
| `spec.md` | P3.D6 requirements | Added delta note: actual implementation uses `APP_NAME` and `SYSTEM_USER_ID` constants from `app.models.constants` instead of string literals. `INIT_SESSION_ID = "__init__"` used for `app:` scope initialization session (DD-12). Worker startup also creates `db_engine` and `db_session_factory` for direct Workflow table access — absent from spec requirements. | Prevents future implementers from hardcoding strings when constants are available; surfaces undocumented startup resource. |
| `phase-0/delta-report.md` | .env.example Drift §3 | Corrected "(added by Phase 3)" → "(added by Phase 4)" for `search_provider` field attribution. | Factual correction: Phase 4's spec P4.D2 explicitly adds `search_provider` to Settings. |

---

## Remediation Required (Code)

| # | Scope | What | Why |
|---|-------|------|-----|
| — | None | All Phase 3 code is correct. Findings are documentation-only. | — |

---

## No Action Required

| Finding | Rationale |
|---------|-----------|
| NFR-3 text expansion | Heartbeats are Phase 2's W09. Phase 3's ResumabilityConfig covers crash recovery. Retry hooks and advanced provider fallback are Phase 11. No Phase 3 deliverable affected. |
| engine.md App Container shows `TokenTrackingPlugin()` | Phase 3 adds `LoggingPlugin()` only. `TokenTrackingPlugin` is Phase 11 scope (BOM E08). engine.md shows the production config; Phase 3 implements the first plugin. No drift. |
| ADK import path differences between spec and engine.md | Phase 3 spec documents implementation-verified paths against the installed package (the correct source of truth). engine.md is architecturally illustrative. No action needed on spec. |
| `INIT_SESSION_ID` constant — used by Phase 3 | `INIT_SESSION_ID = "__init__"` is used by Phase 3's worker `on_startup` for `app:` scope initialization (DD-12) — the session ID for the initialization session that writes `app:skill_index` and `app:workflow_registry`. Documented in spec P3.D6 delta note. No additional action needed. |
