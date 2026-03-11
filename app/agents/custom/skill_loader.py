"""SkillLoaderAgent — loads matched skills into session state."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

from app.agents.protocols import NullSkillLibrary, SkillMatchContext

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)


class SkillLoaderAgent(BaseAgent):
    """Deterministic agent that loads matched skills into session state."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    skill_library: object = NullSkillLibrary()

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        from app.agents.protocols import SkillLibraryProtocol

        state = ctx.session.state
        library = cast("SkillLibraryProtocol", self.skill_library)

        # Build match context from session state
        match_context = SkillMatchContext(
            deliverable_type=state.get("deliverable_type"),  # type: ignore[arg-type]
            file_patterns=state.get("file_patterns", []),  # type: ignore[arg-type]
            tags=state.get("tags", []),  # type: ignore[arg-type]
            agent_role=state.get("agent_role"),  # type: ignore[arg-type]
        )

        entries = library.match(match_context)

        loaded_skills: dict[str, str] = {}
        loaded_skill_names: list[str] = []

        for entry in entries:
            content = library.load(entry)
            loaded_skills[entry.name] = content.content
            loaded_skill_names.append(entry.name)

        logger.debug(
            "SkillLoader loaded %d skills: %s", len(loaded_skill_names), loaded_skill_names
        )

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "loaded_skills": loaded_skills,
                    "loaded_skill_names": loaded_skill_names,
                }
            ),
        )
