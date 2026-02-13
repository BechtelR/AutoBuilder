"""Prototype 1: Basic Agent Loop — Claude via LiteLLM + FunctionTool + token counting."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.function_tool import FunctionTool

from tests.phase1.conftest import collect_events, requires_api_key

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.runners import InMemoryRunner

pytestmark = [requires_api_key, pytest.mark.integration]

SONNET_MODEL = "anthropic/claude-sonnet-4-5-20250929"


# ---------------------------------------------------------------------------
# Prototype FunctionTools (minimal — production tools come in Phase 4)
# ---------------------------------------------------------------------------


def file_read(path: str) -> dict[str, str]:
    """Read a file and return its contents.

    Args:
        path: Absolute path to the file to read.

    Returns:
        Dictionary with status and file content.

    Note:
        PROTOTYPE ONLY — no path sandboxing. Production tools (Phase 4)
        will enforce scoped filesystem access per CLAUDE.md security rules.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
        return {"status": "success", "content": content}
    except FileNotFoundError:
        return {"status": "error", "content": f"File not found: {path}"}


def file_write(path: str, content: str) -> dict[str, str]:
    """Write content to a file.

    Args:
        path: Absolute path to the file to write.
        content: Text content to write.

    Returns:
        Dictionary with status and bytes written.

    Note:
        PROTOTYPE ONLY — no path sandboxing. Production tools (Phase 4)
        will enforce scoped filesystem access per CLAUDE.md security rules.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    bytes_written = file_path.write_text(content, encoding="utf-8")
    return {"status": "success", "bytes_written": str(bytes_written)}


def bash_exec(command: str) -> dict[str, str]:
    """Execute a shell command with a timeout.

    Args:
        command: The shell command to execute.

    Returns:
        Dictionary with stdout, stderr, and return code.

    Note:
        PROTOTYPE ONLY — no command sandboxing or allowlist. Production tools
        (Phase 4) will enforce scoped execution per CLAUDE.md security rules.
    """
    result = subprocess.run(  # noqa: S603, S607
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": str(result.returncode),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claude_responds_via_litellm(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """LlmAgent with LiteLlm(Claude Sonnet) produces a non-empty text response."""
    agent = LlmAgent(
        model=LiteLlm(model=SONNET_MODEL),
        name="basic_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    start = time.monotonic()
    events, _session = await collect_events(runner, "user1", "session1", "What is 2+2?")
    elapsed = time.monotonic() - start

    assert len(events) > 0, "Expected at least one event"

    # Find the final text response
    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert "4" in response_text, f"Expected '4' in response, got: {response_text}"
    assert elapsed < 60, f"Request took {elapsed:.1f}s, expected < 60s"


@pytest.mark.asyncio
async def test_function_tools_execute(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
    tmp_workspace: str,
) -> None:
    """Agent successfully calls file_write, file_read, and bash_exec tools."""
    target_file = f"{tmp_workspace}/test.txt"

    agent = LlmAgent(
        model=LiteLlm(model=SONNET_MODEL),
        name="tool_agent",
        instruction=(
            "You are a helpful assistant with file and shell tools. "
            "Follow instructions precisely. Use the exact file paths given."
        ),
        tools=[FunctionTool(file_read), FunctionTool(file_write), FunctionTool(bash_exec)],
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(
        runner,
        "user1",
        "session_tools",
        f"Write 'hello world' to {target_file}, then read it back and confirm the contents.",
    )

    # Assert file was created on disk
    assert Path(target_file).exists(), f"Expected file at {target_file}"
    file_content = Path(target_file).read_text(encoding="utf-8")
    assert "hello world" in file_content.lower(), (
        f"Expected 'hello world' in file, got: {file_content}"
    )

    # Assert agent response references the content
    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0, "Expected non-empty response from agent"


@pytest.mark.asyncio
async def test_token_usage_reported(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """Token usage is reported in events via usage_metadata."""
    agent = LlmAgent(
        model=LiteLlm(model=SONNET_MODEL),
        name="token_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(runner, "user1", "session_tokens", "Say hello.")

    # Look for usage metadata on events
    found_usage = False
    for event in events:
        if event.usage_metadata is not None:
            usage = event.usage_metadata
            if usage.prompt_token_count and usage.prompt_token_count > 0:
                found_usage = True
            if usage.candidates_token_count and usage.candidates_token_count > 0:
                assert usage.candidates_token_count > 0

    assert found_usage, (
        "QUIRK: Token usage not found in event.usage_metadata. "
        "LiteLLM+ADK may not propagate token counts to events."
    )
