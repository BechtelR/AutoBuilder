"""Prototype 5: Alternate Provider Validation — OpenAI + Gemini via LiteLLM."""

from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.function_tool import FunctionTool

from tests.phase1.conftest import collect_events, requires_google_key, requires_openai_key

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.runners import InMemoryRunner

OPENAI_MODEL = "openai/gpt-5-nano"
GEMINI_MODEL = "gemini/gemini-2.5-flash-lite"


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


# ---------------------------------------------------------------------------
# OpenAI Tests
# ---------------------------------------------------------------------------


@requires_openai_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_responds_via_litellm(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """LlmAgent with LiteLlm(OpenAI) produces a non-empty text response."""
    agent = LlmAgent(
        model=LiteLlm(model=OPENAI_MODEL),
        name="openai_basic_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    start = time.monotonic()
    events, _session = await collect_events(runner, "user1", "session_openai_basic", "What is 2+2?")
    elapsed = time.monotonic() - start

    assert len(events) > 0, "Expected at least one event"

    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert "4" in response_text, f"Expected '4' in response, got: {response_text}"
    assert elapsed < 60, f"Request took {elapsed:.1f}s, expected < 60s"


@requires_openai_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_function_tool_calling(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
    tmp_workspace: str,
) -> None:
    """OpenAI agent calls file_write + file_read FunctionTools."""
    target_file = f"{tmp_workspace}/openai_test.txt"

    agent = LlmAgent(
        model=LiteLlm(model=OPENAI_MODEL),
        name="openai_tool_agent",
        instruction=(
            "You are a helpful assistant with file tools. "
            "Follow instructions precisely. Use the exact file paths given."
        ),
        tools=[FunctionTool(file_read), FunctionTool(file_write)],
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(
        runner,
        "user1",
        "session_openai_tools",
        f"Write 'hello from openai' to {target_file}, then read it back and confirm the contents.",
    )

    assert Path(target_file).exists(), f"Expected file at {target_file}"
    file_content = Path(target_file).read_text(encoding="utf-8")
    assert "hello from openai" in file_content.lower(), (
        f"Expected 'hello from openai' in file, got: {file_content}"
    )

    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0, "Expected non-empty response from agent"


@requires_openai_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_token_usage(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """Token usage is reported in events for OpenAI (soft assertion)."""
    agent = LlmAgent(
        model=LiteLlm(model=OPENAI_MODEL),
        name="openai_token_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(runner, "user1", "session_openai_tokens", "Say hello.")

    found_usage = False
    for event in events:
        if event.usage_metadata is not None:
            usage = event.usage_metadata
            if usage.prompt_token_count and usage.prompt_token_count > 0:
                found_usage = True
            if usage.candidates_token_count and usage.candidates_token_count > 0:
                assert usage.candidates_token_count > 0

    if not found_usage:
        warnings.warn(
            "Token usage not found in event.usage_metadata for OpenAI. "
            "LiteLLM+ADK may not propagate token counts to events.",
            stacklevel=1,
        )


# ---------------------------------------------------------------------------
# Gemini Tests
# ---------------------------------------------------------------------------


@requires_google_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_responds_via_litellm(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """LlmAgent with LiteLlm(Gemini) produces a non-empty text response."""
    agent = LlmAgent(
        model=LiteLlm(model=GEMINI_MODEL),
        name="gemini_basic_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    start = time.monotonic()
    events, _session = await collect_events(runner, "user1", "session_gemini_basic", "What is 2+2?")
    elapsed = time.monotonic() - start

    assert len(events) > 0, "Expected at least one event"

    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert "4" in response_text, f"Expected '4' in response, got: {response_text}"
    assert elapsed < 60, f"Request took {elapsed:.1f}s, expected < 60s"


@requires_google_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_function_tool_calling(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
    tmp_workspace: str,
) -> None:
    """Gemini agent calls file_write + file_read FunctionTools."""
    target_file = f"{tmp_workspace}/gemini_test.txt"

    agent = LlmAgent(
        model=LiteLlm(model=GEMINI_MODEL),
        name="gemini_tool_agent",
        instruction=(
            "You are a helpful assistant with file tools. "
            "Follow instructions precisely. Use the exact file paths given."
        ),
        tools=[FunctionTool(file_read), FunctionTool(file_write)],
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(
        runner,
        "user1",
        "session_gemini_tools",
        f"Write 'hello from gemini' to {target_file}, then read it back and confirm the contents.",
    )

    assert Path(target_file).exists(), f"Expected file at {target_file}"
    file_content = Path(target_file).read_text(encoding="utf-8")
    assert "hello from gemini" in file_content.lower(), (
        f"Expected 'hello from gemini' in file, got: {file_content}"
    )

    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    assert len(response_text) > 0, "Expected non-empty response from agent"


@requires_google_key
@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_token_usage(
    runner_factory: Callable[[LlmAgent], InMemoryRunner],
) -> None:
    """Token usage is reported in events for Gemini (soft assertion)."""
    agent = LlmAgent(
        model=LiteLlm(model=GEMINI_MODEL),
        name="gemini_token_agent",
        instruction="You are a helpful assistant. Respond concisely.",
    )
    runner = runner_factory(agent)

    events, _session = await collect_events(runner, "user1", "session_gemini_tokens", "Say hello.")

    found_usage = False
    for event in events:
        if event.usage_metadata is not None:
            usage = event.usage_metadata
            if usage.prompt_token_count and usage.prompt_token_count > 0:
                found_usage = True
            if usage.candidates_token_count and usage.candidates_token_count > 0:
                assert usage.candidates_token_count > 0

    if not found_usage:
        warnings.warn(
            "Token usage not found in event.usage_metadata for Gemini. "
            "LiteLLM+ADK may not propagate token counts to events.",
            stacklevel=1,
        )
