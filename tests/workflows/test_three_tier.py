"""Three-tier skill/agent merge validation tests."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.skills.library import SkillLibrary

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_skill(
    base_dir: Path,
    name: str,
    *,
    description: str = "Test skill",
    priority: int = 0,
) -> Path:
    """Write a minimal SKILL.md file."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = (
        f"---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"priority: {priority}\n"
        f"---\n\n"
        f"Body of {name}.\n"
    )
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_dir


class TestSkillThreeTierMerge:
    def test_global_only(self, tmp_path: Path) -> None:
        """No workflow_dir -> two-tier (backward compatible)."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")
        lib = SkillLibrary(global_dir)
        lib.scan()
        assert "alpha" in lib.get_index()

    def test_workflow_overrides_global(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        _write_skill(global_dir, "shared", description="Global version")
        _write_skill(workflow_dir, "shared", description="Workflow version")
        lib = SkillLibrary(global_dir, workflow_dir=workflow_dir)
        lib.scan()
        idx = lib.get_index()
        assert idx["shared"].description == "Workflow version"

    def test_project_overrides_workflow(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "shared", description="Global")
        _write_skill(workflow_dir, "shared", description="Workflow")
        _write_skill(project_dir, "shared", description="Project")
        lib = SkillLibrary(global_dir, workflow_dir=workflow_dir, project_dir=project_dir)
        lib.scan()
        assert lib.get_index()["shared"].description == "Project"

    def test_project_overrides_global_through_workflow(self, tmp_path: Path) -> None:
        """Project overrides global even when workflow tier exists but has no skill."""
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "alpha", description="Global")
        workflow_dir.mkdir(exist_ok=True)  # empty workflow dir
        _write_skill(project_dir, "alpha", description="Project")
        lib = SkillLibrary(global_dir, workflow_dir=workflow_dir, project_dir=project_dir)
        lib.scan()
        assert lib.get_index()["alpha"].description == "Project"

    def test_unique_names_additive(self, tmp_path: Path) -> None:
        """Global alpha + workflow beta + project gamma = all three."""
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "alpha")
        _write_skill(workflow_dir, "beta")
        _write_skill(project_dir, "gamma")
        lib = SkillLibrary(global_dir, workflow_dir=workflow_dir, project_dir=project_dir)
        lib.scan()
        idx = lib.get_index()
        assert "alpha" in idx
        assert "beta" in idx
        assert "gamma" in idx

    def test_workflow_dir_missing_no_error(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")
        lib = SkillLibrary(global_dir, workflow_dir=tmp_path / "nonexistent")
        lib.scan()
        assert len(lib.get_index()) == 1

    def test_workflow_dir_none_backward_compat(self, tmp_path: Path) -> None:
        """workflow_dir=None preserves existing two-tier behavior."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "alpha")
        _write_skill(project_dir, "beta")
        lib = SkillLibrary(global_dir, project_dir=project_dir)  # no workflow_dir
        lib.scan()
        idx = lib.get_index()
        assert "alpha" in idx
        assert "beta" in idx

    def test_override_logged(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        _write_skill(global_dir, "shared")
        _write_skill(workflow_dir, "shared")
        with caplog.at_level(logging.INFO, logger="app"):
            lib = SkillLibrary(global_dir, workflow_dir=workflow_dir)
            lib.scan()
        assert any(
            "override" in r.message.lower() or "overrides" in r.message.lower()
            for r in caplog.records
        )

    def test_three_tier_count(self, tmp_path: Path) -> None:
        """All three tiers contribute unique skills."""
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        project_dir = tmp_path / "project"
        for i in range(3):
            _write_skill(global_dir, f"g{i}")
        for i in range(2):
            _write_skill(workflow_dir, f"w{i}")
        _write_skill(project_dir, "p0")
        lib = SkillLibrary(global_dir, workflow_dir=workflow_dir, project_dir=project_dir)
        lib.scan()
        assert len(lib.get_index()) == 6  # 3 + 2 + 1
