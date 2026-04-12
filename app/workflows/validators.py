"""Validator framework -- evidence collection, completion gates, and reports."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import cast

from app.models.constants import STAGE_CURRENT
from app.models.enums import (
    CompletionCondition,
    DeliverableStatus,
    StageApproval,
    ValidatorSchedule,
    ValidatorType,
)
from app.workflows.manifest import (
    CompletionLayerDef,
    CompletionReport,
    ReportSection,
    StageDef,
    ValidatorDefinition,
    ValidatorResult,
    VerificationLayer,
    WorkflowManifest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias for validator functions
# ---------------------------------------------------------------------------

_ValidatorFunc = Callable[[dict[str, object]], ValidatorResult]

# ---------------------------------------------------------------------------
# Standard validators -- pure functions reading state keys
# ---------------------------------------------------------------------------


def lint_check(state: dict[str, object]) -> ValidatorResult:
    """Check lint results from state. Passes if lint_passed is True."""
    lint_passed = state.get("lint_passed")
    if lint_passed is None:
        return ValidatorResult(
            validator_name="lint_check",
            passed=False,
            message="No lint results found in state",
        )
    return ValidatorResult(
        validator_name="lint_check",
        passed=bool(lint_passed),
        evidence={"lint_passed": lint_passed, "lint_results": state.get("lint_results", {})},
        message="" if lint_passed else "Lint check failed",
    )


def test_suite(state: dict[str, object]) -> ValidatorResult:
    """Check test results from state. Passes if tests_passed is True."""
    tests_passed = state.get("tests_passed")
    if tests_passed is None:
        return ValidatorResult(
            validator_name="test_suite",
            passed=False,
            message="No test results found in state",
        )
    return ValidatorResult(
        validator_name="test_suite",
        passed=bool(tests_passed),
        evidence={
            "tests_passed": tests_passed,
            "test_results": state.get("test_results", {}),
        },
        message="" if tests_passed else "Test suite failed",
    )


def regression_tests(state: dict[str, object]) -> ValidatorResult:
    """Check regression test results. Passes if passed is True or skipped."""
    results = state.get("regression_results")
    if results is None:
        return ValidatorResult(
            validator_name="regression_tests",
            passed=False,
            message="No regression results found in state",
        )
    if isinstance(results, dict):
        rd = cast("dict[str, object]", results)
        skipped = rd.get("skipped", False)
        if skipped:
            return ValidatorResult(
                validator_name="regression_tests",
                passed=True,
                evidence={"skipped": True},
                message="Regression tests skipped",
            )
        passed = bool(rd.get("passed", False))
        return ValidatorResult(
            validator_name="regression_tests",
            passed=passed,
            evidence={k: v for k, v in rd.items()},
            message="" if passed else "Regression tests failed",
        )
    return ValidatorResult(
        validator_name="regression_tests",
        passed=False,
        evidence={"raw": str(results)},
        message="Invalid regression results format",
    )


def code_review(state: dict[str, object]) -> ValidatorResult:
    """Check review status. Passes if review_passed is True."""
    review_passed = state.get("review_passed")
    if review_passed is None:
        return ValidatorResult(
            validator_name="code_review",
            passed=False,
            message="No review result found in state",
        )
    return ValidatorResult(
        validator_name="code_review",
        passed=bool(review_passed),
        evidence={"review_passed": review_passed},
        message="" if review_passed else "Code review failed",
    )


def dependency_validation(state: dict[str, object]) -> ValidatorResult:
    """Check dependency graph for validity. Passes if dependency_order exists."""
    order = state.get("dependency_order")
    if order is None:
        return ValidatorResult(
            validator_name="dependency_validation",
            passed=False,
            message="No dependency order found in state",
        )
    if not isinstance(order, list):
        return ValidatorResult(
            validator_name="dependency_validation",
            passed=False,
            evidence={"raw": str(order)},
            message="Dependency order is not a list",
        )
    return ValidatorResult(
        validator_name="dependency_validation",
        passed=True,
        evidence={"dependency_order": order},
    )


def deliverable_status_check(state: dict[str, object]) -> ValidatorResult:
    """Check that all deliverables are at required status."""
    statuses = state.get("deliverable_statuses")
    if statuses is None:
        return ValidatorResult(
            validator_name="deliverable_status_check",
            passed=False,
            message="No deliverable statuses found in state",
        )
    if not isinstance(statuses, dict):
        return ValidatorResult(
            validator_name="deliverable_status_check",
            passed=False,
            message="Invalid deliverable statuses format",
        )
    sd = cast("dict[str, object]", statuses)
    completed = DeliverableStatus.COMPLETED
    all_done = all(v == completed for v in sd.values())
    incomplete = [k for k, v in sd.items() if v != completed]
    return ValidatorResult(
        validator_name="deliverable_status_check",
        passed=all_done,
        evidence={"total": len(sd), "incomplete": incomplete},
        message="" if all_done else f"{len(incomplete)} deliverables not completed",
    )


# ---------------------------------------------------------------------------
# Validator dispatch registry
# ---------------------------------------------------------------------------

_STANDARD_VALIDATORS: dict[str, _ValidatorFunc] = {
    "lint_check": lint_check,
    "test_suite": test_suite,
    "regression_tests": regression_tests,
    "code_review": code_review,
    "dependency_validation": dependency_validation,
    "deliverable_status_check": deliverable_status_check,
}


# ---------------------------------------------------------------------------
# ValidatorRunner -- dispatches by type, collects results
# ---------------------------------------------------------------------------


class ValidatorRunner:
    """Dispatches validators by type and collects results."""

    def evaluate(
        self,
        validator_def: ValidatorDefinition,
        state: dict[str, object],
    ) -> ValidatorResult:
        """Evaluate a single validator against the given state."""
        if validator_def.type == ValidatorType.DETERMINISTIC:
            func = _STANDARD_VALIDATORS.get(validator_def.name)
            if func is not None:
                return func(state)
            return ValidatorResult(
                validator_name=validator_def.name,
                passed=False,
                message=f"Unknown validator: {validator_def.name}",
            )

        if validator_def.type == ValidatorType.APPROVAL:
            approved = state.get(f"approval:{validator_def.name}")
            return ValidatorResult(
                validator_name=validator_def.name,
                passed=bool(approved),
                evidence={"approved": approved},
                message="" if approved else "Approval not yet granted",
            )

        if validator_def.type == ValidatorType.LLM:
            result_key = f"llm_validator:{validator_def.name}"
            result = state.get(result_key)
            if result is None:
                return ValidatorResult(
                    validator_name=validator_def.name,
                    passed=False,
                    message=(f"LLM validator '{validator_def.name}' has not produced results"),
                )
            return ValidatorResult(
                validator_name=validator_def.name,
                passed=bool(result),
                evidence={"llm_result": result},
            )

        return ValidatorResult(
            validator_name=validator_def.name,
            passed=False,
            message=f"Unknown validator type: {validator_def.type}",
        )

    def evaluate_batch(
        self,
        validators: list[ValidatorDefinition],
        schedule: ValidatorSchedule,
        state: dict[str, object],
    ) -> list[ValidatorResult]:
        """Evaluate all validators matching the given schedule."""
        results: list[ValidatorResult] = []
        for v in validators:
            if v.schedule == schedule:
                results.append(self.evaluate(v, state))
        return results


# ---------------------------------------------------------------------------
# Completion gates (F27/F28)
# ---------------------------------------------------------------------------


def _check_deliverable_statuses(state: dict[str, object]) -> tuple[bool, list[str]]:
    """Check deliverable_statuses state key. Returns (all_done, incomplete_names)."""
    statuses = state.get("deliverable_statuses")
    if statuses is None:
        return (False, [])
    if not isinstance(statuses, dict):
        return (False, [])
    sd = cast("dict[str, object]", statuses)
    completed = DeliverableStatus.COMPLETED
    incomplete = [k for k, v in sd.items() if v != completed]
    return (len(incomplete) == 0, incomplete)


def _find_stage(manifest: WorkflowManifest, name: object) -> StageDef | None:
    """Find a stage definition by name."""
    for s in manifest.stages:
        if s.name == name:
            return s
    return None


def verify_stage_completion(
    state: dict[str, object],
    manifest: WorkflowManifest,
    validator_results: list[ValidatorResult],
) -> tuple[bool, list[str]]:
    """AND-composed gate: deliverables + validators + approval must all pass.

    Returns (passed, list of failure reasons).
    Hard gate -- no override parameter.
    """
    if not manifest.stages:
        return (True, [])

    failures: list[str] = []

    current_stage_name = state.get(STAGE_CURRENT)
    if current_stage_name is None:
        return (False, ["No current stage set"])

    stage_def = _find_stage(manifest, current_stage_name)
    if stage_def is None:
        return (False, [f"Stage '{current_stage_name}' not found in manifest"])

    # Dimension 1: Check required validators passed
    for v_def in stage_def.validators:
        if not v_def.required:
            continue
        matching = [r for r in validator_results if r.validator_name == v_def.name]
        if not matching:
            failures.append(f"Validator '{v_def.name}' has not been evaluated")
        elif not matching[-1].passed:
            failures.append(f"Validator '{v_def.name}' failed")

    # Dimension 2: Check deliverable status if criteria specified
    criteria = stage_def.completion_criteria
    if criteria in (
        CompletionCondition.ALL_VERIFIED,
        CompletionCondition.ALL_DELIVERABLES_PLANNED,
    ):
        if state.get("deliverable_statuses") is None:
            failures.append("No deliverable statuses found")
        else:
            all_done, incomplete = _check_deliverable_statuses(state)
            if not all_done:
                failures.append(f"{len(incomplete)} deliverables not completed")

    # Dimension 3: Check approval
    if stage_def.approval and stage_def.approval != StageApproval.AUTO:
        approval_key = f"approval:stage:{current_stage_name}"
        if not state.get(approval_key):
            failures.append(f"Stage '{current_stage_name}' not approved ({stage_def.approval})")

    return (len(failures) == 0, failures)


def verify_taskgroup_completion(
    state: dict[str, object],
    manifest: WorkflowManifest,
    validator_results: list[ValidatorResult],
) -> tuple[bool, list[str]]:
    """Hard gate for TaskGroup close -- deliverables done, validators passing.

    Returns (passed, list of failure reasons).
    """
    if not manifest.stages:
        return (True, [])

    failures: list[str] = []

    # Check deliverable statuses at taskgroup scope
    if state.get("deliverable_statuses") is None:
        failures.append("No deliverable statuses found")
    else:
        all_done, incomplete = _check_deliverable_statuses(state)
        if not all_done:
            failures.append(f"{len(incomplete)} deliverables not completed")

    # Check required validators
    current_stage_name = state.get(STAGE_CURRENT)
    if current_stage_name is not None:
        stage_def = _find_stage(manifest, current_stage_name)
        if stage_def is not None:
            for v_def in stage_def.validators:
                if not v_def.required:
                    continue
                if v_def.schedule in (
                    ValidatorSchedule.PER_DELIVERABLE,
                    ValidatorSchedule.PER_BATCH,
                    ValidatorSchedule.PER_TASKGROUP,
                ):
                    matching = [r for r in validator_results if r.validator_name == v_def.name]
                    if not matching:
                        failures.append(f"Validator '{v_def.name}' not evaluated")
                    elif not matching[-1].passed:
                        failures.append(f"Validator '{v_def.name}' failed")

    return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Completion report generation
# ---------------------------------------------------------------------------

DEFAULT_VERIFICATION_LAYERS: list[CompletionLayerDef] = [
    CompletionLayerDef(name="functional", description="Does it work as specified?"),
    CompletionLayerDef(name="architectural", description="Does implementation match design?"),
    CompletionLayerDef(name="contract", description="Were all deliverables completed?"),
]


def generate_completion_report(
    scope: str,
    manifest: WorkflowManifest,
    results: list[ValidatorResult],
    additional_sections: list[ReportSection] | None = None,
) -> CompletionReport:
    """Generate a completion report from validator results.

    Uses manifest's completion_report.layers if defined,
    otherwise falls back to DEFAULT_VERIFICATION_LAYERS.
    """
    report_config = manifest.completion_report
    layer_defs: list[CompletionLayerDef]
    if "layers" in report_config:
        raw_layers = report_config["layers"]
        if isinstance(raw_layers, list):
            typed_layers = cast("list[dict[str, object]]", raw_layers)
            layer_defs = [CompletionLayerDef.model_validate(entry) for entry in typed_layers]
        else:
            layer_defs = list(DEFAULT_VERIFICATION_LAYERS)
    else:
        layer_defs = list(DEFAULT_VERIFICATION_LAYERS)

    # Build verification layers
    layers: list[VerificationLayer] = []
    for layer_def in layer_defs:
        matching_results: list[ValidatorResult] = []
        for source in layer_def.evidence_sources:
            for r in results:
                if r.validator_name == source:
                    matching_results.append(r)

        all_passed = all(r.passed for r in matching_results) if matching_results else False

        layers.append(
            VerificationLayer(
                name=layer_def.name,
                description=layer_def.description,
                passed=all_passed,
                validator_results=matching_results,
                summary=(
                    f"{sum(1 for r in matching_results if r.passed)}/{len(matching_results)} passed"
                ),
            )
        )

    return CompletionReport(
        scope=scope,
        layers=layers,
        additional_sections=additional_sections or [],
    )
