"""Prototype 2: Mixed Agent Coordination — LlmAgent + CustomAgent in SequentialAgent."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.models.lite_llm import LiteLlm

from tests.phase1.conftest import collect_events, requires_api_key

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.runners import InMemoryRunner

pytestmark = [requires_api_key, pytest.mark.integration]

SONNET_MODEL = "anthropic/claude-sonnet-4-5-20250929"


class LinterAgent(BaseAgent):
    """Deterministic agent that validates plan output from session state."""

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Read plan_output from state, validate, and write lint results."""
        plan: str = str(ctx.session.state.get("plan_output", ""))
        has_steps = len(plan.strip()) > 0

        delta: dict[str, object] = {
            "lint_results": f"Plan length: {len(plan)} chars, has content: {has_steps}",
            "lint_passed": has_steps,
        }
        yield Event(
            author=self.name,
            actions=EventActions(state_delta=delta),
        )


def _build_pipeline() -> SequentialAgent:
    """Build the plan_agent -> linter_agent sequential pipeline."""
    plan_agent = LlmAgent(
        model=LiteLlm(model=SONNET_MODEL),
        name="plan_agent",
        instruction="Write a brief 3-step plan for making a sandwich. Be concise.",
        output_key="plan_output",
    )

    linter_agent = LinterAgent(name="linter_agent")

    return SequentialAgent(
        name="pipeline",
        sub_agents=[plan_agent, linter_agent],
    )


@pytest.mark.asyncio
async def test_sequential_llm_plus_custom_agent(
    runner_factory: Callable[[SequentialAgent], InMemoryRunner],
) -> None:
    """LlmAgent writes to state via output_key; CustomAgent reads and validates."""
    pipeline = _build_pipeline()
    runner = runner_factory(pipeline)

    events, session = await collect_events(
        runner, "user1", "session_mixed", "Make me a sandwich plan."
    )

    state = session.state

    # Assert plan_output written by LlmAgent
    assert "plan_output" in state, "plan_output not found in session state"
    plan_output = str(state["plan_output"])
    assert len(plan_output.strip()) > 0, "plan_output is empty"

    # Assert lint results written by LinterAgent
    assert "lint_results" in state, "lint_results not found in session state"
    assert state.get("lint_passed") is True, f"lint_passed is {state.get('lint_passed')}"

    # Assert events from both agent types
    authors = {event.author for event in events if event.author}
    assert "plan_agent" in authors, f"plan_agent not in event authors: {authors}"
    assert "linter_agent" in authors, f"linter_agent not in event authors: {authors}"


@pytest.mark.asyncio
async def test_custom_agent_events_in_unified_stream(
    runner_factory: Callable[[SequentialAgent], InMemoryRunner],
) -> None:
    """Event stream contains events from both LLM and deterministic agents in order."""
    pipeline = _build_pipeline()
    runner = runner_factory(pipeline)

    events, _session = await collect_events(
        runner, "user1", "session_stream", "Make me a sandwich plan."
    )

    # Collect events by author
    plan_events = [e for e in events if e.author == "plan_agent"]
    linter_events = [e for e in events if e.author == "linter_agent"]

    assert len(plan_events) > 0, "No events from plan_agent"
    assert len(linter_events) > 0, "No events from linter_agent"

    # Verify ordering: first plan_agent event should appear before first linter_agent event
    first_plan_idx = next(i for i, e in enumerate(events) if e.author == "plan_agent")
    first_linter_idx = next(i for i, e in enumerate(events) if e.author == "linter_agent")
    assert first_plan_idx < first_linter_idx, (
        f"plan_agent events (idx={first_plan_idx}) should precede "
        f"linter_agent events (idx={first_linter_idx})"
    )
