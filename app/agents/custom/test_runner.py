"""TestRunnerAgent — runs project test suite and produces structured results."""

from __future__ import annotations

import asyncio
import logging
import shlex
from typing import TYPE_CHECKING

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)

_DEFAULT_COMMAND = "pytest"
_DEFAULT_WORKING_DIR = "."


class TestRunnerAgent(BaseAgent):
    """Deterministic agent that runs tests via subprocess and captures results."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        command = str(state.get("project_test_command", _DEFAULT_COMMAND))
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
            logger.warning("TestRunnerAgent failed to run command: %s", exc)
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        tests_passed = exit_code == 0

        test_results: dict[str, object] = {
            "passed": tests_passed,
            "exit_code": exit_code,
            "output": stdout + stderr,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
        }

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "test_results": test_results,
                    "tests_passed": tests_passed,
                }
            ),
        )
