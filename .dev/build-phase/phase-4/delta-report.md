# Phase 4 Delta Report
*Generated: 2026-02-27*
*Phase status: DONE*
*Sources compared: PRD v6.0, Architecture v2.0, BOM v1.2.3*

## Summary

Phase 4 is the Core Toolset phase — 42 FunctionTools across 8 categories with an ADK-native `GlobalToolset`. Its 62 BOM components are explicitly mapped in the spec's BOM Coverage table. The PRD requirements in Phase 4's domain have not materially changed.

Two categories of drift were identified, both introduced by the Phase 4 code review:

1. **Typed enum promotion**: The Phase 4 review (Reviewer 1) replaced string-literal validation sets (`VALID_*: set[str]`) with 6 new `StrEnum` types: `EscalationPriority`, `EscalationRequestType`, `CeoItemType`, `DependencyAction`, `PmOverrideAction`, `GitWorktreeAction`. This promotion was flagged as `[SPEC-UPDATE]` in review.md. The spec's P4.D6 requirement line 363 states "Validation uses string comparison against known values (not enum imports — CEO/Director queue enums arrive in Phase 5)" which is now outdated. Management tool signatures in spec and model still show `str` for typed parameters. The 6 enums implement BOM components V20 and V21 plus additional unplanned typed enum promotions. V22 (Director queue status enum) remains unimplemented -- see Remediation Required.

2. **Function signature additions**:
   - `git_worktree(path: str, action: str, ...)` — spec and model use `action: str`; review added `GitWorktreeAction` typed enum
   - `web_search(query: str, num_results: int = 5)` — spec and model are missing `provider: str | None = None` optional parameter added by the review (flagged as `[SPEC-UPDATE]` in review.md)

3. **Security additions not documented in spec**:
   - `http_request` and `web_fetch`: SSRF protection via `urlparse` scheme check (http/https only), introduced by Reviewer 3
   - Path containment: `validate_path()` changed from `str.startswith()` to `Path.relative_to()` by Reviewer 1

Most findings are documentation-only. One code gap requires remediation: BOM component V22 (Director queue status enum) is assigned to Phase 4 but has no implementation in `app/models/enums.py`.

---

## PRD Delta

### New Requirements (in scope)

| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|
| — | None | No new product requirements fall in Phase 4's tool execution domain. | No action |

*Evaluation*: Phase 4 satisfies the tool execution layer requirements. The PRD structural changes (Specification renamed to Brief throughout, new PR-8 resource pre-flight validation inserted before old PR-8, new Information Architecture entities WorkflowStage/Phase/Batch/Completion Report) do not affect Phase 4's deliverables — all new entities are Phase 5–8 scope.

### Changed Requirements

| PR-N | What Changed | FR Affected | Action |
|------|-------------|-------------|--------|
| NFR-3 | PRD v6.0 added: "LLM reliability is AutoBuilder's responsibility — handled through heartbeats, retry hooks, and provider fallback." | None | No action — heartbeats in Phase 2 (W09), retry hooks and provider fallback are Phase 11 scope. Phase 4's idempotency guards (E11) address tool-level resume reliability. |

### Contract Drift

| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|
| All contract items (9) | No drift. All items verified: 42 tools callable from LlmAgent, schemas auto-generated, role filtering correct, bash_exec timeout/capture verified, code intelligence verified, three-tier task system verified, PM escalation path verified, Director management signatures verified, fix_agent role permissions verified. | No action |

---

## Architecture Delta

### Architecture Decisions That Supersede This Phase

| Architecture Section | Issue | Component Affected | Action |
|---------------------|-------|-------------------|--------|
| Phase 4 review.md `[SPEC-UPDATE]` item 1 | Reviewer 1 added 6 new `StrEnum` types (`EscalationPriority`, `EscalationRequestType`, `CeoItemType`, `DependencyAction`, `PmOverrideAction`, `GitWorktreeAction`) replacing `VALID_*: set[str]` validation constants in `management.py`. spec.md P4.D6 requirement line 363 reads "Validation uses string comparison against known values (not enum imports — CEO/Director queue enums arrive in Phase 5)" — this note is now outdated. Management tool function signatures in spec.md P4.D6 and model.md still show `str` for all enum-typed parameters. | spec.md P4.D6, model.md Management tool signatures, model.md CEO/Director Queue Validation Constants | Add delta note to spec P4.D6. Update model.md signatures and constants sections. |
| Phase 4 review.md `[SPEC-UPDATE]` item 2 | `web_search` was extended with an optional `provider: str \| None = None` parameter by the review. spec.md P4.D4 requirement line 283 and model.md line 217 both show `web_search(query: str, num_results: int = 5)` — missing `provider` parameter. | spec.md P4.D4, model.md web_search signature | Add delta note to spec P4.D4. Update model.md web_search signature. |
| Phase 4 review.md Reviewer 1 | `git_worktree(path: str, action: str, ...)` — review added `GitWorktreeAction` typed enum for the `action` parameter. spec.md P4.D3 line 257 uses `action: str`. model.md line 207 also shows `action: str`. | spec.md P4.D3, model.md git_worktree signature | Add delta note to spec P4.D3. Update model.md git_worktree signature. |
| Phase 4 review.md Reviewer 3 | `http_request` has SSRF protection: `urlparse(url).scheme` is checked to allow only `http` and `https`. Rejected schemes return a clear error string. Not mentioned in spec P4.D2 requirements or model.md. | spec.md P4.D2 | Add delta note to spec P4.D2. |
| Phase 4 review.md Reviewer 1 | Path containment validation changed from `str.startswith(project_root)` to `Path(path).relative_to(project_root)` — the `Path.relative_to()` approach is robust to symlinks and path normalization edge cases that `startswith` misses. spec.md P4.D1 mentions path validation but doesn't specify the method. model.md Notes section mentions path validation without specifics. | spec.md P4.D1 | Add delta note to spec P4.D1. |

### New BOM Components

| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|
| — | — | — | No new BOM components beyond the 62 already mapped. The 6 review-added typed enums implement V20 and V21 (2 of 3 planned Director queue enums) and promote 3 additional string validations to typed enums (CeoItemType, DependencyAction, GitWorktreeAction). V22 (Director queue status enum) was planned in the BOM but not implemented — see Remediation Required. |

### Dropped BOM Components

| Component ID | Deliverable | Status |
|-------------|-------------|--------|
| — | — | No BOM components assigned to Phase 4 have been dropped. |

### BOM Coverage Verification

62 Phase 4 BOM components are in the spec BOM Coverage table (lines ~477–541): T01-T40 (42 tools, some with b/c suffixes), TM01-TM07 (7 modules), TS01-TS09 (9 toolset components), V20-V22 (3 Director queue enums), E11 (idempotent tool execution guards).

**Coverage gap found — V22:** `07-COMPONENTS.md` defines V22 as "Director queue status enum (`PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO`)" and assigns it to Phase 4. V20 and V21 are implemented: `EscalationRequestType` (V20: type enum) and `EscalationPriority` (V21: priority enum) both exist in `app/models/enums.py`. V22 has no corresponding enum implementation — no enum with values `PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO` exists. The spec's BOM Coverage table marks V22 as covered by P4.D6, but the code evidence does not support this. **Code remediation required — see Remediation Required section.**

### `web_fetch` SSRF Protection (also affected — not just `http_request`)

Reviewer 3 added SSRF protection to **both** `http_request` (execution.py) and `web_fetch` (web.py). The spec P4.D4 `web_fetch` requirements also need a delta note, and P4.D2 should note both tools received SSRF protection.

### `search_provider` Attribution Confirmed

spec.md P4.D4 explicitly documents `search_provider` as a Phase 4 Settings addition (`Settings has search_provider: str defaulting to "tavily"`). Phase 0 delta-report was corrected in a prior audit cycle (Phase 0 delta-report §Settings class verification now reads "added by Phase 4"). Phase 3 delta-report correctly attributes this as Phase 4. No further action.

---

## Artifact Changes Made

| Artifact | Section | Change | Rationale |
|----------|---------|--------|-----------|
| `spec.md` | P4.D1 requirements | Added delta note: path containment uses `Path.relative_to()` not `str.startswith()` (Reviewer 1 security fix). | Prevents future maintainers from reverting to the weaker validation pattern. |
| `spec.md` | P4.D2 requirements | Added delta note: `http_request` has SSRF protection — `urlparse` scheme check allows only http/https (Reviewer 3). | Security fix not visible from spec; delta note makes it discoverable. |
| `spec.md` | P4.D4 requirements | Added delta note: `web_fetch` also has SSRF protection via `urlparse` scheme check (same Reviewer 3 addition, applied to both execution tools). | Reflector found `web_fetch` was also updated in web.py; initial delta note only covered `http_request`. |
| `spec.md` | P4.D3 requirements | Added delta note: `git_worktree` action parameter is `GitWorktreeAction` (typed enum, `ADD \| LIST \| REMOVE`), not bare `str` (Reviewer 1 `[SPEC-UPDATE]`). | Explicit `[SPEC-UPDATE]` flag in review.md. |
| `spec.md` | P4.D4 requirements | Added delta note: `web_search` accepts optional `provider: str \| None = None` parameter to override the configured default (Reviewer `[SPEC-UPDATE]`). | Explicit `[SPEC-UPDATE]` flag in review.md. |
| `spec.md` | P4.D6 requirements | Added delta note: actual implementation uses 6 typed `StrEnum` types instead of string-comparison validation sets. Requirement line 363 ("Validation uses string comparison against known values") is outdated. Management tool signatures updated to show typed enum parameters (Reviewer 1 `[SPEC-UPDATE]`). | Explicit `[SPEC-UPDATE]` flag in review.md; prevents Phase 5 from duplicating already-done enum promotion. |
| `model.md` | Tool Function Signatures — Git | Updated `git_worktree` signature: `action: str` → `action: GitWorktreeAction`. | Matches implementation. |
| `model.md` | Tool Function Signatures — Web | Updated `web_search` signature: added `provider: str \| None = None`. | Matches implementation. |
| `model.md` | Tool Function Signatures — Management | Updated management tool signatures to use typed enums: `escalate_to_director(priority: EscalationPriority, ...)`, `manage_dependencies(action: DependencyAction, ...)`, `escalate_to_ceo(item_type: CeoItemType, priority: EscalationPriority, ...)`, `override_pm(..., action: PmOverrideAction, ...)`. | Matches implementation; prevents Phase 5 from generating incorrect API signatures. |
| `model.md` | CEO/Director Queue Validation Constants | Replaced `VALID_*: set[str]` sections with typed enum references. Added note that Phase 4 review promoted these to `StrEnum`. | Keeps model current with review changes. |
| `model.md` | Tool Parameter Enums | Added 6 new enums: `EscalationPriority`, `EscalationRequestType`, `CeoItemType`, `DependencyAction`, `PmOverrideAction`, `GitWorktreeAction`. | Matches implementation; makes enums discoverable for Phase 5 integration. |

---

## Remediation Required (Code)

| # | Scope | What | Why |
|---|-------|------|-----|
| 1 | `app/models/enums.py` + `app/tools/management.py` | Add `DirectorQueueStatus` enum (or equivalent) with values `PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO` | BOM component V22 ("Director queue status enum") is assigned to Phase 4 and listed as covered by P4.D6 in the BOM Coverage table, but no corresponding enum exists in `app/models/enums.py`. All 6 review-added enums are verified against 07-COMPONENTS.md — V22 is the only gap. Management tools that track Director queue item lifecycle will need this type in Phase 5; defining it in Phase 4 completes the BOM obligation. |

---

## No Action Required

| Finding | Rationale |
|---------|-----------|
| NFR-3 text expansion | Heartbeats are Phase 2's W09. Phase 4's E11 idempotency guards cover tool-level resume. Retry hooks and advanced provider fallback are Phase 11. No Phase 4 deliverable affected. |
| V20 and V21 BOM component names vs enum names | BOM names map correctly: V20 → `EscalationRequestType`, V21 → `EscalationPriority`. Delta note in spec P4.D6 records these mappings. V22 is a code gap — handled in Remediation Required. |
| PRD structural changes (Specification→Brief, PR-8 insertion, new entities) | All structural changes affect Phase 5+ scope. Phase 4's tool execution domain is unchanged. |
| `search_provider` — Phase 4 attribution | Confirmed correct. P4.D4 is the definitive source. Phase 0 and Phase 3 delta-reports already corrected in prior audit cycle. |
| `T40b` vs `T40` BOM ID | spec.md lists `T40` (`query_dependency_graph`) consistently. BOM Coverage table at spec line 546 shows `T40 | query_dependency_graph`. P4.D6 BOM Components at spec line 346 also shows `T40`. `T40` is the canonical ID for `query_dependency_graph`. |
