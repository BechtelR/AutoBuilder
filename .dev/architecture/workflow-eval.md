[<- Architecture Overview](../02-ARCHITECTURE.md)

# Workflow Eval Suite

**AutoBuilder Platform**
**Workflow Evaluation Architecture Reference**

---

## Status

**Phase 14 — Pre-Design Sketch.** This document captures architectural intent from Phase 7b shaping. It will be expanded to a full L2 spec during Phase 14 shaping. Phase 7b builds the foundational dry run; Phase 14 elevates it to the self-improving eval suite described here.

---

## Why This Exists

The high-performance of workflows is the entire utility of AutoBuilder. Every workflow that enters production should have been stress-tested against the eval suite. Every production failure should make the eval suite smarter. The tenth run of a workflow should be measurably better than the first — not because the LLM improved, but because the eval suite caught more edge cases and the workflow was refined against them.

**PRD traceability:** PR-6 (workflow plugins model composability), PR-22 (three-layer verification with machine evidence), Success Metric: "Workflow memory improvement — escalations per deliverable decrease >=20% between run 1 and run 5."

---

## Core Architecture

### Eval Suite as Workflow Certification Pipeline

The eval suite is not a test runner. It is a **certification pipeline** — a structured process that a workflow must pass before activation and that accumulates rigor over time.

```
Workflow authored
  -> Eval suite runs (multiple passes)
    -> Pass 1: Happy path with synthetic input (lightweight LLM)
    -> Pass 2: Error injection (invalid inputs, agent failures, timeout)
    -> Pass 3: Lifecycle events (pause/resume, mid-execution edit, escalation)
    -> Pass 4+: Regression cases (accumulated from prior production failures)
  -> Eval report generated
    -> All passes green -> CEO reviews report + workflow -> Activation gate
    -> Any pass red -> Issues surfaced -> Workflow revised -> Re-run suite
```

### Self-Improvement Feedback Loop

```
Workflow activated -> Production execution -> Outcomes captured
     ^                                            |
     |                                            v
     |                              Failure? Escalation? Quality issue?
     |                                            |
     |                                            v
     |                              New eval test case generated
     |                              (input scenario + expected behavior)
     |                                            |
     |                                            v
     +---- Improvement proposal <--- Eval suite expanded
                |
                v
           Workflow revised -> Re-certified against expanded suite
```

Each production failure becomes a regression test. The eval suite grows monotonically. A workflow's certification bar rises over time — which is exactly how reliability compounds.

### Eval Dimensions

| Dimension | What It Tests | Pass Criteria |
|-----------|--------------|---------------|
| **Functional** | Does the workflow produce correct output for known inputs? | Output matches expected structure and content quality threshold |
| **Lifecycle** | Does the workflow handle pause, resume, edit, abort correctly? | State preserved across lifecycle events; no data loss |
| **Failure handling** | Does the workflow escalate, retry, and recover correctly? | Failures escalate to correct tier; recovery doesn't re-execute verified work |
| **Gate integrity** | Do quality gates block bad output? | Deliberately bad input fails gates; good input passes |
| **State flow** | Do nodes pass data correctly between them? | All declared inputs satisfied; no orphaned state keys |
| **Performance** | Does the workflow complete within time/cost budget? | Wall-clock and token usage within configured thresholds |

### Pluggable Test Scenarios

Workflow authors define test scenarios alongside the workflow:

```
auto-code/
  WORKFLOW.yaml
  pipeline/                    # node prompts
  agents/
  eval/                        # eval suite scenarios
    happy_path.yaml            # standard input, expected output shape
    invalid_brief.yaml         # malformed input, expected rejection
    agent_failure.yaml         # simulated agent timeout, expected escalation
    regression/                # auto-accumulated from production
      001_missing_dep.yaml     # from production incident 2026-05-12
```

Each scenario defines: input (synthetic brief/materials), expected behavior (which nodes run, what state keys are written), expected outcome (pass/fail, output structure), and failure injection (if any).

### Eval Reports

Machine-readable structured reports that serve as:
- **Certification evidence** for the activation gate
- **Regression baseline** for future eval runs
- **Input to the context optimizer** (which context configurations produced best results)

---

## Relationship to Phase 7b Dry Run

Phase 7b builds the **execution foundation**:
- Full E2E dry run with lightweight LLM
- Multiple passes (happy path + error path minimum)
- Pause/resume and edit injection testing
- Structured report output

Phase 14 wraps this foundation in:
- The self-improving regression accumulation framework
- Pluggable test scenario format
- Integration with the context optimizer
- Automated test case generation from production failures
- Certification workflow (eval suite as a gate, not just a check)

The Phase 7b dry run is designed to be forward-compatible with Phase 14's eval suite — same execution model, same report structure, expanded scope.

---

## See Also

- [Context Optimizer](./context-optimizer.md) — optimizes context assembly based on eval results
- [Workflows](./workflows.md) — workflow composition system
- [Execution](./execution.md) — autonomous execution engine
- Pre-work notes: [.dev/.todo/260413_pre-phase-14.md](../.todo/260413_pre-phase-14.md)

---

**Document Version:** 0.1 (Pre-Design Sketch)
**Last Updated:** 2026-04-13
**Status:** Phase 14 — Pre-Design
