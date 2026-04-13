"""Tests for regression test wiring in the batch loop (D9)."""

from __future__ import annotations

import pytest

from app.workers.tasks import _run_regression_tests  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
class TestRunRegressionTests:
    """Test the _run_regression_tests helper function."""

    async def test_runs_when_policy_always(self) -> None:
        """Runs regression tests when policy is 'always'."""
        state: dict[str, object] = {
            "pm:regression_policy": "always",
            "working_directory": "/tmp",
        }
        # Use a command that always succeeds
        state["pm:regression_policy"] = {
            "schedule": "always",
            "command": "echo regression_ok",
        }
        result = await _run_regression_tests(state, None)  # type: ignore[arg-type]
        assert result["ran"] is True
        assert result["passed"] is True
        assert "regression_ok" in str(result["output"])

    async def test_runs_when_policy_after_batch(self) -> None:
        """Runs regression tests when policy is 'after_batch'."""
        state: dict[str, object] = {
            "pm:regression_policy": {
                "schedule": "after_batch",
                "command": "echo batch_done",
            },
        }
        result = await _run_regression_tests(state, None)  # type: ignore[arg-type]
        assert result["ran"] is True
        assert result["passed"] is True

    async def test_reports_failure_on_nonzero_exit(self) -> None:
        """Reports failure when subprocess exits non-zero."""
        state: dict[str, object] = {
            "pm:regression_policy": {
                "schedule": "always",
                "command": "false",  # exits with 1
            },
        }
        result = await _run_regression_tests(state, None)  # type: ignore[arg-type]
        assert result["ran"] is True
        assert result["passed"] is False

    async def test_handles_bad_command(self) -> None:
        """Handles command execution errors gracefully."""
        state: dict[str, object] = {
            "pm:regression_policy": {
                "schedule": "always",
                "command": "/nonexistent/binary_that_does_not_exist",
            },
        }
        result = await _run_regression_tests(state, None)  # type: ignore[arg-type]
        assert result["ran"] is True
        assert result["passed"] is False
