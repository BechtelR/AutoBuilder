"""Tests for session-scoped todo tools and shared task placeholders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.enums import TaskStatus, TodoAction, TodoStatus
from app.tools.task import (
    task_create,
    task_query,
    task_update,
    todo_list,
    todo_read,
    todo_write,
)

if TYPE_CHECKING:
    from tests.tools.conftest import FakeToolContext


# ---------------------------------------------------------------------------
# todo_write + todo_read round-trip
# ---------------------------------------------------------------------------


class TestTodoAddAndRead:
    def test_add_creates_task_and_read_returns_it(self, tool_context: FakeToolContext) -> None:
        # Signature: todo_write(action, task_id, content, tool_context)
        result = todo_write(
            TodoAction.ADD,
            "",
            "Test task",
            tool_context,  # type: ignore[arg-type]
        )

        assert result.startswith("Todo ")
        assert "added" in result
        task_id = result.split()[1]

        # todo_read only takes tool_context; returns all todos
        read_result = todo_read(tool_context)  # type: ignore[arg-type]
        assert task_id in read_result
        assert "Test task" in read_result
        assert TodoStatus.PENDING in read_result

    def test_add_without_content_returns_error(self, tool_context: FakeToolContext) -> None:
        result = todo_write(
            TodoAction.ADD,
            "",
            "",
            tool_context,  # type: ignore[arg-type]
        )
        assert "Error" in result
        assert "content" in result

    def test_read_empty_returns_no_todos(self, tool_context: FakeToolContext) -> None:
        result = todo_read(tool_context)  # type: ignore[arg-type]
        assert "No todos found" in result


# ---------------------------------------------------------------------------
# todo_list
# ---------------------------------------------------------------------------


class TestTodoList:
    def test_list_returns_all_tasks(self, tool_context: FakeToolContext) -> None:
        todo_write(
            TodoAction.ADD,
            "",
            "Task A",
            tool_context,  # type: ignore[arg-type]
        )
        todo_write(
            TodoAction.ADD,
            "",
            "Task B",
            tool_context,  # type: ignore[arg-type]
        )

        result = todo_list(tool_context)  # type: ignore[arg-type]
        assert "Task A" in result
        assert "Task B" in result

    def test_list_with_status_filter(self, tool_context: FakeToolContext) -> None:
        result_a = todo_write(
            TodoAction.ADD,
            "",
            "Task A",
            tool_context,  # type: ignore[arg-type]
        )
        todo_write(
            TodoAction.ADD,
            "",
            "Task B",
            tool_context,  # type: ignore[arg-type]
        )

        task_a_id = result_a.split()[1]
        todo_write(
            TodoAction.COMPLETE,
            task_a_id,
            "",
            tool_context,  # type: ignore[arg-type]
        )

        done_list = todo_list(tool_context, filter=TodoStatus.DONE)  # type: ignore[arg-type]
        assert "Task A" in done_list
        assert "Task B" not in done_list

        pending_list = todo_list(
            tool_context,  # type: ignore[arg-type]
            filter=TodoStatus.PENDING,  # type: ignore[arg-type]
        )
        assert "Task B" in pending_list
        assert "Task A" not in pending_list

    def test_list_empty_returns_message(self, tool_context: FakeToolContext) -> None:
        result = todo_list(tool_context)  # type: ignore[arg-type]
        assert "No todos found" in result


# ---------------------------------------------------------------------------
# todo_write: UPDATE
# ---------------------------------------------------------------------------


class TestTodoUpdate:
    def test_update_changes_content(self, tool_context: FakeToolContext) -> None:
        add_result = todo_write(
            TodoAction.ADD,
            "",
            "Original",
            tool_context,  # type: ignore[arg-type]
        )
        task_id = add_result.split()[1]

        update_result = todo_write(
            TodoAction.UPDATE,
            task_id,
            "Revised",
            tool_context,  # type: ignore[arg-type]
        )
        assert "updated" in update_result

        read_result = todo_read(tool_context)  # type: ignore[arg-type]
        assert "Revised" in read_result
        assert "Original" not in read_result

    def test_update_without_task_id_returns_error(self, tool_context: FakeToolContext) -> None:
        result = todo_write(
            TodoAction.UPDATE,
            "",
            "X",
            tool_context,  # type: ignore[arg-type]
        )
        assert "Error" in result
        assert "task_id" in result

    def test_update_without_content_returns_error(self, tool_context: FakeToolContext) -> None:
        add_result = todo_write(
            TodoAction.ADD,
            "",
            "Original",
            tool_context,  # type: ignore[arg-type]
        )
        task_id = add_result.split()[1]
        result = todo_write(
            TodoAction.UPDATE,
            task_id,
            "",
            tool_context,  # type: ignore[arg-type]
        )
        assert "Error" in result
        assert "content" in result

    def test_update_nonexistent_returns_not_found(self, tool_context: FakeToolContext) -> None:
        result = todo_write(
            TodoAction.UPDATE,
            "nope",
            "X",
            tool_context,  # type: ignore[arg-type]
        )
        assert "Not found" in result


# ---------------------------------------------------------------------------
# todo_write: COMPLETE and REMOVE
# ---------------------------------------------------------------------------


class TestTodoComplete:
    def test_complete_marks_done(self, tool_context: FakeToolContext) -> None:
        add_result = todo_write(
            TodoAction.ADD,
            "",
            "Do it",
            tool_context,  # type: ignore[arg-type]
        )
        task_id = add_result.split()[1]

        complete_result = todo_write(
            TodoAction.COMPLETE,
            task_id,
            "",
            tool_context,  # type: ignore[arg-type]
        )
        assert "DONE" in complete_result

        read_result = todo_read(tool_context)  # type: ignore[arg-type]
        assert TodoStatus.DONE in read_result


class TestTodoRemove:
    def test_remove_deletes_task(self, tool_context: FakeToolContext) -> None:
        add_result = todo_write(
            TodoAction.ADD,
            "",
            "Remove me",
            tool_context,  # type: ignore[arg-type]
        )
        task_id = add_result.split()[1]

        remove_result = todo_write(
            TodoAction.REMOVE,
            task_id,
            "",
            tool_context,  # type: ignore[arg-type]
        )
        assert "removed" in remove_result

        # After removal, reading all todos should not contain the removed task
        read_result = todo_read(tool_context)  # type: ignore[arg-type]
        assert task_id not in read_result

    def test_remove_nonexistent_returns_not_found(self, tool_context: FakeToolContext) -> None:
        result = todo_write(
            TodoAction.REMOVE,
            "nope",
            "",
            tool_context,  # type: ignore[arg-type]
        )
        assert "Not found" in result


# ---------------------------------------------------------------------------
# Shared task placeholders
# ---------------------------------------------------------------------------


class TestTaskCreate:
    def test_returns_confirmation_with_uuid_and_placeholder(self) -> None:
        result = task_create("My Title", "My Description")
        assert "My Title" in result
        assert "placeholder" in result
        # UUID hex prefix is 8 chars
        parts = result.split()
        task_id = parts[1]
        assert len(task_id) == 8


class TestTaskUpdate:
    def test_returns_confirmation(self) -> None:
        result = task_update("abc", status=TaskStatus.DONE)
        assert "abc" in result
        assert "placeholder" in result


class TestTaskQuery:
    def test_returns_placeholder_message(self) -> None:
        result = task_query()
        assert "placeholder" in result
