"""Tests for AgentRegistry, parse_definition_file, and 3-scope cascade."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from app.agents._registry import (
    CLASS_REGISTRY,
    AgentRegistry,
    AgentResolutionEntry,
    parse_definition_file,
    register_custom_agent,
)
from app.agents.assembler import InstructionAssembler, InstructionContext
from app.lib.exceptions import NotFoundError, ValidationError
from app.models.enums import AgentType, DefinitionScope, ModelRole

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_DEFINITION = """\
---
name: coder
description: Implement code changes
type: llm
tool_role: coder
model_role: code
output_key: code_output
---

You are a coder agent. Write clean code.
"""

_PARTIAL_OVERRIDE = """\
---
name: coder
description: Project-specific coder
type: llm
model_role: review
---
"""

_FULL_OVERRIDE = """\
---
name: coder
description: Fully replaced coder
type: llm
tool_role: reviewer
model_role: review
---

Completely new instructions for this scope.
"""

_CUSTOM_DEFINITION = """\
---
name: memory_loader
description: Loads memory
type: custom
class: MemoryLoaderAgent
---
"""


def _write_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class _FakeBaseAgent:
    """Minimal stand-in for BaseAgent in tests."""

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def _make_registry(tmp_path: Path) -> AgentRegistry:
    """Build an AgentRegistry with mocked dependencies."""
    assembler = InstructionAssembler()

    router = MagicMock()
    router.select_model = MagicMock(return_value="anthropic/claude-sonnet-4-6")

    toolset = MagicMock()
    toolset.get_tools_for_role = MagicMock(return_value=[])

    return AgentRegistry(
        assembler=assembler,
        router=router,
        toolset=toolset,
    )


def _default_ctx() -> InstructionContext:
    return InstructionContext(agent_name="test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseDefinitionFile:
    def test_parse_valid(self, tmp_path: Path) -> None:
        """test_parse_definition_file_valid — parse a valid .md file."""
        f = _write_file(tmp_path / "coder.md", _VALID_DEFINITION)
        entry = parse_definition_file(f, DefinitionScope.GLOBAL)

        assert entry.name == "coder"
        assert entry.description == "Implement code changes"
        assert entry.agent_type == AgentType.LLM
        assert entry.tool_role == "coder"
        assert entry.model_role == "code"
        assert entry.output_key == "code_output"
        assert entry.body is not None
        assert "clean code" in entry.body
        assert entry.scope == DefinitionScope.GLOBAL
        assert entry.source_path == f

    def test_parse_missing_required_fields(self, tmp_path: Path) -> None:
        """test_parse_definition_file_missing_required_fields — missing name."""
        content = "---\ndescription: test\ntype: llm\n---\n"
        f = _write_file(tmp_path / "bad.md", content)
        with pytest.raises(ValidationError, match="missing required fields"):
            parse_definition_file(f, DefinitionScope.GLOBAL)

    def test_parse_unknown_type(self, tmp_path: Path) -> None:
        """test_parse_definition_file_unknown_type — type: foo."""
        content = "---\nname: x\ndescription: x\ntype: foo\n---\n"
        f = _write_file(tmp_path / "bad.md", content)
        with pytest.raises(ValidationError, match="invalid type"):
            parse_definition_file(f, DefinitionScope.GLOBAL)

    def test_parse_custom_missing_class(self, tmp_path: Path) -> None:
        """Custom type without class field raises error."""
        content = "---\nname: x\ndescription: x\ntype: custom\n---\n"
        f = _write_file(tmp_path / "bad.md", content)
        with pytest.raises(ValidationError, match="requires 'class' field"):
            parse_definition_file(f, DefinitionScope.GLOBAL)

    def test_partial_override_body_none(self, tmp_path: Path) -> None:
        """Frontmatter-only file has body=None."""
        f = _write_file(tmp_path / "coder.md", _PARTIAL_OVERRIDE)
        entry = parse_definition_file(f, DefinitionScope.WORKFLOW)
        assert entry.body is None


class TestScan:
    def test_scan_discovers_files(self, tmp_path: Path) -> None:
        """test_scan_discovers_files — scan a temp dir with .md files."""
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)
        _write_file(
            tmp_path / "planner.md",
            "---\nname: planner\ndescription: Plan\ntype: llm\n---\nPlan stuff.\n",
        )
        reg = _make_registry(tmp_path)
        reg.scan((tmp_path, DefinitionScope.GLOBAL))

        sources = reg.get_resolution_sources()
        assert "coder" in sources
        assert "planner" in sources

    def test_three_scope_cascade_override(self, tmp_path: Path) -> None:
        """test_three_scope_cascade_override — project scope overrides global."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        _write_file(global_dir / "coder.md", _VALID_DEFINITION)
        _write_file(project_dir / "coder.md", _FULL_OVERRIDE)

        reg = _make_registry(tmp_path)
        reg.scan(
            (global_dir, DefinitionScope.GLOBAL),
            (project_dir, DefinitionScope.PROJECT),
        )

        sources = reg.get_resolution_sources()
        assert sources["coder"].scope == DefinitionScope.PROJECT
        assert sources["coder"].partial_override is False

    def test_partial_override_inherits_body(self, tmp_path: Path) -> None:
        """test_partial_override_inherits_body — frontmatter-only file inherits parent body."""
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        global_dir.mkdir()
        workflow_dir.mkdir()

        _write_file(global_dir / "coder.md", _VALID_DEFINITION)
        _write_file(workflow_dir / "coder.md", _PARTIAL_OVERRIDE)

        reg = _make_registry(tmp_path)
        reg.scan(
            (global_dir, DefinitionScope.GLOBAL),
            (workflow_dir, DefinitionScope.WORKFLOW),
        )

        # Build to verify body was inherited
        agent = reg.build("coder", _default_ctx())
        # The instruction should contain text from the global body
        instruction: str = getattr(agent, "instruction", "")
        assert "clean code" in instruction

    def test_partial_override_merges_frontmatter(self, tmp_path: Path) -> None:
        """test_partial_override_merges_frontmatter — child frontmatter overrides parent."""
        global_dir = tmp_path / "global"
        workflow_dir = tmp_path / "workflow"
        global_dir.mkdir()
        workflow_dir.mkdir()

        _write_file(global_dir / "coder.md", _VALID_DEFINITION)
        _write_file(workflow_dir / "coder.md", _PARTIAL_OVERRIDE)

        reg = _make_registry(tmp_path)
        reg.scan(
            (global_dir, DefinitionScope.GLOBAL),
            (workflow_dir, DefinitionScope.WORKFLOW),
        )

        sources = reg.get_resolution_sources()
        assert sources["coder"].scope == DefinitionScope.WORKFLOW
        assert sources["coder"].partial_override is True

        # model_role should come from the override
        # tool_role should be inherited from parent
        # We verify via the router call during build
        reg.build("coder", _default_ctx())
        reg._router.select_model.assert_called_with(ModelRole.REVIEW)  # type: ignore[union-attr]

    def test_full_override_replaces_body(self, tmp_path: Path) -> None:
        """test_full_override_replaces_body — body present = full replacement."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()

        _write_file(global_dir / "coder.md", _VALID_DEFINITION)
        _write_file(project_dir / "coder.md", _FULL_OVERRIDE)

        reg = _make_registry(tmp_path)
        reg.scan(
            (global_dir, DefinitionScope.GLOBAL),
            (project_dir, DefinitionScope.PROJECT),
        )

        agent = reg.build("coder", _default_ctx())
        instruction: str = getattr(agent, "instruction", "")
        assert "Completely new instructions" in instruction
        assert "clean code" not in instruction

    def test_project_scope_custom_rejected(self, tmp_path: Path) -> None:
        """test_project_scope_custom_rejected — project-scope type:custom raises error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        _write_file(project_dir / "memory.md", _CUSTOM_DEFINITION)

        reg = _make_registry(tmp_path)
        with pytest.raises(ValidationError, match="Project-scope custom agents"):
            reg.scan((project_dir, DefinitionScope.PROJECT))

    def test_same_scope_name_collision(self, tmp_path: Path) -> None:
        """test_same_scope_name_collision — two files same name in same dir."""
        # Create two files that both parse to name: coder
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)
        _write_file(
            tmp_path / "coder2.md",
            "---\nname: coder\ndescription: Another\ntype: llm\n---\n",
        )

        reg = _make_registry(tmp_path)
        with pytest.raises(ValidationError, match="Duplicate agent name"):
            reg.scan((tmp_path, DefinitionScope.GLOBAL))


class TestBuild:
    def test_build_llm_agent(self, tmp_path: Path) -> None:
        """test_build_llm_agent — build returns LlmAgent with correct model, instruction, tools."""
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)

        reg = _make_registry(tmp_path)
        reg.scan((tmp_path, DefinitionScope.GLOBAL))

        agent = reg.build("coder", _default_ctx())
        assert agent.name == "coder"
        assert "litellm/" in getattr(agent, "model", "")
        assert getattr(agent, "description", "") == "Implement code changes"

    def test_build_custom_agent(self, tmp_path: Path) -> None:
        """test_build_custom_agent — build returns registered CustomAgent instance."""
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        _write_file(global_dir / "memory_loader.md", _CUSTOM_DEFINITION)

        # Register fake custom agent class
        CLASS_REGISTRY["MemoryLoaderAgent"] = _FakeBaseAgent  # type: ignore[assignment]
        try:
            reg = _make_registry(tmp_path)
            reg.scan((global_dir, DefinitionScope.GLOBAL))

            agent = reg.build("memory_loader", _default_ctx())
            assert isinstance(agent, _FakeBaseAgent)
            assert getattr(agent, "name", None) == "memory_loader"
        finally:
            CLASS_REGISTRY.pop("MemoryLoaderAgent", None)

    def test_build_missing_agent_raises(self, tmp_path: Path) -> None:
        """test_build_missing_agent_raises — unknown name raises NotFoundError."""
        reg = _make_registry(tmp_path)
        reg.scan()  # Empty scan

        with pytest.raises(NotFoundError, match="not found"):
            reg.build("nonexistent", _default_ctx())

    def test_definition_param_overrides_lookup(self, tmp_path: Path) -> None:
        """test_definition_param_overrides_lookup — build('PM_1', ctx, definition='coder')."""
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)

        reg = _make_registry(tmp_path)
        reg.scan((tmp_path, DefinitionScope.GLOBAL))

        agent = reg.build("PM_1", _default_ctx(), definition="coder")
        assert agent.name == "PM_1"
        # Should have used coder definition's description
        assert getattr(agent, "description", "") == "Implement code changes"

    def test_resolution_auditability(self, tmp_path: Path) -> None:
        """test_resolution_auditability — get_resolution_sources returns entries."""
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)

        reg = _make_registry(tmp_path)
        reg.scan((tmp_path, DefinitionScope.GLOBAL))

        sources = reg.get_resolution_sources()
        assert "coder" in sources
        entry = sources["coder"]
        assert isinstance(entry, AgentResolutionEntry)
        assert entry.scope == DefinitionScope.GLOBAL
        assert entry.file_path.endswith("coder.md")
        assert entry.partial_override is False

    def test_output_key_set_on_llm_agent(self, tmp_path: Path) -> None:
        """test_output_key_set_on_llm_agent — LlmAgent has output_key from definition."""
        _write_file(tmp_path / "coder.md", _VALID_DEFINITION)

        reg = _make_registry(tmp_path)
        reg.scan((tmp_path, DefinitionScope.GLOBAL))

        agent = reg.build("coder", _default_ctx())
        assert getattr(agent, "output_key", None) == "code_output"


class TestRegisterCustomAgent:
    def test_register_and_lookup(self) -> None:
        """register_custom_agent populates CLASS_REGISTRY."""
        register_custom_agent("TestAgent", _FakeBaseAgent)  # type: ignore[arg-type]
        try:
            assert CLASS_REGISTRY["TestAgent"] is _FakeBaseAgent
        finally:
            CLASS_REGISTRY.pop("TestAgent", None)
