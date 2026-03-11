"""ReviewCycleAgent — iterative review loop with state-driven termination.

ADK's LoopAgent only terminates on event.actions.escalate, which LlmAgents
cannot produce. This CustomAgent implements the review loop directly, checking
review_result in session state after each reviewer pass (spec DD-6 alternative).

The reviewer LlmAgent writes to output_key="review_result". This agent parses
that text for an approval signal, writes the boolean review_passed to state,
and decides whether to continue the loop.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)

# Signals the reviewer LLM is instructed to include (see reviewer.md)
_APPROVAL_SIGNALS = ("APPROVED", "review_passed", "passed: true", "verdict: approved")


def _is_review_approved(review_result: object) -> bool:
    """Detect approval from the reviewer's output text."""
    if not isinstance(review_result, str):
        return False
    upper = review_result.upper()
    return any(signal.upper() in upper for signal in _APPROVAL_SIGNALS)


class ReviewCycleAgent(BaseAgent):
    """CustomAgent that loops reviewer -> fixer -> linter -> tester.

    Terminates when:
    - reviewer's review_result indicates approval, OR
    - max_iterations reached (deliverable marked failed).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    max_iterations: int = 3

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        for iteration in range(1, self.max_iterations + 1):
            logger.info("ReviewCycle iteration %d/%d", iteration, self.max_iterations)

            # Run each sub-agent in sequence
            for sub_agent in self.sub_agents:
                async for event in sub_agent.run_async(ctx):
                    yield event

                # Check for early termination after reviewer runs
                if sub_agent.name.startswith("reviewer"):
                    review_result = ctx.session.state.get("review_result")
                    approved = _is_review_approved(review_result)

                    # Write the parsed boolean to state for downstream consumers
                    yield Event(
                        author=self.name,
                        actions=EventActions(
                            state_delta={"review_passed": approved},
                        ),
                    )

                    if approved:
                        logger.info("ReviewCycle: reviewer approved at iteration %d", iteration)
                        return

        # Max iterations exhausted without approval
        logger.warning("ReviewCycle exhausted %d iterations without approval", self.max_iterations)
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "review_cycle_exhausted": True,
                    "review_cycle_iterations": self.max_iterations,
                    "review_passed": False,
                }
            ),
        )
