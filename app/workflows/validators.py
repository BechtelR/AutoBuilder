"""Validator framework -- evidence collection, completion gates, and reports."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from app.models.constants import DELIVERABLE_STATUSES_KEY, PM_PENDING_ESCALATIONS_KEY, STAGE_CURRENT
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

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias for validator functions
# ---------------------------------------------------------------------------

_ValidatorFunc = Callable[[dict[str, object]], ValidatorResult]

# ---------------------------------------------------------------------------
# Standard validators -- pure functions reading state keys
# ---------------------------------------------------------------------------


def lint_check(state: dict[str, object]) -> ValidatorResult:
    """Check lint results from state.

    Primary key: ``lint_results`` (structured dict with ``passed`` field).
    Fallback key: ``lint_passed`` (boolean written by LinterAgent alongside lint_results).
    """
    lint_results_raw = state.get("lint_results")
    if isinstance(lint_results_raw, dict) and "passed" in lint_results_raw:
        lint_results = cast("dict[str, object]", lint_results_raw)
        passed = lint_results["passed"] is True
        return ValidatorResult(
            validator_name="lint_check",
            passed=passed,
            evidence={"lint_results": lint_results, "lint_passed": state.get("lint_passed")},
            message="" if passed else "Lint check failed",
        )
    # Fallback: read boolean key written by LinterAgent
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
        evidence={"lint_passed": lint_passed},
        message="" if lint_passed else "Lint check failed",
    )


def test_suite(state: dict[str, object]) -> ValidatorResult:
    """Check test results from state.

    Primary key: ``test_results`` (structured dict with ``passed`` field).
    Fallback key: ``tests_passed`` (boolean written by TestRunnerAgent alongside test_results).
    """
    test_results_raw = state.get("test_results")
    if isinstance(test_results_raw, dict) and "passed" in test_results_raw:
        test_results = cast("dict[str, object]", test_results_raw)
        passed = test_results["passed"] is True
        return ValidatorResult(
            validator_name="test_suite",
            passed=passed,
            evidence={"test_results": test_results, "tests_passed": state.get("tests_passed")},
            message="" if passed else "Test suite failed",
        )
    # Fallback: read boolean key written by TestRunnerAgent
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
        evidence={"tests_passed": tests_passed},
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
    evidence: dict[str, object] = {"review_passed": review_passed}
    # Include review cycle count and reviewer assessment when available
    review_iterations = state.get("review_iterations")
    if review_iterations is not None:
        evidence["review_iterations"] = review_iterations
    review_result = state.get("review_result")
    if review_result is not None:
        evidence["review_result"] = review_result
    return ValidatorResult(
        validator_name="code_review",
        passed=bool(review_passed),
        evidence=evidence,
        message="" if review_passed else "Code review failed",
    )


def integration_tests(state: dict[str, object]) -> ValidatorResult:
    """Check integration test results. Passes if integration_tests_passed is True."""
    passed = state.get("integration_tests_passed")
    if passed is None:
        return ValidatorResult(
            validator_name="integration_tests",
            passed=False,
            message="No integration test results found in state",
        )
    return ValidatorResult(
        validator_name="integration_tests",
        passed=bool(passed),
        evidence={
            "integration_tests_passed": passed,
            "integration_test_results": state.get("integration_test_results", {}),
        },
        message="" if passed else "Integration tests failed",
    )


def dependency_validation(state: dict[str, object]) -> ValidatorResult:
    """Check dependency graph for acyclicity and reference validity.

    Reads ``dependency_graph`` (dict mapping deliverable → list of dependencies)
    and ``dependency_order`` (topological sort result) from state.
    Passes if graph is acyclic and all referenced dependencies exist.
    """
    graph_raw = state.get("dependency_graph")
    order = state.get("dependency_order")

    # If only order exists (legacy), accept if it's a valid list
    if graph_raw is None and order is None:
        return ValidatorResult(
            validator_name="dependency_validation",
            passed=False,
            message="No dependency graph or order found in state",
        )

    # Validate graph structure if present
    if graph_raw is not None:
        if not isinstance(graph_raw, dict):
            return ValidatorResult(
                validator_name="dependency_validation",
                passed=False,
                evidence={"raw": str(graph_raw)},
                message="Dependency graph is not a dict",
            )
        graph: dict[str, object] = cast("dict[str, object]", graph_raw)
        all_nodes = set(graph.keys())

        def _as_str_list(val: object) -> list[str] | None:
            """Return val as list[str] if it is one, else None."""
            if not isinstance(val, list):
                return None
            raw: list[object] = cast("list[object]", val)
            return [item for item in raw if isinstance(item, str)]

        # Check all referenced dependencies exist as nodes
        invalid_refs: list[str] = []
        for node, deps_raw in graph.items():
            deps = _as_str_list(deps_raw)
            if deps is None:
                continue
            for dep in deps:
                if dep not in all_nodes:
                    invalid_refs.append(f"{node} -> {dep}")

        # Cycle detection via topological sort (Kahn's algorithm)
        in_degree: dict[str, int] = {n: 0 for n in all_nodes}
        for deps_raw in graph.values():
            deps = _as_str_list(deps_raw)
            if deps is None:
                continue
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = deque(n for n, d in in_degree.items() if d == 0)
        sorted_nodes: list[str] = []
        while queue:
            node = queue.popleft()
            sorted_nodes.append(node)
            node_deps = _as_str_list(graph.get(node))
            if node_deps is None:
                continue
            for dep in node_deps:
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        has_cycle = len(sorted_nodes) != len(all_nodes)
        failures: list[str] = []
        if has_cycle:
            cycle_nodes = [n for n in all_nodes if n not in sorted_nodes]
            failures.append(f"Cycle detected involving: {', '.join(cycle_nodes)}")
        if invalid_refs:
            failures.append(f"Invalid references: {', '.join(invalid_refs)}")

        graph_summary: dict[str, list[str]] = {
            k: cast("list[str]", v) for k, v in graph.items() if isinstance(v, list)
        }
        return ValidatorResult(
            validator_name="dependency_validation",
            passed=len(failures) == 0,
            evidence={
                "node_count": len(all_nodes),
                "has_cycle": has_cycle,
                "invalid_references": invalid_refs,
                "topological_order": sorted_nodes,
                "dependency_graph_summary": graph_summary,
            },
            message="; ".join(failures) if failures else "",
        )

    # Fallback: only dependency_order available (no graph to validate)
    if not isinstance(order, list):
        return ValidatorResult(
            validator_name="dependency_validation",
            passed=False,
            evidence={"raw": str(order)},
            message="Dependency order is not a list",
        )
    order_raw: list[object] = cast("list[object]", order)
    order_list: list[str] = [item for item in order_raw if isinstance(item, str)]
    return ValidatorResult(
        validator_name="dependency_validation",
        passed=True,
        evidence={"dependency_order": order_list, "node_count": len(order_list)},
    )


def deliverable_status_check(state: dict[str, object]) -> ValidatorResult:
    """Check that all deliverables are at required status."""
    statuses = state.get(DELIVERABLE_STATUSES_KEY)
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
    # Per-deliverable status map as required by spec
    per_deliverable: dict[str, str] = {
        k: str(v) if not isinstance(v, str) else v for k, v in sd.items()
    }
    return ValidatorResult(
        validator_name="deliverable_status_check",
        passed=all_done,
        evidence={
            "total": len(sd),
            "incomplete": incomplete,
            "per_deliverable_status": per_deliverable,
        },
        message="" if all_done else f"{len(incomplete)} deliverables not completed",
    )


# ---------------------------------------------------------------------------
# Validator dispatch registry
# ---------------------------------------------------------------------------

_STANDARD_VALIDATORS: dict[str, _ValidatorFunc] = {
    "lint_check": lint_check,
    "test_suite": test_suite,
    "regression_tests": regression_tests,
    "integration_tests": integration_tests,
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
        validator: ValidatorDefinition,
        state: dict[str, object],
        session: AsyncSession | None = None,
    ) -> ValidatorResult:
        """Evaluate a single validator against the given state.

        Args:
            validator: Validator definition from the manifest.
            state: Pipeline session state snapshot.
            session: Optional DB session for validators needing data access.
        """
        if validator.type == ValidatorType.DETERMINISTIC:
            func = _STANDARD_VALIDATORS.get(validator.name)
            if func is not None:
                return func(state)
            return ValidatorResult(
                validator_name=validator.name,
                passed=False,
                message=f"Unknown validator: {validator.name}",
            )

        if validator.type == ValidatorType.APPROVAL:
            approved = state.get(f"approval:{validator.name}")
            return ValidatorResult(
                validator_name=validator.name,
                passed=bool(approved),
                evidence={"approved": approved},
                message="" if approved else "Approval not yet granted",
            )

        if validator.type == ValidatorType.LLM:
            result_key = f"llm_validator:{validator.name}"
            result = state.get(result_key)
            if result is None:
                return ValidatorResult(
                    validator_name=validator.name,
                    passed=False,
                    message=(f"LLM validator '{validator.name}' has not produced results"),
                )
            return ValidatorResult(
                validator_name=validator.name,
                passed=bool(result),
                evidence={"llm_result": result},
            )

        return ValidatorResult(
            validator_name=validator.name,
            passed=False,
            message=f"Unknown validator type: {validator.type}",
        )

    def evaluate_batch(
        self,
        validators: list[ValidatorDefinition],
        schedule: ValidatorSchedule,
        state: dict[str, object],
        session: AsyncSession | None = None,
    ) -> list[ValidatorResult]:
        """Evaluate all validators matching the given schedule."""
        results: list[ValidatorResult] = []
        for v in validators:
            if v.schedule == schedule:
                results.append(self.evaluate(v, state, session=session))
        return results


# ---------------------------------------------------------------------------
# Completion gates (F27/F28)
# ---------------------------------------------------------------------------


def _check_deliverable_statuses(state: dict[str, object]) -> tuple[bool, list[str]]:
    """Check deliverable_statuses state key. Returns (all_done, incomplete_names).

    A deliverable is "done" (not outstanding) if it has reached any terminal
    status: COMPLETED, FAILED, or SKIPPED. Non-terminal statuses (PLANNED,
    PENDING, IN_PROGRESS, BLOCKED) are outstanding per FR-8a.70.
    """
    statuses = state.get(DELIVERABLE_STATUSES_KEY)
    if statuses is None:
        return (False, [])
    if not isinstance(statuses, dict):
        return (False, [])
    sd = cast("dict[str, object]", statuses)
    terminal = {DeliverableStatus.COMPLETED, DeliverableStatus.FAILED, DeliverableStatus.SKIPPED}
    incomplete = [k for k, v in sd.items() if v not in terminal]
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
        if state.get(DELIVERABLE_STATUSES_KEY) is None:
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
    if state.get(DELIVERABLE_STATUSES_KEY) is None:
        failures.append("No deliverable statuses found")
    else:
        all_done, incomplete = _check_deliverable_statuses(state)
        if not all_done:
            failures.append(f"{len(incomplete)} deliverables not completed")

    # Check pending escalations (hard gate -- spec requires zero unresolved)
    pending_escalations = state.get(PM_PENDING_ESCALATIONS_KEY, 0)
    if isinstance(pending_escalations, int) and pending_escalations > 0:
        failures.append(f"{pending_escalations} pending escalation(s) unresolved")
    elif isinstance(pending_escalations, list):
        esc_list = cast("list[object]", pending_escalations)
        if len(esc_list) > 0:
            failures.append(f"{len(esc_list)} pending escalation(s) unresolved")

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
    CompletionLayerDef(
        name="functional",
        description="Does it work as specified?",
        evidence_sources=["lint_check", "test_suite", "regression_tests", "integration_tests"],
    ),
    CompletionLayerDef(
        name="architectural",
        description="Does implementation match design?",
        evidence_sources=["code_review", "architecture_conformance"],
    ),
    CompletionLayerDef(
        name="contract",
        description="Were all deliverables completed?",
        evidence_sources=["deliverable_status_check", "dependency_validation"],
    ),
]


def generate_completion_report(
    scope: str,
    manifest: WorkflowManifest,
    validator_results: list[ValidatorResult],
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
            for r in validator_results:
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
