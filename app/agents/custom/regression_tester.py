"""RegressionTestAgent — runs cross-deliverable regression tests."""

from __future__ import annotations

import asyncio
import logging
import shlex
from typing import TYPE_CHECKING, cast

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)

_DEFAULT_WORKING_DIR = "."


class RegressionTestAgent(BaseAgent):
    """Deterministic agent that runs regression tests if enabled by policy."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        raw_policy = state.get("regression_policy")
        policy: dict[str, object] = (
            cast("dict[str, object]", raw_policy)
            if isinstance(raw_policy, dict)
            else {"enabled": False}
        )

        enabled = bool(policy.get("enabled", False))

        if not enabled:
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={
                        "regression_results": {"skipped": True, "reason": "disabled"},
                    }
                ),
            )
            return

        # Regression testing enabled — run the command
        raw_cmd = policy.get("command")
        command = str(raw_cmd) if raw_cmd is not None else "pytest --tb=short"
        working_dir = str(state.get("working_directory", _DEFAULT_WORKING_DIR))

        args = shlex.split(command)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0
        except Exception as exc:
            logger.warning("RegressionTestAgent failed to run command: %s", exc)
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        regression_passed = exit_code == 0

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "regression_results": {
                        "skipped": False,
                        "passed": regression_passed,
                        "exit_code": exit_code,
                        "output": stdout + stderr,
                        "command": command,
                    },
                }
            ),
        )
