---
description: Design the architecture model for a phase — components, interfaces, data flow, no implementation code.
argument-hint: <phase-number>
---

<objective>
Produce a high-level architecture model for Phase {$ARGUMENTS}. Output: `model.md` in `.dev/build-phase/phase-{N}/`.

This is a DESIGN artifact — no implementation code. Defines components, interfaces, types, and data flow that the build phase will implement.

Conciseness principle: model what the builder must comply with. Skip signatures that are obvious from the interface name and types. Skip diagrams for trivial flows. Design for decisions, not dictation.

CRITICAL: NOT done until model.md is written AND every spec deliverable maps to at least one component. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask).

Bootstrap (parallel reads):
- @.dev/build-phase/phase-{N}/spec.md — full spec (deliverables, decisions, files)
- @.dev/02-ARCHITECTURE.md — five-layer architecture (conformance target)
- @.dev/03-STRUCTURE.md — file placement truth
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Selective deep-reads (only what the phase touches, via INDEX.md):
- Agents → `architecture/agents.md` | Skills → `architecture/skills.md` | Workflows → `architecture/workflows.md`
- State/memory → `architecture/state.md` | Tools → `architecture/tools.md`
- Tech decisions → `04-TECH_STACK.md` | Design history → `.discussion/design-changelog.md`

If spec.md doesn't exist: stop and tell user to run `/spec-phase {N}` first.
If model.md exists: ask user — overwrite or skip?
</context>

<process>
Steps 1-8 sequential. Announce each step.

STEP 1 — READ SPEC
Extract from spec.md: deliverables (IDs, files, descriptions, requirements), design decisions, build order, prerequisites. Build a mental map of what this phase delivers.

STEP 2 — ARCHITECTURE CONFORMANCE
Verify ALL components slot into the five-layer architecture from `02-ARCHITECTURE.md`:
1. **Interface layer** — CLI (typer), dashboard (React SPA)
2. **Gateway layer** — FastAPI routes/models, ARQ queue, database access
3. **Worker layer** — ARQ workers, anti-corruption layer
4. **Engine layer** — ADK orchestration, agents, tools, state
5. **Infrastructure layer** — Redis, database, filesystem

For each component in scope: identify its layer. Flag any that don't fit cleanly — these are architecture violations requiring resolution before proceeding. Also verify conformance with `00-VISION.md` principles (API-first, ADK behind ACL, out-of-process execution, etc.).

STEP 3 — IDENTIFY COMPONENTS
Map spec deliverables to concrete components: modules, classes, functions. Show how they connect. Group by architecture layer. For UI components: list names and relationships only — detailed UI design belongs in separate files.

STEP 4 — DEFINE INTERFACES
For each component boundary: define Protocol classes or ABCs with method signatures only. No implementation bodies. Include type hints for all parameters and return types. These are the contracts the build phase must satisfy.
Omit signatures that are obvious from the class hierarchy (e.g., subclass constructors that just narrow a parent parameter).

STEP 5 — DEFINE KEY TYPES
Pydantic models at API boundaries, enums for state/status, TypedDicts for internal DTOs. Field-level detail. Follow enum convention: values MUST match names (uppercase).

STEP 6 — MAP DATA FLOW
Trace how data transforms across layers. Show the type chain: what enters each boundary and what exits. Use Mermaid diagrams. Include the full type safety chain where applicable (SQLAlchemy → Pydantic → OpenAPI → TypeScript).
One diagram per distinct data path. Skip flows that are self-evident from the interfaces (e.g., simple CRUD with no transformation).

STEP 7 — DIAGRAM LOGIC FLOW
State machines, pipeline stages, decision trees. Use Mermaid state diagrams or flowcharts. Describe transitions, conditions, and outcomes — no implementation code.
Only diagram non-obvious logic. If a lifecycle is linear (A → B → C) with no branching, a bullet list suffices.

STEP 8 — WRITE model.md
Follow template at `.dev/build-phase/.templates/model.md`. Fill all sections. Include integration points (existing system + future phase extensions). Re-read to verify completeness.
</process>

<output>
One file: `.dev/build-phase/phase-{N}/model.md`

Follow template at `.dev/build-phase/.templates/model.md` — fill all `{placeholders}`, keep all sections.

Requirements:
- Every spec deliverable maps to at least one component
- Every component has an identified architecture layer
- Interfaces use Protocol/ABC with full type signatures
- Mermaid diagrams for component, data flow, and logic flow
- No implementation code — signatures and types only
- Integration points cover both existing system and future extensions
</output>

<verification>
Re-read model.md and check:
1. Component diagram present with Mermaid, components grouped by architecture layer
2. Every spec deliverable (P{N}.D{n}) traceable to at least one component
3. All interfaces have Protocol/ABC definitions with typed signatures
4. Key types include Pydantic models and enums with field-level detail
5. Data flow shows type transformations across boundaries
6. Logic flow uses state diagrams or flowcharts (Mermaid)
7. Integration points table covers existing components AND future extensions
8. Zero implementation code (no function bodies beyond `...`)
9. All components conform to the five-layer architecture from `02-ARCHITECTURE.md`

Fix failures before returning.
</verification>

<success_criteria>
- model.md written to disk at `.dev/build-phase/phase-{N}/model.md`
- Every spec deliverable traceable to component(s)
- All components placed in correct architecture layer
- Interfaces defined as Protocol/ABC with typed signatures
- Mermaid diagrams for component layout, data flow, and logic flow
- No implementation code
- Architecture conformance verified against `02-ARCHITECTURE.md`
</success_criteria>
