---
description: Design the architecture model for a phase — components, interfaces, data flow, no implementation code.
argument-hint: <phase-number>
---

<objective>
Produce a high-level architecture model for Phase {$ARGUMENTS}. Output: `model.md` in `.dev/build-phase/phase-{N}/`.

This is a DESIGN artifact — no implementation code. Defines components, interfaces, types, and data flow that the build phase will implement.

Conciseness principle: model what the builder must comply with. Skip signatures that are obvious from the interface name and types. Skip diagrams for trivial flows. Design for decisions, not dictation.

CRITICAL: NOT done until model.md is written AND every component traces to an L2 architecture section. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask).

Bootstrap (parallel reads):
- @.dev/build-phase/phase-{N}/frd.md — phase functional requirements (capabilities + FR IDs)
- @.dev/07-COMPONENTS.md — filter by phase number for **authoritative component list** with types and dependencies
- @.dev/02-ARCHITECTURE.md — system architecture (conformance target, defines layers)
- @.dev/03-STRUCTURE.md — file placement truth
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Selective deep-reads (only architecture files referenced in BOM "Source" column for this phase's components):
- Agents → `architecture/agents.md` | Skills → `architecture/skills.md` | Workflows → `architecture/workflows.md`
- State/memory → `architecture/state.md` | Tools → `architecture/tools.md`
- Tech decisions → `04-TECH_STACK.md` | Design history → `.discussion/design-changelog.md`

If frd.md doesn't exist: stop and tell user to run `/shape-phase {N}` first.
If model.md exists: ask user — overwrite or skip?
</context>

<delegation>
Use subagents to preserve context window:
- `Explore` — codebase research, understand existing patterns in target modules
- `subtask` — parallel research into specific technical areas
</delegation>

<process>
Steps 1-8 sequential. Announce each step.

STEP 1 — READ FRD
Extract from frd.md: capabilities (CAP-{n} IDs and descriptions), consumer roles, functional requirements (FR-{N}.{nn}), non-functional requirements, rabbit holes. Build a mental map of what this phase must do and for whom.

STEP 2 — ARCHITECTURE CONFORMANCE
Read the architecture layers defined in `02-ARCHITECTURE.md`. For each component in scope: identify which layer it belongs to. Flag any that don't fit cleanly — these are architecture violations requiring resolution before proceeding.

STEP 3 — IDENTIFY COMPONENTS
Identify the concrete components — modules, classes, functions — needed to support this phase's domain (informed by the FRD capabilities read in Step 1). Show how they connect. Group by architecture layer. For each component, identify which L2 architecture section defines its design contract. For UI components: list names and relationships only — detailed UI design belongs in separate files.

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
- Every component has an identified architecture layer and traces to an L2 architecture section
- L2 Architecture Conformance table fully populated
- Interfaces use Protocol/ABC with full type signatures
- Mermaid diagrams for component, data flow, and logic flow
- No implementation code — signatures and types only
- Integration points cover both existing system and future extensions
</output>

<verification>
Re-read model.md and check:
1. Component diagram present with Mermaid, components grouped by architecture layer
2. L2 Architecture Conformance table present and fully populated (every component → architecture file + section)
3. All interfaces have Protocol/ABC definitions with typed signatures
4. Key types include Pydantic models and enums with field-level detail
5. Data flow shows type transformations across boundaries
6. Logic flow uses state diagrams or flowcharts (Mermaid)
7. Integration points table covers existing components AND future extensions
8. Zero implementation code (no function bodies beyond `...`)
9. All components conform to the architecture layers defined in `02-ARCHITECTURE.md`

Fix failures before returning.
</verification>

<success_criteria>
- model.md written to disk at `.dev/build-phase/phase-{N}/model.md`
- All components placed in correct architecture layer and traced to L2 architecture section
- L2 Architecture Conformance table fully populated
- Interfaces defined as Protocol/ABC with typed signatures
- Mermaid diagrams for component layout, data flow, and logic flow
- No implementation code
- Architecture conformance verified against `02-ARCHITECTURE.md`
</success_criteria>
