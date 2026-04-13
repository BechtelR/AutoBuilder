"""Tests for completion reports, stage verification, and artifact wiring in _execute_stage_loop."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.artifacts import ArtifactStore
from app.db.models import (
    Artifact,
    StageExecution,
    TaskGroupExecution,
    Workflow,
)
from app.db.models import ValidatorResult as ValidatorResultModel
from app.models.enums import (
    PipelineEventType,
    StageStatus,
    WorkflowStatus,
)
from app.workflows.completion import (
    CompletionReportBuilder,
    store_stage_report,
    store_taskgroup_report,
)
from tests.conftest import require_infra

if TYPE_CHECKING:
    import uuid
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _seed_workflow(db: AsyncSession) -> Workflow:
    wf = Workflow(workflow_type="auto-code", status=WorkflowStatus.RUNNING)
    db.add(wf)
    await db.flush()
    return wf


async def _seed_stage(
    db: AsyncSession, workflow_id: uuid.UUID, *, project_id: uuid.UUID | None = None
) -> StageExecution:
    se = StageExecution(
        workflow_id=workflow_id,
        project_id=project_id,
        stage_name="build",
        stage_index=0,
        status=StageStatus.ACTIVE,
    )
    db.add(se)
    await db.flush()
    return se


async def _seed_taskgroup(
    db: AsyncSession,
    stage_execution_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
    number: int = 1,
) -> TaskGroupExecution:
    tge = TaskGroupExecution(
        stage_execution_id=stage_execution_id,
        project_id=project_id,
        taskgroup_number=number,
        status=StageStatus.ACTIVE,
    )
    db.add(tge)
    await db.flush()
    return tge


async def _add_validator(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    stage_execution_id: uuid.UUID,
    *,
    name: str,
    passed: bool,
) -> ValidatorResultModel:
    vr = ValidatorResultModel(
        workflow_id=workflow_id,
        stage_execution_id=stage_execution_id,
        validator_name=name,
        passed=passed,
        evidence={},
    )
    db.add(vr)
    await db.flush()
    return vr


# ---------------------------------------------------------------------------
# Tests: TaskGroup completion generates report and stores in DB
# ---------------------------------------------------------------------------


@require_infra
class TestTaskGroupCompletionReport:
    @pytest.mark.asyncio
    async def test_taskgroup_report_stored_in_db(self, engine: AsyncEngine) -> None:
        """Build + store a TaskGroup report; verify JSONB persisted."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            tge = await _seed_taskgroup(db, se.id)
            await _add_validator(db, wf.id, se.id, name="lint_check", passed=True)
            await _add_validator(db, wf.id, se.id, name="test_suite", passed=True)
            await db.commit()
            wf_id, se_id, tge_id = wf.id, se.id, tge.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_taskgroup_report(tge_id, wf_id, se_id)
        await store_taskgroup_report(factory, tge_id, report)

        async with factory() as db:
            row = (
                await db.execute(select(TaskGroupExecution).where(TaskGroupExecution.id == tge_id))
            ).scalar_one()
            assert row.completion_report is not None
            assert row.completion_report["type"] == "taskgroup"
            layers = row.completion_report["layers"]
            assert isinstance(layers, dict)
            assert layers["functional_correctness"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_taskgroup_report_unverified_without_evidence(self, engine: AsyncEngine) -> None:
        """TaskGroup without validators produces unverified layers."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            tge = await _seed_taskgroup(db, se.id)
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
            assert layers[layer_name]["status"] == "unverified"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Tests: Stage completion generates aggregate report
# ---------------------------------------------------------------------------


@require_infra
class TestStageCompletionReport:
    @pytest.mark.asyncio
    async def test_stage_report_aggregates_taskgroups(self, engine: AsyncEngine) -> None:
        """Stage report reads per-TaskGroup JSONB reports."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            tge1 = await _seed_taskgroup(db, se.id, number=1)
            tge2 = await _seed_taskgroup(db, se.id, number=2)
            tge1.completion_report = {"all_layers_pass": True, "type": "taskgroup"}
            tge2.completion_report = {"all_layers_pass": False, "type": "taskgroup"}
            await db.commit()
            wf_id, se_id = wf.id, se.id

        builder = CompletionReportBuilder(factory)
        report = await builder.build_stage_report(se_id, wf_id)

        assert report["type"] == "stage"
        assert report["all_layers_pass"] is False  # one TG failed
        tg_reports = report["taskgroup_reports"]
        assert isinstance(tg_reports, list)
        assert len(tg_reports) == 2  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_stage_report_stored_in_db(self, engine: AsyncEngine) -> None:
        """store_stage_report persists to StageExecution.completion_report JSONB."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            await db.commit()
            se_id = se.id

        report: dict[str, object] = {
            "type": "stage",
            "all_layers_pass": True,
            "taskgroup_reports": [],
        }
        await store_stage_report(factory, se_id, report)

        async with factory() as db:
            row = (
                await db.execute(select(StageExecution).where(StageExecution.id == se_id))
            ).scalar_one()
            assert row.completion_report is not None
            assert row.completion_report["type"] == "stage"


# ---------------------------------------------------------------------------
# Tests: Completion reports stored as artifacts
# ---------------------------------------------------------------------------


@require_infra
class TestCompletionReportArtifacts:
    @pytest.mark.asyncio
    async def test_taskgroup_report_artifact(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """Completion report saved as artifact with correct content_type."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            tge = await _seed_taskgroup(db, se.id)
            await db.commit()
            tge_id = tge.id

        report: dict[str, object] = {"type": "taskgroup", "all_layers_pass": True}
        content = json.dumps(report, default=str).encode()

        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)
        artifact_id = await store.save(
            entity_type="taskgroup_execution",
            entity_id=tge_id,
            filename="completion_report.json",
            content=content,
            content_type="application/json",
        )

        # Verify stored in DB
        async with factory() as db:
            art = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one()
            assert art.content_type == "application/json"
            assert art.entity_type == "taskgroup_execution"
            assert art.entity_id == tge_id

        # Verify content on disk
        loaded = await store.load(artifact_id)
        assert loaded is not None
        assert json.loads(loaded) == report

    @pytest.mark.asyncio
    async def test_stage_report_artifact(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """Stage completion report saved as artifact, loadable by ID."""
        factory = _make_factory(engine)
        async with factory() as db:
            wf = await _seed_workflow(db)
            se = await _seed_stage(db, wf.id)
            await db.commit()
            se_id = se.id

        report: dict[str, object] = {"type": "stage", "all_layers_pass": False}
        content = json.dumps(report, default=str).encode()

        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)
        artifact_id = await store.save(
            entity_type="stage_execution",
            entity_id=se_id,
            filename="completion_report.json",
            content=content,
            content_type="application/json",
        )

        loaded = await store.load(artifact_id)
        assert loaded is not None
        parsed = json.loads(loaded)
        assert parsed["type"] == "stage"
        assert parsed["all_layers_pass"] is False


# ---------------------------------------------------------------------------
# Tests: Context recreation uses CONTEXT_RECREATED event type
# ---------------------------------------------------------------------------


@dataclass
class _FakeSession:
    id: str = ""
    state: dict[str, object] = field(default_factory=lambda: dict[str, object]())


class _FakeSessionService:
    def __init__(self) -> None:
        self._sessions: dict[str, _FakeSession] = {}

    def _key(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"{app_name}:{user_id}:{session_id}"

    async def get_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> _FakeSession | None:
        return self._sessions.get(self._key(app_name, user_id, session_id))

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state: dict[str, object] | None = None,
    ) -> _FakeSession:
        session = _FakeSession(id=session_id, state=dict(state) if state else {})
        self._sessions[self._key(app_name, user_id, session_id)] = session
        return session


class _MockPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object] | None]] = []

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append((workflow_id, str(event_type), metadata))


class TestContextRecreationEventType:
    @pytest.mark.asyncio
    async def test_recreate_context_uses_context_recreated(self) -> None:
        """recreate_context publishes CONTEXT_RECREATED, not STATE_UPDATED."""
        from app.agents.context_recreation import recreate_context
        from app.models.constants import APP_NAME, SYSTEM_USER_ID

        svc = _FakeSessionService()
        publisher = _MockPublisher()

        await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-sess",
            state={"workflow_id": "wf-1"},
        )

        await recreate_context(
            session_service=svc,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            old_session_id="old-sess",
            publisher=publisher,  # type: ignore[arg-type]
            stages=["a", "b"],
        )

        # Both events should be CONTEXT_RECREATED
        for _wf_id, event_type, _meta in publisher.events:
            assert event_type == PipelineEventType.CONTEXT_RECREATED
            assert event_type != PipelineEventType.STATE_UPDATED

    @pytest.mark.asyncio
    async def test_recreate_context_at_taskgroup_uses_context_recreated(self) -> None:
        """recreate_context_at_taskgroup publishes CONTEXT_RECREATED."""
        from app.agents.context_recreation import recreate_context_at_taskgroup
        from app.models.constants import APP_NAME, SYSTEM_USER_ID

        svc = _FakeSessionService()
        publisher = _MockPublisher()

        old_session = await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-tg-sess",
            state={"workflow_id": "wf-2", "pm:stage": "build"},
        )

        await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            publisher=publisher,  # type: ignore[arg-type]
            workflow_id="wf-2",
            stages=["build", "review"],
        )

        assert len(publisher.events) >= 2
        for _wf_id, event_type, _meta in publisher.events:
            assert event_type == PipelineEventType.CONTEXT_RECREATED
