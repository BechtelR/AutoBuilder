"""Hybrid agent: deterministic topological sort + LLM for ambiguous deps."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, cast

import litellm
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

    from app.config.settings import Settings

logger = logging.getLogger(__name__)


class DependencyResolverAgent(BaseAgent):
    """Hybrid: topological sort + LiteLLM for ambiguous dependency resolution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    model_role: str | None = None
    instruction_body: str | None = None

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Resolve deliverable dependencies via toposort, LLM fallback for cycles."""
        raw = ctx.session.state.get("deliverables", [])
        deliverables = cast("list[object]", raw) if isinstance(raw, list) else []

        if len(deliverables) <= 1:
            analysis = "No deliverables to resolve" if not deliverables else "Single deliverable"
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={"dependency_order": deliverables, "dependency_analysis": analysis},
                ),
            )
            return

        dep_graph: dict[str, list[str]] = {}
        names: list[str] = []
        for d in deliverables:
            if isinstance(d, dict):
                d_typed = cast("dict[str, object]", d)
                name = str(d_typed.get("name", ""))
                raw_deps = d_typed.get("depends_on", [])
                if isinstance(raw_deps, list):
                    dep_graph[name] = [str(x) for x in cast("list[object]", raw_deps)]
                else:
                    dep_graph[name] = []
                names.append(name)
            else:
                names.append(str(d))
                dep_graph[str(d)] = []

        order = self._topological_sort(names, dep_graph)
        analysis = "Topological sort applied"
        if order is None and self.model_role:
            order, analysis = await self._llm_classify(names, dep_graph)
        elif order is None:
            order, analysis = names, "Could not resolve dependencies, using original order"

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"dependency_order": order, "dependency_analysis": analysis},
            ),
        )

    def _topological_sort(self, names: list[str], graph: dict[str, list[str]]) -> list[str] | None:
        """Kahn's algorithm. Returns None if cycle detected."""
        name_set = set(names)
        in_deg: dict[str, int] = {
            n: len([d for d in graph.get(n, []) if d in name_set]) for n in names
        }
        queue = sorted(n for n in names if in_deg[n] == 0)
        result: list[str] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for name in names:
                if node in graph.get(name, []) and name not in result and name not in queue:
                    in_deg[name] -= 1
                    if in_deg[name] == 0:
                        queue.append(name)
                        queue.sort()
        return result if len(result) == len(names) else None

    async def _llm_classify(
        self, names: list[str], graph: dict[str, list[str]]
    ) -> tuple[list[str], str]:
        """Use LLM to classify ambiguous dependency relationships."""
        try:
            from app.models.enums import ModelRole
            from app.router.router import LlmRouter

            router = LlmRouter.from_settings(self._get_settings())
            role = ModelRole(self.model_role.upper()) if self.model_role else ModelRole.FAST
            prompt = self.instruction_body or (
                "You are a dependency analyzer. Determine optimal execution order."
            )
            user_msg = (
                f"Deliverables: {json.dumps(names)}\n"
                f"Known dependencies: {json.dumps(graph)}\n"
                "A cycle was detected. Return a JSON array of names in execution order."
            )
            response = await litellm.acompletion(  # type: ignore[reportUnknownMemberType]
                model=router.select_model(role),
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            content = str(
                response.choices[0].message.content  # type: ignore[reportUnknownMemberType]
                or ""
            )
            try:
                order = json.loads(content)
                if isinstance(order, list):
                    return [str(x) for x in cast("list[object]", order)], "LLM-assisted resolution"
            except json.JSONDecodeError:
                pass
            return names, f"LLM response unparseable, using original order: {content[:200]}"
        except Exception as e:
            logger.warning("LLM dependency classification failed: %s", e)
            return names, f"LLM classification failed: {e}, using original order"

    @staticmethod
    def _get_settings() -> Settings:
        """Get application settings (isolated for testability)."""
        from app.config.settings import get_settings

        return get_settings()
