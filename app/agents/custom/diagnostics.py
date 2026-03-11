"""Hybrid agent: deterministic aggregation + LLM for root-cause analysis."""

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


class DiagnosticsAgent(BaseAgent):
    """Hybrid: aggregates lint/test results + LiteLLM for root-cause analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    model_role: str | None = None
    instruction_body: str | None = None

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Read lint + test results, aggregate, optionally use LLM for analysis."""
        state = ctx.session.state
        lint_results, test_results = state.get("lint_results", {}), state.get("test_results", {})
        lint_passed, tests_passed = state.get("lint_passed", True), state.get("tests_passed", True)

        issues: list[dict[str, object]] = []
        if isinstance(lint_results, dict) and not lint_passed:
            lr = cast("dict[str, object]", lint_results)
            raw = lr.get("findings", [])
            if isinstance(raw, list):
                for f in cast("list[object]", raw):
                    if isinstance(f, str):
                        issues.append({"source": "linter", "message": f})
                    elif isinstance(f, dict):
                        issues.append({"source": "linter", **cast("dict[str, object]", f)})
        if isinstance(test_results, dict) and not tests_passed:
            tr = cast("dict[str, object]", test_results)
            # TestRunnerAgent writes "output" (combined stdout+stderr), not "failures"
            output = tr.get("output", "")
            if isinstance(output, str) and output.strip():
                issues.append({"source": "test", "output": output})

        if not issues:
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={
                        "diagnostics_analysis": {
                            "status": "clean",
                            "issues": [],
                            "root_causes": [],
                            "recommendations": [],
                        },
                    }
                ),
            )
            return

        root_causes: list[str] = []
        recommendations: list[str] = []
        if self.model_role:
            root_causes, recommendations = await self._llm_analyze(issues)

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "diagnostics_analysis": {
                        "status": "issues_found",
                        "issue_count": len(issues),
                        "issues": issues,
                        "root_causes": root_causes,
                        "recommendations": recommendations,
                    },
                }
            ),
        )

    async def _llm_analyze(self, issues: list[dict[str, object]]) -> tuple[list[str], list[str]]:
        """Use LLM for root-cause analysis of aggregated issues."""
        try:
            from app.models.enums import ModelRole
            from app.router.router import LlmRouter

            router = LlmRouter.from_settings(self._get_settings())
            role = ModelRole(self.model_role.upper()) if self.model_role else ModelRole.FAST
            prompt = self.instruction_body or (
                "You are a code diagnostics expert. Identify root causes and recommendations."
            )
            user_msg = (
                f"Analyze these issues. Return JSON: "
                f'{{"root_causes": [...], "recommendations": [...]}}\n\n'
                f"Issues:\n{json.dumps(issues, indent=2, default=str)}"
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
                or "{}"
            )
            try:
                parsed: object = json.loads(content)
                if isinstance(parsed, dict):
                    p = cast("dict[str, object]", parsed)
                    rc, rec = p.get("root_causes", []), p.get("recommendations", [])
                    return (
                        [str(x) for x in cast("list[object]", rc)] if isinstance(rc, list) else [],
                        [str(x) for x in cast("list[object]", rec)]
                        if isinstance(rec, list)
                        else [],
                    )
            except json.JSONDecodeError:
                pass
            return [], []
        except Exception as e:
            logger.warning("LLM diagnostics analysis failed: %s", e)
            return [], []

    @staticmethod
    def _get_settings() -> Settings:
        """Get application settings (isolated for testability)."""
        from app.config.settings import get_settings

        return get_settings()
