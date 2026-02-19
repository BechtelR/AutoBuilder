"""Shared constants and helpers for tool modules."""

import asyncio
from pathlib import Path

from app.lib.logging import get_logger

logger = get_logger("tools")

MAX_OUTPUT_LENGTH: int = 10_000


def truncate_output(text: str, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    """Truncate text and append a notice if it exceeds max_length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"\n... (truncated, {len(text)} total chars)"


def validate_path(path: str, project_root: str) -> Path:
    """Validate a path is within project_root. Returns resolved Path.

    Rejects:
    - Paths containing '..' traversal
    - Absolute paths outside project_root
    - Symlinks resolving outside project_root
    """
    root = Path(project_root).resolve()

    if ".." in Path(path).parts:
        msg = f"Path traversal rejected: {path}"
        raise ValueError(msg)

    # Handle relative and absolute paths
    candidate = Path(path) if Path(path).is_absolute() else root / path
    resolved = candidate.resolve()

    try:
        resolved.relative_to(root)
    except ValueError:
        msg = f"Path outside project root: {path}"
        raise ValueError(msg) from None

    return resolved


async def run_git(args: list[str], cwd: str) -> tuple[int, str]:
    """Run a git command and return (exit_code, output)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace").strip()
