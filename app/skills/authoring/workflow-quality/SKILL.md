---
name: workflow-quality
description: How to design validators, completion criteria, and evidence collection for AutoBuilder workflows
version: "1.0"
triggers:
  - always: true
tags: [authoring, workflows, quality, validators]
applies_to: [planner, reviewer]
priority: 5
---

# Workflow Quality Design

This skill covers how to design validators, completion criteria, and evidence collection in AutoBuilder workflows. These mechanisms are the deterministic layer that prevents partial or incorrect work from advancing through a pipeline.

## Standard Validators

AutoBuilder provides six standard validators. Each reads from session state — validators never perform work.

| Validator | When to Use |
|-----------|-------------|
| `lint_check` | Any workflow producing code. Reads linter output from session state keys `lint_results` (dict with `passed` field) or `lint_passed` (boolean fallback). |
| `test_suite` | Workflows with test generation. Reads `test_results` (dict with `passed` field) or `tests_passed` (boolean fallback). |
| `regression_tests` | When existing tests must remain green after changes. Reads `regression_results` (dict with `passed` and optional `skipped` fields). |
| `code_review` | Workflows with a reviewer agent. Reads `review_passed` (boolean) and checks approval signal. |
| `dependency_validation` | Workflows touching dependency manifests (pyproject.toml, package.json). Reads `dependency_graph` (dict) and `dependency_order` (list). |
| `deliverable_status_check` | Always include in the final stage gate. Reads the deliverable status from session state. |

Use the minimum set of validators that proves correctness. Do not stack validators that check overlapping concerns.

## ValidatorSchedule

The schedule controls when each validator runs relative to pipeline progress.

| Schedule | Runs | Use When |
|----------|------|----------|
| `per_deliverable` | After every deliverable completes | Correctness is checked per-unit (default for most validators) |
| `per_batch` | After each batch of deliverables | Batch-level coherence checks (e.g., integration tests across a batch) |
| `per_taskgroup` | After all deliverables in a TaskGroup finish | TaskGroup-scoped invariants |
| `per_stage` | Once at stage completion gate | Architectural or holistic checks that require full stage output |

Set `lint_check` and `test_suite` to `per_deliverable` — catching failures early reduces rework. Set `code_review` and `regression_tests` to `per_stage` when reviewing all changes together is more meaningful than reviewing each in isolation.

## CompletionCriteria

CompletionCriteria use AND-composition. All conditions must be true for a stage or TaskGroup to advance.

```yaml
completion_criteria:
  deliverable_status: complete          # All deliverables reach COMPLETE status
  validator_results:
    - lint_check: pass
    - test_suite: pass
    - code_review: approved
  approval: director                    # Human-in-the-loop gate
```

**AND-composition rules:**
- Every `validator_results` entry must pass.
- `deliverable_status: complete` requires every deliverable in scope to be in `COMPLETE` state.
- If `approval` is set, human confirmation is required before advancing regardless of validator outcomes.
- Missing `approval` key defaults to `auto` — no human gate.

## Evidence Collection Principle

Validators read existing agent output. They never perform work.

```
# Correct pattern
lint_check reads: session_state["lint_results"]    # Written by linter agent
test_suite reads: session_state["test_results"]    # Written by tester agent

# Incorrect pattern
lint_check runs: ruff check .                       # Validator is not a worker
```

If the expected state key is absent, the validator returns `inconclusive` and the stage gate fails. This surfaces missing agent output explicitly rather than silently passing.

## Three-Layer Completion Reports

Stage completion reports aggregate evidence across three layers:

1. **Functional layer** — deliverable status: are all deliverables `COMPLETE`? Any `FAILED` or `BLOCKED`?
2. **Architectural layer** — design conformance: do code_review results confirm the implementation matches the design?
3. **Contract layer** — spec coverage: do all acceptance criteria from the deliverable spec appear in test results or reviewer sign-off?

Not every workflow needs all three layers. A simple code workflow needs functional and contract layers. An architectural refactor warrants all three.

## Approval Configuration

Per-stage `approval` controls who must sign off before the next stage begins:

| Value | Meaning |
|-------|---------|
| `auto` | No human gate — completion criteria alone advance the stage |
| `director` | Director agent reviews and approves the completion report |
| `ceo` | Human CEO approves via CEO queue — blocks until resolved |

Use `ceo` approval on stages that produce externally visible deliverables (deploys, releases, public-facing changes). Use `director` for internal quality gates that a human should review but not necessarily be blocked on.

## Hard Gate Principle

TaskGroup and stage completion gates are deterministic. The PM cannot override a failed gate.

- A gate that has unmet `validator_results` conditions returns `BLOCKED` regardless of PM instruction.
- A gate with `approval: ceo` remains `BLOCKED` until the CEO queue item resolves.
- The only path through a hard gate is satisfying its conditions — there is no bypass mechanism.

This is intentional. Deterministic gates prevent LLM judgment from overriding objective evidence.

## Checklist

- [ ] Every validator in `validator_results` has a corresponding agent that writes the expected state key
- [ ] `deliverable_status_check` is included in the final stage gate
- [ ] `ValidatorSchedule` matches the granularity of the check (per-deliverable vs per-stage)
- [ ] `approval` is set to `ceo` for externally visible outcomes
- [ ] Completion report covers functional + contract layers at minimum
- [ ] No validator performs work — all validators read from session state
