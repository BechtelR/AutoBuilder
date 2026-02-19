"""Session-scoped todo tools and shared task placeholders.

Todo tools use ADK ToolContext for session state persistence.
Shared task tools are sync placeholders for Phase 5 persistence.
"""

import uuid

from google.adk.tools.tool_context import ToolContext

from app.lib.logging import get_logger
from app.models.enums import TaskStatus, TodoAction, TodoStatus

logger = get_logger("tools.task")


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
# Shared task tools (Phase 5 persistence placeholders)
# ---------------------------------------------------------------------------


def task_create(
    title: str,
    description: str,
    assignee: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Create a cross-session task visible to all agents in the project.

    Args:
        title: Short title for the task.
        description: Detailed description of what needs to be done.
        assignee: Optional agent or user to assign the task to.
        tags: Optional list of tags for categorization.

    Returns:
        Confirmation message with the generated task ID.
    """
    task_id = uuid.uuid4().hex[:8]
    logger.debug(
        "Task created (placeholder): %s title=%s assignee=%s tags=%s",
        task_id,
        title,
        assignee,
        tags,
    )
    return f"Task {task_id} created: {title} (placeholder — persistence in Phase 5)"


def task_update(
    task_id: str,
    status: TaskStatus | None = None,
    notes: str | None = None,
) -> str:
    """Update a shared task's status or add notes.

    Args:
        task_id: The unique identifier of the task to update.
        status: New status value, if changing.
        notes: Additional notes to append, if any.

    Returns:
        Confirmation message.
    """
    logger.debug(
        "Task updated (placeholder): %s status=%s notes=%s",
        task_id,
        status,
        notes,
    )
    return f"Task {task_id} updated (placeholder — persistence in Phase 5)"


def task_query(
    filter: TaskStatus | None = None,
    assignee: str | None = None,
) -> str:
    """Query shared tasks with optional status filter and assignee.

    Args:
        filter: Filter tasks by status value.
        assignee: Filter tasks by assigned agent or user.

    Returns:
        Query result placeholder message.
    """
    logger.debug(
        "Task query (placeholder): filter=%s assignee=%s",
        filter,
        assignee,
    )
    return "Task query (placeholder — persistence in Phase 5)"
