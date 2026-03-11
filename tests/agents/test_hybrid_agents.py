"""Tests for hybrid custom agents (DependencyResolverAgent, DiagnosticsAgent)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.events import Event

from app.agents._registry import CLASS_REGISTRY, parse_definition_file
from app.models.enums import DefinitionScope

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


def as_list(val: object) -> list[object]:
    """Cast a state_delta value to list for length/index access."""
    return cast("list[object]", val)


def make_llm_response(content: str) -> MagicMock:
    """Create a mock litellm acompletion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# DependencyResolverAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_resolver_empty() -> None:
    """Empty deliverables yields empty order."""
    from app.agents.custom.dependency_resolver import DependencyResolverAgent

    agent = DependencyResolverAgent(name="dep_resolver")
    ctx = make_ctx({"deliverables": []})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["dependency_order"] == []
    assert "No deliverables" in str(delta["dependency_analysis"])


@pytest.mark.asyncio
async def test_dependency_resolver_single() -> None:
    """Single deliverable returned as-is."""
    from app.agents.custom.dependency_resolver import DependencyResolverAgent

    agent = DependencyResolverAgent(name="dep_resolver")
    ctx = make_ctx({"deliverables": ["auth-service"]})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["dependency_order"] == ["auth-service"]
    assert "Single deliverable" in str(delta["dependency_analysis"])


@pytest.mark.asyncio
async def test_dependency_resolver_topological_sort() -> None:
    """Explicit deps produce correct topological order without LLM."""
    from app.agents.custom.dependency_resolver import DependencyResolverAgent

    agent = DependencyResolverAgent(name="dep_resolver")
    deliverables: list[dict[str, object]] = [
        {"name": "api", "depends_on": ["models"]},
        {"name": "models", "depends_on": []},
        {"name": "frontend", "depends_on": ["api"]},
    ]
    ctx = make_ctx({"deliverables": deliverables})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    order = delta["dependency_order"]
    assert order == ["models", "api", "frontend"]
    assert delta["dependency_analysis"] == "Topological sort applied"


@pytest.mark.asyncio
async def test_dependency_resolver_llm_fallback() -> None:
    """Cycle detected triggers LLM classification (mocked)."""
    from app.agents.custom.dependency_resolver import DependencyResolverAgent

    agent = DependencyResolverAgent(name="dep_resolver", model_role="fast")
    # Create a cycle: A->B, B->A
    deliverables = [
        {"name": "A", "depends_on": ["B"]},
        {"name": "B", "depends_on": ["A"]},
    ]
    ctx = make_ctx({"deliverables": deliverables})

    mock_response = make_llm_response(json.dumps(["A", "B"]))

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch.object(
            DependencyResolverAgent,
            "_get_settings",
            return_value=MagicMock(
                default_code_model="test-model",
                default_plan_model="test-model",
                default_review_model="test-model",
                default_fast_model="test-model",
            ),
        ),
    ):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert delta["dependency_order"] == ["A", "B"]
    assert "LLM-assisted" in str(delta["dependency_analysis"])


# ---------------------------------------------------------------------------
# DiagnosticsAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostics_clean() -> None:
    """All passing yields clean status, no analysis."""
    from app.agents.custom.diagnostics import DiagnosticsAgent

    agent = DiagnosticsAgent(name="diagnostics")
    ctx = make_ctx({"lint_passed": True, "tests_passed": True})

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    analysis = as_dict(delta["diagnostics_analysis"])
    assert analysis["status"] == "clean"
    assert analysis["issues"] == []
    assert analysis["root_causes"] == []


@pytest.mark.asyncio
async def test_diagnostics_with_issues() -> None:
    """Lint + test failures are aggregated into issues list.

    Uses the actual data format from LinterAgent (string findings) and
    TestRunnerAgent (output field, not failures).
    """
    from app.agents.custom.diagnostics import DiagnosticsAgent

    agent = DiagnosticsAgent(name="diagnostics")
    ctx = make_ctx(
        {
            "lint_passed": False,
            "lint_results": {
                "findings": ["main.py:1: unused import 'os'"],
            },
            "tests_passed": False,
            "test_results": {
                "output": "FAILED test_foo - AssertionError\n1 failed",
            },
        }
    )

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    analysis = as_dict(delta["diagnostics_analysis"])
    assert analysis["status"] == "issues_found"
    assert analysis["issue_count"] == 2
    issues = as_list(analysis["issues"])
    assert len(issues) == 2
    assert as_dict(issues[0])["source"] == "linter"
    assert as_dict(issues[1])["source"] == "test"


@pytest.mark.asyncio
async def test_diagnostics_llm_analysis() -> None:
    """Issues + model_role triggers LLM root-cause analysis (mocked)."""
    from app.agents.custom.diagnostics import DiagnosticsAgent

    agent = DiagnosticsAgent(name="diagnostics", model_role="fast")
    ctx = make_ctx(
        {
            "lint_passed": False,
            "lint_results": {
                "findings": [{"file": "main.py", "msg": "missing import"}],
            },
            "tests_passed": True,
        }
    )

    llm_result = json.dumps(
        {
            "root_causes": ["Missing import of 'os' module"],
            "recommendations": ["Add 'import os' to main.py"],
        }
    )
    mock_response = make_llm_response(llm_result)

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch.object(
            DiagnosticsAgent,
            "_get_settings",
            return_value=MagicMock(
                default_code_model="test-model",
                default_plan_model="test-model",
                default_review_model="test-model",
                default_fast_model="test-model",
            ),
        ),
    ):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    assert len(events) == 1
    delta = events[0].actions.state_delta
    analysis = as_dict(delta["diagnostics_analysis"])
    assert analysis["status"] == "issues_found"
    root_causes = as_list(analysis["root_causes"])
    assert len(root_causes) == 1
    assert "Missing import" in str(root_causes[0])
    assert len(as_list(analysis["recommendations"])) == 1


@pytest.mark.asyncio
async def test_diagnostics_llm_failure_graceful() -> None:
    """LLM failure yields empty root_causes, no exception raised."""
    from app.agents.custom.diagnostics import DiagnosticsAgent

    agent = DiagnosticsAgent(name="diagnostics", model_role="fast")
    ctx = make_ctx(
        {
            "lint_passed": False,
            "lint_results": {
                "findings": [{"file": "x.py", "msg": "error"}],
            },
            "tests_passed": True,
        }
    )

    with (
        patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ),
        patch.object(
            DiagnosticsAgent,
            "_get_settings",
            return_value=MagicMock(
                default_code_model="test-model",
                default_plan_model="test-model",
                default_review_model="test-model",
                default_fast_model="test-model",
            ),
        ),
    ):
        events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    assert len(events) == 1
    delta = events[0].actions.state_delta
    analysis = as_dict(delta["diagnostics_analysis"])
    assert analysis["status"] == "issues_found"
    assert analysis["root_causes"] == []
    assert analysis["recommendations"] == []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_both_registered() -> None:
    """DependencyResolverAgent and DiagnosticsAgent in CLASS_REGISTRY."""
    import app.agents.custom  # noqa: F401  # type: ignore[reportUnusedImport]

    assert "DependencyResolverAgent" in CLASS_REGISTRY
    assert "DiagnosticsAgent" in CLASS_REGISTRY


# ---------------------------------------------------------------------------
# Definition files
# ---------------------------------------------------------------------------


def test_definition_files_parseable() -> None:
    """Both .md definition files parse correctly."""
    agents_dir = Path(__file__).resolve().parents[2] / "app" / "agents"

    for filename in ("dependency_resolver.md", "diagnostics.md"):
        filepath = agents_dir / filename
        assert filepath.exists(), f"Definition file not found: {filepath}"
        entry = parse_definition_file(filepath, DefinitionScope.GLOBAL)
        assert entry.agent_type.value == "CUSTOM", f"{filename} should be type custom"
        assert entry.class_ref is not None, f"{filename} missing class field"
        assert entry.output_key is not None, f"{filename} missing output_key"
        assert entry.model_role == "fast", f"{filename} should have model_role fast"
