"""FormatterAgent — runs code formatter on project files."""

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

_DEFAULT_COMMAND = "ruff format ."
_DEFAULT_WORKING_DIR = "."


class FormatterAgent(BaseAgent):
    """Deterministic agent that runs a code formatter subprocess."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        command = str(state.get("project_formatter_command", _DEFAULT_COMMAND))
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
            logger.warning("FormatterAgent failed to run command: %s", exc)
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        # Count changed files from output (heuristic: non-empty lines in stdout)
        changed_lines = [line for line in stdout.splitlines() if line.strip()]
        files_changed = len(changed_lines)

        formatter_results: dict[str, object] = {
            "exit_code": exit_code,
            "files_changed": files_changed,
            "summary": stdout.strip() if stdout.strip() else "No changes",
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
        }

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "formatter_results": formatter_results,
                }
            ),
        )
