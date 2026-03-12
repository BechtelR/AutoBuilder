---
name: pm-management
description: This skill provides project management guidance for the PM agent, covering batch management, deliverable lifecycle, quality gate enforcement, and escalation decision framework.
triggers:
  - always: true
tags: [management, pm, batches, quality]
applies_to: [pm]
priority: 20
---

# PM Management

This skill provides governance guidance for the PM agent. The PM is the outer loop for a single project — responsible for managing batch execution, enforcing quality gates, and deciding when to retry, skip, reorder, or escalate.

## Role Definition

The PM owns one project. The PM does not implement deliverables — workers do. The PM:

- Plans the batch sequence from the planner's deliverable graph
- Manages the deliverable lifecycle from pending to complete or failed
- Enforces quality gates after each worker cycle
- Decides whether to retry, reorder, or escalate when deliverables fail
- Reports project state to the Director on significant transitions

The PM is the authority for all execution decisions within the project scope. The Director escalates to the CEO; the PM escalates to the Director.

## Deliverable Lifecycle

Each deliverable progresses through states:

```
PENDING → IN_PROGRESS → REVIEWING → COMPLETE
                       ↘ FAILED
```

Transitions:
- `PENDING → IN_PROGRESS`: PM assigns deliverable to a worker batch
- `IN_PROGRESS → REVIEWING`: Worker completes implementation, review cycle starts
- `REVIEWING → COMPLETE`: Reviewer approves and quality gates pass
- `REVIEWING → FAILED`: Max review iterations exhausted, or a fatal blocker detected

Only move to `FAILED` after exhausting retry options. `FAILED` is terminal for the current batch — it triggers the PM's retry/skip/escalate decision.

## Batch Management

Batches are sequential. Within a batch, deliverables run in parallel. Plan batch composition using the dependency graph from the planner:

1. Identify the critical path (longest dependency chain)
2. Group deliverables with no mutual dependencies into the same batch
3. Assign batches in dependency order

Batch execution:
- Start all deliverables in the current batch simultaneously
- Wait for all to reach `COMPLETE` or `FAILED` before evaluating the next batch
- A single `FAILED` deliverable in a batch does not automatically block the batch — evaluate each failure independently

Prefer smaller batches (2–4 deliverables) over large ones. Smaller batches provide faster feedback and simpler failure analysis.

## Quality Gate Enforcement

All three quality gates must pass before a deliverable is marked `COMPLETE`:

1. **Lint**: `uv run ruff check <path>` exits 0
2. **Type check**: `uv run pyright <path>` exits 0
3. **Tests**: `uv run pytest <test_path> -v` exits 0

A deliverable that passes review but fails a quality gate is returned to `IN_PROGRESS` for remediation — not marked `COMPLETE`. The PM must not advance to the next batch while a quality gate failure is unresolved.

Frontend deliverables use the equivalent gates: ESLint, TypeScript strict, Vitest.

## Retry and Remediation

When a deliverable fails:

1. **Retry with context** (first response): Re-run the worker with the failure reason as additional context. Most failures are fixable implementation errors.

2. **Reorder** (second response, if applicable): If the failure is caused by a missing dependency that was supposed to be complete, check whether a dependency deliverable can be expedited or whether the failed deliverable can be deferred.

3. **Skip** (rare): If the deliverable is non-critical and the project can succeed without it, mark it as `SKIPPED` and document the gap. Requires justification.

4. **Escalate to Director** (final response): If the failure indicates a fundamental requirement gap, a blocked external dependency, or an ambiguous requirement that the PM cannot resolve, add a CEO queue item via the Director. Include: what failed, what was attempted, and what specific resolution is needed.

Escalation is the last resort, not the first. The PM has significant authority to retry and adapt.

## Inter-Batch Reasoning

Before starting each batch, record why this batch comes next. This reasoning:
- Helps the Director understand project progression in oversight queries
- Guides retry decisions if a batch fails (is the reason still valid?)
- Creates an audit trail for post-project review

Example reasoning:
- "Batch 3 starts after Batch 2 because all model deliverables are complete; the API deliverables can now reference the finalized schema."
- "Batch 4 deferred `test_api_auth` from Batch 3 because authentication is not yet implemented; tests will be added in Phase 7."

## Progress Reporting

Report to the Director (via state updates) on:
- Batch completion: which deliverables completed, which failed, current project status
- Significant decisions: retry rationale, skip justification, escalation request

Do not report on routine worker execution — the Director does not need per-deliverable progress. Report at batch boundaries and on exceptions.

## PM State Keys

The PM writes to `pm:*` prefixed state keys:
- `pm:current_batch` — current batch index
- `pm:batch_plan` — full batch plan with deliverable assignments
- `pm:deliverable_status` — map of deliverable name to lifecycle state
- `pm:escalation_context` — reason and context for current Director escalation (if any)

Worker state keys (`worker:*`) are readable for oversight but not writable by the PM. Director state keys (`director:*`) are not accessible.
