---
description: Create a complete buildable spec for a roadmap phase — design, research, and crystal-clear deliverables.
argument-hint: <phase-number> [--research-only | --resume]
---

<objective>
Produce a buildable specification for Phase {$ARGUMENTS}. Output: `spec.md` in `.dev/build-phase/phase-{N}/`.

CRITICAL: NOT done until spec.md is written AND every roadmap completion contract item traces to a deliverable. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags: `--research-only` (steps 1-3 only), `--resume` (continue existing spec).

Bootstrap (parallel, token discipline — do NOT bulk-read):
- @.dev/01-ROADMAP.md — target phase + prerequisites ONLY
- @.dev/00-VISION.md — vision goals (features must align)
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
Steps 1-9 sequential. Announce each step.

STEP 1 — PREREQUISITE AUDIT
Check prerequisite phase's completion contract. Evidence from git/code/`.dev/build-phase/`. Unmet → stop and report.

STEP 2 — EXISTING CODE SURVEY
For every file the phase creates or modifies (per `03-STRUCTURE.md` + roadmap deliverables):
- Read what's already there. Note current patterns, imports, conventions.
- Identify interfaces the phase must extend or conform to.
- Flag conflicts between existing code and roadmap expectations.
- Use `Explore` agents for modules with substantial existing code.
Record findings — feed into Design Decisions (spec.md section) and Deliverable Decomposition (Step 5).
Skip for Phase 0 or phases that create entirely new directories.

STEP 3 — DESIGN COMPLETENESS AUDIT
Per deliverable group verify: clear responsibility, interfaces defined, file placement in `03-STRUCTURE.md`, dependencies, integration points.
Check gaps: open questions table, unmade architecture decisions, unvalidated patterns.
`--research-only` → report gaps and stop.

STEP 4 — RESEARCH & RESOLUTION
Per gap: research (`.dev/.knowledge/`, architecture docs, web) → propose with rationale → get user confirmation on non-obvious choices → record for spec.
Use `Explore`/`subtask` agents for parallel research.

STEP 5 — DELIVERABLE DECOMPOSITION
Per deliverable: ID (`P{N}.D{n}`), title (imperative), description (what not how, 2-4 sentences), files (exact paths from `03-STRUCTURE.md`), dependencies (by ID), requirements (what must be true when complete — concrete, measurable), validation command.

Rules: single-session completable, max 3-4 files, DAG deps, every contract item mapped, add implied deliverables.

STEP 6 — VISION ALIGNMENT
Verify features align with `00-VISION.md` goals. Each feature should trace to at least one vision differentiator or problem being solved. Flag features that don't connect to the vision — these may be scope creep.

STEP 7 — COMPLETION CONTRACT TRACEABILITY
Matrix: every roadmap contract item → deliverable(s) → validation command. Any uncovered → add deliverable. Include both roadmap-level requirements AND phase-specific requirements.

STEP 8 — BUILD ORDER
Topological sort into parallel batches respecting deps.

STEP 9 — WRITE OUTPUT
Write spec.md per output section. Re-read to verify completeness.
</process>

<output>
One file: `.dev/build-phase/phase-{N}/spec.md`

Follow template at `.dev/build-phase/.templates/spec.md` — fill all `{placeholders}`, keep all sections.

Requirements:
- Standalone (fresh session needs only this + referenced docs)
- Features section lists all phase deliveries as simple line-items
- Requirements per deliverable state what must be true when complete
- Completion Contract Traceability covers ALL roadmap contract items
- All file paths valid per `03-STRUCTURE.md`
</output>

<verification>
Re-read spec.md and check:
1. Has: Overview (with vision alignment), Features, Prerequisites, Design Decisions, Deliverables (ID/Files/Depends/Description/Requirements/Validation), Build Order, Traceability, Research Notes
2. Roadmap contract item count matches traceability matrix count
3. All requirements concrete (no "works correctly")
4. All file paths valid per `03-STRUCTURE.md`
5. Features trace to `00-VISION.md` goals
6. Both roadmap-level and phase-specific requirements included

Fix failures before returning.
</verification>

<success_criteria>
- spec.md written to disk
- Every roadmap contract item → deliverable (traceability)
- Features section present with line-items mapping to deliverables
- Requirements per deliverable (not "acceptance criteria")
- Concrete requirements, valid file paths, valid DAG build order
- Features align with `00-VISION.md` vision goals
</success_criteria>
