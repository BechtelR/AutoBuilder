"""Tests for completion gates and completion report generation."""

from __future__ import annotations

import inspect
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    StageExecution,
    TaskGroupExecution,
    Workflow,
)
from app.db.models import (
    ValidatorResult as ValidatorResultModel,
)
from app.models.enums import (
    CompletionCondition,
    StageApproval,
    StageStatus,
    ValidatorSchedule,
    ValidatorType,
    WorkflowStatus,
)
from app.workflows.completion import (
    CompletionReportBuilder,
    store_stage_report,
    store_taskgroup_report,
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

# Import infra markers from root conftest
from tests.conftest import require_infra

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncEngine


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
            stages=[StageDef(name="a", description="A", approval=StageApproval.AUTO)],
        )
        passed, _failures = verify_stage_completion({}, m, [])
        assert passed is False


class TestVerifyTaskgroupCompletion:
    def test_all_done(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="build", description="Build", approval=StageApproval.AUTO)],
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
            stages=[StageDef(name="build", description="Build", approval=StageApproval.AUTO)],
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
        sections = [ReportSection(title="quality", content="All good")]
        report = generate_completion_report("stage:build", m, [], additional_sections=sections)
        assert len(report.additional_sections) == 1
        assert report.additional_sections[0].title == "quality"

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


# ---------------------------------------------------------------------------
# DB-backed tests: CompletionReportBuilder
# ---------------------------------------------------------------------------


def _make_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _make_workflow(db: AsyncSession) -> Workflow:
    wf = Workflow(workflow_type="auto-code", status=WorkflowStatus.RUNNING)
    db.add(wf)
    await db.flush()
    return wf


async def _make_stage(db: AsyncSession, workflow_id: uuid.UUID) -> StageExecution:
    se = StageExecution(
        workflow_id=workflow_id,
        stage_name="build",
        stage_index=0,
        status=StageStatus.ACTIVE,
    )
    db.add(se)
    await db.flush()
    return se


async def _make_taskgroup(
    db: AsyncSession, stage_execution_id: uuid.UUID, *, number: int = 1
) -> TaskGroupExecution:
    tge = TaskGroupExecution(
        stage_execution_id=stage_execution_id,
        taskgroup_number=number,
        status=StageStatus.ACTIVE,
    )
    db.add(tge)
    await db.flush()
    return tge


async def _add_validator_result(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    stage_execution_id: uuid.UUID,
    *,
    name: str,
    passed: bool,
    evidence: dict[str, object] | None = None,
    message: str = "",
) -> ValidatorResultModel:
    vr = ValidatorResultModel(
        workflow_id=workflow_id,
        stage_execution_id=stage_execution_id,
        validator_name=name,
        passed=passed,
        evidence=evidence or {},
        message=message or None,
    )
    db.add(vr)
    await db.flush()
    return vr


@require_infra
class TestCompletionReportBuilder:
    """DB-backed tests for CompletionReportBuilder."""

    @pytest.mark.asyncio
    async def test_taskgroup_report_with_validator_evidence(self, engine: AsyncEngine) -> None:
        """Three layers are populated from ValidatorResult rows in the DB."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge = await _make_taskgroup(db, se.id)
            await _add_validator_result(
                db, wf.id, se.id, name="lint_check", passed=True, evidence={"files": 3}
            )
            await _add_validator_result(
                db, wf.id, se.id, name="test_suite", passed=True, evidence={"tests": 10}
            )
            await _add_validator_result(db, wf.id, se.id, name="code_review", passed=True)
            await _add_validator_result(
                db, wf.id, se.id, name="deliverable_status_check", passed=True
            )
            await db.commit()
            wf_id, se_id, tge_id = wf.id, se.id, tge.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_taskgroup_report(
            tge_id, wf_id, se_id, cost=Decimal("0.05"), duration_seconds=12.3
        )

        assert report["type"] == "taskgroup"
        assert report["all_layers_pass"] is True
        layers = report["layers"]
        assert isinstance(layers, dict)
        assert layers["functional_correctness"]["status"] == "pass"  # type: ignore[index]
        assert layers["architectural_conformance"]["status"] == "pass"  # type: ignore[index]
        assert layers["contract_completion"]["status"] == "pass"  # type: ignore[index]
        assert report["metrics"]["cost"] == "0.05"  # type: ignore[index]
        assert report["metrics"]["duration_seconds"] == 12.3  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_taskgroup_report_no_validators_unverified(self, engine: AsyncEngine) -> None:
        """Layers without evidence are marked 'unverified', all_layers_pass is False."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge = await _make_taskgroup(db, se.id)
            await db.commit()
            wf_id, se_id, tge_id = wf.id, se.id, tge.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_taskgroup_report(tge_id, wf_id, se_id)

        assert report["all_layers_pass"] is False
        layers = report["layers"]
        assert isinstance(layers, dict)
        for layer_name in (
            "functional_correctness",
            "architectural_conformance",
            "contract_completion",
        ):
            layer = layers[layer_name]  # type: ignore[index]
            assert layer["status"] == "unverified"
            assert layer["evidence"] == []

    @pytest.mark.asyncio
    async def test_taskgroup_report_partial_fail(self, engine: AsyncEngine) -> None:
        """If any functional validator fails, all_layers_pass is False."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge = await _make_taskgroup(db, se.id)
            await _add_validator_result(
                db, wf.id, se.id, name="lint_check", passed=False, message="lint failed"
            )
            await _add_validator_result(db, wf.id, se.id, name="code_review", passed=True)
            await _add_validator_result(
                db, wf.id, se.id, name="deliverable_status_check", passed=True
            )
            await db.commit()
            wf_id, se_id, tge_id = wf.id, se.id, tge.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_taskgroup_report(tge_id, wf_id, se_id)

        assert report["all_layers_pass"] is False
        layers = report["layers"]
        assert isinstance(layers, dict)
        assert layers["functional_correctness"]["status"] == "fail"  # type: ignore[index]
        func_evidence = layers["functional_correctness"]["evidence"]  # type: ignore[index]
        assert any(e["validator"] == "lint_check" for e in func_evidence)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_stage_report_aggregates_taskgroup_reports(self, engine: AsyncEngine) -> None:
        """Stage report collects per-TaskGroup completion_report JSONB entries."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge1 = await _make_taskgroup(db, se.id, number=1)
            tge2 = await _make_taskgroup(db, se.id, number=2)
            tge1.completion_report = {"all_layers_pass": True, "type": "taskgroup"}
            tge2.completion_report = {"all_layers_pass": True, "type": "taskgroup"}
            await db.commit()
            se_id, wf_id = se.id, wf.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_stage_report(
            se_id, wf_id, cost=Decimal("0.12"), duration_seconds=60.0
        )

        assert report["type"] == "stage"
        assert report["all_layers_pass"] is True
        tg_reports = report["taskgroup_reports"]
        assert isinstance(tg_reports, list)
        assert len(tg_reports) == 2  # type: ignore[arg-type]
        assert report["metrics"]["taskgroup_count"] == 2  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_stage_report_missing_taskgroup_fails(self, engine: AsyncEngine) -> None:
        """A TaskGroup without a completion_report makes stage all_layers_pass False."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge1 = await _make_taskgroup(db, se.id, number=1)
            tge1.completion_report = {"all_layers_pass": True, "type": "taskgroup"}
            # tge2 intentionally left with no report
            _tge2 = await _make_taskgroup(db, se.id, number=2)
            await db.commit()
            se_id, wf_id = se.id, wf.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_stage_report(se_id, wf_id)

        assert report["all_layers_pass"] is False
        tg_reports = report["taskgroup_reports"]
        assert isinstance(tg_reports, list)
        assert any(r.get("status") == "missing" for r in tg_reports)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_store_and_retrieve_taskgroup_report(self, engine: AsyncEngine) -> None:
        """store_taskgroup_report persists report to JSONB; re-read confirms it."""
        from sqlalchemy import select as sa_select

        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge = await _make_taskgroup(db, se.id)
            await db.commit()
            tge_id = tge.id

        report: dict[str, object] = {
            "type": "taskgroup",
            "all_layers_pass": True,
            "layers": {"functional_correctness": {"status": "pass", "evidence": []}},
        }
        await store_taskgroup_report(factory, tge_id, report)

        async with factory() as db:
            row = (
                await db.execute(
                    sa_select(TaskGroupExecution).where(TaskGroupExecution.id == tge_id)
                )
            ).scalar_one()
            assert row.completion_report is not None
            assert row.completion_report["all_layers_pass"] is True

    @pytest.mark.asyncio
    async def test_store_and_retrieve_stage_report(self, engine: AsyncEngine) -> None:
        """store_stage_report persists report to JSONB; re-read confirms it."""
        from sqlalchemy import select as sa_select

        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            await db.commit()
            se_id = se.id

        report: dict[str, object] = {
            "type": "stage",
            "all_layers_pass": False,
            "taskgroup_reports": [],
        }
        await store_stage_report(factory, se_id, report)

        async with factory() as db:
            row = (
                await db.execute(sa_select(StageExecution).where(StageExecution.id == se_id))
            ).scalar_one()
            assert row.completion_report is not None
            assert row.completion_report["type"] == "stage"
            assert row.completion_report["all_layers_pass"] is False

    @pytest.mark.asyncio
    async def test_report_includes_metrics(self, engine: AsyncEngine) -> None:
        """Reports include cost and duration_seconds in their metrics dict."""
        from sqlalchemy import select as sa_select

        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _make_workflow(db)
            se = await _make_stage(db, wf.id)
            tge = await _make_taskgroup(db, se.id)
            await db.commit()
            wf_id, se_id, tge_id = wf.id, se.id, tge.id

        builder = CompletionReportBuilder(factory)

        tg_report = await builder.build_taskgroup_report(
            tge_id, wf_id, se_id, cost=Decimal("1.23"), duration_seconds=99.9
        )
        assert tg_report["metrics"]["cost"] == "1.23"  # type: ignore[index]
        assert tg_report["metrics"]["duration_seconds"] == 99.9  # type: ignore[index]

        # Persist tg_report so build_stage_report can read it
        async with factory() as db:
            row = (
                await db.execute(
                    sa_select(TaskGroupExecution).where(TaskGroupExecution.id == tge_id)
                )
            ).scalar_one()
            row.completion_report = tg_report
            await db.commit()

        stage_report = await builder.build_stage_report(
            se_id, wf_id, cost=Decimal("2.50"), duration_seconds=120.0
        )
        assert stage_report["metrics"]["cost"] == "2.50"  # type: ignore[index]
        assert stage_report["metrics"]["duration_seconds"] == 120.0  # type: ignore[index]
        assert stage_report["metrics"]["taskgroup_count"] == 1  # type: ignore[index]
