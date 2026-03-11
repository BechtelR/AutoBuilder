"""Tests for ReviewCycleAgent — iterative review loop with state-driven termination."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

from app.agents.custom.review_cycle import (
    ReviewCycleAgent,
    _is_review_approved,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext


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


class _EmitterAgent(BaseAgent):
    """Stub agent that writes a state_delta value when run.

    Writes to both state_delta (for event) and ctx.session.state (simulating
    ADK's internal state application for subsequent reads).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state_key: str = ""
    state_value: object = None

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if self.state_key:
            ctx.session.state[self.state_key] = self.state_value
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={self.state_key: self.state_value}),
            )


class _NoopAgent(BaseAgent):
    """Stub agent that yields no events. Tracks call count."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    call_count: int = 0

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        self.call_count += 1
        return
        yield  # pragma: no cover


# ---------------------------------------------------------------------------
# _is_review_approved unit tests
# ---------------------------------------------------------------------------


class TestIsReviewApproved:
    def test_approved_signal(self) -> None:
        assert _is_review_approved("## Verdict: APPROVED\nLooks good.") is True

    def test_review_passed_signal(self) -> None:
        assert _is_review_approved("review_passed: yes") is True

    def test_passed_true_signal(self) -> None:
        assert _is_review_approved("passed: true") is True

    def test_verdict_approved_signal(self) -> None:
        assert _is_review_approved("verdict: approved") is True

    def test_changes_requested(self) -> None:
        assert _is_review_approved("CHANGES_REQUESTED: fix line 42") is False

    def test_empty_string(self) -> None:
        assert _is_review_approved("") is False

    def test_non_string_input(self) -> None:
        assert _is_review_approved(42) is False

    def test_none_input(self) -> None:
        assert _is_review_approved(None) is False

    def test_case_insensitive(self) -> None:
        assert _is_review_approved("approved") is True
        assert _is_review_approved("Approved") is True


# ---------------------------------------------------------------------------
# ReviewCycleAgent integration tests
#
# ReviewCycleAgent._run_async_impl calls sub_agent.run_async(ctx), which
# triggers ADK's full agent lifecycle (plugin manager, callbacks). To avoid
# needing a real InvocationContext, we monkeypatch run_async on sub-agents
# to call _run_async_impl directly.
# ---------------------------------------------------------------------------


def _patch_sub_agents_run_async(agent: ReviewCycleAgent) -> None:
    """Monkeypatch sub_agents so run_async delegates to _run_async_impl.

    This bypasses ADK lifecycle hooks (plugin_manager, callbacks) that
    require a real InvocationContext. Uses object.__setattr__ because
    Pydantic BaseAgent models reject normal attribute assignment.
    """
    for sub in agent.sub_agents:
        original_impl = sub._run_async_impl  # type: ignore[reportPrivateUsage]

        async def _patched_run_async(  # type: ignore[override]
            ctx: InvocationContext, _impl: object = original_impl
        ) -> AsyncGenerator[Event, None]:
            async for event in _impl(ctx):  # type: ignore[union-attr]
                yield event

        object.__setattr__(sub, "run_async", _patched_run_async)


@pytest.mark.asyncio
async def test_review_cycle_immediate_approval() -> None:
    """Reviewer approves on first pass, cycle terminates after 1 iteration."""
    reviewer = _EmitterAgent(
        name="reviewer", state_key="review_result", state_value="## Verdict: APPROVED"
    )
    fixer = _NoopAgent(name="fixer")
    linter = _NoopAgent(name="linter")
    tester = _NoopAgent(name="tester")

    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, linter, tester],
        max_iterations=3,
    )
    _patch_sub_agents_run_async(agent)
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    author_names = [e.author for e in events]
    assert "reviewer" in author_names
    assert "review_cycle" in author_names
    # After reviewer approves, the loop should return immediately --
    # fixer should NOT be called
    assert fixer.call_count == 0

    cycle_events = [e for e in events if e.author == "review_cycle"]
    assert len(cycle_events) == 1
    assert cycle_events[0].actions.state_delta["review_passed"] is True


@pytest.mark.asyncio
async def test_review_cycle_max_iterations_exhausted() -> None:
    """Reviewer never approves, cycle runs all iterations and marks exhausted."""
    reviewer = _EmitterAgent(
        name="reviewer",
        state_key="review_result",
        state_value="CHANGES_REQUESTED: fix line 42",
    )
    fixer = _NoopAgent(name="fixer")
    linter = _NoopAgent(name="linter")
    tester = _NoopAgent(name="tester")

    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, linter, tester],
        max_iterations=2,
    )
    _patch_sub_agents_run_async(agent)
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    reviewer_events = [e for e in events if e.author == "reviewer"]
    assert len(reviewer_events) == 2

    # Fixer, linter, tester each called twice (once per iteration)
    assert fixer.call_count == 2
    assert linter.call_count == 2
    assert tester.call_count == 2

    cycle_events = [e for e in events if e.author == "review_cycle"]
    last_cycle = cycle_events[-1]
    assert last_cycle.actions.state_delta["review_cycle_exhausted"] is True
    assert last_cycle.actions.state_delta["review_cycle_iterations"] == 2
    assert last_cycle.actions.state_delta["review_passed"] is False


@pytest.mark.asyncio
async def test_review_cycle_approval_on_second_pass() -> None:
    """Reviewer rejects first, approves second. Verifies iteration count."""
    call_count = 0

    class _ConditionalReviewer(BaseAgent):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        async def _run_async_impl(  # type: ignore[override]
            self, ctx: InvocationContext
        ) -> AsyncGenerator[Event, None]:
            nonlocal call_count
            call_count += 1
            result = "## Verdict: APPROVED" if call_count >= 2 else "CHANGES_REQUESTED: fix issue"
            ctx.session.state["review_result"] = result
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"review_result": result}),
            )

    reviewer = _ConditionalReviewer(name="reviewer")
    fixer = _NoopAgent(name="fixer")
    linter = _NoopAgent(name="linter")
    tester = _NoopAgent(name="tester")

    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, linter, tester],
        max_iterations=5,
    )
    _patch_sub_agents_run_async(agent)
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    reviewer_events = [e for e in events if e.author == "reviewer"]
    assert len(reviewer_events) == 2

    # Fixer/linter/tester run once in first iteration, not called in second
    # (reviewer approves on second pass, loop returns before reaching fixer)
    assert fixer.call_count == 1

    cycle_events = [e for e in events if e.author == "review_cycle"]
    last_cycle = cycle_events[-1]
    assert last_cycle.actions.state_delta["review_passed"] is True
    assert "review_cycle_exhausted" not in last_cycle.actions.state_delta


@pytest.mark.asyncio
async def test_review_cycle_state_writes_via_state_delta() -> None:
    """All ReviewCycleAgent state writes use state_delta, not direct assignment."""
    reviewer = _EmitterAgent(name="reviewer", state_key="review_result", state_value="APPROVED")
    fixer = _NoopAgent(name="fixer")
    linter = _NoopAgent(name="linter")
    tester = _NoopAgent(name="tester")

    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, linter, tester],
        max_iterations=1,
    )
    _patch_sub_agents_run_async(agent)
    ctx = make_ctx()

    events = await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    cycle_events = [e for e in events if e.author == "review_cycle"]
    for event in cycle_events:
        assert event.actions.state_delta is not None
        assert len(event.actions.state_delta) > 0


@pytest.mark.asyncio
async def test_review_cycle_runs_all_sub_agents_per_iteration() -> None:
    """When reviewer does not approve, all 4 sub-agents run in each iteration."""
    reviewer = _EmitterAgent(
        name="reviewer",
        state_key="review_result",
        state_value="CHANGES_REQUESTED",
    )
    fixer = _NoopAgent(name="fixer")
    linter = _NoopAgent(name="linter")
    tester = _NoopAgent(name="tester")

    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, linter, tester],
        max_iterations=1,
    )
    _patch_sub_agents_run_async(agent)
    ctx = make_ctx()

    await collect_events(agent._run_async_impl(ctx))  # type: ignore[reportPrivateUsage]

    assert fixer.call_count == 1
    assert linter.call_count == 1
    assert tester.call_count == 1


@pytest.mark.asyncio
async def test_review_cycle_default_max_iterations() -> None:
    """Default max_iterations is 3."""
    agent = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[],
    )
    assert agent.max_iterations == 3
