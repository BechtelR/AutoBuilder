# Phase {N} FRD: {Phase Title}
*Generated: {date}*

## Objective

{Why this phase exists — what consumer-facing value does it unlock? Trace to PRD requirements. 2-3 sentences max.}

## Consumer Roles

{Who consumes this phase's output? These are the roles that requirements are written for and that verify E2E completion. A phase may have multiple consumers.}

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| {Role name} | {Who this is — end-user, API caller, developer, operator, the system itself, etc.} | {What "end-to-end" means for this role — e.g., "API request → response", "workflow submitted → deliverables produced"} |

## Appetite

{Time/effort constraint. Not an estimate — a budget. "This phase is worth X weeks of effort." Fixed time, variable scope — if something doesn't fit in the appetite, it's a no-go, not a stretch goal.}

## Capabilities

{Grouped by observable behavior, not by technical component. Each capability is something a consumer of this phase can DO or OBSERVE when complete. The "consumer" depends on the phase: end-user (dashboard/CLI), API caller (gateway routes), developer/operator (infrastructure/tooling), or the system itself (engine/agents). Order by priority.}

### CAP-{n}: {Capability Name}

{What this capability does — 1-2 sentences from the consumer's perspective. For backend phases, the consumer may be a developer, operator, API caller, or the system itself.}

**Requirements:**
- [ ] **FR-{N}.{nn}**: {E2E consumer-observable behavior, workflow or function. "When X, the system Y." Testable by agents — checked off only when proven via E2E verification.}
- [ ] **FR-{N}.{nn}**: {Next requirement.}
- [ ] **FR-{N}.{nn}**: {Edge case / error scenario — same format. "When X is invalid, the system Y." What does the consumer see? How does the system recover? These are first-class requirements, not afterthoughts.}

---

*(repeat per capability)*

## Non-Functional Requirements

{Quality attributes that cross-cut capabilities. Only categories relevant to this phase — don't pad.}

- [ ] **NFR-{N}.{nn}**: {Measurable target — e.g., "< 200ms response for X at Y concurrency"}
- [ ] **NFR-{N}.{nn}**: {Reliability / security / limits — concrete, not "should be fast"}

## Rabbit Holes

{Known gotchas, complexity traps, and technical risks identified upfront. Each one saves the builder from discovering it mid-implementation.}

- {Gotcha — what it is, why it's dangerous, how to avoid it}

## No-Gos

{What this phase explicitly will NOT do. As important as what it will do. Prevents scope creep during spec and build.}

- {Excluded capability or behavior — with brief rationale}

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-{N}.{nn} | {PRD requirement ID or description} | {PRD domain area} |

*Every FRD requirement derives from a PRD requirement.*

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | {Exact text from roadmap completion contract} | CAP-{n}: FR-{N}.{nn} |

*Every roadmap contract item for this phase must appear. Zero uncovered.*
