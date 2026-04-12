---
name: workflow-testing
description: How to test and validate AutoBuilder workflow manifests and pipeline composition
version: "1.0"
triggers:
  - always: true
tags: [authoring, workflows, testing, validation]
applies_to: [coder, tester]
priority: 5
---

# Workflow Testing

This skill covers how to test and validate AutoBuilder workflow manifests and pipeline composition. Workflow tests are Python tests under `tests/workflows/` that verify registry discovery, manifest parsing, stage transitions, and validator logic.

## Validating a WORKFLOW.yaml Manifest

WORKFLOW.yaml uses progressive disclosure — only `name` and `description` are strictly required. Validate with WorkflowRegistry directly:

```python
from pathlib import Path
from app.workflows.registry import WorkflowRegistry

registry = WorkflowRegistry(workflows_dir=Path("app/workflows"))
registry.scan()
manifest = registry.get_manifest("my-workflow")
assert manifest.name == "my-workflow"
```

**Manifest validation checklist:**
- `name` matches the containing directory name — the registry enforces this at scan time.
- All keys in `required_tools` are recognized tool role names.
- All `triggers` entries use recognized trigger types (`deliverable_type`, `tag_match`, `always`).
- `default_models` keys are valid model role names (`CODE`, `PLAN`, `REVIEW`, `FAST`).

A malformed manifest produces a warning log and is skipped — it does not fail startup. Test for this by writing a deliberately broken WORKFLOW.yaml into a temp directory and calling `registry.scan()`, then asserting the broken workflow is absent from `registry.list_available()`.

## Testing WorkflowRegistry Discovery

WorkflowRegistry scans `app/workflows/` at startup. Test discovery by pointing the registry at a temp directory:

```python
import pytest
from pathlib import Path
from app.workflows.registry import WorkflowRegistry

def test_registry_discovers_workflow(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "my-workflow"
    workflow_dir.mkdir()
    (workflow_dir / "WORKFLOW.yaml").write_text(
        "name: my-workflow\ndescription: test workflow\n"
    )

    registry = WorkflowRegistry(workflows_dir=tmp_path)
    registry.scan()

    names = [e.name for e in registry.list_available()]
    assert "my-workflow" in names
```

**Match testing — keyword trigger:**

```python
def test_registry_matches_by_tag(tmp_path: Path) -> None:
    # Write manifest with tag_match trigger
    # Assert registry.match(deliverable) returns expected workflow
```

**Match testing — explicit trigger:**

```python
def test_registry_matches_explicit(tmp_path: Path) -> None:
    # Write manifest with deliverable_type trigger
    # Assert match returns this workflow for a matching deliverable type
```

## Testing Pipeline Instantiation

Test that `create_pipeline()` returns a valid ADK agent tree without actually running the pipeline:

```python
from pathlib import Path
from unittest.mock import MagicMock
from app.workflows.registry import WorkflowRegistry

async def test_pipeline_instantiation() -> None:
    ctx = MagicMock()
    registry = WorkflowRegistry(workflows_dir=Path("app/workflows"))
    registry.scan()
    pipeline = await registry.create_pipeline("auto-code", ctx)
    assert pipeline is not None
    assert hasattr(pipeline, "name")
```

Do not invoke the pipeline in unit tests — that requires a live ADK session. Pipeline instantiation tests verify the agent tree is constructed without errors.

## Stage Transition Testing

Stage transitions are deterministic: a stage advances when its `CompletionCriteria` are fully satisfied. Test by constructing a session state that satisfies (or fails) the criteria:

```python
from app.workflows.validators import verify_stage_completion, ValidatorRunner
from app.workflows.manifest import WorkflowManifest, ValidatorResult

def test_stage_advances_when_criteria_met() -> None:
    state = {
        "pm:current_stage": "build",
        "lint_results": {"passed": True},
        "test_results": {"passed": True},
        "deliverable_statuses": {"d1": "COMPLETED"},
    }
    # Run validators, then check stage completion gate
    passed, failures = verify_stage_completion(state, manifest, validator_results)
    assert passed is True

def test_stage_blocked_when_validator_fails() -> None:
    state = {
        "pm:current_stage": "build",
        "lint_results": {"passed": False},
        "test_results": {"passed": True},
        "deliverable_statuses": {"d1": "COMPLETED"},
    }
    passed, failures = verify_stage_completion(state, manifest, validator_results)
    assert passed is False
    assert any("lint_check" in f for f in failures)
```

## Validator Result Testing

Validators read session state keys written by agents. Mock session state with the expected keys to test each validator in isolation:

```python
from app.workflows.validators import lint_check

def test_lint_check_passes_on_clean_output() -> None:
    state = {"lint_results": {"passed": True, "error_count": 0}}
    result = lint_check(state)
    assert result.passed is True

def test_lint_check_fails_when_key_absent() -> None:
    result = lint_check({})
    assert result.passed is False
    assert "No lint results" in result.message
```

A missing state key causes the validator to return `passed=False` — test that `verify_stage_completion()` returns failures when a required validator has not been evaluated.

## Testing Stage Completion AND-Composition

Stage completion gates use AND-composition via `verify_stage_completion()`. All conditions (validators passed, deliverables complete, approval granted) must be true. Test every partial-failure combination:

```python
import pytest
from app.workflows.validators import verify_stage_completion, ValidatorResult

@pytest.mark.parametrize("validator_passed,deliverables_done,expected", [
    (True, True, True),    # All conditions met
    (False, True, False),  # Validator failed
    (True, False, False),  # Deliverable incomplete
    (False, False, False), # Both failed
])
def test_stage_gate_and_composition(
    validator_passed: bool, deliverables_done: bool, expected: bool
) -> None:
    status = "COMPLETED" if deliverables_done else "IN_PROGRESS"
    state: dict[str, object] = {
        "pm:current_stage": "build",
        "deliverable_statuses": {"d1": status},
    }
    results = [ValidatorResult(validator_name="lint_check", passed=validator_passed)]
    passed, failures = verify_stage_completion(state, manifest, results)
    assert passed is expected
```

## Key Test File Patterns

| File | Tests |
|------|-------|
| `tests/workflows/test_registry.py` | Registry discovery, manifest parsing, trigger matching |
| `tests/workflows/test_stages.py` | Stage gate evaluation, transition logic, approval blocking |
| `tests/workflows/test_validators.py` | Individual validator pass/fail logic, missing state key handling |

All workflow tests use real file I/O via `tmp_path` for manifest loading and in-memory dicts for session state. No Redis or database required — workflow logic is stateless by design.

## Checklist

- [ ] Registry scan test uses `tmp_path`, not `app/workflows/` directly
- [ ] Pipeline instantiation test mocks `PipelineContext`, does not invoke ADK
- [ ] Stage transition tests cover: all-pass, single-fail, missing-key (inconclusive)
- [ ] AND-composition tests use `parametrize` for all partial-failure combinations
- [ ] Validator tests assert `passed=False` with descriptive message when expected state key is absent
