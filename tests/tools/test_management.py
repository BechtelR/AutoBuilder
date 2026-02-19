"""Tests for management tools (PM and Director)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from app.models.enums import (
    CeoItemType,
    DependencyAction,
    EscalationPriority,
    EscalationRequestType,
    PmOverrideAction,
)
from app.tools.management import (
    escalate_to_ceo,
    escalate_to_director,
    get_project_context,
    list_projects,
    manage_dependencies,
    override_pm,
    query_deliverables,
    query_dependency_graph,
    query_project_status,
    reorder_deliverables,
    select_ready_batch,
    update_deliverable,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Director: escalate_to_ceo
# ---------------------------------------------------------------------------


class TestEscalateToCeo:
    def test_valid_params_returns_confirmation_with_uuid(self) -> None:
        result = escalate_to_ceo(
            item_type=CeoItemType.NOTIFICATION,
            priority=EscalationPriority.HIGH,
            message="Something important",
            metadata="{}",
        )
        assert "CEO queue item" in result
        # Extract UUID (8 hex chars after "CEO queue item ")
        parts = result.split()
        idx = parts.index("item") + 1
        item_id = parts[idx].rstrip(":")
        assert len(item_id) == 8

    def test_invalid_item_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            CeoItemType("BOGUS")

    def test_invalid_priority_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            EscalationPriority("EXTREME")


# ---------------------------------------------------------------------------
# PM: escalate_to_director
# ---------------------------------------------------------------------------


class TestEscalateToDirector:
    def test_valid_params_returns_confirmation(self) -> None:
        result = escalate_to_director(
            priority=EscalationPriority.NORMAL,
            context="Need help with architecture",
            request_type=EscalationRequestType.ESCALATION,
        )
        assert "Escalation" in result
        assert "ESCALATION" in result
        assert "placeholder" in result

    def test_invalid_request_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            EscalationRequestType("INVALID_TYPE")


# ---------------------------------------------------------------------------
# Director: override_pm
# ---------------------------------------------------------------------------


class TestOverridePm:
    def test_invalid_action_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            PmOverrideAction("DESTROY")

    def test_valid_action_returns_confirmation(self) -> None:
        result = override_pm(
            project_id="proj1",
            action=PmOverrideAction.PAUSE,
            reason="needs review",
        )
        assert "PM override" in result
        assert "PAUSE" in result
        assert "placeholder" in result


# ---------------------------------------------------------------------------
# PM: manage_dependencies
# ---------------------------------------------------------------------------


class TestManageDependencies:
    def test_invalid_action_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            DependencyAction("NUKE")

    def test_valid_add_returns_confirmation(self) -> None:
        result = manage_dependencies(
            action=DependencyAction.ADD,
            source_id="d1",
            target_id="d2",
        )
        assert "Dependency ADD" in result
        assert "placeholder" in result

    def test_add_without_target_returns_error(self) -> None:
        result = manage_dependencies(action=DependencyAction.ADD, source_id="d1")
        assert "target_id is required" in result

    def test_remove_without_target_returns_error(self) -> None:
        result = manage_dependencies(action=DependencyAction.REMOVE, source_id="d1")
        assert "target_id is required" in result

    def test_query_without_target_succeeds(self) -> None:
        result = manage_dependencies(action=DependencyAction.QUERY, source_id="d1")
        assert "QUERY" in result
        assert "placeholder" in result


# ---------------------------------------------------------------------------
# PM: select_ready_batch
# ---------------------------------------------------------------------------


class TestSelectReadyBatch:
    def test_returns_placeholder_message(self) -> None:
        result = select_ready_batch("proj1")
        assert "proj1" in result
        assert "placeholder" in result


# ---------------------------------------------------------------------------
# Director: get_project_context
# ---------------------------------------------------------------------------


class TestGetProjectContext:
    def test_detects_python_project(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\ndependencies = ["fastapi", "uvicorn"]\n')

        result = get_project_context(str(tmp_path))
        assert "Python project" in result
        assert "myapp" in result
        assert "fastapi" in result

    def test_detects_node_project(self, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "my-dashboard", "dependencies": {"react": "^19.0.0"}}))

        result = get_project_context(str(tmp_path))
        assert "JavaScript/TypeScript project" in result
        assert "my-dashboard" in result
        assert "react" in result

    def test_no_config_files_returns_message(self, tmp_path: Path) -> None:
        result = get_project_context(str(tmp_path))
        assert "No recognised project config files" in result

    def test_nonexistent_path_returns_error(self, tmp_path: Path) -> None:
        result = get_project_context(str(tmp_path / "nonexistent"))
        assert "not a directory" in result

    def test_detects_rust_project(self, tmp_path: Path) -> None:
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "myapp"\n')
        result = get_project_context(str(tmp_path))
        assert "Rust" in result


# ---------------------------------------------------------------------------
# PM: update_deliverable, query_deliverables, reorder_deliverables
# ---------------------------------------------------------------------------


class TestUpdateDeliverable:
    def test_returns_confirmation(self) -> None:
        result = update_deliverable("d1", "IN_PROGRESS")
        assert "d1" in result
        assert "IN_PROGRESS" in result

    def test_with_notes(self) -> None:
        result = update_deliverable("d1", "DONE", notes="all tests pass")
        assert "all tests pass" in result


class TestQueryDeliverables:
    def test_returns_placeholder(self) -> None:
        result = query_deliverables("proj1")
        assert "proj1" in result
        assert "placeholder" in result

    def test_with_status_filter(self) -> None:
        result = query_deliverables("proj1", status="PENDING")
        assert "PENDING" in result


class TestReorderDeliverables:
    def test_returns_count(self) -> None:
        result = reorder_deliverables("proj1", ["d1", "d2", "d3"])
        assert "3" in result
        assert "proj1" in result


# ---------------------------------------------------------------------------
# Director: list_projects, query_project_status, query_dependency_graph
# ---------------------------------------------------------------------------


class TestListProjects:
    def test_returns_placeholder(self) -> None:
        result = list_projects()
        assert "placeholder" in result

    def test_with_status_filter(self) -> None:
        result = list_projects(status="ACTIVE")
        assert "ACTIVE" in result


class TestQueryProjectStatus:
    def test_returns_placeholder(self) -> None:
        result = query_project_status("proj1")
        assert "proj1" in result
        assert "placeholder" in result


class TestQueryDependencyGraph:
    def test_returns_placeholder(self) -> None:
        result = query_dependency_graph("proj1")
        assert "proj1" in result
        assert "placeholder" in result

    def test_with_deliverable_focus(self) -> None:
        result = query_dependency_graph("proj1", deliverable_id="d1")
        assert "d1" in result


# ---------------------------------------------------------------------------
# Cross-cutting: all placeholders mention Phase
# ---------------------------------------------------------------------------


class TestPlaceholders:
    def test_placeholder_tools_reference_phase(self) -> None:
        """All placeholder management tools reference a Phase in their output."""
        results = [
            select_ready_batch("p1"),
            escalate_to_director(EscalationPriority.HIGH, "ctx", EscalationRequestType.ESCALATION),
            escalate_to_ceo(CeoItemType.TASK, EscalationPriority.HIGH, "msg", "{}"),
            override_pm("p1", PmOverrideAction.PAUSE, "reason"),
            manage_dependencies(DependencyAction.QUERY, "d1"),
            update_deliverable("d1", "DONE"),
            query_deliverables("p1"),
            reorder_deliverables("p1", ["d1"]),
            list_projects(),
            query_project_status("p1"),
            query_dependency_graph("p1"),
        ]
        for result in results:
            assert "Phase" in result or "placeholder" in result
