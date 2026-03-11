"""Tests for InstructionAssembler."""

from __future__ import annotations

from app.agents.assembler import (
    SAFETY_CONTENT,
    InstructionAssembler,
    InstructionContext,
    escape_braces,
)
from app.models.enums import FragmentType


def _make_assembler() -> InstructionAssembler:
    return InstructionAssembler()


class TestSafetyFragment:
    def test_safety_fragment_always_prepended(self) -> None:
        asm = _make_assembler()
        result = asm.assemble("test_agent", "Do stuff.", InstructionContext())
        assert result.startswith(SAFETY_CONTENT)

    def test_safety_fragment_identical_regardless_of_inputs(self) -> None:
        asm = _make_assembler()

        ctx_minimal = InstructionContext()
        ctx_full = InstructionContext(
            project_config="proj config",
            task_context="task ctx",
            loaded_skills={"skill_a": "content_a"},
            agent_name="agent_x",
        )

        asm.assemble("a1", "body1", ctx_minimal)
        frags_minimal = asm.get_source_map()

        asm.assemble("a2", "body2", ctx_full)
        frags_full = asm.get_source_map()

        safety_minimal = [f for f in frags_minimal if f.fragment_type == FragmentType.SAFETY]
        safety_full = [f for f in frags_full if f.fragment_type == FragmentType.SAFETY]

        assert len(safety_minimal) == 1
        assert len(safety_full) == 1
        assert safety_minimal[0].content == safety_full[0].content


class TestAssemblyOrder:
    def test_assembly_order(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(
            project_config="project instructions",
            task_context="task instructions",
            loaded_skills={"my_skill": "skill body"},
        )
        result = asm.assemble("agent", "identity body", ctx)
        parts = result.split("\n\n---\n\n")

        assert len(parts) == 5
        assert parts[0] == SAFETY_CONTENT
        assert parts[1] == "identity body"
        assert parts[2] == "project instructions"
        assert parts[3] == "task instructions"
        assert "## Skill: my_skill" in parts[4]

    def test_project_fragment_omitted_when_none(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(task_context="task")
        asm.assemble("agent", "body", ctx)
        frags = asm.get_source_map()

        types = [f.fragment_type for f in frags]
        assert FragmentType.PROJECT not in types
        assert FragmentType.TASK in types

    def test_task_fragment_omitted_when_none(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(project_config="proj")
        asm.assemble("agent", "body", ctx)
        frags = asm.get_source_map()

        types = [f.fragment_type for f in frags]
        assert FragmentType.TASK not in types
        assert FragmentType.PROJECT in types

    def test_skill_fragment_omitted_when_empty(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext()
        asm.assemble("agent", "body", ctx)
        frags = asm.get_source_map()

        types = [f.fragment_type for f in frags]
        assert FragmentType.SKILL not in types


class TestCurlyBraceEscaping:
    def test_curly_brace_escaping(self) -> None:
        text = "Use {key} and also {literal_json}"
        escaped = escape_braces(text)
        # {key} and {literal_json} are both valid identifiers -> preserved
        assert "{key}" in escaped
        assert "{literal_json}" in escaped

        # Actual JSON-like braces
        text2 = 'config = {"name": "val"}'
        escaped2 = escape_braces(text2)
        assert '{{"name": "val"}}' in escaped2

    def test_curly_brace_escaping_optional(self) -> None:
        text = "Hello {name?}, welcome to {place}"
        escaped = escape_braces(text)
        assert "{name?}" in escaped
        assert "{place}" in escaped

    def test_project_fragment_uses_escaping(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(project_config='Use {agent_name} and {"key": "val"}')
        result = asm.assemble("agent", "body", ctx)
        parts = result.split("\n\n---\n\n")
        project_part = parts[2]
        assert "{agent_name}" in project_part
        assert '{{"key": "val"}}' in project_part

    def test_skill_fragment_uses_escaping(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(loaded_skills={"sk": 'Template {var} and {"a": 1}'})
        result = asm.assemble("agent", "body", ctx)
        parts = result.split("\n\n---\n\n")
        skill_part = parts[2]
        assert "{var}" in skill_part
        assert '{{"a": 1}}' in skill_part


class TestSourceMap:
    def test_source_map_auditability(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(
            project_config="proj",
            task_context="task",
            loaded_skills={"alpha": "a_content"},
            agent_name="my_agent",
        )
        asm.assemble("test_agent", "body", ctx)
        frags = asm.get_source_map()

        assert len(frags) == 5
        sources = {f.fragment_type: f.source for f in frags}
        assert sources[FragmentType.SAFETY] == "hardcoded"
        assert sources[FragmentType.IDENTITY] == "agent:test_agent"
        assert "project_config" in sources[FragmentType.PROJECT]
        assert sources[FragmentType.TASK] == "session_state"
        assert sources[FragmentType.SKILL] == "alpha"


class TestDeterminism:
    def test_deterministic_output(self) -> None:
        ctx = InstructionContext(
            project_config="proj {var}",
            task_context="task",
            loaded_skills={"b": "bb", "a": "aa"},
        )

        asm1 = InstructionAssembler()
        result1 = asm1.assemble("agent", "body", ctx)

        asm2 = InstructionAssembler()
        result2 = asm2.assemble("agent", "body", ctx)

        assert result1 == result2

    def test_full_assembly_all_fragments(self) -> None:
        asm = _make_assembler()
        ctx = InstructionContext(
            project_config="Project rules here",
            task_context="Current task context",
            loaded_skills={"coding": "Code in Python", "testing": "Write tests"},
            agent_name="coder",
        )
        result = asm.assemble("coder", "You are a coder agent.", ctx)
        frags = asm.get_source_map()

        # All fragment types present
        types = {f.fragment_type for f in frags}
        assert types == {
            FragmentType.SAFETY,
            FragmentType.IDENTITY,
            FragmentType.PROJECT,
            FragmentType.TASK,
            FragmentType.SKILL,
        }

        # Verify separator count (5 fragments = 4 separators)
        assert result.count("\n\n---\n\n") == 4

        # Verify content ordering
        safety_pos = result.index(SAFETY_CONTENT)
        body_pos = result.index("You are a coder agent.")
        project_pos = result.index("Project rules here")
        task_pos = result.index("Current task context")
        skill_pos = result.index("## Skill:")

        assert safety_pos < body_pos < project_pos < task_pos < skill_pos
