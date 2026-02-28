# Phase 2 Delta Report
*Generated: 2026-02-27*
*Phase status: DONE*
*Sources compared: PRD v6.0, Architecture v2.0, BOM v1.2.3*

## Summary

Phase 2 is a pure infrastructure phase — its deliverables (FastAPI gateway, async database layer, ARQ workers, logging, exceptions, Docker) are stable and not affected by upstream product changes. The PRD requirements in Phase 2's domain (NFR-4, NFR-5, NFR-6, and foundations for PR-9, PR-34) have not materially changed.

Three categories of drift were identified:

1. **Review-introduced implementation changes not reflected in docs**: The double-review pass (review.md) introduced several improvements — pure ASGI middleware replacing `BaseHTTPMiddleware`, bidirectional ORM relationships with `lazy="raise"`, FK indexes, and a non-root Docker user — that were never backported to spec.md or model.md.

2. **Phase 3 changes to Phase 2 components**: Phase 3 updated `app/gateway/deps.py` (ArqRedis replacing `redis.asyncio.Redis`) and added `app/gateway/routes/workflows.py`, and added `error_message` to the Workflow ORM model. Phase 2's docs still describe the pre-Phase-3 state.

3. **Stale Dockerfile pattern**: spec.md Research Notes Dockerfile pattern shows `python:3.11-slim` and unpinned `uv:latest`, but the actual `Dockerfile` uses `python:3.12-slim` and pinned `uv:0.9`.

All findings are documentation-only. No code changes are required.

---

## PRD Delta

### New Requirements (in scope)

| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|
| — | None | No new product requirements fall in Phase 2's infrastructure domain. | No action |

*Evaluation*: All new PRD requirements (PR-1–PR-37) covering agents, workflows, CEO queue, memory, skills, etc. are assigned to later phases. NFR-4, NFR-5, NFR-6 — the three requirements Phase 2 most directly satisfies — remain in scope and unchanged.

### Changed Requirements

| PR-N | What Changed | FR Affected | Action |
|------|-------------|-------------|--------|
| NFR-3 | PRD v6.0 added: "LLM reliability is AutoBuilder's responsibility — handled through heartbeats, retry hooks, and provider fallback." | None | No action — Phase 2 already implements the heartbeat cron (W09). Retry hooks and provider fallback are Phase 11 scope. |
| NFR-5 | PRD v6.0 added: "Third-party workflow plugins and Agent Skills standard skills install without code changes." | None | No action — Agent Skills is Phase 6 scope; workflow plugins are Phase 7+. Phase 2's API-first gateway is the correct foundation. |

### Structural PRD Changes (No Phase 2 Impact)

PRD v6.0 also introduced structural changes that do not affect Phase 2's completed scope:

| Change | Scope Impact |
|--------|-------------|
| "Specification" renamed to "Brief" throughout | None — Phase 2's `specifications` table is correctly named (it stores the raw content; "Brief" is the product-level concept). No Phase 2 deliverable changes. |
| New PR-8 inserted (resource pre-flight validation before execution begins), renumbering old PR-8–PR-37 to PR-9–PR-37 | None — Phase 2's infrastructure doesn't implement any PR-8 functionality. The roadmap already uses the current PR-N numbering. |
| Information Architecture section restructured; added Workflow Stage, Phase, Batch, Completion Report as first-class entities | None — all new entities are Phase 5–8 scope. Phase 2's three minimal ORM models (specifications, workflows, deliverables) are correctly scoped. |

### Dropped Requirements

| FR | Formerly traced to | Disposition |
|----|-------------------|-------------|
| — | None | No Phase 2 requirements trace to dropped PRD IDs. |

### Contract Drift

| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|
| All 6 contract items | No drift. All items verified against current architecture (gateway starts, worker starts, migrations run, Redis PING, enqueue round-trip, quality gates pass). | No action |

---

## Architecture Delta

### Architecture Decisions That Supersede This Phase

| Architecture Section | Issue | Component Affected | Action |
|---------------------|-------|-------------------|--------|
| Review pass (review.md F1) | `BaseHTTPMiddleware` replaced with pure ASGI classes. Actual implementations: `ErrorHandlingMiddleware(app: ASGIApp)` with `__call__(scope, receive, send)` and `RequestLoggingMiddleware` with the same signature. The review.md documents this change as fixing SSE response buffering. spec.md Research Notes "Key Import Paths" (line ~415) still lists `from starlette.middleware.base import BaseHTTPMiddleware`. model.md error middleware interface (line ~129) shows a function signature `async def error_handling_middleware(request, call_next)` — the wrong pattern. | spec.md Research Notes, model.md Error Middleware | Update spec.md to note BaseHTTPMiddleware NOT used. Update model.md to show ASGI class pattern. |
| Phase 3 gateway update | Phase 3 replaced `redis.asyncio.Redis` with `ArqRedis` as the single gateway Redis client. The lifespan now calls `await create_pool(redis_settings)` and stores `app.state.arq_pool: ArqRedis`. A new `get_arq_pool() -> ArqRedis` dependency was added alongside the existing `get_redis()`. spec.md DD-5 still says "A single `redis.asyncio.Redis` instance created at gateway startup." | spec.md DD-5 | Add note documenting Phase 3 supersession. |
| Phase 3 gateway update | model.md Gateway Dependencies (line ~108) shows `get_redis() -> Redis: # type: ignore[type-arg]` using `redis.asyncio.Redis`. After Phase 3, this still exists but the underlying value is `ArqRedis`. A new `get_arq_pool() -> ArqRedis` dependency was added but is not in model.md. | model.md Major Interfaces | Add note and document `get_arq_pool()` as Phase 3 addition. |
| Review pass (review.md) | Bidirectional `relationship()` with `lazy="raise"` were added to ORM models. FK columns were marked with `index=True`. model.md ORM Models section (lines ~306–328) shows only column definitions — no `relationship()` calls, no index annotations. | model.md ORM Models | Add note documenting review-introduced additions. |
| Review pass (review.md) | Non-root Docker user (`appuser`, UID 1000) was added as a security improvement. The actual `Dockerfile` creates and switches to `appuser` (lines 22-23, 38). spec.md P2.D8 requirements list (lines ~222–226) makes no mention of this. | spec.md P2.D8 | Add note documenting non-root user requirement. |
| Phase 3 migration | Phase 3 added migration `002_add_workflow_error_message.py` which adds `error_message: Mapped[str | None]` to the `Workflow` ORM model. spec.md DD-3 and model.md ORM Models (Workflow section) do not include this column. | spec.md DD-3, model.md ORM Models | Add note documenting Phase 3 column addition. |
| spec.md Research Notes (line ~370) | Dockerfile pattern shows `FROM python:3.11-slim` (builder stage) and `ghcr.io/astral-sh/uv:latest` (unpinned). The actual `Dockerfile` uses `FROM python:3.12-slim` for both stages and `ghcr.io/astral-sh/uv:0.9` (pinned per review.md fix #10). | spec.md Research Notes | Update Python version and uv pin in Dockerfile example. |

### New BOM Components

| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|
| — | — | — | No new BOM components have been added to Phase 2's domain. |

*Note*: M20 (Redis connection pool) and O02 (structured logging) are both `✓` Phase 2 components in the BOM but were not previously enumerated in this phase's documentation. Both are correctly covered: M20 by P2.D5/P2.D7 (ArqRedis pool in lifespan), O02 by P2.D1 (JsonFormatter, setup_logging, get_logger). No action needed.

### Dropped BOM Components

| Component ID | Deliverable | Status |
|-------------|-------------|--------|
| — | — | No BOM components assigned to Phase 2 have been dropped. |

---

## Artifact Changes Made

| Artifact | Section | Change | Rationale |
|----------|---------|--------|-----------|
| `spec.md` | Research Notes "Key Import Paths" | Replaced `BaseHTTPMiddleware` import with note: "NOT USED — pure ASGI middleware classes used instead (SSE-safe)". Added correct import pattern. | Prevents future implementers from using the wrong middleware pattern; review.md F1 established this as a critical fix. |
| `spec.md` | DD-5 (Redis Client Management) | Added delta note: Phase 3 superseded `redis.asyncio.Redis` with `ArqRedis` via `create_pool()`. | Aligns DD-5 with current implementation; prevents confusion when reading Phase 3+ code. |
| `spec.md` | P2.D8 (Dockerfile) requirements | Added note: non-root `appuser` (UID 1000) was added during code review as a security practice. | Surfaces security requirement that was implicit in review.md but absent from the deliverable spec. |
| `spec.md` | DD-3 (Database Models) | Added delta note: Phase 3 added `error_message: Mapped[str | None]` to `Workflow` via migration `002_add_workflow_error_message.py`. | Documents Phase 3 schema extension to Phase 2's table. |
| `spec.md` | Research Notes (Dockerfile pattern) | Updated both stages: `FROM python:3.11-slim` → `FROM python:3.12-slim`, `ghcr.io/astral-sh/uv:latest` → `ghcr.io/astral-sh/uv:0.9`. | Aligns documentation with actual `Dockerfile` (Python 3.12, pinned uv per review.md fix #10). |
| `model.md` | Error Middleware interface | Updated `error_handling_middleware` function signature → `ErrorHandlingMiddleware` pure ASGI class pattern with `__init__(self, app: ASGIApp)` and `__call__(scope, receive, send)`. | Matches actual `app/gateway/middleware/errors.py` implementation (ASGI class, not middleware function). |
| `model.md` | Gateway Dependencies interface | Added `get_arq_pool() -> ArqRedis` alongside `get_redis()`. Added delta note about Phase 3 ArqRedis supersession. | Documents Phase 3 dependency addition; `get_arq_pool()` is the canonical way to get the pool after Phase 3. |
| `model.md` | ORM Models (Specification, Workflow, Deliverable) | Added note about bidirectional `relationship()` with `lazy="raise"`, FK `index=True`, and Phase 3 `error_message` column. | Documents review-introduced relationship pattern and Phase 3 schema change. |

---

## Remediation Required (Code)

| # | Scope | What | Why |
|---|-------|------|-----|
| — | None | All Phase 2 code is correct (or superseded correctly by Phase 3). All findings are documentation drift. | — |

---

## No Action Required

| Finding | Rationale |
|---------|-----------|
| NFR-3, NFR-5 text expansion | Both additions (heartbeats/retry hooks for NFR-3; workflow plugins/Agent Skills for NFR-5) are Phase 6+ scope. Phase 2's infrastructure foundation is complete and correct. |
| "Specification" → "Brief" rename in PRD | Phase 2's `specifications` table is correctly named — it stores the raw content. The product-level "Brief" concept is Phase 5 scope (BOM: D05, G10-G14). No Phase 2 deliverable changes. |
| PR-8 insertion (renumbering old PR-8 → PR-9) | Roadmap already uses current PRD IDs (PR-9, PR-34 for Phase 2). No documentation drift. |
| Gateway routes drift (Phase 3 additions) | `POST /workflows/run` and associated models were added in Phase 3. Phase 2 model.md documents only Phase 2 scope. Accumulated drift is a Phase 3 concern, not Phase 2. |
| M20 (Redis connection pool), O02 (structured logging) BOM coverage | Both are correctly implemented by Phase 2 deliverables. Missing from audit enumeration only — no coverage gap. |
| `get_redis()` return type still `Redis` after Phase 3 | `ArqRedis` is a superset of `Redis`; existing `get_redis()` callers are unaffected. The function signature `get_redis() -> Redis` with `type: ignore[type-arg]` continues to work. The new `get_arq_pool()` is the canonical post-Phase-3 accessor — documented in model.md now. |
