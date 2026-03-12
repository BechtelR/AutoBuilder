---
name: task-decomposition
description: This skill provides strategies for decomposing complex tasks into structured deliverables with dependency tracking, acceptance criteria, and validation commands.
triggers:
  - always: true
tags: [planning, decomposition, deliverables]
applies_to: [planner]
priority: 10
---

# Task Decomposition

This skill provides strategies for decomposing a complex engineering goal into a structured set of deliverables that can be executed by AutoBuilder's worker pipeline.

## Core Principle

A deliverable is the smallest independently verifiable unit of work. It has a clear input, a clear output, and acceptance criteria that can be checked without human judgment. When decomposing, ask: "Can a worker execute this without clarification? Can a reviewer verify it without running the entire system?"

## Decomposition Strategies

Choose the strategy that fits the nature of the work:

**Functional decomposition** — split by capability. Use when the goal is a feature with multiple independent sub-capabilities.
- Example: "Add project archival" → archive endpoint, archive UI button, cascade to deliverables, audit event

**Structural decomposition** — split by layer. Use when changes must propagate through the stack (data model → migration → API → frontend).
- Example: "Add `owner_id` to projects" → migration deliverable, model update, API update, TypeScript regen

**Risk-based decomposition** — tackle the highest-uncertainty work first. Use when the goal has unknowns that could invalidate later work.
- Example: "Integrate new LLM provider" → provider abstraction first, then routing, then fallback

**Batch-aligned decomposition** — group into execution batches where items in the same batch have no dependencies on each other. This enables parallel execution.

## Dependency Graph

Every deliverable specifies its dependencies. A deliverable can only start when all its dependencies are complete.

Rules:
- Migration deliverables must precede model and API deliverables that use the new columns
- Model deliverables must precede API deliverables that expose the model
- API deliverables must precede frontend deliverables that consume the endpoints
- Test deliverables depend on the deliverable they test

Represent dependencies explicitly:
```
migration_001  (no deps)
model_project  → depends on: migration_001
api_projects   → depends on: model_project
test_api       → depends on: api_projects
```

Identify the critical path: the longest dependency chain determines minimum completion time.

## Acceptance Criteria

Each deliverable includes acceptance criteria — specific, binary conditions. Avoid vague criteria.

Good criteria:
- `uv run pytest tests/gateway/routes/test_projects.py -v` passes
- `uv run ruff check app/gateway/routes/projects.py` exits 0
- `GET /projects/{id}` returns `{"id": "...", "status": "ACTIVE", ...}` with status 200
- Migration applies cleanly: `uv run alembic upgrade head` exits 0

Avoid:
- "Code is well-structured" (not verifiable)
- "Tests pass" (too vague — which tests?)
- "Frontend looks good" (requires human judgment)

## Validation Commands

Each deliverable includes validation commands that can be run by the worker after implementation:

```yaml
validation:
  - uv run ruff check app/gateway/routes/projects.py
  - uv run pyright app/gateway/routes/projects.py
  - uv run pytest tests/gateway/routes/test_projects.py -v
```

Structure validation commands to be:
- Targeted — test the specific deliverable, not the full suite
- Fast — single-file lint and type checks before full test runs
- Ordered — lint first (cheapest), then type check, then tests

## Batch Grouping

Group deliverables into sequential batches. Items in the same batch run in parallel; batches run sequentially.

Batch construction rules:
1. All items in a batch must have their dependencies in prior batches
2. Prefer smaller batches (2–4 items) over large batches — smaller batches have faster feedback loops
3. Risk-reduction deliverables go in early batches
4. Test deliverables can be in the same batch as their implementation deliverable if they are independent (e.g., test for a previously-completed deliverable)

Example batch plan:
```
Batch 1: migration_001
Batch 2: model_project, model_deliverable  (parallel, both depend on migration_001)
Batch 3: api_projects, api_deliverables    (parallel, each depends on its model)
Batch 4: test_api_projects, test_api_deliverables  (parallel)
```

## Sizing Guidelines

Deliverables should be completable in a single worker session. Indicators a deliverable is too large:
- Acceptance criteria require changes across more than 3 files
- Estimated implementation exceeds ~300 lines of new code
- The deliverable description requires "and" to be meaningful (split at each "and")

Indicators a deliverable is too small:
- It has no acceptance criteria that can be independently verified
- It would take under 5 minutes to complete manually

## Output Format

Produce a structured plan with:
1. Deliverable list with names, descriptions, and type tags
2. Dependency graph (explicit list per deliverable)
3. Batch assignment
4. Acceptance criteria per deliverable
5. Validation commands per deliverable

Always state the inter-batch reasoning: why does batch N come before batch N+1? This helps the PM agent reason about reordering when a deliverable fails.
