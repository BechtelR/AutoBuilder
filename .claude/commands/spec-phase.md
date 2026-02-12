---
description: Create a complete buildable spec for a roadmap phase — design, research, and crystal-clear deliverables.
argument-hint: <phase-number> [--research-only | --resume]
---

<objective>
Produce a buildable specification for Phase {$ARGUMENTS}. Output: `spec.md` + `prompt.md` in `.dev/build/phase-{N}/`.

CRITICAL: NOT done until BOTH files written AND every roadmap completion contract item traces to a deliverable. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags: `--research-only` (steps 1-3 only), `--resume` (continue existing spec).

Bootstrap (parallel, token discipline — do NOT bulk-read):
- @.dev/01-ROADMAP.md — target phase + prerequisites ONLY
- @.dev/03-STRUCTURE.md — file placement truth
- @.dev/INDEX.md — doc map for on-demand lookups

Selective deep-reads (only what the phase touches, via INDEX.md):
- Infrastructure/gateway → `02-ARCHITECTURE.md` | Agents → `05-AGENTS.md`
- Skills → `06-SKILLS.md` | Workflows → `07-WORKFLOWS.md`
- State/memory → `08-STATE_MEMORY.md` | Tools → `09-TOOLS.md`
- Tech decisions → `04-TECH_STACK.md` | Design history → `.discussion/design-changelog.md`

Skip `CLAUDE.md` and `.claude/rules/` (already in context).
If spec exists and no flag: ask user — overwrite or resume?
</context>

<process>
Steps 1-7 sequential. Announce each step.

STEP 1 — PREREQUISITE AUDIT
Check prerequisite phase's completion contract. Evidence from git/code/`.dev/build/`. Unmet → stop and report.

STEP 2 — DESIGN COMPLETENESS AUDIT
Per deliverable group verify: clear responsibility, interfaces defined, file placement in `03-STRUCTURE.md`, dependencies, integration points.
Check gaps: open questions table, unmade architecture decisions, unvalidated patterns.
`--research-only` → report gaps and stop.

STEP 3 — RESEARCH & RESOLUTION
Per gap: research (`.dev/.knowledge/`, architecture docs, web) → propose with rationale → get user confirmation on non-obvious choices → record for spec.
Use `Explore`/`subtask` agents for parallel research.

STEP 4 — DELIVERABLE DECOMPOSITION
Per deliverable: ID (`P{N}.D{n}`), title (imperative), description (what not how, 2-4 sentences), files (exact paths from `03-STRUCTURE.md`), dependencies (by ID), acceptance criteria (concrete, testable), validation command.

Rules: single-session completable, max 3-4 files, DAG deps, every contract item mapped, add implied deliverables.

STEP 5 — COMPLETION CONTRACT TRACEABILITY
Matrix: every roadmap contract item → deliverable(s) → validation command. Any uncovered → add deliverable.

STEP 6 — BUILD ORDER
Topological sort into parallel batches respecting deps.

STEP 7 — WRITE OUTPUT FILES
Write both files per output section. Re-read both to verify completeness.
</process>

<output>
Two files. Both MUST be written.

FILE 1: `.dev/build/phase-{N}/spec.md`

```
# Phase {N} Spec: {Phase Title}
*Generated: {date}*

## Overview
{Phase goal expanded with design decisions}

## Prerequisites
{Each prerequisite — met/unmet with evidence}

## Design Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|

## Deliverables

### P{N}.D1: {Title}
**Files:** `path/to/file.py`
**Depends on:** —
**Description:** {what to build}
**Acceptance criteria:**
- [ ] {testable condition}
**Validation:** `{command}`

(repeat for all deliverables)

## Build Order
{Batched topological sort}

## Completion Contract Traceability
| Completion Contract Item | Covered By | Validation |

## Research Notes
{Key findings, patterns, APIs referenced}
```

FILE 2: `.dev/build/phase-{N}/prompt.md`

Follow template at `.dev/build/.templates/prompt.md` — fill all `{placeholders}`, keep all 9 sections.

Requirements:
- Standalone (fresh session needs only this + spec + referenced docs)
- Section 3: ALL roadmap contract items, none omitted
- Section 8: parallel reviewer subagents scaled to deliverable count — do not weaken
- Section 9: evidence-based completion — every checkbox needs proof. Do not modify structure, only fill values
</output>

<verification>
Re-read both files and check:
1. spec.md has: Overview, Prerequisites, Design Decisions, Deliverables (ID/Files/Depends/Description/Criteria/Validation), Build Order, Traceability, Research Notes
2. prompt.md has all 9 sections: Context, Objective, Success Criteria, Scope, Work Breakdown, Constraints, Quality Gate, Review Gate, Completion Protocol
3. Roadmap contract item count matches traceability matrix count AND prompt.md section 3 count
4. Section 8 has: reviewer scaling table, scope checklist, fix loop with HIGH-severity re-review
5. Section 9 has substeps 9a-9e, all requiring evidence — no blind check-offs
6. All acceptance criteria concrete (no "works correctly")
7. All file paths valid per `03-STRUCTURE.md`

Fix failures before returning.
</verification>

<success_criteria>
- Both files written to disk
- Every roadmap contract item → deliverable (traceability) → prompt.md success criteria (section 3)
- Section 8 mandates scaled parallel reviewers with fix loop
- Section 9 enforces evidence-gated completion of spec.md + roadmap
- Concrete acceptance criteria, valid file paths, valid DAG build order
- prompt.md is standalone and follows the 9-section template
</success_criteria>
