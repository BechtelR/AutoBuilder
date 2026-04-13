"""Tests for context recreation pipeline."""

from __future__ import annotations

import importlib.util
import sys
import types  # noqa: TC003
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.context_recreation import (
    RecreationResult,
    create_fresh_session,
    load_taskgroup_checkpoint,
    persist_to_memory,
    recreate_context,
    recreate_context_at_taskgroup,
)
from app.db.models import StageExecution, TaskGroupExecution, Workflow
from app.lib.exceptions import WorkerError
from app.models.constants import (
    APP_NAME,
    SYSTEM_USER_ID,
)
from app.models.enums import StageStatus, WorkflowStatus
from tests.conftest import require_infra

# Load auto-code pipeline constants (directory name has a hyphen, can't use normal import)
_AUTO_CODE_PIPELINE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "app"
    / "workflows"
    / "auto-code"
    / "pipeline.py"
)


def _load_auto_code_pipeline() -> types.ModuleType:
    module_name = "_test_ctx_auto_code_pipeline"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _AUTO_CODE_PIPELINE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_auto_code_mod = _load_auto_code_pipeline()
PIPELINE_STAGES: list[str] = _auto_code_mod.PIPELINE_STAGE_NAMES  # type: ignore[attr-defined]
STAGE_COMPLETION_KEYS: dict[str, str] = _auto_code_mod.STAGE_COMPLETION_KEYS  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeSession:
    """Minimal session-like object with mutable state dict and id."""

    id: str = ""
    state: dict[str, object] = field(default_factory=lambda: dict[str, object]())


class FakeSessionService:
    """Dict-backed session service for testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, FakeSession] = {}

    def _key(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"{app_name}:{user_id}:{session_id}"

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> FakeSession | None:
        return self._sessions.get(self._key(app_name, user_id, session_id))

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state: dict[str, object] | None = None,
    ) -> FakeSession:
        session = FakeSession(id=session_id, state=dict(state) if state else {})
        self._sessions[self._key(app_name, user_id, session_id)] = session
        return session


class MockEventPublisher:
    """Records publish_lifecycle calls for assertion."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object] | None]] = []

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.events.append((workflow_id, str(event_type), metadata))


# ---------------------------------------------------------------------------
# TestPersistToMemory
# ---------------------------------------------------------------------------


class TestPersistToMemory:
    @pytest.mark.asyncio
    async def test_degraded_no_service(self) -> None:
        result = await persist_to_memory({}, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_degraded_with_service(self) -> None:
        # Phase 5b: even with a memory service, returns False
        result = await persist_to_memory({"key": "val"}, object())
        assert result is False


# ---------------------------------------------------------------------------
# TestCreateFreshSession
# ---------------------------------------------------------------------------


class TestCreateFreshSession:
    @pytest.mark.asyncio
    async def test_creates_session_with_seed(self) -> None:
        svc = FakeSessionService()
        seed = {"workflow_id": "wf-1", "pm:batch_position": 3}

        new_id = await create_fresh_session(
            svc,
            APP_NAME,
            SYSTEM_USER_ID,
            seed,  # type: ignore[arg-type]
        )

        assert isinstance(new_id, str)
        assert len(new_id) > 0

        # Verify session exists with seeded state
        session = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=new_id
        )
        assert session is not None
        assert session.state["workflow_id"] == "wf-1"
        assert session.state["pm:batch_position"] == 3

    @pytest.mark.asyncio
    async def test_creates_unique_ids(self) -> None:
        svc = FakeSessionService()
        id1 = await create_fresh_session(svc, APP_NAME, SYSTEM_USER_ID, {})  # type: ignore[arg-type]
        id2 = await create_fresh_session(svc, APP_NAME, SYSTEM_USER_ID, {})  # type: ignore[arg-type]
        assert id1 != id2


# ---------------------------------------------------------------------------
# TestRecreateContext
# ---------------------------------------------------------------------------


class TestRecreateContext:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        svc = FakeSessionService()
        publisher = MockEventPublisher()

        # Create old session with some state (keys match auto-code STAGE_COMPLETION_KEYS)
        await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-session",
            state={
                "workflow_id": "wf-1",
                "project_config": {"retry_budget": 5},
                "implementation_plan": "plan data",
                "code_output": "code data",
                "loaded_skill_names": ["s1"],
                "memory_context": "ctx",
                "unrelated_temp": "ignored",
            },
        )

        result = await recreate_context(
            session_service=svc,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            old_session_id="old-session",
            publisher=publisher,  # type: ignore[arg-type]
            memory_service=None,
            stages=PIPELINE_STAGES,
            stage_completion_keys=STAGE_COMPLETION_KEYS,
        )

        assert isinstance(result, RecreationResult)
        assert result.new_session_id != "old-session"
        assert result.memory_available is False
        assert "workflow_id" in result.seeded_keys
        assert "project_config" in result.seeded_keys
        # code_output matches _output suffix -> seeded
        assert "code_output" in result.seeded_keys
        # implementation_plan does not match _output suffix -> NOT seeded (Phase 8a gap)
        assert "implementation_plan" not in result.seeded_keys

        # State-based detection: skill_loader, memory_loader, planner, coder done
        assert "skill_loader" not in result.remaining_stages
        assert "memory_loader" not in result.remaining_stages
        assert "planner" not in result.remaining_stages
        assert "coder" not in result.remaining_stages
        assert "formatter" in result.remaining_stages

        # Old session preserved
        old = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id="old-session"
        )
        assert old is not None

        # New session has seeded state
        new = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=result.new_session_id
        )
        assert new is not None
        assert new.state["workflow_id"] == "wf-1"

        # Audit events published (started + completed)
        assert len(publisher.events) == 2
        assert publisher.events[0][2] is not None
        assert publisher.events[0][2]["recreation"] == "started"
        assert publisher.events[1][2] is not None
        assert publisher.events[1][2]["recreation"] == "completed"

    @pytest.mark.asyncio
    async def test_old_session_not_found(self) -> None:
        svc = FakeSessionService()
        publisher = MockEventPublisher()

        with pytest.raises(WorkerError, match="not found for recreation"):
            await recreate_context(
                session_service=svc,  # type: ignore[arg-type]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                old_session_id="nonexistent",
                publisher=publisher,  # type: ignore[arg-type]
                stages=PIPELINE_STAGES,
            )

        # Error event published
        error_events = [
            e for e in publisher.events if e[2] is not None and e[2].get("recreation") == "failed"
        ]
        assert len(error_events) == 1

    @pytest.mark.asyncio
    async def test_explicit_completed_stages(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-session",
            state={"workflow_id": "wf-1"},
        )

        result = await recreate_context(
            session_service=svc,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            old_session_id="old-session",
            completed_stages=["skill_loader", "memory_loader", "planner", "coder"],
            stages=PIPELINE_STAGES,
        )

        assert "skill_loader" not in result.remaining_stages
        assert "planner" not in result.remaining_stages
        assert "formatter" in result.remaining_stages

    @pytest.mark.asyncio
    async def test_no_publisher(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-session",
            state={"workflow_id": "wf-1"},
        )

        # Should succeed without publisher
        result = await recreate_context(
            session_service=svc,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            old_session_id="old-session",
            publisher=None,
            stages=PIPELINE_STAGES,
        )
        assert isinstance(result, RecreationResult)

    @pytest.mark.asyncio
    async def test_degraded_memory(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id="old-session",
            state={"workflow_id": "wf-1"},
        )

        result = await recreate_context(
            session_service=svc,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            old_session_id="old-session",
            memory_service=None,
            stages=PIPELINE_STAGES,
        )
        assert result.memory_available is False


# ---------------------------------------------------------------------------
# TestRecreationResult
# ---------------------------------------------------------------------------


class TestRecreationResult:
    def test_frozen(self) -> None:
        result = RecreationResult(new_session_id="abc")
        with pytest.raises(AttributeError):
            result.new_session_id = "xyz"  # type: ignore[misc]

    def test_defaults(self) -> None:
        result = RecreationResult(new_session_id="abc")
        assert result.remaining_stages == []
        assert result.seeded_keys == []
        assert result.memory_available is False


# ---------------------------------------------------------------------------
# Helpers for infra tests (TaskGroup checkpoint tests)
# ---------------------------------------------------------------------------


def _make_session_factory(engine: object) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]


async def _create_workflow(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    """Insert a minimal Workflow and return its ID."""
    async with factory() as db:
        wf = Workflow(workflow_type="test", status=WorkflowStatus.RUNNING)
        db.add(wf)
        await db.commit()
        await db.refresh(wf)
        return wf.id


async def _create_stage_execution(
    factory: async_sessionmaker[AsyncSession],
    workflow_id: uuid.UUID,
) -> uuid.UUID:
    """Insert a minimal StageExecution and return its ID."""
    async with factory() as db:
        se = StageExecution(
            workflow_id=workflow_id,
            stage_name="build",
            stage_index=0,
            status=StageStatus.ACTIVE,
        )
        db.add(se)
        await db.commit()
        await db.refresh(se)
        return se.id


async def _create_taskgroup_execution(
    factory: async_sessionmaker[AsyncSession],
    stage_execution_id: uuid.UUID,
    *,
    checkpoint_data: dict[str, object] | None = None,
) -> uuid.UUID:
    """Insert a TaskGroupExecution and return its ID."""
    async with factory() as db:
        tge = TaskGroupExecution(
            stage_execution_id=stage_execution_id,
            taskgroup_number=1,
            status=StageStatus.ACTIVE,
            checkpoint_data=checkpoint_data,
        )
        db.add(tge)
        await db.commit()
        await db.refresh(tge)
        return tge.id


# ---------------------------------------------------------------------------
# TestLoadTaskgroupCheckpoint
# ---------------------------------------------------------------------------


@require_infra
class TestLoadTaskgroupCheckpoint:
    @pytest.mark.asyncio
    async def test_load_existing_checkpoint(self, engine: object) -> None:
        """TaskGroupExecution with checkpoint_data returns the dict."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        se_id = await _create_stage_execution(factory, wf_id)
        checkpoint: dict[str, object] = {
            "deliverable_statuses": {"d1": "COMPLETED"},
            "stage_progress": {"build": "COMPLETED"},
            "accumulated_cost": 1.23,
            "loaded_skill_names": ["skill_a"],
            "workflow_id": "wf-test",
            "completed_stages": ["skill_loader", "planner"],
        }
        tge_id = await _create_taskgroup_execution(factory, se_id, checkpoint_data=checkpoint)

        result = await load_taskgroup_checkpoint(factory, tge_id)  # type: ignore[arg-type]

        assert result is not None
        assert result["deliverable_statuses"] == {"d1": "COMPLETED"}
        assert result["accumulated_cost"] == 1.23
        assert result["loaded_skill_names"] == ["skill_a"]
        assert result["completed_stages"] == ["skill_loader", "planner"]

    @pytest.mark.asyncio
    async def test_load_checkpoint_none_when_no_data(self, engine: object) -> None:
        """TaskGroupExecution without checkpoint_data returns None."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        se_id = await _create_stage_execution(factory, wf_id)
        tge_id = await _create_taskgroup_execution(factory, se_id, checkpoint_data=None)

        result = await load_taskgroup_checkpoint(factory, tge_id)  # type: ignore[arg-type]
        assert result is None

    @pytest.mark.asyncio
    async def test_load_checkpoint_nonexistent_id(self, engine: object) -> None:
        """Nonexistent TaskGroupExecution ID returns None."""
        factory = _make_session_factory(engine)
        result = await load_taskgroup_checkpoint(factory, uuid.uuid4())  # type: ignore[arg-type]
        assert result is None


# ---------------------------------------------------------------------------
# TestRecreateContextAtTaskgroup
# ---------------------------------------------------------------------------


class TestRecreateContextAtTaskgroup:
    @pytest.mark.asyncio
    async def test_merges_checkpoint_into_state(self) -> None:
        """Checkpoint data merges into old session state, checkpoint wins on conflict."""
        svc = FakeSessionService()
        old_session = FakeSession(
            id="old-session",
            state={
                "workflow_id": "wf-original",
                "pm:batch_position": 2,
                "project_config": {"retry_budget": 5},
                "loaded_skill_names": ["old_skill"],
            },
        )

        # Simulate checkpoint that overrides loaded_skill_names
        checkpoint: dict[str, object] = {
            "loaded_skill_names": ["new_skill_a", "new_skill_b"],
            "completed_stages": ["skill_loader", "planner"],
            "accumulated_cost": 4.56,
            "workflow_id": "wf-original",
        }

        # We can't use real DB here, so test without db_session_factory.
        # The checkpoint must be injected via the old session state merge path.
        # To test the full DB path, see TestLoadTaskgroupCheckpointIntegration below.
        merged_session = FakeSession(
            id="old-session",
            state={**old_session.state, **checkpoint},
        )

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=merged_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            stages=PIPELINE_STAGES,
            stage_completion_keys=STAGE_COMPLETION_KEYS,
        )

        assert isinstance(result, RecreationResult)
        assert result.new_session_id != "old-session"

        # Verify seeded state includes checkpoint keys
        assert "loaded_skill_names" in result.seeded_keys
        assert "completed_stages" in result.seeded_keys
        assert "workflow_id" in result.seeded_keys

        # Verify the new session has merged values
        new_session = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=result.new_session_id
        )
        assert new_session is not None
        assert new_session.state["loaded_skill_names"] == ["new_skill_a", "new_skill_b"]
        assert new_session.state["completed_stages"] == ["skill_loader", "planner"]

    @pytest.mark.asyncio
    async def test_publishes_events(self) -> None:
        """Context recreation at TaskGroup boundary publishes started+completed events."""
        svc = FakeSessionService()
        publisher = MockEventPublisher()

        old_session = FakeSession(
            id="old-sess",
            state={"workflow_id": "wf-1"},
        )

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            publisher=publisher,  # type: ignore[arg-type]
            workflow_id="wf-1",
            stages=PIPELINE_STAGES,
        )

        assert isinstance(result, RecreationResult)
        # Should have started + completed events
        assert len(publisher.events) == 2
        started_meta = publisher.events[0][2]
        assert started_meta is not None
        assert started_meta["recreation"] == "started"
        assert started_meta["recreation_type"] == "taskgroup_boundary"
        assert started_meta["old_session_id"] == "old-sess"

        completed_meta = publisher.events[1][2]
        assert completed_meta is not None
        assert completed_meta["recreation"] == "completed"
        assert completed_meta["recreation_type"] == "taskgroup_boundary"
        assert completed_meta["new_session_id"] == result.new_session_id
        assert isinstance(completed_meta["seeded_keys"], list)
        assert isinstance(completed_meta["remaining_stages"], list)

    @pytest.mark.asyncio
    async def test_seeded_state_includes_checkpoint_keys(self) -> None:
        """completed_stages and loaded_skill_names from checkpoint always appear in seed."""
        svc = FakeSessionService()

        old_session = FakeSession(
            id="old-sess",
            state={
                "workflow_id": "wf-1",
                # These keys don't match _CRITICAL_KEY_PREFIXES but should be seeded
                # from checkpoint path
                "completed_stages": ["skill_loader", "memory_loader"],
                "loaded_skill_names": ["my_skill"],
                "accumulated_cost": 2.5,
                "deliverable_statuses": {"d1": "COMPLETED"},
            },
        )

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            stages=PIPELINE_STAGES,
        )

        # loaded_skill_names matches _CRITICAL_KEY_PREFIXES directly
        assert "loaded_skill_names" in result.seeded_keys
        # completed_stages and deliverable_statuses should be seeded via checkpoint path
        assert "completed_stages" in result.seeded_keys
        assert "deliverable_statuses" in result.seeded_keys
        assert "accumulated_cost" in result.seeded_keys
        assert "workflow_id" in result.seeded_keys

    @pytest.mark.asyncio
    async def test_no_publisher_no_workflow(self) -> None:
        """Works correctly without publisher and workflow_id."""
        svc = FakeSessionService()
        old_session = FakeSession(id="old-sess", state={"workflow_id": "wf-1"})

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            stages=PIPELINE_STAGES,
        )

        assert isinstance(result, RecreationResult)
        assert result.new_session_id != "old-sess"

    @pytest.mark.asyncio
    async def test_empty_old_state(self) -> None:
        """Handles empty old session state without errors."""
        svc = FakeSessionService()
        old_session = FakeSession(id="old-sess", state={})

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
        )

        assert isinstance(result, RecreationResult)
        assert result.seeded_keys == []
        assert result.remaining_stages == []


# ---------------------------------------------------------------------------
# TestRecreateContextAtTaskgroupWithDB
# ---------------------------------------------------------------------------


@require_infra
class TestRecreateContextAtTaskgroupWithDB:
    """Integration tests that use real PostgreSQL for checkpoint loading."""

    @pytest.mark.asyncio
    async def test_full_checkpoint_merge_from_db(self, engine: object) -> None:
        """End-to-end: checkpoint from DB merges into recreation seed."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        se_id = await _create_stage_execution(factory, wf_id)

        checkpoint: dict[str, object] = {
            "deliverable_statuses": {"d1": "COMPLETED", "d2": "FAILED"},
            "stage_progress": {"build": "COMPLETED"},
            "accumulated_cost": 7.89,
            "loaded_skill_names": ["skill_x"],
            "workflow_id": "wf-test",
            "completed_stages": ["skill_loader", "planner", "coder"],
        }
        tge_id = await _create_taskgroup_execution(factory, se_id, checkpoint_data=checkpoint)

        svc = FakeSessionService()
        publisher = MockEventPublisher()

        old_session = FakeSession(
            id="old-work-session",
            state={
                "workflow_id": "wf-test",
                "project_config": {"retry_budget": 10},
                "pm:batch_position": 3,
            },
        )

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            db_session_factory=factory,  # type: ignore[arg-type]
            current_taskgroup_id=tge_id,
            publisher=publisher,  # type: ignore[arg-type]
            workflow_id="wf-test",
            stages=PIPELINE_STAGES,
            stage_completion_keys=STAGE_COMPLETION_KEYS,
        )

        assert isinstance(result, RecreationResult)

        # Verify checkpoint data merged into seed
        new_session = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=result.new_session_id
        )
        assert new_session is not None
        assert new_session.state["loaded_skill_names"] == ["skill_x"]
        assert new_session.state["completed_stages"] == ["skill_loader", "planner", "coder"]
        assert new_session.state["accumulated_cost"] == 7.89
        assert new_session.state["deliverable_statuses"] == {"d1": "COMPLETED", "d2": "FAILED"}
        assert new_session.state["workflow_id"] == "wf-test"

        # Events published
        assert len(publisher.events) == 2
        assert publisher.events[0][2] is not None
        assert publisher.events[0][2]["recreation"] == "started"
        assert publisher.events[1][2] is not None
        assert publisher.events[1][2]["recreation"] == "completed"

    @pytest.mark.asyncio
    async def test_no_checkpoint_data_falls_through(self, engine: object) -> None:
        """When TaskGroup has no checkpoint, recreation uses only old session state."""
        factory = _make_session_factory(engine)
        wf_id = await _create_workflow(factory)
        se_id = await _create_stage_execution(factory, wf_id)
        tge_id = await _create_taskgroup_execution(factory, se_id, checkpoint_data=None)

        svc = FakeSessionService()
        old_session = FakeSession(
            id="old-sess",
            state={
                "workflow_id": "wf-1",
                "pm:batch_position": 5,
            },
        )

        result = await recreate_context_at_taskgroup(
            session_service=svc,  # type: ignore[arg-type]
            old_session=old_session,  # type: ignore[arg-type]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            db_session_factory=factory,  # type: ignore[arg-type]
            current_taskgroup_id=tge_id,
            stages=PIPELINE_STAGES,
        )

        new_session = await svc.get_session(
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=result.new_session_id
        )
        assert new_session is not None
        assert new_session.state["workflow_id"] == "wf-1"
        assert new_session.state["pm:batch_position"] == 5
