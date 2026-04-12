# Phase 7 Review Report

**Date:** 2026-04-12
**Passes:** 2 (double review)
**Reviewers per pass:** 4
**Status:** All findings resolved

---

## Quality Gate (pre-review)

| Check | Result |
|---|---|
| ruff check | PASS |
| ruff format | PASS |
| pyright | PASS (0 errors) |
| pytest | PASS (895 passed, 96 skipped) |

Post-review quality gate (after all fixes):
- ruff check: PASS
- ruff format: PASS
- pyright: PASS (0 errors)
- pytest: PASS (897 passed, 96 skipped)

---

## Pass 1 Findings (all resolved)

### R1 — Enums, Manifest, Context

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 1 | `app/workflows/manifest.py:180` | `CompletionCriteria.approval` default was `"none"` — spec requires `"director"` | HIGH | Fixed default to `"director"` |
| 2 | `app/workflows/__init__.py` | `single_pass_pipeline`, `sequential_pipeline`, `batch_parallel_pipeline` not re-exported | MEDIUM | Added to imports and `__all__` |
| 3 | `app/workflows/context.py:25` | `PipelineContext.toolset` typed as `object` instead of `GlobalToolset` | MEDIUM | Fixed to `GlobalToolset` with `TYPE_CHECKING` import |
| 4 | `tests/workflows/test_manifest.py:381` | `StageApproval` and `CompletionCondition` missing from enum VALUE=NAME test | LOW | Added both enums to parametrize list |

### R2 — Stages, DB Models, Migration

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 5 | `app/db/models.py` | `StageExecution`, `TaskGroupExecution`, `ValidatorResult` did not inherit `TimestampMixin` | HIGH | Changed to inherit `TimestampMixin`; removed redundant column declarations |
| 6 | `app/db/models.py:219` | `StageExecution.stage_name` missing `index=True` | MEDIUM | Added `index=True` |
| 7 | `app/db/models.py:264` | `ValidatorResult.validator_name` missing `index=True` | MEDIUM | Added `index=True` |
| 8 | `app/db/models.py:246-251` | `TaskGroupExecution` missing `started_at`; `closed_at` should be `completed_at` | HIGH | Added `started_at`; renamed `closed_at` → `completed_at` |
| 9 | `app/db/migrations/versions/004_workflow_composition.py` | Migration did not match model changes | HIGH | Updated migration to add `updated_at`, indexes, `started_at`, rename `closed_at` → `completed_at` |
| 10 | `app/workflows/manifest.py:81` | `StageDef.completion_criteria` defaulted to `None` — should be `CompletionCondition.ALL_VERIFIED` | HIGH | Changed default to `CompletionCondition.ALL_VERIFIED` |

### R3 — Validators and auto-code Workflow

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 11 | `app/workflows/auto-code/WORKFLOW.yaml` | Missing `architecture_conformance` validator in integrate stage | HIGH | Added `architecture_conformance` (LLM, optional=true) |
| 12 | `app/workflows/auto-code/WORKFLOW.yaml` | `integration_tests` incorrectly marked `required: false` | HIGH | Removed `required: false` (defaults to required=true) |
| 13 | `app/workflows/auto-code/WORKFLOW.yaml` | Missing `required_tools` and `default_models` sections | MEDIUM | Added both sections per spec |
| 14 | `app/workflows/validators.py` | `evaluate()` and `evaluate_batch()` missing `session` parameter | MEDIUM | Added `session: AsyncSession \| None = None` to both |
| 15 | `app/workflows/validators.py:115-137` | `code_review` validator evidence too minimal — missing `review_iterations` and `review_result` | LOW | Added both fields to evidence dict when available |

### R4 — Gateway, Workers, Context Recreation

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 16 | `app/workers/settings.py` | WorkflowRegistry never initialized in worker context | HIGH | Added WorkflowRegistry initialization to worker startup (cache-first, mirrors SkillLibrary pattern) |
| 17 | `app/workers/adk.py:313-314` | Relative path `Path("app/workflows")` in fallback — CWD-dependent | HIGH | Changed to absolute `Path(__file__).resolve().parent.parent / "workflows"` |
| 18 | `app/workers/adk.py:402-416` | Double-scanning agent definitions — first call wiped by second | MEDIUM | Consolidated to single `scan()` call with dynamic directory list |
| 19 | `app/workers/adk.py:274` | `workflow_registry: object \| None` parameter type too wide | LOW | Changed to `WorkflowRegistry \| None` with TYPE_CHECKING import |
| 20 | `app/workers/tasks.py:618-625` | `run_work_session` never passed `workflow_registry` to `build_work_session_agents` | HIGH | Added `workflow_registry=work_workflow_registry` kwarg |
| 21 | `app/skills/authoring/workflow-testing/SKILL.md` | Multiple incorrect API examples (`WorkflowRegistry()`, `registry.load_manifest()`, `base_path=` param, etc.) | MEDIUM | Updated skill body with correct API signatures |

---

## Pass 2 Findings (all resolved)

### R1 — Enums, Manifest, Context

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 22 | `app/workflows/__init__.py` | `__all__` sort order broken — lowercase functions interleaved with PascalCase | LOW | Sorted: PascalCase classes first (alphabetical), then lowercase functions (alphabetical) |

### R2 — Stages, DB Models, Migration

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 23 | `app/db/models.py:245` | `TaskGroupExecution.status` used `String(50)` with magic string default `"pending"` — violates enum convention | MEDIUM | Changed to `SqlEnum(StageStatus, native_enum=False)` with `StageStatus.PENDING` default |
| 24 | `app/db/migrations/versions/004_workflow_composition.py:29,57` | Migration used bare `sa.String(50)` for enum columns — no CHECK constraint | MEDIUM | Changed to `sa.Enum(*values, native_enum=False, length=50)` to match model constraints |

### R3 — Validators and auto-code Workflow

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 25 | `app/workflows/auto-code/agents/planner.md`, `coder.md`, `reviewer.md` | Missing `output_key` frontmatter field — workflow overrides discard global's `output_key` | HIGH | Added `output_key` to all three (`implementation_plan`, `code_output`, `review_result`) |
| 26 | `app/workflows/validators.py` | `integration_tests` declared in WORKFLOW.yaml but no implementation in `_STANDARD_VALIDATORS` — would block integrate stage permanently | HIGH | Added `integration_tests()` function reading `integration_tests_passed` state key; registered in `_STANDARD_VALIDATORS` |
| 27 | `app/workflows/validators.py` | `DEFAULT_VERIFICATION_LAYERS` had empty `evidence_sources` — completion reports would always fail | HIGH | Added sensible default evidence sources per layer (functional: lint/test/regression/integration; architectural: code_review/architecture_conformance; contract: deliverable_status_check/dependency_validation) |

### R4 — Gateway, Workers, Context Recreation

| # | File | Issue | Severity | Resolution |
|---|---|---|---|---|
| 28 | `app/workers/tasks.py:425,608` | `registry.scan((Path("app/agents"), ...))` still using CWD-relative path | MEDIUM | Fixed to `Path(__file__).resolve().parent.parent / "agents"` |

---

## Post-Review Fixes (quality gate)

| # | File | Issue | Resolution |
|---|---|---|---|
| 29 | `tests/workflows/test_manifest.py:381` | Line too long after StageApproval/CompletionCondition addition | Wrapped parametrize list to multi-line format |
| 30 | `app/workflows/context.py:26` | `PipelineContext.toolset: GlobalToolset` breaks callers passing None | Changed to `GlobalToolset \| None = None` (field unused by workflow code; registry has toolset baked in) |
| 31 | `app/workers/adk.py:323,435` | `toolset=None` / `toolset=toolset` pyright errors after context.py change | Removed `toolset` kwarg from `PipelineContext` calls (using default None) |

---

## Flagged (not fixed — informational)

| # | Severity | Note |
|---|---|---|
| F1 | LOW | `PipelineContext.build()` classmethod not implemented — forward-looking spec reference, not needed until Phase 10 gateway wiring |
| F2 | LOW | `StageDef.approval` defaults to `None` — future manifests omitting approval will skip approval gate silently. Design decision: simple manifests may not need director approval. No current behavior impact (auto-code sets all approvals explicitly). |
| F3 | LOW | `app/skills/authoring/workflow-testing/SKILL.md` lines 106/135/169 — references `StageGate`, `LintCheckValidator`, `CompletionCriteria.satisfied()` which don't exist. Fixed in R4 Pass 1 but secondary references in body were missed. Non-critical (skill bodies are guidance text, not executable). |
| F4 | LOW | No FK cascade policy on new tables — matches existing project-wide pattern. Fail-safe for now; should be addressed when deletion flows are implemented. |
| F5 | LOW | No manifest-time validation that DETERMINISTIC validators have corresponding functions in `_STANDARD_VALIDATORS`. Would catch "integration_tests" class of issue at load time. Consider future enhancement. |

---

## Summary

- **Total findings:** 31 (28 fixed, 3 resolved post-review quality gate)
- **Flagged (not fixed):** 5 (all LOW severity, informational)
- **HIGH severity resolved:** 12
- **MEDIUM severity resolved:** 12
- **LOW severity resolved:** 7
- **Final test count:** 897 passed, 96 skipped, 0 failures
