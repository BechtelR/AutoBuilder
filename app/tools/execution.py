"""Shell execution and HTTP request tools for ADK agents."""

import asyncio
from urllib.parse import urlparse

import httpx
from google.adk.tools.tool_context import ToolContext

from app.lib.logging import get_logger
from app.tools._shared import MAX_OUTPUT_LENGTH, truncate_output

_ALLOWED_SCHEMES = frozenset({"http", "https"})

logger = get_logger("tools.execution")


async def bash_exec(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
    idempotency_key: str | None = None,
    tool_context: ToolContext | None = None,
) -> str:
    """Run a shell command. Subprocess wrapper with timeout and output capture.

    Runs the command via an async subprocess shell. Output (stdout + stderr
    combined) is captured and truncated to a safe length.

    Args:
        command: The shell command to execute.
        cwd: Working directory for the command. Defaults to the current
            working directory if not specified.
        timeout: Maximum seconds to wait before killing the process.
            Defaults to 30.
        idempotency_key: Optional cache key. When provided together with
            tool_context, the result is cached in agent state so that
            repeated calls with the same key return instantly.
        tool_context: ADK-injected context (excluded from LLM schema
            automatically). Used for idempotency caching.

    Returns:
        A string containing the exit code and command output, or an error
        description if the command failed to start or timed out.
    """
    # Idempotency: return cached result if available
    if idempotency_key is not None and tool_context is not None:
        cache_key = f"tool_runs:{idempotency_key}"
        cached = tool_context.state.get(cache_key)  # type: ignore[union-attr]
        if cached is not None:
            logger.debug("idempotency cache hit", extra={"key": idempotency_key})
            return str(cached)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except OSError as exc:
        logger.warning("bash_exec failed to start", extra={"command": command, "error": str(exc)})
        return f"error: failed to start process: {exc}"

    try:
        stdout_bytes, _ = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("bash_exec timed out", extra={"command": command, "timeout": timeout})
        return f"error: command timed out after {timeout}s"

    output = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
    exit_code = proc.returncode or 0
    result = f"exit_code={exit_code}\n{truncate_output(output)}"

    # Idempotency: store result for future calls
    if idempotency_key is not None and tool_context is not None:
        cache_key = f"tool_runs:{idempotency_key}"
        tool_context.actions.state_delta[cache_key] = result  # type: ignore[index]

    return result


async def http_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> str:
    """Structured HTTP call for API testing, webhooks, and external service interaction.

    Makes an async HTTP request using the specified method, URL, headers,
    and body. The response body is truncated to a safe length.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.).
        url: The fully-qualified URL to send the request to.
        headers: Optional HTTP headers as key-value pairs.
        body: Optional request body as a string.

    Returns:
        A string containing the HTTP status code and response body,
        or an error description if the request failed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"error: URL scheme '{parsed.scheme}' not allowed (only http/https)"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                content=body,
            )
    except httpx.ConnectError as exc:
        logger.warning("http_request connection failed", extra={"url": url, "error": str(exc)})
        return f"error: connection failed: {exc}"
    except httpx.TimeoutException:
        logger.warning("http_request timed out", extra={"url": url})
        return "error: request timed out after 30s"
    except httpx.HTTPError as exc:
        logger.warning("http_request HTTP error", extra={"url": url, "error": str(exc)})
        return f"error: HTTP error: {exc}"

    response_body = truncate_output(response.text, MAX_OUTPUT_LENGTH)
    return f"status={response.status_code}\n{response_body}"
