"""Tests for deterministic custom agents."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.events import Event

from app.agents._registry import CLASS_REGISTRY, parse_definition_file
from app.agents.protocols import NullSkillLibrary, SkillContent, SkillMatchContext
from app.models.enums import DefinitionScope
from app.skills.library import SkillEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_events(gen: object) -> list[Event]:
    """Collect all events from an async generator."""
    events: list[Event] = []
    async for event in gen:  # type: ignore[union-attr]
        assert isinstance(event, Event)
        events.append(event)
    return events


def make_ctx(state: dict[str, object] | None = None) -> MagicMock:
    """Create a mock InvocationContext with session state."""
    ctx = MagicMock()
    ctx.session.state = state or {}
    return ctx


def as_dict(val: object) -> dict[str, object]:
    """Cast a state_delta value to dict for nested access."""
    return cast("dict[str, object]", val)


# ---------------------------------------------------------------------------
# SkillLoaderAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skill_loader_null_library() -> None:
    """SkillLoaderAgent with NullSkillLibrary yields empty results."""
    from app.agents.custom.skill_loader import SkillLoaderAgent

    agent = SkillLoaderAgent(name="skill_loader", skill_library=NullSkillLibrary())
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["loaded_skills"] == {}
    assert delta["loaded_skill_names"] == []


@pytest.mark.asyncio
async def test_skill_loader_state_delta() -> None:
    """SkillLoaderAgent populates LoadedSkillData with content, applies_to, triggers."""
    from app.agents.custom.skill_loader import SkillLoaderAgent

    mock_library = MagicMock()
    entry = SkillEntry(
        name="test_skill",
        description="A test skill",
        applies_to=["coder"],
        triggers=[],
    )
    mock_library.match.return_value = [entry]
    mock_library.resolve_cascades.return_value = [entry]
    mock_library.load.return_value = SkillContent(entry=entry, content="skill content here")

    agent = SkillLoaderAgent(name="skill_loader", skill_library=mock_library)
    ctx = make_ctx({"deliverable_type": "api", "agent_role": "coder"})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert "loaded_skills" in delta
    assert "loaded_skill_names" in delta

    skill_data = as_dict(delta["loaded_skills"])["test_skill"]
    assert isinstance(skill_data, dict)
    assert skill_data["content"] == "skill content here"
    assert skill_data["applies_to"] == ["coder"]
    assert isinstance(skill_data["matched_triggers"], list)

    assert delta["loaded_skill_names"] == ["test_skill"]

    # Verify match was called with correct context
    call_args = mock_library.match.call_args[0][0]
    assert isinstance(call_args, SkillMatchContext)
    assert call_args.deliverable_type == "api"
    assert call_args.agent_role == "coder"

    # Verify resolve_cascades was called
    mock_library.resolve_cascades.assert_called_once()


@pytest.mark.asyncio
async def test_skill_loader_matched_triggers() -> None:
    """SkillLoaderAgent captures matched trigger types in LoadedSkillData."""
    from app.agents.custom.skill_loader import SkillLoaderAgent
    from app.models.enums import TriggerType
    from app.skills.library import TriggerSpec

    mock_library = MagicMock()
    entry = SkillEntry(
        name="api_skill",
        description="API skill",
        triggers=[TriggerSpec(trigger_type=TriggerType.DELIVERABLE_TYPE, value="api")],
    )
    mock_library.match.return_value = [entry]
    mock_library.resolve_cascades.return_value = [entry]
    mock_library.load.return_value = SkillContent(entry=entry, content="api content")

    agent = SkillLoaderAgent(name="skill_loader", skill_library=mock_library)
    ctx = make_ctx({"deliverable_type": "api"})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    delta = events[0].actions.state_delta
    skill_data = as_dict(delta["loaded_skills"])["api_skill"]
    assert isinstance(skill_data, dict)
    assert "DELIVERABLE_TYPE" in skill_data["matched_triggers"]


@pytest.mark.asyncio
async def test_skill_loader_cascade_resolution() -> None:
    """SkillLoaderAgent calls resolve_cascades and includes cascaded entries."""
    from app.agents.custom.skill_loader import SkillLoaderAgent

    mock_library = MagicMock()
    entry_a = SkillEntry(name="a_skill", description="A")
    entry_b = SkillEntry(name="b_skill", description="B (cascaded)")
    mock_library.match.return_value = [entry_a]
    mock_library.resolve_cascades.return_value = [entry_a, entry_b]

    def _load(entry: SkillEntry) -> SkillContent:
        return SkillContent(entry=entry, content=f"{entry.name} body")

    mock_library.load.side_effect = _load

    agent = SkillLoaderAgent(name="skill_loader", skill_library=mock_library)
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    delta = events[0].actions.state_delta
    assert delta["loaded_skill_names"] == ["a_skill", "b_skill"]
    skills = as_dict(delta["loaded_skills"])
    assert "a_skill" in skills
    assert "b_skill" in skills


# ---------------------------------------------------------------------------
# MemoryLoaderAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_loader_empty_service() -> None:
    """MemoryLoaderAgent with no service yields empty context, memory_loaded=true."""
    from app.agents.custom.memory_loader import MemoryLoaderAgent

    agent = MemoryLoaderAgent(name="memory_loader")
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["memory_context"] == {}
    assert delta["memory_loaded"] is True


@pytest.mark.asyncio
async def test_memory_loader_service_failure() -> None:
    """MemoryLoaderAgent on exception yields empty context, memory_loaded=false."""
    from app.agents.custom.memory_loader import MemoryLoaderAgent

    mock_service = MagicMock()
    mock_service.search_memory = AsyncMock(side_effect=RuntimeError("connection lost"))

    agent = MemoryLoaderAgent(name="memory_loader", memory_service=mock_service)
    ctx = make_ctx({"memory_query": "test query"})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["memory_context"] == {}
    assert delta["memory_loaded"] is False


# ---------------------------------------------------------------------------
# LinterAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linter_agent_success() -> None:
    """LinterAgent with exit 0 yields lint_passed=true."""
    from app.agents.custom.linter import LinterAgent

    agent = LinterAgent(name="linter")
    ctx = make_ctx({"project_linter_command": "ruff check .", "working_directory": "/tmp"})

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"All good\n", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["lint_passed"] is True
    assert as_dict(delta["lint_results"])["passed"] is True
    assert as_dict(delta["lint_results"])["exit_code"] == 0
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_linter_agent_failure() -> None:
    """LinterAgent with exit 1 yields lint_passed=false with findings."""
    from app.agents.custom.linter import LinterAgent

    agent = LinterAgent(name="linter")
    ctx = make_ctx()

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"file.py:1:1 E001 error\nfile.py:2:1 E002 error\n", b"")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    delta = events[0].actions.state_delta
    assert delta["lint_passed"] is False
    assert as_dict(delta["lint_results"])["passed"] is False
    assert len(cast("list[object]", as_dict(delta["lint_results"])["findings"])) == 2


# ---------------------------------------------------------------------------
# TestRunnerAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_runner_success() -> None:
    """TestRunnerAgent with exit 0 yields tests_passed=true."""
    from app.agents.custom.test_runner import TestRunnerAgent

    agent = TestRunnerAgent(name="tester")
    ctx = make_ctx({"project_test_command": "pytest -v"})

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"3 passed\n", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    delta = events[0].actions.state_delta
    assert delta["tests_passed"] is True
    assert as_dict(delta["test_results"])["passed"] is True


@pytest.mark.asyncio
async def test_test_runner_failure() -> None:
    """TestRunnerAgent with exit 1 yields tests_passed=false."""
    from app.agents.custom.test_runner import TestRunnerAgent

    agent = TestRunnerAgent(name="tester")
    ctx = make_ctx()

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"1 failed, 2 passed\n", b"")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    delta = events[0].actions.state_delta
    assert delta["tests_passed"] is False
    assert as_dict(delta["test_results"])["passed"] is False


# ---------------------------------------------------------------------------
# FormatterAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_formatter_agent() -> None:
    """FormatterAgent captures formatter results in state."""
    from app.agents.custom.formatter import FormatterAgent

    agent = FormatterAgent(name="formatter")
    ctx = make_ctx()

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"2 files reformatted\n", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    delta = events[0].actions.state_delta
    assert "formatter_results" in delta
    assert as_dict(delta["formatter_results"])["exit_code"] == 0
    assert as_dict(delta["formatter_results"])["command"] == "ruff format ."


# ---------------------------------------------------------------------------
# RegressionTestAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_tester_disabled() -> None:
    """RegressionTestAgent with disabled policy yields skipped result."""
    from app.agents.custom.regression_tester import RegressionTestAgent

    agent = RegressionTestAgent(name="regression_tester")
    ctx = make_ctx()  # No regression_policy → defaults to disabled

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert as_dict(delta["regression_results"])["skipped"] is True
    assert as_dict(delta["regression_results"])["reason"] == "disabled"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_all_agents_registered() -> None:
    """All 9 custom agents are registered in CLASS_REGISTRY after import."""
    import app.agents.custom  # noqa: F401  # type: ignore[reportUnusedImport]

    expected = {
        "SkillLoaderAgent",
        "MemoryLoaderAgent",
        "LinterAgent",
        "TestRunnerAgent",
        "FormatterAgent",
        "RegressionTestAgent",
        "DependencyResolverAgent",
        "DiagnosticsAgent",
        "ReviewCycleAgent",
    }
    assert expected.issubset(set(CLASS_REGISTRY.keys()))


# ---------------------------------------------------------------------------
# Definition files
# ---------------------------------------------------------------------------


def test_definition_files_parseable() -> None:
    """All 6 .md definition files parse correctly."""
    agents_dir = Path(__file__).resolve().parents[2] / "app" / "agents"

    definition_files = [
        "skill_loader.md",
        "memory_loader.md",
        "linter.md",
        "tester.md",
        "formatter.md",
        "regression_tester.md",
    ]

    for filename in definition_files:
        filepath = agents_dir / filename
        assert filepath.exists(), f"Definition file not found: {filepath}"
        entry = parse_definition_file(filepath, DefinitionScope.GLOBAL)
        assert entry.agent_type.value == "CUSTOM", f"{filename} should be type custom"
        assert entry.class_ref is not None, f"{filename} missing class field"
        assert entry.output_key is not None, f"{filename} missing output_key"
