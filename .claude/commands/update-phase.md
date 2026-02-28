---
description: Propagate upstream PRD and architecture changes into an already-completed phase — produces a delta report and updated artifacts, no code changes.
argument-hint: <phase-number> [--report-only]
---

<objective>
Audit Phase {$ARGUMENTS} artifacts against the current upstream sources (PRD, L1 architecture, relevant L2 architecture files) and produce a structured delta report plus updated documentation artifacts.

This is a DOCUMENTATION command — no code is written, modified, or deleted. It patches `frd.md`, `spec.md`, and `model.md` only. Code changes that may be required as a result of the audit are surfaced as recommendations in the report and scheduled for a future build session.

CRITICAL: NOT done until `delta-report.md` is written AND all affected artifacts are updated to reflect current upstream. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags:
- `--report-only` — steps 1-4 only (through delta analysis and reflector critique), write draft delta report, stop before artifact updates

Bootstrap (parallel reads):
- Phase artifacts: `.dev/build-phase/phase-{N}/frd.md`, `spec.md`, `model.md`, `review.md`
- `.dev/01-PRD.md` — current PRD
- `.dev/02-ARCHITECTURE.md` — current L1 architecture
- `.dev/08-ROADMAP.md` — current roadmap
- `.dev/07-COMPONENTS.md` — current BOM

Selective deep-reads: after reading the BOM, identify which L2 architecture files are cited in the "Source" column for this phase's components. Read only those files — do not read L2 files that have no components assigned to this phase.

If phase artifacts don't exist: stop and tell user this phase hasn't been planned yet — run `/shape-phase {N}` first.
If `--report-only`: skip Step 5 (artifact updates), stop after Step 4.
</context>

<delegation>
Use subagents to preserve context window:
- `Explore` — codebase research, understand what has been built
- `subtask` — parallel analysis of FRD, spec, and model deltas
- `reflector` — critique the delta analysis for completeness and accuracy (Step 4)
</delegation>

<process>
Steps 1-5 sequential. Announce each step.

STEP 1 — ESTABLISH BASELINE

Read all phase artifacts and construct a baseline inventory:

A. **FRD baseline** — extract every capability (CAP-{n}) and requirement (FR-{N}.{nn} / NFR-{N}.{nn}). Note their PRD traceability links (which PR-N / NFR-N each traces to).

B. **Spec baseline** — extract every deliverable (P{N}.D{n}) and its BOM component list, requirement list, and roadmap contract traceability.

C. **Model baseline** — extract every interface, type, and component. Note their L2 architecture source citations.

D. **Contract baseline** — extract all completion contract items from the roadmap for this phase (from `08-ROADMAP.md`). Record their current status (checked / unchecked / DONE).

E. **Build status** — note what has been implemented (review.md, roadmap phase status). This determines which artifacts can be safely updated vs. which require a follow-up build session.

STEP 2 — AUDIT PRD DELTA

Compare the phase FRD against current `01-PRD.md`:

A. **New requirements** — PRD requirements (PR-N, NFR-N) that were added after this phase was planned, that fall within this phase's domain. How do you know they're in-scope? They reference architecture components or capabilities that this phase owns (per BOM). List each with: the PRD ID, the requirement text, and which FRD capability (if any) partially covers it.

B. **Changed requirements** — PRD requirements that existed when this phase was planned but whose text or scope has materially changed. Compare the PRD requirement against any FRD requirement that references it. List each with: PRD ID, what changed, which FR-{N}.{nn} is affected.

C. **Dropped requirements** — FRD requirements that trace to a PRD requirement ID that no longer exists in the current PRD. These requirements may be orphaned. List each.

D. **Contract drift** — roadmap contract items for this phase that are no longer aligned with the current PRD. Flag any whose wording or scope has diverged.

Use the sync rules from `.dev/.workflow.md`:
> PRD changes propagate to: Architecture → BOM → Roadmap → affected FRDs

STEP 3 — AUDIT ARCHITECTURE DELTA

Compare the phase model (and FRD design constraints / rabbit holes) against current architecture:

A. **Architecture decisions that supersede the phase model** — identify L1 or L2 architecture changes that contradict or supersede design decisions made in this phase's model or spec. For each: cite the architecture section, describe the conflict, and identify which model component or spec deliverable is affected.

B. **New components in scope** — BOM components assigned to this phase that weren't listed when the phase was planned (added in a BOM update). For each: component ID, type, L2 source, which deliverable should cover it.

C. **Dropped components** — BOM components that were in the phase spec but have been removed or reassigned in the current BOM (marked DROP or moved to a different phase). These may create orphaned deliverables.

D. **L2 architecture changes** — for each L2 file this phase reads from, note any section-level changes that affect this phase's model interfaces, types, or data flow.

Use the sync rules:
> L2 Architecture changes propagate to: BOM → Roadmap → affected Specs/Models

STEP 4 — PRODUCE DELTA REPORT

Synthesize Steps 2-3 into a structured delta report. Before writing the final report, launch a `reflector` agent with:
- **Spec/Instructions**: The delta analysis findings from Steps 2-3
- **Scope**: The phase artifacts (frd.md, spec.md, model.md) and upstream source documents (PRD, architecture)

Challenge the reflector to verify:
- Are all PRD requirements in this phase's domain covered by the delta analysis?
- Is every changed/new requirement correctly classified (new vs. changed vs. dropped)?
- Are architecture conflicts real conflicts or just refinements that don't require FRD changes?
- Are there any implied gaps not surfaced by the structural comparison?

Incorporate reflector feedback. Then write the delta report.

`--report-only` → write `delta-report.md` and stop here.

STEP 5 — UPDATE ARTIFACTS

Apply the delta findings to phase artifacts. Update only documentation — no code.

**Remediations by artifact:**

| Finding Type | Artifact to Update | Action |
|-------------|-------------------|--------|
| New PRD requirement in scope | `frd.md` | Add capability (CAP-{n}) and requirement(s) (FR-{N}.{nn}) with PRD traceability |
| Changed PRD requirement | `frd.md` | Update affected FR-{N}.{nn} text; update PRD traceability link |
| Dropped PRD requirement | `frd.md` | Mark requirement as deprecated with note: "PRD requirement removed; implementation may be retained if architecture still calls for it" |
| Architecture supersedes model decision | `model.md` | Update the affected interface/type/component to conform to current architecture; add note explaining the change |
| New BOM component in scope | `spec.md` | Add to an existing deliverable or create new deliverable; update BOM Coverage matrix |
| Dropped BOM component | `spec.md` | Mark deliverable note as "BOM component reassigned/dropped — implementation status: [check actual code]" |
| Contract drift | `{N}-ROADMAP.md` | Do NOT modify roadmap contract items for DONE phases. Add a note in delta-report.md recommending a roadmap annotation |

**Rules:**
- If a DONE phase has implementation that would need to change: do NOT modify spec.md requirements or mark them as failed. Instead, log in `delta-report.md` as a "Remediation Required" item with specific recommendation.
- If a phase is PLANNED (not yet built): update artifacts freely — the phase hasn't been implemented.
- Never mark a verified deliverable as incomplete based solely on a documentation audit.
- If a delta requires code changes, record it in the "Remediation Required" section of the report — it will be addressed in a targeted build session.

After all artifact updates: re-read each updated artifact and verify internal consistency (traceability maps still hold, no orphaned IDs).
</process>

<output>
Primary output: `.dev/build-phase/phase-{N}/delta-report.md`

Secondary outputs (updated in-place, if applicable):
- `.dev/build-phase/phase-{N}/frd.md` — updated requirements with new/changed PRD traces
- `.dev/build-phase/phase-{N}/spec.md` — updated deliverables with new/changed BOM components
- `.dev/build-phase/phase-{N}/model.md` — updated interfaces conforming to current architecture

**Delta Report structure:**

```markdown
# Phase {N} Delta Report
*Generated: {date}*
*Phase status: {DONE | IN PROGRESS | PLANNED}*
*Sources compared: PRD v{X.X}, Architecture v{X.X}, BOM v{X.X}*

## Summary
{Brief narrative of what changed upstream and overall impact.}

## PRD Delta

### New Requirements (in scope)
| PR-N | Requirement | FRD Impact | Action |
|------|-------------|------------|--------|

### Changed Requirements
| PR-N | What Changed | FR-{N}.{nn} Affected | Action |
|------|-------------|---------------------|--------|

### Dropped Requirements
| FR-{N}.{nn} | Formerly traced to | Disposition |
|-------------|-------------------|-------------|

### Contract Drift
| Contract Item | Drift | Recommendation |
|--------------|-------|----------------|

## Architecture Delta

### Architecture Decisions That Supersede This Phase
| Architecture Section | Conflict | Model Component Affected | Action |
|---------------------|----------|------------------------|--------|

### New BOM Components
| Component ID | Type | Source | Suggested Deliverable |
|-------------|------|--------|-----------------------|

### Dropped BOM Components
| Component ID | Deliverable | Status |
|-------------|-------------|--------|

## Artifact Changes Made
List all changes applied to frd.md, spec.md, model.md with brief rationale for each.

## Remediation Required (Code)
Items requiring a targeted build session — not addressed in this audit:
| # | Scope | What | Why |
|---|-------|------|-----|

## No Action Required
Findings reviewed but determined non-impactful with rationale.
```
</output>

<verification>
Re-read `delta-report.md` and check:
1. Every PRD requirement in the phase's domain has been evaluated (new, changed, dropped, or explicitly "no change")
2. Every L2 architecture file this phase references has been evaluated for delta
3. Every finding is classified with an action (Update, Deprecate, Log for remediation, No action)
4. Updated artifacts have been re-read and are internally consistent (traceability maps intact)
5. Code-level remediations are logged in the report, NOT applied to artifacts
6. Report is self-contained — a reader can understand the delta without reading the process

Fix failures before returning.
</verification>

<success_criteria>
- `delta-report.md` written to `.dev/build-phase/phase-{N}/delta-report.md`
- All PRD requirements in the phase's domain evaluated
- All architecture delta items identified and classified
- frd.md, spec.md, model.md updated where applicable (documentation only)
- Code remediations logged in report, not applied
- All updated artifacts verified for internal consistency
</success_criteria>
