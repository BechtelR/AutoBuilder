---
description: Assemble the architecture model for a phase — components, interfaces, data flow, design decisions. Zero implementation code. Agent-first reference.
argument-hint: <phase-number>
---

<objective>
Produce an architecture model for Phase {$ARGUMENTS}. Output: `model.md` in `.dev/build-phase/phase-{N}/`.

This is a DESIGN artifact — it assembles the relevant architecture into one coherent picture for this phase. It does not replace the L1/L2 architecture docs (those remain the source of truth). It answers: what components does this phase involve, how do they relate, what types cross their boundaries, and what design decisions apply?

Why this exists: builders working from specs alone lack architectural context. They need to see how this phase's components fit into the system's layers, what interfaces exist between them, and how data flows across boundaries — without reading six architecture files. This document assembles that picture.

The builder conforms to the ARCHITECTURE (L1/L2 docs), not to this document. This document is the assembly, not the authority. Architecture references throughout point to the source of truth.

Conciseness principle: assemble what the builder needs to see in one place. Skip what's obvious. Don't restate architecture docs — reference them. Target: under 400 lines.

CRITICAL: NOT done until model.md is written AND every BOM component traces to an L2 architecture section AND every FRD capability maps to at least one component. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask).

Bootstrap (parallel reads):
- @.dev/build-phase/phase-{N}/frd.md — phase functional requirements (capabilities + FR IDs)
- @.dev/07-COMPONENTS.md — filter by phase number for **authoritative component list** with types and dependencies
- @.dev/02-ARCHITECTURE.md — system architecture (conformance target, defines layers)
- @.dev/03-STRUCTURE.md — file placement truth
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Selective deep-reads — derive from BOM, never hardcode:
1. From the BOM rows for this phase, collect the unique values in the **Source** column (e.g., `agents.md §Agent Hierarchy` → file `.dev/architecture/agents.md`)
2. Deep-read those architecture files IN FULL (not just referenced sections — type definitions, decision numbers, and cross-references can appear anywhere in the file)
3. On-demand only (pull in during research steps if a gap requires it): `.decision-log.md`, `04-TECH_STACK.md`

**CRITICAL**: BOM Source column refs can be stale. Never copy a BOM ref into `architecture_ref` without verifying the section heading exists in the target file.

If frd.md doesn't exist: stop and tell user to run `/shape-phase {N}` first.
If model.md exists: ask user — overwrite or skip?
</context>

<delegation>
Design context — read @.claude/agents/architect.md before design steps. Internalize its principles and checklist.

Use subagents to preserve context window:
- `Explore` — parallel codebase research, understand existing patterns in target modules
- `subtask` — parallel research into specific technical areas, local or external (when reference needed)
- `reviewer` — final document verification (Step 4)
</delegation>

<format-principles>
The output is optimized for agent consumption while remaining human-legible:

1. **YAML blocks for structured relationships** — components, interfaces, data flows, types. Agents parse YAML with near-perfect accuracy. Humans scan it easily.
2. **Prose for design rationale and notes** — the "why" behind decisions, constraints that aren't structural. Keep terse.
3. **YAML is authoritative** — all structured relationships expressed in YAML. The component diagram (Mermaid) is a derived human verification aid, not a data source.
4. **No Protocol/ABC class definitions** — these look like implementation code, which invites builders to refactor rather than conform. Express interfaces as typed input/output contracts.
5. **Reference, don't duplicate** — every component points to its L2 architecture section. Don't restate what's there — the builder reads the referenced section directly.
6. **Scale format to component count** — When a phase has >15 components, use single-line flow-style YAML for component entries (`- { id: F01, name: ..., satisfies: [...] }`). Multi-line blocks are fine for phases with fewer components. Budget: components ≤40% of total lines, leaving room for interfaces, types, flows, and decisions. Apply the same flow-style to interfaces, types, flows, and integrations when needed to stay under 400 lines.
</format-principles>

<process>
Steps 1-4 sequential. Announce each step.

STEP 1 — RESEARCH

A. **Read FRD** — extract capabilities (CAP-{n}), consumer roles, functional requirements, rabbit holes. Understand what this phase must do and for whom.
B. **Build heading index** — for each L2 file identified from the BOM, extract all `##` and `###` headings. These are the ONLY valid values for `architecture_ref`. Never paraphrase or write section names from memory — use the exact heading text.
C. **Verify BOM refs** — for each BOM component's Source column value, confirm the referenced section exists in the heading index. IF a BOM ref points to a nonexistent section, flag it as a gap (stale BOM ref), identify the correct L2 section or flag as an L2 gap, AND add it to the *architect work list* for step G.
D. **Catalog existing L2 decisions** — grep all L2 files for `Decision D` to build a list of already-decided architectural choices. These must NOT be restated as model design decisions.
E. **Verify L2 type definitions** — for types that will appear in the model (from BOM dependencies, FRD requirements, or interface contracts), check if the L2 docs already define their fields. Use the L2 definition verbatim. If new field names are needed, add it to the *architect work list* for step G.
F. **Survey existing code** — if prerequisite phases have been built, understand established patterns, interfaces, and conventions. Use `Explore` agents for substantial codebases.
G. **Architect Work** — if architecture updates are required from current research, do NOT proceed.
Verify the gaps or discrepencies -> stop and notify the user -> use the AskUserQuestion tool to get confirmation to proceed with the corrective architecture work. Do not proceed until the user confirms.
Invoke one or multiple *architect agents* with the full context (including PRD and FRD) to implement a complete and accurate architecture resolution. Backpropogate new work to other related documents as needed.
WAIT for the agent(s) to confirm completion before proceeding.

STEP 2 — DESIGN

For each component group (by architecture layer):

A. **Define component responsibilities** — one sentence each. What it does, not how.
B. **Define interfaces** — at non-trivial component boundaries, specify what's exchanged (typed inputs/outputs) and any important behavioral expectations (idempotency, error propagation, etc.). Every type named in an interface MUST appear in Key Types (defined here or identified as existing from prior phases).
C. **Trace data flows** — for non-trivial paths, show how data transforms across component boundaries. Name the types at each step. Check the FRD for the authoritative flow description — don't invent steps that contradict FRD requirements.
D. **Record design decisions** — ONLY where the L2 architecture leaves options open. Cross-check against the L2 decision catalog from Step 1D. If a decision is already made in L2, reference it in an "Already decided in L2" list — don't re-record it.
E. **Audit terminology** — check that component names and lifecycle terms accurately describe the architectural behavior (e.g., "loop" implies continuous iteration, "turn" implies triggered single-pass; "resume" implies continuing from state, "start" implies fresh beginning). Flag terms that mislead.
F. **Flag gaps** — components that lack L2 guidance, patterns that conflict, open questions for the user. BOM refs to nonexistent L2 sections are gaps — report them to the user and repeat step 1-G above.

STEP 3 — WRITE model.md

**Pre-write gate** (verify before writing):
- Every `architecture_ref` value exists in the heading index from Step 1B (exact match, not paraphrase)
- Every type referenced in interfaces is either defined in Key Types or identified as existing
- No design decision duplicates an L2 decision from the catalog in Step 1D
- Every type's fields match the L2 definition (if one exists) — never invent field names

Estimate total lines: count BOM components × format cost (1 line for flow-style, 8 for multi-line) + ~150 lines for remaining sections. If the estimate exceeds 400, use flow-style YAML for all structured blocks (components, interfaces, types, flows, integrations).

Write using the structure defined in <output>. Verify:
- Every FRD capability maps to at least one component
- Every BOM component appears
- Target under 400 lines

STEP 4 — REVIEWER VERIFICATION

Spawn a `reviewer` agent with model.md, the verification checklist, and source doc references. Reviewer verifies and fixes directly. If reviewer flags items needing design decisions, resolve and re-run.
</process>

<output>
One file: `.dev/build-phase/phase-{N}/model.md`

Read template at `.dev/build-phase/.templates/model.md` — fill all `{placeholders}`, keep all sections. Do NOT add sections beyond those defined in the template.
</output>

<verification>
Re-read model.md and check:
1. Every BOM component for this phase appears in the components block
2. Every FRD capability (CAP-{n}) is satisfied by at least one component
3. Every component has an architecture_ref pointing to an L2 section
4. L2 Architecture Conformance table present and consistent with component architecture_refs
5. Every component has a layer assignment consistent with `02-ARCHITECTURE.md`
6. Interfaces defined for non-trivial component boundaries with typed contracts
7. Key types cover cross-boundary data — no undefined types in interfaces or flows
8. Data flows trace non-trivial paths — no gaps in type chains
9. Design decisions address open architectural choices (not restating L2 docs)
10. Integration points cover existing connections and future extension points
11. No implementation code — no function bodies, no class definitions
12. Component diagram present (single Mermaid flowchart, consistent with YAML components and interfaces)
13. Under 400 lines
14. References L2 docs rather than duplicating their content

Fix failures before returning.
</verification>

<success_criteria>
- model.md written to disk at `.dev/build-phase/phase-{N}/model.md`
- Every BOM component listed with layer, responsibility, and architecture_ref
- Every FRD capability traces to component(s)
- Interfaces defined at non-trivial boundaries
- Data flows trace type chains across components
- Design decisions recorded with rationale
- Under 400 lines
- Zero implementation code, zero duplication of source docs
- Architecture conformance verified against `02-ARCHITECTURE.md`
</success_criteria>
