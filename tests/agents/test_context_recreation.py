"""Tests for context recreation pipeline."""

from __future__ import annotations

import importlib.util
import sys
import types  # noqa: TC003
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.agents.context_recreation import (
    RecreationResult,
    create_fresh_session,
    determine_remaining_stages,
    identify_critical_keys,
    persist_to_memory,
    recreate_context,
    seed_critical_keys,
)
from app.lib.exceptions import WorkerError
from app.models.constants import (
    APP_NAME,
    DELIVERABLE_STATUS_PREFIX,
    PM_BATCH_POSITION_KEY,
    SYSTEM_USER_ID,
)

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
# TestIdentifyCriticalKeys
# ---------------------------------------------------------------------------


class TestIdentifyCriticalKeys:
    def test_empty_state(self) -> None:
        assert identify_critical_keys({}) == []

    def test_matches_deliverable_status(self) -> None:
        state: dict[str, object] = {
            f"{DELIVERABLE_STATUS_PREFIX}d1": "COMPLETED",
            f"{DELIVERABLE_STATUS_PREFIX}d2": "FAILED",
            "unrelated": "ignored",
        }
        keys = identify_critical_keys(state)
        assert f"{DELIVERABLE_STATUS_PREFIX}d1" in keys
        assert f"{DELIVERABLE_STATUS_PREFIX}d2" in keys
        assert "unrelated" not in keys

    def test_matches_pm_keys(self) -> None:
        state: dict[str, object] = {
            PM_BATCH_POSITION_KEY: 3,
            "pm:some_other": "data",
        }
        keys = identify_critical_keys(state)
        assert PM_BATCH_POSITION_KEY in keys
        assert "pm:some_other" in keys

    def test_matches_director_keys(self) -> None:
        state: dict[str, object] = {"director:governance_override": "strict"}
        keys = identify_critical_keys(state)
        assert "director:governance_override" in keys

    def test_matches_project_config(self) -> None:
        state: dict[str, object] = {"project_config": {"retry_budget": 5}}
        keys = identify_critical_keys(state)
        assert "project_config" in keys

    def test_matches_workflow_id(self) -> None:
        state: dict[str, object] = {"workflow_id": "wf-1"}
        keys = identify_critical_keys(state)
        assert "workflow_id" in keys

    def test_matches_output_key_suffixes(self) -> None:
        state: dict[str, object] = {
            "plan_output": "some plan",
            "code_result": "some code",
            "agent_response": "text",
            "random_key": "ignored",
        }
        keys = identify_critical_keys(state)
        assert "plan_output" in keys
        assert "code_result" in keys
        assert "agent_response" in keys
        assert "random_key" not in keys

    def test_result_is_sorted(self) -> None:
        state: dict[str, object] = {
            "workflow_id": "x",
            "director:a": "y",
            "pm:b": "z",
        }
        keys = identify_critical_keys(state)
        assert keys == sorted(keys)

    def test_loaded_skill_names_prefix(self) -> None:
        state: dict[str, object] = {"loaded_skill_names": ["skill1"]}
        keys = identify_critical_keys(state)
        assert "loaded_skill_names" in keys


# ---------------------------------------------------------------------------
# TestDetermineRemainingStages
# ---------------------------------------------------------------------------


class TestDetermineRemainingStages:
    def test_no_completed_returns_all(self) -> None:
        remaining = determine_remaining_stages(PIPELINE_STAGES)
        assert remaining == PIPELINE_STAGES

    def test_explicit_completed_stages(self) -> None:
        completed = ["skill_loader", "memory_loader", "planner"]
        remaining = determine_remaining_stages(PIPELINE_STAGES, completed_stages=completed)
        assert "skill_loader" not in remaining
        assert "memory_loader" not in remaining
        assert "planner" not in remaining
        assert "coder" in remaining
        assert remaining[0] == "coder"

    def test_state_based_detection(self) -> None:
        state: dict[str, object] = {
            "loaded_skill_names": ["s1"],
            "memory_context": "ctx",
            "implementation_plan": "plan data",
        }
        remaining = determine_remaining_stages(
            PIPELINE_STAGES, state=state, stage_completion_keys=STAGE_COMPLETION_KEYS
        )
        assert "skill_loader" not in remaining
        assert "memory_loader" not in remaining
        assert "planner" not in remaining
        assert "coder" in remaining

    def test_completed_stages_takes_precedence_over_state(self) -> None:
        state: dict[str, object] = {"plan_output": "plan data"}
        # Explicit completed_stages overrides state
        remaining = determine_remaining_stages(
            PIPELINE_STAGES, completed_stages=["coder"], state=state
        )
        # planner still in remaining because completed_stages doesn't include it
        assert "planner" in remaining
        assert "coder" not in remaining

    def test_all_completed(self) -> None:
        remaining = determine_remaining_stages(
            PIPELINE_STAGES, completed_stages=list(PIPELINE_STAGES)
        )
        assert remaining == []

    def test_preserves_order(self) -> None:
        completed = ["planner", "coder"]
        remaining = determine_remaining_stages(PIPELINE_STAGES, completed_stages=completed)
        expected_order = [s for s in PIPELINE_STAGES if s not in completed]
        assert remaining == expected_order

    def test_none_values_in_state_not_counted(self) -> None:
        state: dict[str, object] = {"implementation_plan": None}
        remaining = determine_remaining_stages(
            PIPELINE_STAGES, state=state, stage_completion_keys=STAGE_COMPLETION_KEYS
        )
        assert "planner" in remaining


# ---------------------------------------------------------------------------
# TestSeedCriticalKeys
# ---------------------------------------------------------------------------


class TestSeedCriticalKeys:
    def test_extracts_critical_keys_only(self) -> None:
        state: dict[str, object] = {
            "workflow_id": "wf-1",
            "project_config": {"retry_budget": 5},
            "unrelated": "ignored",
            "temp_data": "also ignored",
        }
        seed = seed_critical_keys(state)
        assert "workflow_id" in seed
        assert "project_config" in seed
        assert "unrelated" not in seed
        assert "temp_data" not in seed

    def test_preserves_values(self) -> None:
        state: dict[str, object] = {
            "pm:batch_position": 42,
            f"{DELIVERABLE_STATUS_PREFIX}d1": "COMPLETED",
        }
        seed = seed_critical_keys(state)
        assert seed["pm:batch_position"] == 42
        assert seed[f"{DELIVERABLE_STATUS_PREFIX}d1"] == "COMPLETED"

    def test_empty_state(self) -> None:
        assert seed_critical_keys({}) == {}


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
# TestPipelineStageConstants
# ---------------------------------------------------------------------------


class TestPipelineStageConstants:
    """Verify auto-code pipeline constants (canonical source: auto-code/pipeline.py)."""

    def test_stages_count(self) -> None:
        assert len(PIPELINE_STAGES) == 9

    def test_completion_keys_match_stages(self) -> None:
        """Every stage has a corresponding completion key."""
        for stage in PIPELINE_STAGES:
            assert stage in STAGE_COMPLETION_KEYS, f"Missing completion key for {stage}"
