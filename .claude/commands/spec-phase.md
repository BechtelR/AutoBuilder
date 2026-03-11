---
description: Create a complete buildable spec for a roadmap phase — design, research, and crystal-clear deliverables.
argument-hint: <phase-number> [--research-only | --resume]
---

<objective>
Produce a buildable specification for Phase {$ARGUMENTS}. Output: `spec.md` in `.dev/build-phase/phase-{N}/`.

CRITICAL: NOT done until spec.md is written AND every FRD requirement traces to a deliverable (if FRD exists) AND every BOM component maps to a deliverable AND every roadmap contract item traces to a deliverable. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags:
- `--research-only` — steps 1-4 only, report gaps and stop
- `--resume` — read existing spec.md, re-run all steps against current state (prerequisite specs may have been added, code may have changed), update sections that are stale or incomplete, leave valid sections unchanged

Bootstrap (parallel, token discipline — do NOT bulk-read):
- @.dev/07-COMPONENTS.md — filter by phase number, this is the **authoritative component list** for the phase
- @.dev/08-ROADMAP.md — target phase scope summary, completion contract, prerequisites ONLY
- @.dev/03-STRUCTURE.md — file placement truth
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

FRD read:
- `.dev/build-phase/phase-{N}/frd.md` — phase functional requirements (Spec traces to these)
- If FRD doesn't exist: warn user to run `/shape-phase {N}` first. Proceed only if user confirms — traceability will be incomplete.

Selective deep-reads — derive from BOM, never hardcode:
1. From the BOM rows for this phase, collect the unique values in the **Source** column (e.g., `gateway.md §Route Structure` → file `.dev/architecture/gateway.md`; `state.md §1.2` → file `.dev/architecture/state.md`)
2. Deep-read ONLY those architecture files, focused on the referenced sections. No others.
3. On-demand only (pull in during Step 4 research if a gap requires it): `.decision-log.md` (design rationale), `04-TECH_STACK.md` (tech constraints), `06-PROVIDERS.md` (model routing).

Skip `CLAUDE.md` and `.claude/rules/` (already in context).
If spec exists and no flag: ask user — overwrite or resume?
</context>

<delegation>
Design context — read @.claude/agents/architect.md before design steps. Internalize its principles and checklist; apply them throughout Steps 3-5.

Use subagents to preserve context window:
- `Explore` — codebase research, understand existing patterns in target modules
- `subtask` — parallel research into specific technical areas, local or web
- `reviewer` — final document verification (Step 10): verify spec.md against the verification checklist and source documents. It finds AND fixes issues directly.
</delegation>

<process>
Steps 1-10 sequential. Announce each step.

STEP 1 — PREREQUISITE AUDIT
A. **Load BOM scope** — read `07-COMPONENTS.md`, extract ALL components assigned to this phase number. This is the exhaustive list of what the phase must deliver. Every component ID (e.g., G10, D08, E05) becomes a deliverable or part of a deliverable.
B. For each prerequisite phase listed in the roadmap:
1. Identify what THIS phase depends on from it (interfaces, types, patterns)
2. Check what's available:
   - Spec exists → use its deliverables and decisions as reliable input
   - Code exists → note established patterns and interfaces for Step 2
   - Neither → work from roadmap descriptions, note assumptions in Design Decisions
Build-phase will hard-gate on actual code. Spec-phase plans against what's known.

STEP 2 — EXISTING CODE SURVEY
For every file the phase creates or modifies (per `03-STRUCTURE.md` + BOM components):
- Read what's already there. Note current patterns, imports, conventions.
- Identify interfaces the phase must extend or conform to.
- Flag conflicts between existing code and roadmap expectations.
- Use `Explore` agents for modules with substantial existing code.
Record findings — feed into Design Decisions (spec.md section) and Deliverable Decomposition (Step 5).
Skip for Phase 0 or phases that create entirely new directories.

STEP 3 — DESIGN COMPLETENESS AUDIT
Per deliverable group verify: clear responsibility, interfaces defined, file placement in `03-STRUCTURE.md`, dependencies, integration points.
Check gaps: open questions table, unmade architecture decisions, unvalidated patterns.

STEP 4 — RESEARCH & RESOLUTION
Per gap: research (`.dev/.knowledge/`, architecture docs, web) → propose with rationale → get user confirmation on non-obvious choices → record for spec.
Use `Explore`/`subtask` agents for parallel research.
`--research-only` → report findings and stop here.

STEP 5 — DELIVERABLE DECOMPOSITION
Map BOM components to deliverables. Each deliverable may implement 1+ BOM components. Every BOM component for this phase MUST appear in at least one deliverable.

Per deliverable: ID (`P{N}.D{n}`), title (imperative), BOM components (list IDs, e.g., `G10, G11, A70`), description (what not how, 2-4 sentences), files (exact paths from `03-STRUCTURE.md`), dependencies (by ID), requirements (what must be true when complete — concrete, measurable), validation command.

Rules: single-session completable, max 3-4 files, DAG deps, every contract item mapped, every BOM component covered, add implied deliverables.

STEP 6 — FRD TRACEABILITY
If FRD exists: verify every FRD requirement (FR-{N}.{nn}) traces to at least one deliverable. Flag requirements with no deliverable coverage — these are gaps. Flag deliverables with no FRD requirement — these may be scope creep.
If no FRD: skip this step, note the gap.

STEP 7 — TRACEABILITY MATRICES
Write three matrices for the spec (Step 6 found gaps; this step produces the artifact):
A. **FRD coverage** (if FRD exists): formalize the Step 6 mapping — every FRD requirement (FR-{N}.{nn}) → deliverable(s). Zero uncovered.
B. **BOM coverage**: every BOM component ID for this phase → deliverable ID. Any uncovered → add to existing deliverable or create new one. Zero BOM components may be left unmapped.
C. **Contract traceability**: every roadmap contract item → deliverable(s) → validation command. Any uncovered → add deliverable.

STEP 8 — BUILD ORDER
Topological sort into parallel batches respecting deps.

STEP 9 — WRITE OUTPUT
Write spec.md per output section.

STEP 10 — REVIEWER VERIFICATION
Spawn a `reviewer` agent. Provide: spec.md path, the verification checklist (from <verification> section), and references to source documents (FRD, BOM, roadmap contract). Reviewer verifies and fixes issues directly. If reviewer flags items needing design decisions, resolve them and re-run reviewer.
</process>

<output>
One file: `.dev/build-phase/phase-{N}/spec.md`

Follow template at `.dev/build-phase/.templates/spec.md` — fill all `{placeholders}`, keep all sections.

Requirements:
- Standalone (fresh session needs only this + referenced docs)
- Requirements per deliverable state what must be true when complete
- FRD Coverage maps every FR-{N}.{nn} to deliverable(s) (if FRD exists, zero uncovered)
- Completion Contract Traceability covers ALL roadmap contract items
- BOM Coverage maps every phase component to a deliverable (zero unmapped)
- All file paths valid per `03-STRUCTURE.md`
</output>

<verification>
Re-read spec.md and check:
1. Has: Overview, Prerequisites, Design Decisions, Deliverables (ID/BOM Components/Files/Depends/Description/Requirements/Validation), Build Order, Traceability (FRD + BOM + Contract coverage), Research Notes
2. Every FRD requirement (FR-{N}.{nn}) maps to a deliverable (if FRD exists)
3. Every BOM component for this phase maps to a deliverable (zero unmapped)
4. Roadmap contract item count matches traceability matrix count
5. All requirements concrete (no "works correctly")
6. All file paths valid per `03-STRUCTURE.md`
7. Valid DAG build order with no circular dependencies

Fix failures before returning.
</verification>

<success_criteria>
- spec.md written to disk
- Every FRD requirement → deliverable (if FRD exists, zero unmapped)
- Every BOM component for this phase → deliverable (zero unmapped)
- Every roadmap contract item → deliverable (traceability)
- Concrete requirements, valid file paths, valid DAG build order
</success_criteria>
