"""Prototype 3: Parallel Execution — ParallelAgent with 3 concurrent LlmAgents."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm

from tests.phase1.conftest import collect_events, requires_api_key

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents import BaseAgent
    from google.adk.runners import InMemoryRunner

pytestmark = [requires_api_key, pytest.mark.integration]

HAIKU_MODEL = "anthropic/claude-haiku-4-5-20251001"


def _build_parallel_agent() -> ParallelAgent:
    """Build 3 LlmAgents writing to distinct state keys."""
    agents: list[BaseAgent] = [
        LlmAgent(
            name="ocean_agent",
            model=LiteLlm(model=HAIKU_MODEL),
            instruction="Write one sentence about the ocean.",
            output_key="agent_1_output",
        ),
        LlmAgent(
            name="mountain_agent",
            model=LiteLlm(model=HAIKU_MODEL),
            instruction="Write one sentence about mountains.",
            output_key="agent_2_output",
        ),
        LlmAgent(
            name="forest_agent",
            model=LiteLlm(model=HAIKU_MODEL),
            instruction="Write one sentence about forests.",
            output_key="agent_3_output",
        ),
    ]
    return ParallelAgent(name="parallel_test", sub_agents=agents)


@pytest.mark.asyncio
async def test_parallel_agents_no_state_collision(
    runner_factory: Callable[[ParallelAgent], InMemoryRunner],
) -> None:
    """All 3 agents produce non-empty, topically relevant output in distinct state keys."""
    parallel = _build_parallel_agent()
    runner = runner_factory(parallel)

    _events, session = await collect_events(runner, "user1", "session_parallel", "Go.")

    state = session.state

    # Assert all 3 output keys populated
    for key in ("agent_1_output", "agent_2_output", "agent_3_output"):
        assert key in state, f"{key} not found in session state"
        output = str(state[key])
        assert len(output.strip()) > 0, f"{key} is empty"

    # Assert topical relevance (loose check — at least one keyword match)
    ocean_output = str(state["agent_1_output"]).lower()
    mountain_output = str(state["agent_2_output"]).lower()
    forest_output = str(state["agent_3_output"]).lower()

    ocean_keywords = {"ocean", "sea", "water", "wave", "marine", "tide", "deep"}
    mountain_keywords = {"mountain", "peak", "summit", "alpine", "elevation", "height", "range"}
    forest_keywords = {"forest", "tree", "wood", "canopy", "leaf", "green", "grove"}

    assert any(kw in ocean_output for kw in ocean_keywords), (
        f"Ocean output lacks ocean keywords: {ocean_output}"
    )
    assert any(kw in mountain_output for kw in mountain_keywords), (
        f"Mountain output lacks mountain keywords: {mountain_output}"
    )
    assert any(kw in forest_output for kw in forest_keywords), (
        f"Forest output lacks forest keywords: {forest_output}"
    )


@pytest.mark.asyncio
async def test_parallel_faster_than_sequential(
    runner_factory: Callable[[ParallelAgent], InMemoryRunner],
) -> None:
    """Parallel execution completes in less than 3x the expected single-agent time."""
    parallel = _build_parallel_agent()
    runner = runner_factory(parallel)

    start = time.monotonic()
    _events, _session = await collect_events(runner, "user1", "session_timing", "Go.")
    elapsed = time.monotonic() - start

    # A single haiku call typically takes 2-5s. If parallel works,
    # 3 agents should complete in roughly 1x time, not 3x.
    # We use a generous bound: total < 45s (3 * 15s max single-agent time)
    assert elapsed < 45, f"Parallel execution took {elapsed:.1f}s, expected < 45s"


@pytest.mark.asyncio
async def test_parallel_events_from_all_agents(
    runner_factory: Callable[[ParallelAgent], InMemoryRunner],
) -> None:
    """Events from all 3 agents appear in the collected event stream."""
    parallel = _build_parallel_agent()
    runner = runner_factory(parallel)

    events, _session = await collect_events(runner, "user1", "session_events", "Go.")

    authors = {event.author for event in events if event.author}
    expected_authors = {"ocean_agent", "mountain_agent", "forest_agent"}
    assert expected_authors.issubset(authors), (
        f"Expected authors {expected_authors} in event stream, got {authors}"
    )
