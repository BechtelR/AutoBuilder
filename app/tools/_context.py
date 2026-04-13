"""Module-level registry for non-serializable tool execution context.

Management tools need access to DB sessions, ARQ pool, and other infrastructure
that cannot be serialized into ADK session state. This registry provides a
process-local lookup keyed by session_id.

Workers register context at session start and unregister on cleanup.
Tools access via get_tool_context(tool_context.state["_session_id"]).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.lib.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from arq.connections import ArqRedis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.events.publisher import EventPublisher
    from app.workflows.registry import WorkflowRegistry

logger = get_logger("tools._context")

SESSION_ID_KEY = "_session_id"


@dataclass
class ToolExecutionContext:
    """Non-serializable execution context for management tools."""

    db_session_factory: async_sessionmaker[AsyncSession]
    arq_pool: ArqRedis
    workflow_registry: WorkflowRegistry
    publisher: EventPublisher
    artifacts_root: Path | None = field(default=None)


_REGISTRY: dict[str, ToolExecutionContext] = {}


def register_tool_context(session_id: str, ctx: ToolExecutionContext) -> None:
    """Register tool execution context for a session."""
    _REGISTRY[session_id] = ctx
    logger.debug("Registered tool context for session %s", session_id)


def get_tool_context(session_id: str) -> ToolExecutionContext:
    """Get tool execution context by session ID. Raises KeyError if not registered."""
    try:
        return _REGISTRY[session_id]
    except KeyError:
        raise KeyError(
            f"No tool execution context registered for session '{session_id}'. "
            "Ensure the worker registered context before running the agent."
        ) from None


def unregister_tool_context(session_id: str) -> None:
    """Remove tool execution context for a session."""
    _REGISTRY.pop(session_id, None)
    logger.debug("Unregistered tool context for session %s", session_id)
