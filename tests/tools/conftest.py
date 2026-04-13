"""Fixtures for tool tests.

Provides project directories, git repos, and ADK ToolContext for testing.
"""

import os
import subprocess
from pathlib import Path

import pytest

_tavily_available: bool = bool(os.environ.get("TAVILY_API_KEY"))

require_tavily_key = pytest.mark.skipif(
    not _tavily_available,
    reason="TAVILY_API_KEY not set",
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A temporary project directory with a sample file."""
    (tmp_path / "hello.txt").write_text("Hello, world!\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.py").write_text("x = 1\n")
    return tmp_path


@pytest.fixture
def git_repo(project_dir: Path) -> Path:
    """A temporary git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "-A"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    return project_dir


class FakeActions:
    """Minimal stand-in for ToolContext.actions."""

    def __init__(self) -> None:
        self.state_delta: dict[str, object] = {}


class FakeToolContext:
    """Minimal stand-in for ADK ToolContext used by todo tools.

    Provides `.state` (dict-like read) and `.actions.state_delta` (dict write).
    """

    def __init__(self, initial_state: dict[str, object] | None = None) -> None:
        self._state: dict[str, object] = initial_state or {}
        self.actions = FakeActions()

    @property
    def state(self) -> dict[str, object]:
        # Apply any pending state_delta so reads reflect writes
        merged = dict(self._state)
        merged.update(self.actions.state_delta)
        return merged

    def get(self, key: str, default: object = None) -> object:
        return self.state.get(key, default)


@pytest.fixture
def tool_context() -> FakeToolContext:
    """A fresh FakeToolContext with empty state."""
    return FakeToolContext()
