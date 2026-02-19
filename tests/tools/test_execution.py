"""Tests for bash_exec and http_request tools."""

from pathlib import Path

import pytest

from app.tools.execution import bash_exec, http_request
from tests.tools.conftest import FakeToolContext


async def test_bash_exec_echo() -> None:
    """Simple echo returns output with exit_code=0."""
    result = await bash_exec("echo hello")
    assert "hello" in result
    assert "exit_code=0" in result


async def test_bash_exec_timeout() -> None:
    """Command exceeding timeout returns timeout error."""
    result = await bash_exec("sleep 10", timeout=1)
    assert "timed out" in result
    assert "1s" in result


async def test_bash_exec_nonzero_exit() -> None:
    """Non-zero exit code is reported in the output."""
    result = await bash_exec("exit 42")
    assert "exit_code=42" in result


async def test_bash_exec_output_truncation() -> None:
    """Output exceeding MAX_OUTPUT_LENGTH is truncated."""
    result = await bash_exec("yes | head -6000")
    assert "truncated" in result


async def test_bash_exec_cwd(tmp_path: Path) -> None:
    """Command runs in the specified working directory."""
    result = await bash_exec("pwd", cwd=str(tmp_path))
    assert str(tmp_path) in result
    assert "exit_code=0" in result


async def test_bash_exec_idempotency_with_context() -> None:
    """Repeated calls with same idempotency_key return cached result."""
    ctx = FakeToolContext()
    result1 = await bash_exec(
        "echo first-run",
        idempotency_key="test-key",
        tool_context=ctx,  # type: ignore[arg-type]
    )
    assert "first-run" in result1

    # Second call with same key should return cached result, not re-execute
    result2 = await bash_exec(
        "echo second-run",
        idempotency_key="test-key",
        tool_context=ctx,  # type: ignore[arg-type]
    )
    assert result2 == result1
    assert "second-run" not in result2


async def test_bash_exec_different_keys_not_cached() -> None:
    """Different idempotency keys execute independently."""
    ctx = FakeToolContext()
    result1 = await bash_exec(
        "echo run-a",
        idempotency_key="key-a",
        tool_context=ctx,  # type: ignore[arg-type]
    )
    result2 = await bash_exec(
        "echo run-b",
        idempotency_key="key-b",
        tool_context=ctx,  # type: ignore[arg-type]
    )
    assert "run-a" in result1
    assert "run-b" in result2


async def test_http_request_connection_error() -> None:
    """HTTP request to unreachable host returns connection error."""
    result = await http_request("GET", "http://192.0.2.1:1")
    assert "error:" in result.lower()


@pytest.mark.network
async def test_http_request_get() -> None:
    """GET request to httpbin returns status 200."""
    result = await http_request("GET", "https://httpbin.org/get")
    assert "status=200" in result
