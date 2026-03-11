"""Tests for agent definition files — validates all .md files in app/agents/ parse correctly."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents._registry import AgentFileEntry, parse_definition_file
from app.models.enums import AgentType, DefinitionScope

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "agents"

# All expected LLM definition files
_EXPECTED_LLM_FILES = ["director", "pm", "planner", "coder", "reviewer", "fixer"]


def _parse(name: str) -> AgentFileEntry:
    """Parse a definition file by agent name."""
    return parse_definition_file(AGENTS_DIR / f"{name}.md", DefinitionScope.GLOBAL)


class TestAllDefinitionFilesParseable:
    def test_all_definition_files_parseable(self) -> None:
        """All .md files in app/agents/ parse without error."""
        md_files = sorted(AGENTS_DIR.glob("*.md"))
        assert len(md_files) >= len(_EXPECTED_LLM_FILES), (
            f"Expected at least {len(_EXPECTED_LLM_FILES)} .md files, found {len(md_files)}"
        )
        for md_file in md_files:
            entry = parse_definition_file(md_file, DefinitionScope.GLOBAL)
            assert entry.name, f"File {md_file} has empty name"
            assert entry.description, f"File {md_file} has empty description"
            assert entry.agent_type in (AgentType.LLM, AgentType.CUSTOM)


class TestDirectorDefinition:
    def test_director_definition(self) -> None:
        """Director definition has correct frontmatter fields."""
        entry = _parse("director")
        assert entry.name == "director"
        assert entry.description == "Cross-project governance and CEO communication"
        assert entry.agent_type == AgentType.LLM
        assert entry.tool_role == "director"
        assert entry.model_role == "plan"
        assert entry.output_key == "director_response"


class TestPmDefinition:
    def test_pm_definition(self) -> None:
        """PM definition has correct frontmatter fields."""
        entry = _parse("pm")
        assert entry.name == "pm"
        assert entry.description == "Autonomous project management and deliverable orchestration"
        assert entry.agent_type == AgentType.LLM
        assert entry.tool_role == "pm"
        assert entry.model_role == "plan"
        assert entry.output_key == "pm_response"


class TestWorkerDefinitions:
    @pytest.mark.parametrize(
        ("agent_name", "expected_tool_role", "expected_model_role", "expected_output_key"),
        [
            ("planner", "planner", "plan", "implementation_plan"),
            ("coder", "coder", "code", "code_output"),
            ("reviewer", "reviewer", "review", "review_result"),
            ("fixer", "fixer", "code", "code_output"),
        ],
    )
    def test_worker_definitions(
        self,
        agent_name: str,
        expected_tool_role: str,
        expected_model_role: str,
        expected_output_key: str,
    ) -> None:
        """Worker definitions have correct frontmatter fields."""
        entry = _parse(agent_name)
        assert entry.name == agent_name
        assert entry.agent_type == AgentType.LLM
        assert entry.tool_role == expected_tool_role
        assert entry.model_role == expected_model_role
        assert entry.output_key == expected_output_key


class TestAllBodiesNonEmpty:
    def test_all_bodies_non_empty(self) -> None:
        """All LLM definition files have non-empty instruction bodies."""
        for name in _EXPECTED_LLM_FILES:
            entry = _parse(name)
            assert entry.body is not None, f"Agent '{name}' has no body"
            assert len(entry.body.strip()) > 100, (
                f"Agent '{name}' body is too short ({len(entry.body.strip())} chars)"
            )
