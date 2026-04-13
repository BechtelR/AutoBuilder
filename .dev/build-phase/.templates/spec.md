# Phase {N} Spec: {Phase Title}
*Generated: {date}*

## Overview

{Phase goal expanded with design decisions made during research. 2-4 paragraphs covering what this phase delivers, why it matters, and key constraints. Must align with the FRD capabilities (CAP-{n}) — deliverables satisfy FRD requirements, not just roadmap checkboxes.}

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| {Phase X: Title} | {MET/UNMET/N/A} | {concrete proof — git log, file existence, test output} |

## Design Decisions

### DD-{n}: {Decision Title}
{Description of the decision, including context, choice made, and rationale. Use code blocks, diagrams, or tables where they clarify. Each decision should be self-contained — a reader shouldn't need to look elsewhere to understand it.}

(repeat for all decisions)

## Deliverables

### P{N}.D{n}: {Imperative Title}
**Files:** `path/to/file.py`, `path/to/other.py`
**Depends on:** {P{N}.D{x} | —}
**Description:** {What to build — 2-4 sentences. What, not how. Include key patterns or API shapes when they reduce ambiguity.}
**BOM Components:** *(checked off during build when implemented)*
- [ ] `{ID1}` — {component name}
- [ ] `{ID2}` — {component name}
**Requirements:** *(conditions that must be true when complete)*
- [ ] {Specific, measurable condition — no "works correctly"}
- [ ] {Another requirement}
**Validation:**
- `{command to verify — 1-3 commands, e.g. pyright, pytest, curl}`

---

(repeat for all deliverables)

## Build Order

```
Batch 1 (parallel): P{N}.D{x}, P{N}.D{y}
  D{x}: {summary} — {key files}
  D{y}: {summary} — {key files}

Batch 2 (sequential): P{N}.D{z}
  D{z}: {summary} — depends on D{x}, D{y}
```

## Completion Contract Traceability

### FRD Coverage

A **Capability (CAP-{n})** is a named consumer-facing behavior group — the container. **Functional Requirements (FR-{N}.{nn})** are the specific testable conditions within it — the proof. All FRs under a capability must pass for the capability to be satisfied.

| Capability | FRD Requirement | Deliverable(s) |
|---|---|---|
| CAP-{n}: {capability name} | FR-{N}.{nn} | P{N}.D{x} |
| *(same cap)* | FR-{N}.{nn} | P{N}.D{x}, P{N}.D{y} |
| CAP-{n}: {capability name} | FR-{N}.{nn} | P{N}.D{z} |

*Every FRD functional requirement must trace to at least one deliverable. Zero uncovered. If no FRD exists for this phase, omit this section.*

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| {ID} | {Component name} | P{N}.D{x} |

*Every BOM component assigned to Phase {N} in `07-COMPONENTS.md` must appear above. Zero unmapped.*

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | {Exact text from roadmap} | P{N}.D{x}, P{N}.D{y} | `{verification command}` |

## Research Notes

{Key findings from research phase: verified API patterns, import paths, configuration details, gotchas discovered. Use code blocks for API signatures and examples. This section is reference material for the implementer.}

<!-- SPLIT MODE: If spec exceeds 600 lines, delete the Research Notes section above and replace with:
## Research & Extended Design → [spec-research.md](spec-research.md)
See spec-phase.md Step 9 for full split procedure. -->
