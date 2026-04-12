"""GlobalToolset — role-based tool vending via ADK's BaseToolset."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool

from app.tools.code import code_symbols, run_diagnostics
from app.tools.execution import bash_exec, http_request
from app.tools.filesystem import (
    directory_list,
    file_delete,
    file_edit,
    file_glob,
    file_grep,
    file_insert,
    file_move,
    file_multi_edit,
    file_read,
    file_write,
)
from app.tools.git import (
    git_apply,
    git_branch,
    git_commit,
    git_diff,
    git_log,
    git_show,
    git_status,
    git_worktree,
)
from app.tools.management import (
    escalate_to_ceo,
    escalate_to_director,
    get_project_context,
    list_projects,
    manage_dependencies,
    override_pm,
    query_deliverables,
    query_dependency_graph,
    query_project_status,
    reconfigure_stage,
    reorder_deliverables,
    select_ready_batch,
    update_deliverable,
)
from app.tools.task import (
    task_create,
    task_query,
    task_update,
    todo_list,
    todo_read,
    todo_write,
)
from app.tools.web import web_fetch, web_search

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents.readonly_context import ReadonlyContext
    from google.adk.tools.base_tool import BaseTool

# ---------------------------------------------------------------------------
# All 43 tool functions, grouped by category
# ---------------------------------------------------------------------------

_FILESYSTEM_TOOLS: list[Callable[..., object]] = [
    file_read,
    file_write,
    file_edit,
    file_insert,
    file_multi_edit,
    file_glob,
    file_grep,
    file_move,
    file_delete,
    directory_list,
]

_CODE_TOOLS: list[Callable[..., object]] = [
    code_symbols,
    run_diagnostics,
]

_EXECUTION_TOOLS: list[Callable[..., object]] = [
    bash_exec,
    http_request,
]

_GIT_TOOLS: list[Callable[..., object]] = [
    git_status,
    git_commit,
    git_branch,
    git_diff,
    git_log,
    git_show,
    git_worktree,
    git_apply,
]

_WEB_TOOLS: list[Callable[..., object]] = [
    web_fetch,
    web_search,
]

_TODO_TOOLS: list[Callable[..., object]] = [
    todo_read,
    todo_write,
    todo_list,
]

_SHARED_TASK_TOOLS: list[Callable[..., object]] = [
    task_create,
    task_update,
    task_query,
]

_PM_MANAGEMENT_TOOLS: list[Callable[..., object]] = [
    select_ready_batch,
    escalate_to_director,
    update_deliverable,
    query_deliverables,
    reorder_deliverables,
    manage_dependencies,
    reconfigure_stage,
]

_DIRECTOR_MANAGEMENT_TOOLS: list[Callable[..., object]] = [
    escalate_to_ceo,
    list_projects,
    query_project_status,
    override_pm,
    get_project_context,
    query_dependency_graph,
]

ALL_TOOL_FUNCTIONS: list[Callable[..., object]] = (
    _FILESYSTEM_TOOLS
    + _CODE_TOOLS
    + _EXECUTION_TOOLS
    + _GIT_TOOLS
    + _WEB_TOOLS
    + _TODO_TOOLS
    + _SHARED_TASK_TOOLS
    + _PM_MANAGEMENT_TOOLS
    + _DIRECTOR_MANAGEMENT_TOOLS
)

# ---------------------------------------------------------------------------
# Read-only subsets (filesystem + git)
# ---------------------------------------------------------------------------

_FS_READONLY = {"file_read", "file_glob", "file_grep", "directory_list"}
_GIT_READONLY = {"git_status", "git_diff", "git_log", "git_show"}

# ---------------------------------------------------------------------------
# Role permission map (per architecture/tools.md §7.5)
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "planner": (
        _FS_READONLY
        | {"code_symbols", "run_diagnostics"}
        | _GIT_READONLY
        | {"web_fetch", "web_search"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "coder": (
        {f.__name__ for f in _FILESYSTEM_TOOLS}
        | {"code_symbols", "run_diagnostics"}
        | {"bash_exec", "http_request"}
        | {f.__name__ for f in _GIT_TOOLS}
        | {"web_fetch", "web_search"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "reviewer": (
        _FS_READONLY
        | {"code_symbols", "run_diagnostics"}
        | _GIT_READONLY
        | {"web_fetch", "web_search"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "fixer": (
        {f.__name__ for f in _FILESYSTEM_TOOLS}
        | {"code_symbols", "run_diagnostics"}
        | {"bash_exec"}
        | _GIT_READONLY
        | {"web_fetch", "web_search"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "pm": (
        {f.__name__ for f in _PM_MANAGEMENT_TOOLS}
        | {"task_create", "task_update", "task_query"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "director": (
        {f.__name__ for f in _DIRECTOR_MANAGEMENT_TOOLS}
        | {"task_create", "task_update", "task_query"}
        | {"todo_read", "todo_write", "todo_list"}
    ),
    "default": {f.__name__ for f in ALL_TOOL_FUNCTIONS},
}

# ---------------------------------------------------------------------------
# Agent name → role mapping
# ---------------------------------------------------------------------------

AGENT_ROLE_MAP: dict[str, str] = {
    "director": "director",
    "pm": "pm",
    "planner": "planner",
    "coder": "coder",
    "reviewer": "reviewer",
    "fixer": "fixer",
}


def resolve_role(readonly_context: ReadonlyContext | None) -> str:
    """Map an agent's name to its role.

    Resolution order:
    1. Exact match in AGENT_ROLE_MAP
    2. ``pm_`` prefix → ``"pm"``
    3. Fallback to ``"default"`` (all tools)
    """
    if readonly_context is None:
        return "default"
    name: str = readonly_context.agent_name
    if name in AGENT_ROLE_MAP:
        return AGENT_ROLE_MAP[name]
    if name.startswith("pm_"):
        return "pm"
    return "default"


# ---------------------------------------------------------------------------
# GlobalToolset
# ---------------------------------------------------------------------------


class GlobalToolset(BaseToolset):
    """Vends per-role FunctionTools based on permission config.

    ADK calls ``get_tools()`` during agent construction, passing a
    ``ReadonlyContext`` that identifies the requesting agent. The toolset
    filters the full catalog based on the role's permissions.
    """

    def __init__(
        self,
        *,
        excluded_tools: set[str] | None = None,
        tool_filter: list[str] | None = None,
        tool_name_prefix: str | None = None,
    ) -> None:
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._excluded: set[str] = excluded_tools or set()
        self._all_tools: list[BaseTool] = [
            FunctionTool(f)  # type: ignore[reportArgumentType]
            for f in ALL_TOOL_FUNCTIONS
        ]

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        """Return tools filtered by the agent's role."""
        role = resolve_role(readonly_context)
        allowed = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["default"])
        return [t for t in self._all_tools if t.name in allowed and t.name not in self._excluded]

    def get_tools_for_role(self, role: str) -> list[BaseTool]:
        """Return tools for an explicit role string, bypassing agent name lookup."""
        allowed = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["default"])
        return [t for t in self._all_tools if t.name in allowed and t.name not in self._excluded]
