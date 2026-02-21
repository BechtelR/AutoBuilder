---
description: Define phase functional requirements — capabilities, behaviors, edge cases, and testable conditions.
argument-hint: <phase-number> [--research-only | --resume]
---

<objective>
Produce a Functional Requirements Document for Phase {$ARGUMENTS}. Output: `frd.md` in `.dev/build-phase/phase-{N}/`.

This is a PRODUCT THINKING artifact — no implementation code, no technical decomposition, no file paths. Define what this phase must do from its consumers' perspective. Every requirement must be E2E testable. Spec and Model consume this document downstream.

CRITICAL: NOT done until frd.md is written AND every roadmap contract item traces to a capability AND every FRD requirement traces to a PRD requirement. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags:
- `--research-only` — steps 1-3D only (through reflector critique), present findings and stop
- `--resume` — read existing frd.md, re-run all steps against current state, update stale sections, leave valid sections unchanged

Bootstrap (parallel reads):
- @.dev/08-ROADMAP.md — target phase scope summary, completion contract, prerequisites ONLY
- @.dev/07-COMPONENTS.md — filter by phase number for component list (tells you what domain this phase covers)
- @.dev/00-VISION.md — vision goals (capabilities must align)
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

PRD read:
- @.dev/01-PRD.md — product requirements (FRD requirements derive from these)
- If PRD doesn't exist: work from vision + roadmap + architecture. Note the gap — PRD traceability will be incomplete.

Selective deep-reads (for domain understanding and rabbit hole identification — NOT for traceability):
- Read L2 architecture files referenced in BOM "Source" column for this phase's components
- This informs rabbit holes and constraints, not requirements

Skip `CLAUDE.md` and `.claude/rules/` (already in context).
If frd.md exists and no flag: ask user — overwrite or resume?
</context>

<delegation>
Use subagents to preserve context window:
- `Explore` — codebase research, understand existing patterns in the domain
- `subtask` — parallel research into specific capability areas
- `Plan` — help identify capabilities and requirement gaps
- `reflector` — critique drafted capabilities against scope and requirements (Step 3D)
</delegation>

<process>
Steps 1-8 sequential. Announce each step. This command is collaborative — propose to the user, discuss, refine before writing.

STEP 1 — LOAD PHASE SCOPE

A. **Read roadmap** — extract this phase's scope summary, completion contract items, and prerequisites.
B. **Read BOM** — extract ALL components assigned to this phase. These tell you what domain areas this phase covers (gateway routes, agents, tools, etc.) — but do NOT decompose into components. That's the Spec's job.
C. **Read PRD** — identify which product requirements apply to this phase's domain. If no PRD exists, note the gap and work from vision + roadmap.

STEP 2 — UNDERSTAND THE DOMAIN

A. **Read L2 architecture** — only files referenced by this phase's BOM components. Understand the domain, identify constraints, spot potential rabbit holes.
B. **Survey existing code** — if prerequisite phases have been built, understand what already exists that this phase extends. Use `Explore` agents for substantial codebases.
C. **Synthesize** — what is this phase really about? What consumer-facing value does it unlock? What becomes possible that wasn't before?

STEP 3 — DEFINE CONSUMER ROLES AND CAPABILITIES

From the roadmap scope, PRD requirements, and domain understanding:

A. **Identify consumer roles** — who consumes this phase's output? End-user, API caller, developer, operator, the system itself? Define each role and its E2E boundary (what "end-to-end" means for testing). A phase may have multiple consumers.
B. **Draft capabilities** — for EACH consumer role, methodically enumerate every behavior they can observe or action they can perform. Think from the consumer's perspective — walk through their workflows, interactions, and expectations. Capabilities must be exhaustive. Ask: "What can each consumer do after this phase that they couldn't before?"
C. **Set appetite** — propose a time/effort budget based on phase size (S/M/L/XL from roadmap). This is a constraint, not an estimate.
D. **Reflector critique** — before presenting to user, launch a `reflector` agent. Provide it:
   - **Spec/Instructions**: The drafted consumer roles and capability list
   - **Scope**: The phase's roadmap scope, completion contract, BOM components, and PRD requirements (or vision goals if no PRD)

   Challenge questions for the reflector:
   - Are capabilities exhaustive for each consumer role? Walk each consumer's E2E boundary — any gaps?
   - Are capabilities at the right abstraction level? (Not too granular, not too vague)
   - Are there implied capabilities missing? (Error handling, edge cases, degraded modes)
   - Do capabilities overlap or have gaps between them?
   - Is anything included that belongs to a different phase?
   Incorporate reflector feedback before presenting.

`--research-only` → present consumer roles, capabilities, and reflector critique to user. Stop here.

E. **Present to user** — show the consumer roles and capability list with brief descriptions. Ask:
   - Are these the right capabilities?
   - Is anything missing?
   - Is the appetite reasonable?
   - Are the priorities right?

Refine based on user feedback before proceeding.

STEP 4 — DEFINE REQUIREMENTS PER CAPABILITY

For each capability:

A. **Draft functional requirements** (FR-{N}.{nn}) — E2E consumer-observable behaviors. "When X, the system Y." Every requirement must be testable by agents.
B. **Draft edge cases and error scenarios** — as first-class requirements with the same FR-{N}.{nn} format. "When X is invalid, the system Y." What does the consumer observe? How does the system recover?
C. **Draft non-functional requirements** (NFR-{N}.{nn}) — measurable quality attributes that cross-cut capabilities. Performance, reliability, security, limits.

Rules:
- No implementation language. Describe behaviors at the consumer's level. "System executes submitted tasks asynchronously" — not "ARQ dequeues from Redis list." "System responds with the consumer's projects" — not "GET /projects returns JSON from PostgreSQL."
- Every requirement testable end-to-end. If you can't describe how an agent would verify it, rewrite it.
- Edge cases are requirements, not footnotes. Invalid input, service failures, concurrency, rate limits.

STEP 5 — IDENTIFY RABBIT HOLES

From L2 architecture reading and domain research:
- Technical complexity traps the builder should know about upfront
- ADK quirks, framework limitations, integration gotchas
- Things that look simple but aren't

Each rabbit hole: what it is, why it's dangerous, how to navigate it.

STEP 6 — DEFINE NO-GOS

Explicit exclusions. What this phase will NOT do. Derive from:
- Appetite constraint (what doesn't fit in the budget)
- Roadmap boundaries (what belongs to a later phase)
- Scope creep risks (what someone might reasonably try to add)

Each no-go: excluded capability + brief rationale.

STEP 7 — BUILD TRACEABILITY

Two maps:

A. **PRD Coverage** — every FRD requirement (FR-{N}.{nn}) → the PRD requirement it derives from. If PRD doesn't exist, note "PRD pending" and trace to vision goals instead.

B. **Roadmap Contract Coverage** — every roadmap completion contract item → the capability (CAP-{n}) and requirement(s) (FR-{N}.{nn}) that satisfy it. Every contract item must be covered. Zero uncovered.

If gaps exist: either add requirements to cover them or flag to user for resolution.

STEP 8 — WRITE OUTPUT

Write frd.md per template. Re-read to verify completeness.
</process>

<output>
One file: `.dev/build-phase/phase-{N}/frd.md`

Follow template at `.dev/build-phase/.templates/frd.md` — fill all `{placeholders}`, keep all sections.

Requirements:
- Standalone (fresh session needs only this + referenced docs)
- Every requirement is E2E testable — no vague "works correctly"
- Every requirement uses FR-{N}.{nn} / NFR-{N}.{nn} ID format with checkboxes
- Capabilities grouped by consumer behavior, not by technical component
- Zero implementation language — behaviors only
- No code of any kind
</output>

<verification>
Re-read frd.md and check:
1. Has: Objective, Consumer Roles, Appetite, Capabilities (with requirements), NFRs, Rabbit Holes, No-Gos, Traceability (PRD + Roadmap)
2. Consumer roles defined with E2E boundaries — every requirement testable against a declared consumer role
3. Every requirement has an FR/NFR ID and a checkbox
4. Every requirement is E2E testable (could an agent verify this against a declared consumer role?)
5. Every roadmap contract item covered in traceability (count must match)
6. Every FRD requirement traces to a PRD requirement (or vision goal if no PRD)
7. Zero implementation language (no file paths, no class names, no API endpoints)
8. Capabilities describe consumer-observable behaviors, not technical components
9. Edge cases and error scenarios included as first-class requirements
10. No code of any kind

Fix failures before returning.
</verification>

<success_criteria>
- frd.md written to disk at `.dev/build-phase/phase-{N}/frd.md`
- Every capability has testable requirements with FR-{N}.{nn} IDs
- Every requirement E2E verifiable — no vague conditions
- Every roadmap contract item → capability (zero uncovered)
- Every FRD requirement → PRD requirement (traceability)
- Rabbit holes identified from domain research
- No-gos defined with rationale
- Zero implementation language or code in the document
</success_criteria>
