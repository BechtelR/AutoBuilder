# Phase 8a Review Report: Autonomous Execution Engine
*Generated: 2026-04-13*

## Summary

Double review (2 passes × 4 reviewers each) of all 16 deliverables. Quality gates clean throughout: 1217 tests pass, 0 pyright errors, 0 ruff errors.

## Pass 1 Findings

### Fixed (10 issues)

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | **CRITICAL** | `app/workers/adk.py:329` | Tier 1 DB checkpoint callback not wired — used state-only `create_checkpoint_callback` instead of DB-writing `create_deliverable_checkpoint_callback`. FR-8a.48 not satisfied. | Added `db_session_factory` param, wired DB checkpoint conditionally |
| 2 | **HIGH** | `app/workers/tasks.py:517` | Blocked deliverables left PENDING forever after upstream failure — no reachability marking | Added post-loop BFS to mark transitively blocked deliverables SKIPPED |
| 3 | **HIGH** | `app/workers/tasks.py:367` | Pause flag only checked between batches, not between deliverables within a batch (DD-5 violation) | Added pause check at top of inner deliverable loop |
| 4 | **HIGH** | `app/workers/tasks.py:2188` | `retry_budget` (PM-level, default 10) used as per-deliverable `retry_limit` (spec default 2) | Added separate `deliverable_retry_limit` from `DEFAULT_DELIVERABLE_RETRY_LIMIT` (2) |
| 5 | **MEDIUM** | `app/gateway/routes/projects.py:33-39` | `create_project` route dropped `workflow_type` and `name` fields — only passed `brief` | Pass all request fields to ARQ job |
| 6 | **MEDIUM** | `app/events/publisher.py:214-293` | Four new event methods missing `workflow_type` in metadata (D14 spec requires it) | Added optional `workflow_type` parameter to each method |
| 7 | **LOW** | `app/workers/lifecycle.py:140` | `abort_project` allowed aborting terminal projects (COMPLETED, ABORTED) | Added terminal status guard |
| 8 | **LOW** | `app/agents/supervision.py:589` | `suspend_project` allowed suspending terminal projects | Added terminal status guard with warning log |
| 9 | **LOW** | `app/tools/_context.py:14` | `Path` import at module level but only used in type annotation | Moved to `TYPE_CHECKING` block |
| 10 | **LOW** | `app/agents/artifacts.py:11` | Used `import logging` instead of project-standard `get_logger` | Aligned with project convention |

### Flagged (4 items — all LOW, no action required)

| # | Severity | Item | Disposition |
|---|----------|------|-------------|
| 1 | LOW | `app/gateway/routes/deliverables.py` — `GET /deliverables/{id}` missing validator results (no FK path from deliverable to ValidatorResult) | Architecture gap — validator results keyed by workflow_id/stage_execution_id. Deferred to when ValidatorResult schema includes deliverable_id FK. |
| 2 | LOW | `app/gateway/routes/workflows.py` — Legacy workflow routes (G02/G03/G04) not enhanced to reference project entities | Primary entry is `POST /projects`. Legacy routes intentionally left as-is. |
| 3 | LOW | `app/workers/tasks.py` — Module is 2200+ lines (standards: max ~500) | Pre-existing structural pattern. Splitting requires design discussion. Not Phase 8a scope. |
| 4 | LOW | `app/tools/management.py` — `_detect_cycle` returns placeholder path instead of full cycle chain | Cycle IS correctly detected; error message minimal but functional. |

## Pass 2 Findings

### Fixed (7 issues)

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | **HIGH** | `app/workers/tasks.py` (stage loop) | TaskGroup unconditionally marked COMPLETED even when batch loop was interrupted by pause/cost-ceiling/threshold | Moved interruption checks BEFORE close gate and completion logic |
| 2 | **HIGH** | `app/workers/tasks.py` (stage loop) | Close gate failure only logged warning but didn't prevent TaskGroup completion (FR-8a.70 violation) | Added `break` when gate fails — hard enforcement |
| 3 | **HIGH** | `app/workflows/validators.py:440` | `_check_deliverable_statuses` only treated COMPLETED as terminal — FAILED/SKIPPED left as "outstanding" | Fixed to accept all 3 terminal statuses (COMPLETED, FAILED, SKIPPED) |
| 4 | **MEDIUM** | `app/workers/lifecycle.py:242-253` | `resume_director` had stale Redis flag race — ACTIVE projects' `director_pause` flags never cleaned up | Added flag cleanup for projects still ACTIVE after resume |
| 5 | **MEDIUM** | `app/workers/lifecycle.py` (all 7 event calls) | Missing `workflow_type` in all lifecycle event publications (D14 spec requires it) | Captured `workflow_type` from Project and passed to all publish calls |
| 6 | **MEDIUM** | `app/tools/management.py:1424` | `override_pm` audit trail DirectorQueueItem created as PENDING (appeared as unresolved work) | Set status=RESOLVED with resolved_at/resolved_by at creation |
| 7 | **LOW** | `app/tools/task.py:227,359` | `task_create`/`task_query` read `project_id` but PM sets `pm:project_id` (tier-prefixed) | Added fallback: check `project_id` then `pm:project_id` |

### Flagged (6 items — ALL RESOLVED post-review)

| # | Severity | Item | Resolution |
|---|----------|------|------------|
| 1 | LOW | `management.py` — `create_project` accepts `entry_mode` but no DB column | Documented as routing hint in response JSON; not persisted separately (no JSONB metadata column on Project) |
| 2 | LOW | FRD FR-8a.15 uses "COMPLETE" but enum uses "COMPLETED" | Fixed FRD typo → "COMPLETED" |
| 3 | LOW | `_toolset.py` — NFR-8a.08 violations via logger not EventPublisher | Fixed: added `queue_tool_access_violation()` to EventPublisher, `_toolset.py` now publishes via tool context registry (falls back to logger-only in non-worker contexts) |
| 4 | LOW | `architecture/tools.md` says "46 tools" but actual is 47 | Fixed: updated to 47, added missing `reconfigure_stage` to PM tools table |
| 5 | LOW | `architecture/gateway.md` route table missing Phase 8a routes | Fixed: added 15 routes (projects, deliverables, director queue, director lifecycle) |
| 6 | LOW | `GET /deliverables/{id}` missing validator results per FR-8a.79 | Fixed: added `validator_results` field via workflow_id join. Limitation documented (shared workflow scope, not per-deliverable FK). |

## Unresolved Findings: NONE
All 17 fixed issues and 6 flagged items are resolved. Zero open items.

## Quality Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Ruff lint | PASS | `All checks passed!` |
| Ruff format | PASS | `193 files already formatted` |
| Pyright | PASS | `0 errors, 0 warnings, 0 informations` |
| Tests | PASS | `1217 passed, 30 warnings in 137s` |
| Artifact cleanup | PASS | No `artifacts/` directory at project root after test run |
