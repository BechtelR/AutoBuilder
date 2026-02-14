"""Prototype 4: Dynamic Outer Loop — CustomAgent orchestrator with ParallelAgent batches."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.events import Event, EventActions
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from tests.phase1.conftest import collect_events, requires_api_key

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.runners import InMemoryRunner

pytestmark = [requires_api_key, pytest.mark.integration]

HAIKU_MODEL = "anthropic/claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Feature(BaseModel):
    """A feature with dependency tracking."""

    name: str
    depends_on: list[str] = Field(default_factory=list)
    prompt: str


# ---------------------------------------------------------------------------
# Agent factories
# ---------------------------------------------------------------------------


def create_feature_agent(feature: Feature) -> LlmAgent:
    """Create an LlmAgent for a single feature."""
    return LlmAgent(
        name=f"feature_{feature.name}_agent",
        model=LiteLlm(model=HAIKU_MODEL),
        instruction=feature.prompt,
        output_key=f"feature_{feature.name}_output",
    )


# ---------------------------------------------------------------------------
# BatchOrchestrator
# ---------------------------------------------------------------------------


class BatchOrchestrator(BaseAgent):
    """Custom agent that orchestrates features in dependency-ordered batches.

    Dynamically constructs ParallelAgent batches based on the feature DAG.
    Runs a while-loop until all features are completed or no progress is made.
    """

    features: list[Feature] = Field(default_factory=lambda: list[Feature]())

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute features in dependency-ordered parallel batches."""
        completed: set[str] = set()
        batch_num = 0

        while len(completed) < len(self.features):
            ready = [
                f
                for f in self.features
                if f.name not in completed and all(d in completed for d in f.depends_on)
            ]
            if not ready:
                break

            batch_num += 1
            batch_names = sorted([f.name for f in ready])

            yield Event(
                author=self.name,
                actions=EventActions(state_delta={f"batch_{batch_num}_features": batch_names}),
            )

            sub_agents: list[BaseAgent] = [create_feature_agent(f) for f in ready]
            parallel = ParallelAgent(
                name=f"batch_{batch_num}",
                sub_agents=sub_agents,
            )

            async for event in parallel.run_async(ctx):
                yield event

            for f in ready:
                output_key = f"feature_{f.name}_output"
                if ctx.session.state.get(output_key):
                    completed.add(f.name)

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "all_completed": len(completed) == len(self.features),
                    "completed_features": sorted(completed),
                    "total_batches": batch_num,
                }
            ),
        )


# ---------------------------------------------------------------------------
# Test DAG
# ---------------------------------------------------------------------------

FEATURE_DAG = [
    Feature(name="A", depends_on=[], prompt="Write one sentence about apples."),
    Feature(name="B", depends_on=[], prompt="Write one sentence about bananas."),
    Feature(name="C", depends_on=["A"], prompt="Write one sentence about cherries."),
    Feature(name="D", depends_on=["A"], prompt="Write one sentence about dates."),
    Feature(name="E", depends_on=["C", "D"], prompt="Write one sentence about elderberries."),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_features_execute_in_dependency_order(
    runner_factory: Callable[[BatchOrchestrator], InMemoryRunner],
) -> None:
    """Features execute in correct dependency order across 3 batches."""
    orchestrator = BatchOrchestrator(
        name="orchestrator",
        features=FEATURE_DAG,
    )
    runner = runner_factory(orchestrator)

    _events, session = await collect_events(runner, "user1", "session_dag", "Start.")

    state = session.state

    # Batch 1: A and B (no deps)
    batch_1 = state.get("batch_1_features")
    assert batch_1 is not None, "batch_1_features not found"
    assert set(batch_1) == {"A", "B"}, f"Batch 1 should be A,B, got {batch_1}"

    # Batch 2: C and D (depend on A)
    batch_2 = state.get("batch_2_features")
    assert batch_2 is not None, "batch_2_features not found"
    assert set(batch_2) == {"C", "D"}, f"Batch 2 should be C,D, got {batch_2}"

    # Batch 3: E (depends on C,D)
    batch_3 = state.get("batch_3_features")
    assert batch_3 is not None, "batch_3_features not found"
    assert set(batch_3) == {"E"}, f"Batch 3 should be E, got {batch_3}"

    # Assert all 5 feature outputs in state
    for name in ("A", "B", "C", "D", "E"):
        output_key = f"feature_{name}_output"
        assert output_key in state, f"{output_key} not in state"
        assert str(state[output_key]).strip(), f"{output_key} is empty"


@pytest.mark.asyncio
async def test_loop_terminates_on_completion(
    runner_factory: Callable[[BatchOrchestrator], InMemoryRunner],
) -> None:
    """Orchestrator sets completion state after all features finish."""
    orchestrator = BatchOrchestrator(
        name="orchestrator",
        features=FEATURE_DAG,
    )
    runner = runner_factory(orchestrator)

    _events, session = await collect_events(runner, "user1", "session_complete", "Start.")

    state = session.state

    assert state.get("all_completed") is True, f"all_completed is {state.get('all_completed')}"
    assert state.get("total_batches") == 3, f"total_batches is {state.get('total_batches')}"

    completed = state.get("completed_features")
    assert completed is not None, "completed_features not found"
    assert set(completed) == {"A", "B", "C", "D", "E"}, f"completed: {completed}"


@pytest.mark.asyncio
async def test_independent_features_not_blocked_by_unrelated_deps(
    runner_factory: Callable[[BatchOrchestrator], InMemoryRunner],
) -> None:
    """C and D depend only on A, so B's completion status is irrelevant to them.

    This validates the dependency DAG: features with satisfied deps run regardless
    of sibling feature status in the same or prior batches.
    """
    # DAG: A,B independent → C,D depend on A only → E depends on C,D
    # Even though B runs in batch 1 alongside A, C and D only need A.
    features = [
        Feature(name="A", depends_on=[], prompt="Write one sentence about apples."),
        Feature(name="B", depends_on=[], prompt="Write one sentence about bananas."),
        Feature(name="C", depends_on=["A"], prompt="Write one sentence about cherries."),
        Feature(name="D", depends_on=["A"], prompt="Write one sentence about dates."),
        Feature(name="E", depends_on=["C", "D"], prompt="Write one sentence about elderberries."),
    ]

    orchestrator = BatchOrchestrator(
        name="orchestrator",
        features=features,
    )
    runner = runner_factory(orchestrator)

    _events, session = await collect_events(runner, "user1", "session_deps", "Start.")

    state = session.state

    # A completes in batch 1
    assert state.get("feature_A_output"), "Feature A should have output"

    # C and D depend only on A — verify they ran in batch 2
    assert state.get("feature_C_output"), "Feature C should run (depends on A only)"
    assert state.get("feature_D_output"), "Feature D should run (depends on A only)"

    # Verify batch structure confirms C,D are in batch 2 (not blocked by B)
    batch_2 = state.get("batch_2_features")
    assert batch_2 is not None, "batch_2_features not found"
    assert "C" in batch_2, "C should be in batch 2"
    assert "D" in batch_2, "D should be in batch 2"

    # E depends on C,D — should be in batch 3
    assert state.get("feature_E_output"), "Feature E should run (C and D completed)"
