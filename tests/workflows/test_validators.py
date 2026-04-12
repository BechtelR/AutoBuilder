"""Tests for validator framework -- standard validators and ValidatorRunner."""

from __future__ import annotations

from app.models.enums import ValidatorSchedule, ValidatorType
from app.workflows.manifest import ValidatorDefinition
from app.workflows.validators import (
    ValidatorRunner,
    code_review,
    deliverable_status_check,
    dependency_validation,
    lint_check,
    regression_tests,
)
from app.workflows.validators import (
    test_suite as check_test_suite,
)


class TestLintCheck:
    def test_passes_with_true(self) -> None:
        r = lint_check({"lint_passed": True, "lint_results": {}})
        assert r.passed is True

    def test_fails_with_false(self) -> None:
        r = lint_check({"lint_passed": False})
        assert r.passed is False

    def test_missing_key_fails(self) -> None:
        r = lint_check({})
        assert r.passed is False
        assert "found" in r.message.lower()

    def test_evidence_includes_results(self) -> None:
        r = lint_check({"lint_passed": True, "lint_results": {"errors": 0}})
        assert r.evidence["lint_passed"] is True


class TestTestSuite:
    def test_passes(self) -> None:
        r = check_test_suite({"tests_passed": True, "test_results": {"total": 10}})
        assert r.passed is True

    def test_fails(self) -> None:
        r = check_test_suite({"tests_passed": False})
        assert r.passed is False

    def test_missing_fails(self) -> None:
        r = check_test_suite({})
        assert r.passed is False


class TestRegressionTests:
    def test_passes(self) -> None:
        r = regression_tests({"regression_results": {"passed": True, "skipped": False}})
        assert r.passed is True

    def test_fails(self) -> None:
        r = regression_tests({"regression_results": {"passed": False, "skipped": False}})
        assert r.passed is False

    def test_skipped_passes(self) -> None:
        r = regression_tests({"regression_results": {"skipped": True}})
        assert r.passed is True
        assert r.evidence.get("skipped") is True

    def test_missing_fails(self) -> None:
        r = regression_tests({})
        assert r.passed is False


class TestCodeReview:
    def test_passes(self) -> None:
        r = code_review({"review_passed": True})
        assert r.passed is True

    def test_fails(self) -> None:
        r = code_review({"review_passed": False})
        assert r.passed is False

    def test_missing_fails(self) -> None:
        r = code_review({})
        assert r.passed is False


class TestDependencyValidation:
    def test_valid_order(self) -> None:
        r = dependency_validation({"dependency_order": ["a", "b", "c"]})
        assert r.passed is True

    def test_missing_fails(self) -> None:
        r = dependency_validation({})
        assert r.passed is False

    def test_non_list_fails(self) -> None:
        r = dependency_validation({"dependency_order": "not a list"})
        assert r.passed is False


class TestDeliverableStatusCheck:
    def test_all_completed(self) -> None:
        r = deliverable_status_check(
            {"deliverable_statuses": {"d1": "COMPLETED", "d2": "COMPLETED"}}
        )
        assert r.passed is True

    def test_incomplete(self) -> None:
        r = deliverable_status_check(
            {"deliverable_statuses": {"d1": "COMPLETED", "d2": "IN_PROGRESS"}}
        )
        assert r.passed is False
        assert r.evidence["incomplete"] == ["d2"]

    def test_missing_fails(self) -> None:
        r = deliverable_status_check({})
        assert r.passed is False


class TestValidatorRunner:
    def test_deterministic_dispatch(self) -> None:
        runner = ValidatorRunner()
        v_def = ValidatorDefinition(
            name="lint_check",
            type=ValidatorType.DETERMINISTIC,
            schedule=ValidatorSchedule.PER_DELIVERABLE,
        )
        result = runner.evaluate(v_def, {"lint_passed": True})
        assert result.passed is True

    def test_unknown_deterministic(self) -> None:
        runner = ValidatorRunner()
        v_def = ValidatorDefinition(
            name="unknown_validator",
            type=ValidatorType.DETERMINISTIC,
            schedule=ValidatorSchedule.PER_STAGE,
        )
        result = runner.evaluate(v_def, {})
        assert result.passed is False
        assert "unknown" in result.message.lower()

    def test_approval_dispatch(self) -> None:
        runner = ValidatorRunner()
        v_def = ValidatorDefinition(
            name="final_approval",
            type=ValidatorType.APPROVAL,
            schedule=ValidatorSchedule.PER_STAGE,
        )
        # Not approved
        result = runner.evaluate(v_def, {})
        assert result.passed is False
        # Approved
        result = runner.evaluate(v_def, {"approval:final_approval": True})
        assert result.passed is True

    def test_llm_dispatch(self) -> None:
        runner = ValidatorRunner()
        v_def = ValidatorDefinition(
            name="spec_review",
            type=ValidatorType.LLM,
            schedule=ValidatorSchedule.PER_STAGE,
        )
        result = runner.evaluate(v_def, {"llm_validator:spec_review": True})
        assert result.passed is True

    def test_batch_filters_by_schedule(self) -> None:
        runner = ValidatorRunner()
        validators = [
            ValidatorDefinition(
                name="lint_check",
                type=ValidatorType.DETERMINISTIC,
                schedule=ValidatorSchedule.PER_DELIVERABLE,
            ),
            ValidatorDefinition(
                name="test_suite",
                type=ValidatorType.DETERMINISTIC,
                schedule=ValidatorSchedule.PER_DELIVERABLE,
            ),
            ValidatorDefinition(
                name="final_approval",
                type=ValidatorType.APPROVAL,
                schedule=ValidatorSchedule.PER_STAGE,
            ),
        ]
        state: dict[str, object] = {"lint_passed": True, "tests_passed": True}
        results = runner.evaluate_batch(validators, ValidatorSchedule.PER_DELIVERABLE, state)
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_batch_per_stage_only(self) -> None:
        runner = ValidatorRunner()
        validators = [
            ValidatorDefinition(
                name="lint_check",
                type=ValidatorType.DETERMINISTIC,
                schedule=ValidatorSchedule.PER_DELIVERABLE,
            ),
            ValidatorDefinition(
                name="final",
                type=ValidatorType.APPROVAL,
                schedule=ValidatorSchedule.PER_STAGE,
            ),
        ]
        results = runner.evaluate_batch(validators, ValidatorSchedule.PER_STAGE, {})
        assert len(results) == 1
