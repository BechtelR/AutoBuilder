# Phase 0 Delta Report
*Generated: 2026-02-27*
*Phase status: DONE*
*Sources compared: PRD v6.0, Architecture v2.0, BOM v1.2.3, 03-STRUCTURE.md v1.5*

## Summary

Phase 0 is a pure infrastructure phase — its deliverables (pyproject.toml, docker-compose, Alembic, Settings, shared models, pre-commit, scaffold) are stable and not affected by upstream product changes. The PRD requirements in Phase 0's domain (NFR-4, NFR-5, NFR-6) have not materially changed. No new product requirements fall within the scaffold domain.

Three categories of drift were identified:

1. **Directory scaffold drift**: `app/orchestrator/` exists in the codebase (created by Phase 0 spec P0.D5) but was silently removed from `03-STRUCTURE.md` v1.5 (2026-02-18). The directory is an orphan — no BOM component maps to it and no architecture doc references it.

2. **`.env.example` drift**: Three stale entries in P0.D9 — a broken docs reference (`.dev/11-PROVIDERS.md` does not exist), a rejected search provider (`SEARXNG_URL`), and two env vars documented but not loaded by the Settings class (`AUTOBUILDER_MAX_CONCURRENCY`, `AUTOBUILDER_SKILLS_DIR`).

3. **Contract documentation drift**: The "Directory structure matches `.dev/03-STRUCTURE.md`" contract item references a doc that changed after Phase 0 was built. The contract itself is sound; the spec note needs updating to reflect the current structure delta.

All three require code remediation in a targeted build session — no documentation audit alone resolves them.

---

## PRD Delta

### New Requirements (in scope)

| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|
| — | None | No new product requirements fall in Phase 0's scaffold/config domain. | No action |

*Evaluation*: All new PRD requirements (PR-1–PR-37 covering agents, workflows, CEO queue, memory, skills, etc.) are assigned to later phases. NFR-4, NFR-5, NFR-6 — the three requirements Phase 0 satisfies — remain in scope and unchanged.

### Changed Requirements

| PR-N | What Changed | FR Affected | Action |
|------|-------------|-------------|--------|
| NFR-5 | Text expanded in PRD v6.0 to explicitly mention "Agent Skills standard skills install without code changes." This language did not exist when Phase 0 was built. | None | No action — Agent Skills standard is Phase 6 scope (BOM S01–S14). The expansion does not affect Phase 0's deliverables. Note only. |

*Note*: The core obligations of NFR-4 ("credentials never logged or hardcoded"), NFR-5 ("type safety chain"), and NFR-6 ("single machine, env var config") that Phase 0 satisfies are identical in PRD v6.0. The NFR-5 text expansion adds agent-skill-specific language that is entirely Phase 6 territory.

### Dropped Requirements

| FR | Formerly traced to | Disposition |
|----|-------------------|-------------|
| — | None | No Phase 0 requirements trace to dropped PRD IDs. |

### Contract Drift

| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|
| "Directory structure matches `.dev/03-STRUCTURE.md`" | `03-STRUCTURE.md` was updated to v1.5 (2026-02-18) after Phase 0 was built. It removed `app/orchestrator/` and added `app/cli/`. The contract item now technically fails because: (1) `app/orchestrator/` exists in code but not in the spec, and (2) `app/cli/` is in the spec but not in code. | Code remediation: remove `app/orchestrator/` (orphaned). Do NOT create `app/cli/` — that is Phase 10 scope (BOM C01–C06). After remediation, the contract will pass. |

---

## Architecture Delta

### Architecture Decisions That Supersede This Phase

| Architecture Section | Conflict | Component Affected | Action |
|---------------------|----------|--------------------|--------|
| `03-STRUCTURE.md` v1.5 (2026-02-18) | `app/orchestrator/` removed from canonical project structure. No BOM component maps to this directory (the orchestration function is performed by ADK agents — execution.md §PM loop). Directory exists in code as a `__init__.py` placeholder with no content. | spec.md P0.D5 (directory scaffold) | Update spec.md P0.D5 with note. Code remediation: remove `app/orchestrator/`. |
| `03-STRUCTURE.md` v1.5 (2026-02-18) | `app/cli/` added to canonical project structure. Does not yet exist in code — correctly deferred to Phase 10 (BOM C01–C06: `autobuilder run`, `status`, `intervene`, `list`, `logs`, Typer scaffold). | spec.md P0.D5 | Update spec.md P0.D5 with note. No code action for Phase 0; Phase 10 creates `app/cli/`. |

### New BOM Components

| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|
| — | — | — | No BOM components have been added to Phase 0's domain since Phase 0 was planned. All `✓` BOM entries predating this audit were already covered by Phase 0's deliverables. |

### Dropped BOM Components

| Component ID | Deliverable | Status |
|-------------|-------------|--------|
| — | — | No BOM components assigned to Phase 0 have been dropped. |

---

## .env.example Drift (P0.D9)

Three specific issues in the `.env.example` deliverable (P0.D9):

| # | Line | Issue | Action |
|---|------|-------|--------|
| 1 | 26 | References `.dev/11-PROVIDERS.md` — this file does not exist. The correct file is `.dev/06-PROVIDERS.md`. | Code remediation: fix reference. |
| 2 | 16–19 | Comment reads "Phase 1 provider TBD" with `SEARXNG_URL` as an option. Roadmap Q7 (line 338) was closed: "Tavily primary, Brave fallback. Simple if/elif dispatch." SearXNG was rejected. The comment is stale. | Code remediation: update comment to reflect Tavily+Brave decision, remove SearXNG. |
| 3 | 23–24 | `AUTOBUILDER_MAX_CONCURRENCY=6` and `AUTOBUILDER_SKILLS_DIR=./skills` are documented but have no corresponding fields in `app/config/settings.py`. These env vars are not loaded by the application. | Code remediation: either (a) add fields to Settings class if these vars are needed, or (b) remove from `.env.example` if they are aspirational placeholders. |

*Settings class verification*: `app/config/settings.py` confirmed to contain: `db_url`, `redis_url`, `log_level`, `default_code_model`, `default_plan_model`, `default_review_model`, `default_fast_model`, `search_provider` (added by Phase 4; Phase 4's spec P4.D2 explicitly documents it as a Phase 4 addition). All `AUTOBUILDER_DEFAULT_*_MODEL` variables from the CLAUDE.md env table are correctly covered. The `AUTOBUILDER_SEARCH_API_KEY` mentioned in Roadmap Q7 text is not in Settings — per Phase 4 implementation, API keys (`TAVILY_API_KEY`, `BRAVE_API_KEY`) are read directly from environment without the `AUTOBUILDER_` prefix, which is consistent with not configuring them via the Settings class.

---

## Artifact Changes Made

| Artifact | Change | Rationale |
|----------|--------|-----------|
| `spec.md` P0.D5 | Added note documenting the scaffold drift: `app/orchestrator/` is deprecated (removed from `03-STRUCTURE.md` v1.5), `app/cli/` is deferred to Phase 10. Does not mark deliverable as incomplete. | Keeps spec current with architecture evolution; flags the orphaned directory for code remediation. |
| `spec.md` P0.D9 | Added note listing the three `.env.example` stale entries and the required remediation scope. Does not mark deliverable as incomplete. | Surfaces `.env.example` drift discovered by this audit for the next targeted build session. |

---

## Remediation Required (Code)

Items requiring a targeted build session — not addressed in this audit:

| # | Scope | What | Why |
|---|-------|------|-----|
| 1 | `app/orchestrator/` | Remove directory and its `__init__.py` from the codebase | Orphaned placeholder: no BOM component maps to it, not in `03-STRUCTURE.md` v1.5, no architecture section references an "orchestrator" module. Execution is done by PM agent (execution.md §PM loop). |
| 2 | `.env.example` line 26 | Change `.dev/11-PROVIDERS.md` → `.dev/06-PROVIDERS.md` | The referenced file does not exist; `06-PROVIDERS.md` is the correct providers reference. |
| 3 | `.env.example` lines 16–19 | Update search provider comment: remove "Phase 1 TBD" and `SEARXNG_URL`, reflect Roadmap Q7 decision (Tavily primary, Brave fallback) | Roadmap Q7 was closed with Tavily+Brave decision. SearXNG was rejected. The stale comment could mislead future configurators. |
| 4 | `.env.example` lines 23–24 + `app/config/settings.py` | Resolve `AUTOBUILDER_MAX_CONCURRENCY` and `AUTOBUILDER_SKILLS_DIR` gap: either add fields to Settings class or remove from `.env.example` | These vars are documented but not loaded. If they are intended future config, add to Settings with defaults. If aspirational, remove from `.env.example` to avoid confusion. Note: `max_concurrency` is referenced in execution.md §PM loop and BOM X10 (Phase 8 scope); `skills_dir` relates to two-tier skill scan (Phase 6, BOM S10). Recommend removing from `.env.example` for now and adding when phases implement them. |

---

## No Action Required

| Finding | Rationale |
|---------|-----------|
| NFR-5 text expansion (Agent Skills standard) | Added language covers Phase 6 scope only. No Phase 0 deliverable is affected. |
| `AUTOBUILDER_SEARCH_API_KEY` gap in Settings | Intentional: API keys for search providers use provider-native env var names (TAVILY_API_KEY, BRAVE_API_KEY), not the AUTOBUILDER_ prefix. Consistent with Phase 4 implementation. |
| `app/cli/` not yet created | Correct per phased delivery: `app/cli/` is Phase 10 scope (BOM C01–C06). Not a Phase 0 issue. |
| PRD entity model expansion (PR-1–PR-37) | All new product entities (Brief, WorkflowStage, Batch, CEOQueueItem, etc.) are covered by later phases. Phase 0 intentionally delivers only the minimal shared types needed to bootstrap subsequent phases. |
