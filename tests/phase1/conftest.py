"""Shared fixtures for Phase 1 ADK prototype tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from google.adk.agents import BaseAgent
    from google.adk.events import Event
    from google.adk.sessions import Session


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


requires_api_key = pytest.mark.skipif(
    "ANTHROPIC_API_KEY" not in os.environ,
    reason="ANTHROPIC_API_KEY not set — skipping integration test",
)

requires_openai_key = pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="OPENAI_API_KEY not set — skipping OpenAI integration test",
)

requires_google_key = pytest.mark.skipif(
    "GOOGLE_API_KEY" not in os.environ,
    reason="GOOGLE_API_KEY not set — skipping Gemini integration test",
)


@pytest.fixture()
def runner_factory() -> Callable[[BaseAgent], InMemoryRunner]:
    """Factory that accepts a root agent and returns an InMemoryRunner."""

    def _create(agent: BaseAgent) -> InMemoryRunner:
        runner = InMemoryRunner(agent=agent, app_name="phase1_test")
        runner.auto_create_session = True
        return runner

    return _create


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> str:
    """Provide a temporary workspace directory path as a string."""
    return str(tmp_path)


async def collect_events(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    message: str,
) -> tuple[list[Event], Session]:
    """Run an agent and collect all events.

    Args:
        runner: The InMemoryRunner instance.
        user_id: User identifier for the session.
        session_id: Session identifier.
        message: The user message to send.

    Returns:
        Tuple of (list of events, final session state).
    """
    new_message = types.Content(parts=[types.Part(text=message)])
    events: list[Event] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        events.append(event)

    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    assert session is not None, f"Session {session_id} not found after run"
    return events, session
