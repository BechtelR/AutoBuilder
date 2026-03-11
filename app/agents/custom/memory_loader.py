"""MemoryLoaderAgent — loads cross-session memory into session state."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)


class MemoryLoaderAgent(BaseAgent):
    """Deterministic agent that loads memory context into session state.

    Graceful degradation: NEVER raises. On any failure, writes empty context
    with memory_loaded=false.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory_service: object = None

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        query = state.get("memory_query", "")

        memory_context: dict[str, object] = {}
        memory_loaded = False

        try:
            if self.memory_service is not None and hasattr(self.memory_service, "search_memory"):
                search_fn = self.memory_service.search_memory  # type: ignore[union-attr]
                result: object = await search_fn(query)  # type: ignore[reportUnknownVariableType]
                if isinstance(result, dict):
                    memory_context = cast("dict[str, object]", result)
                memory_loaded = True
            else:
                # No service or no search method — still success with empty context
                memory_loaded = True
        except Exception:
            logger.warning(
                "MemoryLoader failed to load memory, degrading gracefully",
                exc_info=True,
            )
            memory_context = dict[str, object]()
            memory_loaded = False

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "memory_context": memory_context,
                    "memory_loaded": memory_loaded,
                }
            ),
        )
