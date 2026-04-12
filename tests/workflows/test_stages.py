"""Tests for stage lifecycle management."""

from __future__ import annotations

import pytest

from app.models.constants import (
    STAGE_COMPLETED_LIST,
    STAGE_CURRENT,
    STAGE_INDEX,
    STAGE_STATUS,
    STAGE_WORKFLOW_STAGES,
)
from app.models.enums import StageStatus
from app.workflows.manifest import StageDef, WorkflowManifest
from app.workflows.stages import initialize_stage_state, reconfigure_stage


class TestInitializeStageState:
    def test_initializes_first_stage(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[
                StageDef(name="alpha", description="First"),
                StageDef(name="beta", description="Second"),
            ],
        )
        state = initialize_stage_state(m)
        assert state[STAGE_CURRENT] == "alpha"
        assert state[STAGE_INDEX] == 0
        assert state[STAGE_STATUS] == StageStatus.PENDING
        assert state[STAGE_COMPLETED_LIST] == []
        assert len(state[STAGE_WORKFLOW_STAGES]) == 2  # type: ignore[arg-type]

    def test_no_stages_returns_minimal_state(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        state = initialize_stage_state(m)
        assert state[STAGE_CURRENT] == ""
        assert state[STAGE_INDEX] == 0
        assert state[STAGE_STATUS] == StageStatus.PENDING
        assert state[STAGE_COMPLETED_LIST] == []
        assert state[STAGE_WORKFLOW_STAGES] == []

    def test_single_stage(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="only", description="Only stage")],
        )
        state = initialize_stage_state(m)
        assert state[STAGE_CURRENT] == "only"
        assert state[STAGE_INDEX] == 0

    def test_all_keys_pm_prefixed(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="a", description="A")],
        )
        state = initialize_stage_state(m)
        for key in state:
            assert isinstance(key, str)
            assert key.startswith("pm:"), f"Key '{key}' missing pm: prefix"

    def test_workflow_stages_contain_stage_data(self) -> None:
        m = WorkflowManifest(
            name="test",
            description="T",
            stages=[StageDef(name="build", description="Build", agents=["coder"])],
        )
        state = initialize_stage_state(m)
        stages = state[STAGE_WORKFLOW_STAGES]
        assert isinstance(stages, list)
        assert stages[0]["name"] == "build"
        assert stages[0]["agents"] == ["coder"]


class TestReconfigureStage:
    def _make_manifest(self) -> WorkflowManifest:
        return WorkflowManifest(
            name="test",
            description="T",
            stages=[
                StageDef(name="alpha", description="First"),
                StageDef(name="beta", description="Second"),
                StageDef(name="gamma", description="Third"),
            ],
        )

    def _initial_state(self, manifest: WorkflowManifest) -> dict[str, object]:
        return initialize_stage_state(manifest)

    def test_advance_sequential(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        delta = reconfigure_stage(state, m, "beta")
        assert delta[STAGE_CURRENT] == "beta"
        assert delta[STAGE_INDEX] == 1
        assert delta[STAGE_STATUS] == StageStatus.ACTIVE
        assert "alpha" in delta[STAGE_COMPLETED_LIST]  # type: ignore[operator]

    def test_advance_twice(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        delta1 = reconfigure_stage(state, m, "beta")
        # Merge delta into state for second advance
        merged: dict[str, object] = {**state, **delta1}
        delta2 = reconfigure_stage(merged, m, "gamma")
        assert delta2[STAGE_CURRENT] == "gamma"
        assert delta2[STAGE_INDEX] == 2
        completed = delta2[STAGE_COMPLETED_LIST]
        assert isinstance(completed, list)
        assert "alpha" in completed
        assert "beta" in completed

    def test_skip_rejected(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        with pytest.raises(ValueError, match="skip"):
            reconfigure_stage(state, m, "gamma")  # skips beta

    def test_revisit_rejected(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        delta = reconfigure_stage(state, m, "beta")
        merged: dict[str, object] = {**state, **delta}
        with pytest.raises(ValueError, match="revisit"):
            reconfigure_stage(merged, m, "alpha")

    def test_same_stage_rejected(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        with pytest.raises(ValueError):
            reconfigure_stage(state, m, "alpha")  # already on alpha

    def test_invalid_stage_name(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        with pytest.raises(ValueError, match="not found"):
            reconfigure_stage(state, m, "nonexistent")

    def test_no_stages_returns_empty(self) -> None:
        m = WorkflowManifest(name="test", description="T")
        state: dict[str, object] = {}
        delta = reconfigure_stage(state, m, "anything")
        assert delta == {}

    def test_does_not_mutate_input(self) -> None:
        m = self._make_manifest()
        state = self._initial_state(m)
        original_completed = list(state[STAGE_COMPLETED_LIST])  # type: ignore[arg-type]
        reconfigure_stage(state, m, "beta")
        assert state[STAGE_COMPLETED_LIST] == original_completed
