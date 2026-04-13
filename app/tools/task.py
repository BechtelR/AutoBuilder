"""Session-scoped todo tools and cross-session task tools with DB persistence.

Todo tools use ADK ToolContext for session state persistence.
Shared task tools use ToolExecutionContext for real DB persistence (FR-8a.25).
"""

from __future__ import annotations

import contextlib
import json
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from google.adk.tools.tool_context import (
    ToolContext,  # noqa: TC002 - runtime import required by ADK FunctionTool
)
from sqlalchemy import select

from app.db.models import ProjectTask
from app.lib.logging import get_logger
from app.models.enums import TaskStatus, TodoAction, TodoStatus
from app.tools._context import SESSION_ID_KEY, get_tool_context

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("tools.task")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _get_db_session(tool_context: ToolContext) -> AsyncIterator[AsyncSession]:
    """Get a DB session from the tool execution context registry."""
    session_id = tool_context.state.get(SESSION_ID_KEY)  # type: ignore[union-attr]
    if session_id is None:
        raise ValueError("Session ID not available in tool context")
    ctx = get_tool_context(str(session_id))
    async with ctx.db_session_factory() as session:
        yield session


def _task_to_dict(task: ProjectTask) -> dict[str, object]:
    """Convert a ProjectTask row to a serializable dict."""
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "assignee": task.assignee,
        "tags": task.tags,
        "notes": task.notes,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Session-scoped todo tools
# ---------------------------------------------------------------------------


def todo_read(tool_context: ToolContext) -> str:
    """Read current task list from session state.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).

    Returns:
        Formatted list of all todo items, or a message if none exist.
    """
    todos: list[dict[str, str]] = list(
        tool_context.state.get("todos", [])  # type: ignore[arg-type]
    )
    if not todos:
        return "No todos found"

    lines: list[str] = []
    for todo in todos:
        status = todo.get("status", TodoStatus.PENDING)
        tid = todo.get("id", "?")
        content = todo.get("content", "")
        lines.append(f"[{status}] {tid}: {content}")

    return "\n".join(lines)


def todo_write(
    action: TodoAction,
    task_id: str,
    content: str,
    tool_context: ToolContext,
) -> str:
    """Add, update, complete, or remove tasks.

    Args:
        action: The operation to perform (ADD, UPDATE, COMPLETE, REMOVE).
        task_id: The todo ID. Required for UPDATE, COMPLETE, REMOVE.
            Pass empty string for ADD (a new ID will be generated).
        content: The todo text. Required for ADD and UPDATE.
            Pass empty string for COMPLETE and REMOVE.
        tool_context: ADK-injected session context (excluded from LLM schema).

    Returns:
        Confirmation message with the affected task ID, or an error description.
    """
    todos: list[dict[str, str]] = list(
        tool_context.state.get("todos", [])  # type: ignore[arg-type]
    )

    if action == TodoAction.ADD:
        if not content:
            return "Error: content is required for ADD action"
        new_id = uuid.uuid4().hex[:8]
        todos.append(
            {
                "id": new_id,
                "content": content,
                "status": TodoStatus.PENDING,
            }
        )
        tool_context.actions.state_delta["todos"] = todos  # type: ignore[index]
        logger.debug("Todo added: %s", new_id)
        return f"Todo {new_id} added"

    if action == TodoAction.UPDATE:
        if not task_id:
            return "Error: task_id is required for UPDATE action"
        if not content:
            return "Error: content is required for UPDATE action"
        for todo in todos:
            if todo.get("id") == task_id:
                todo["content"] = content
                tool_context.actions.state_delta["todos"] = todos  # type: ignore[index]
                logger.debug("Todo updated: %s", task_id)
                return f"Todo {task_id} updated"
        return f"Not found: no todo with id '{task_id}'"

    if action == TodoAction.COMPLETE:
        if not task_id:
            return "Error: task_id is required for COMPLETE action"
        for todo in todos:
            if todo.get("id") == task_id:
                todo["status"] = TodoStatus.DONE
                tool_context.actions.state_delta["todos"] = todos  # type: ignore[index]
                logger.debug("Todo completed: %s", task_id)
                return f"Todo {task_id} marked as DONE"
        return f"Not found: no todo with id '{task_id}'"

    if action == TodoAction.REMOVE:
        if not task_id:
            return "Error: task_id is required for REMOVE action"
        original_len = len(todos)
        todos = [t for t in todos if t.get("id") != task_id]
        if len(todos) == original_len:
            return f"Not found: no todo with id '{task_id}'"
        tool_context.actions.state_delta["todos"] = todos  # type: ignore[index]
        logger.debug("Todo removed: %s", task_id)
        return f"Todo {task_id} removed"

    return f"Error: unknown action '{action}'"


def todo_list(
    tool_context: ToolContext,
    filter: str | None = None,
) -> str:
    """List tasks with optional status filter.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        filter: If provided, only return todos matching this status.

    Returns:
        Formatted list of todos or a message indicating none were found.
    """
    todos: list[dict[str, str]] = list(
        tool_context.state.get("todos", [])  # type: ignore[arg-type]
    )

    if filter:
        todos = [t for t in todos if t.get("status") == filter]

    if not todos:
        return "No todos found"

    lines: list[str] = []
    for todo in todos:
        status = todo.get("status", TodoStatus.PENDING)
        tid = todo.get("id", "?")
        content = todo.get("content", "")
        lines.append(f"[{status}] {tid}: {content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared task tools — DB-persisted (FR-8a.25)
# ---------------------------------------------------------------------------


async def task_create(
    title: str,
    description: str,
    tool_context: ToolContext,
    assignee: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Create a cross-session task visible to all agents in the project.

    Args:
        title: Short title for the task.
        description: Detailed description of what needs to be done.
        tool_context: ADK-injected session context (excluded from LLM schema).
        assignee: Optional agent or user to assign the task to.
        tags: Optional list of tags for categorization.

    Returns:
        JSON with the created task record.
    """
    # Check both unprefixed and PM-prefixed state keys (PM sets "pm:project_id",
    # Director may set "project_id" directly)
    project_id_raw = tool_context.state.get("project_id") or tool_context.state.get("pm:project_id")  # type: ignore[union-attr]
    project_uuid: uuid.UUID | None = None
    if project_id_raw is not None:
        try:
            project_uuid = uuid.UUID(str(project_id_raw))
        except ValueError:
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid project_id in state: {project_id_raw}",
                    }
                }
            )

    try:
        task = ProjectTask(
            title=title,
            description=description,
            assignee=assignee,
            tags=tags or [],
            project_id=project_uuid,
        )

        async with _get_db_session(tool_context) as db:
            db.add(task)
            await db.commit()
            await db.refresh(task)
            result = _task_to_dict(task)

        logger.debug("Task created: %s title=%s", result["id"], title)
        return json.dumps(result)
    except Exception as e:
        logger.exception("Failed to create task")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def task_update(
    task_id: str,
    tool_context: ToolContext,
    status: str | None = None,
    notes: str | None = None,
) -> str:
    """Update a shared task's status or add notes.

    Args:
        task_id: The unique identifier of the task to update.
        tool_context: ADK-injected session context (excluded from LLM schema).
        status: New status value (OPEN, IN_PROGRESS, DONE, BLOCKED), if changing.
        notes: Additional notes to append, if any.

    Returns:
        JSON with the updated task record, or an error message.
    """
    resolved_status: TaskStatus | None = None
    if status is not None:
        try:
            resolved_status = TaskStatus(status)
        except ValueError:
            valid = ", ".join(s.value for s in TaskStatus)
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid status '{status}'. Valid: {valid}",
                    }
                }
            )

    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        return json.dumps(
            {"error": {"code": "INVALID_INPUT", "message": f"Invalid task_id '{task_id}'"}}
        )

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(ProjectTask).where(ProjectTask.id == task_uuid)
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row is None:
                return json.dumps(
                    {"error": {"code": "NOT_FOUND", "message": f"Task '{task_id}' not found"}}
                )

            if resolved_status is not None:
                row.status = resolved_status
            if notes is not None:
                existing = row.notes or ""
                row.notes = f"{existing}\n{notes}".strip() if existing else notes

            await db.commit()
            await db.refresh(row)
            result = _task_to_dict(row)

        logger.debug("Task updated: %s status=%s", task_id, resolved_status)
        return json.dumps(result)
    except Exception as e:
        logger.exception("Failed to update task")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})


async def task_query(
    tool_context: ToolContext,
    filter: str | None = None,
    assignee: str | None = None,
) -> str:
    """Query shared tasks with optional status filter and assignee.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        filter: Filter tasks by status (OPEN, IN_PROGRESS, DONE, BLOCKED).
        assignee: Filter tasks by assigned agent or user.

    Returns:
        JSON array of matching task records.
    """
    resolved_filter: TaskStatus | None = None
    if filter is not None:
        try:
            resolved_filter = TaskStatus(filter)
        except ValueError:
            valid = ", ".join(s.value for s in TaskStatus)
            return json.dumps(
                {
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"Invalid filter '{filter}'. Valid: {valid}",
                    }
                }
            )

    # Check both unprefixed and PM-prefixed state keys (PM sets "pm:project_id",
    # Director may set "project_id" directly)
    project_id_raw = tool_context.state.get("project_id") or tool_context.state.get("pm:project_id")  # type: ignore[union-attr]
    project_uuid: uuid.UUID | None = None
    if project_id_raw is not None:
        with contextlib.suppress(ValueError):
            project_uuid = uuid.UUID(str(project_id_raw))

    try:
        async with _get_db_session(tool_context) as db:
            stmt = select(ProjectTask)
            if project_uuid is not None:
                stmt = stmt.where(ProjectTask.project_id == project_uuid)
            if resolved_filter is not None:
                stmt = stmt.where(ProjectTask.status == resolved_filter)
            if assignee is not None:
                stmt = stmt.where(ProjectTask.assignee == assignee)

            rows = (await db.execute(stmt)).scalars().all()
            results = [_task_to_dict(r) for r in rows]

        logger.debug(
            "Task query: filter=%s assignee=%s count=%d", resolved_filter, assignee, len(results)
        )
        return json.dumps(results)
    except Exception as e:
        logger.exception("Failed to query tasks")
        return json.dumps({"error": {"code": "DB_ERROR", "message": str(e)}})
