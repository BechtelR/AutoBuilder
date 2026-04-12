"""Tests for completion gates and completion report generation."""

from __future__ import annotations

import inspect

from app.models.enums import (
    CompletionCondition,
    StageApproval,
    ValidatorSchedule,
    ValidatorType,
)
from app.workflows.manifest import (
    ReportSection,
    StageDef,
    ValidatorDefinition,
    ValidatorResult,
    WorkflowManifest,
)
from app.workflows.validators import (
    DEFAULT_VERIFICATION_LAYERS,
    generate_completion_report,
    verify_stage_completion,
    verify_taskgroup_completion,
)


class TestVerifyStageCompletion:
    def _make_manifest(self) -> WorkflowManifest:
        return WorkflowManifest(
            name="test",
            description="T",
            stages=[
                StageDef(
                    name="build",
                    description="Build",
                    validators=[
                        ValidatorDefinition(
                            name="lint_check",
                            type=ValidatorType.DETERMINISTIC,
                            schedule=ValidatorSchedule.PER_DELIVERABLE,
                        ),
                        ValidatorDefinition(
                            name="advisory",
                            type=ValidatorType.LLM,
                            schedule=ValidatorSchedule.PER_STAGE,
                            required=False,
                        ),
                    ],
                    completion_criteria=CompletionCondition.ALL_VERIFIED,
                    approval=StageApproval.AUTO,
                )
            ],
        )

    def test_all_pass(self) -> None:
        m = self._make_manifest()
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "COMPLETED"},
        }
        results = [ValidatorResult(validator_name="lint_check", passed=True)]
        passed, failures = verify_stage_completion(state, m, results)
        assert passed is True
        assert failures == []

    def test_validator_failing_blocks(self) -> None:
        m = self._make_manifest()
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "COMPLETED"},
        }
        results = [ValidatorResult(validator_name="lint_check", passed=False)]
        passed, failures = verify_stage_completion(state, m, results)
        assert passed is False
        assert any("lint_check" in f for f in failures)

    def test_missing_validator_blocks(self) -> None:
        m = self._make_manifest()
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "COMPLETED"},
        }
        passed, failures = verify_stage_completion(state, m, [])
        assert passed is False
        assert any("not been evaluated" in f for f in failures)

    def test_advisory_failure_does_not_block(self) -> None:
        m = self._make_manifest()
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "COMPLETED"},
        }
        results = [
            ValidatorResult(validator_name="lint_check", passed=True),
            ValidatorResult(validator_name="advisory", passed=False),
        ]
        passed, _failures = verify_stage_completion(state, m, results)
        assert passed is True

    def test_deliverables_incomplete_blocks(self) -> None:
        m = self._make_manifest()
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "IN_PROGRESS"},
        }
        results = [ValidatorResult(validator_name="lint_check", passed=True)]
        passed, failures = verify_stage_completion(state, m, results)
        assert passed is False
        assert any("deliverable" in f.lower() for f in failures)

    def test_approval_required_blocks(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[
                StageDef(
                    name="review",
                    description="Review",
                    approval=StageApproval.CEO,
                )
            ],
        )
        state: dict[str, object] = {"pm:current_stage": "review"}
        passed, failures = verify_stage_completion(state, m, [])
        assert passed is False
        assert any("approved" in f.lower() for f in failures)

    def test_no_stages_passes(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        passed, _failures = verify_stage_completion({}, m, [])
        assert passed is True

    def test_no_current_stage_fails(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="a", description="A")],
        )
        passed, _failures = verify_stage_completion({}, m, [])
        assert passed is False


class TestVerifyTaskgroupCompletion:
    def test_all_done(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="build", description="Build")],
        )
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "COMPLETED"},
        }
        passed, _failures = verify_taskgroup_completion(state, m, [])
        assert passed is True

    def test_incomplete_blocks(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="build", description="Build")],
        )
        state: dict[str, object] = {
            "pm:current_stage": "build",
            "deliverable_statuses": {"d1": "IN_PROGRESS"},
        }
        passed, _failures = verify_taskgroup_completion(state, m, [])
        assert passed is False

    def test_no_stages_passes(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        passed, _failures = verify_taskgroup_completion({}, m, [])
        assert passed is True

    def test_no_override_parameter(self) -> None:
        """verify_taskgroup_completion has no override parameter -- hard gate."""
        sig = inspect.signature(verify_taskgroup_completion)
        params = list(sig.parameters.keys())
        assert "override" not in params
        assert "force" not in params


class TestGenerateCompletionReport:
    def test_default_layers(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        results = [ValidatorResult(validator_name="test_suite", passed=True)]
        report = generate_completion_report("stage:build", m, results)
        assert len(report.layers) == len(DEFAULT_VERIFICATION_LAYERS)

    def test_custom_layers(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            completion_report={
                "layers": [
                    {
                        "name": "custom",
                        "description": "Custom",
                        "evidence_sources": ["lint_check"],
                    },
                ],
            },
        )
        results = [ValidatorResult(validator_name="lint_check", passed=True)]
        report = generate_completion_report("stage:build", m, results)
        assert len(report.layers) == 1
        assert report.layers[0].name == "custom"
        assert report.layers[0].passed is True

    def test_layer_fails_when_validator_fails(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            completion_report={
                "layers": [
                    {"name": "functional", "evidence_sources": ["test_suite"]},
                ],
            },
        )
        results = [ValidatorResult(validator_name="test_suite", passed=False)]
        report = generate_completion_report("stage:build", m, results)
        assert report.layers[0].passed is False

    def test_layer_without_evidence_fails(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            completion_report={
                "layers": [
                    {"name": "empty", "evidence_sources": ["nonexistent"]},
                ],
            },
        )
        report = generate_completion_report("stage:build", m, [])
        assert report.layers[0].passed is False

    def test_scope_and_timestamp(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        report = generate_completion_report("stage:build", m, [])
        assert report.scope == "stage:build"
        assert report.generated_at is not None

    def test_additional_sections(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        sections = [ReportSection(name="quality", content="All good")]
        report = generate_completion_report("stage:build", m, [], additional_sections=sections)
        assert len(report.additional_sections) == 1
        assert report.additional_sections[0].name == "quality"

    def test_multiple_evidence_sources(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            completion_report={
                "layers": [
                    {
                        "name": "functional",
                        "evidence_sources": ["test_suite", "regression_tests"],
                    },
                ],
            },
        )
        results = [
            ValidatorResult(validator_name="test_suite", passed=True),
            ValidatorResult(validator_name="regression_tests", passed=True),
        ]
        report = generate_completion_report("stage:build", m, results)
        assert report.layers[0].passed is True
        assert len(report.layers[0].validator_results) == 2
