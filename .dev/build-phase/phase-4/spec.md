# Phase 4 Spec: Core Toolset
*Generated: 2026-02-17*
*Updated: 2026-02-18*

## Overview

Phase 4 builds the complete FunctionTool layer that LLM agents use to interact with the environment — 42 tools across 8 categories: filesystem (10), code intelligence (2), execution (2), git (8), web (2), task management (6), PM management (6), and Director management (6) — plus the ADK-native `GlobalToolset` that vends per-role tool subsets based on cascading permission configuration. The architecture includes a Director queue for PM escalations (separate from the CEO queue) and a three-tier task system (session todos, shared tasks, DB deliverables). After this phase, any ADK LlmAgent can be constructed with role-appropriate tools whose schemas are auto-generated from type hints and docstrings.

This phase directly advances three core vision differentiators: **Deterministic + probabilistic composition** (#3) — tools are the deterministic side of the equation, providing reliable environment interaction that LLM agents invoke at their discretion. **Autonomous completion** (#1) — agents cannot "run until done" without filesystem, git, and execution tools. **Structured quality gates** (#6) — role-based tool restrictions (read-only for planners/reviewers, full access for coders, limited exec/git for fix agents) are enforced by the toolset at agent construction time, not by LLM prompting.

Key constraints: All tools execute in ARQ worker processes, never in the gateway. Tool functions are pure Python with full type hints — ADK auto-generates tool schemas from signatures and docstrings. The `GlobalToolset` uses ADK's native `BaseToolset.get_tools(readonly_context)` mechanism for context-sensitive tool vending. Management tools (PM and Director) have correct signatures and validation but operate against placeholder backends until Phases 5/8 provide the DB infrastructure. The escalation path is PM -> Director Queue -> Director -> resolves OR -> CEO Queue -> CEO.

## Features

- **Filesystem tools (10)** — Read, write, edit, insert, multi-edit, glob search, grep search, move, delete files; list directories with depth control — all within agent worktrees
- **Code intelligence tools (2)** — Tree-sitter symbol extraction and on-demand lint/type-check via configurable diagnostics
- **Shell execution (2)** — Run shell commands with timeout, output capture, error reporting, and idempotency guards for ADK Resume; structured HTTP requests for API testing
- **Git operations (8)** — Status, commit (with selective file staging), branch, diff, log, show, worktree management, and patch application for agent-managed repositories
- **Web tools (2)** — Fetch URL content and search the web (Tavily primary, Brave fallback)
- **Task management (6)** — Three-tier system: session-scoped todos (ADK ToolContext), cross-session shared tasks, and DB-backed deliverables (placeholder until Phase 5/8)
- **PM management tools (6)** — Batch selection, Director escalation, deliverable lifecycle management, dependency management (placeholder backends)
- **Director management tools (6)** — CEO queue communication, cross-project visibility, PM oversight, project context detection, dependency graph queries (placeholder backends)
- **GlobalToolset** — ADK-native `BaseToolset` subclass with per-role tool vending via `get_tools(readonly_context)`
- **Cascading permission config** — Role-based tool restrictions: read-only for planners/reviewers, full tools for coders, limited exec/git for fix agents, PM management tools for PM, Director management tools for Director

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 3: ADK Engine Integration | MET | 116 tests pass, 4 skipped (LLM), all quality gates clean. ADK Runner, FunctionTool, and BaseToolset operational in workers. |
| Open Question #7: Web search provider | RESOLVED | Tavily primary, Brave fallback. Simple `if/elif` dispatch. Env vars: `TAVILY_API_KEY`, `BRAVE_API_KEY`. |
| Open Question #8: Agent-browser integration | RESOLVED | Vercel `agent-browser` CLI (npm). Invoked via `bash_exec`. Implementation retargeted to Phase 7/13 (workflow-specific). |

**Note:** Phase 4 can be spec'd and partially developed in parallel with Phase 3 since tool functions are pure Python. Full integration testing (tools inside ADK LlmAgent) requires Phase 3 completion.

## Design Decisions

### DD-1: Tool Function Signatures and Return Types
All tool functions return `str`. ADK FunctionTool feeds the return value directly to the LLM as tool output. Results should be concise, structured text — not JSON blobs or verbose prose. Type hints on parameters are mandatory (ADK auto-generates the tool schema from them). Docstrings are mandatory (ADK uses them as tool descriptions for the LLM).

Functions that need session state access declare a `tool_context: ToolContext` parameter. ADK auto-injects it at runtime — the parameter does not appear in the tool schema sent to the LLM.

```python
from google.adk.tools import ToolContext

def todo_read(tool_context: ToolContext) -> str:
    """Read current task list from session state."""
    tasks = tool_context.state.get("tasks", [])
    # ...

# For tools without state needs, plain parameters:
def file_read(path: str, offset: int | None = None, limit: int | None = None) -> str:
    """Read file contents with optional line offset and limit."""
    # ...
```

### DD-2: Idempotent Tool Execution Guards (E11)
ADK's Resume feature may re-execute tools that already completed successfully. All tools must be safe to re-run:

- **Filesystem tools**: Naturally idempotent — `file_write` overwrites, `file_read` is pure, `file_edit` validates `old` content exists before replacing (fails gracefully if already edited). `file_insert`, `file_multi_edit`, `file_move`, `file_delete` check preconditions before acting.
- **`bash_exec`**: Not inherently idempotent. Includes an optional `idempotency_key` parameter. When provided, the tool checks `temp:tool_runs:{key}` in session state before executing. If the key exists, returns the cached result. After execution, stores the result under that key. This enables callers to ensure one-shot commands (like `npm install`) don't re-run.
- **Git tools**: Check current state before acting — `git_commit` verifies there are staged changes, `git_branch` checks if branch exists before creating.
- **Todo tools**: Session state operations are naturally idempotent (set overwrites).

### DD-3: Web Search Provider
Q7 resolved: **Tavily primary, Brave fallback**. Simple `if/elif` dispatch — no abstract class hierarchy.

- `web_fetch(url: str) -> str` — Direct URL fetching via `httpx` + HTML-to-text extraction via `beautifulsoup4` with `html.parser`. No provider dependency.
- `web_search(query: str, num_results: int = 5) -> str` — Dispatches to configured search provider. Settings: `AUTOBUILDER_SEARCH_PROVIDER` (default: `"tavily"`, fallback: `"brave"`), `TAVILY_API_KEY`, `BRAVE_API_KEY` (read from env directly, not `AUTOBUILDER_` prefixed — aligns with `.env`).

Tavily is the default (simple REST API, designed for AI agents, returns clean results). Brave Search API is the fallback provider. If the configured provider's API key is missing, returns a clear error message. Adding a new provider is adding an `elif` branch and a function.

Q8 resolved: Vercel `agent-browser` CLI (npm package). Agents invoke it via `bash_exec("agent-browser <command>")`. Implementation is workflow-specific (Phase 7/13) — no Phase 4 tooling needed beyond `bash_exec`.

### DD-4: Management Tools — Placeholder Backends
PM management tools (6) and Director management tools (6) require DB infrastructure that arrives in Phase 5 (CEO queue table, Director queue table, project configs) and Phase 8 (deliverable dependency resolution). In Phase 4:

- All 12 management tools have correct signatures, type hints, docstrings, and parameter validation.
- **PM tools** (6): `select_ready_batch`, `escalate_to_director`, `update_deliverable`, `query_deliverables`, `reorder_deliverables`, `manage_dependencies`. PM uses `escalate_to_director` to send issues to the Director queue.
- **Director tools** (6): `escalate_to_ceo`, `list_projects`, `query_project_status`, `override_pm`, `get_project_context`, `query_dependency_graph`. Only the Director can push to the CEO queue.
- `escalate_to_ceo` validates `item_type` against known values (`NOTIFICATION`, `APPROVAL`, `ESCALATION`, `TASK`) and `priority` against known values (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`). Logs the enqueued item via `get_logger("tools.management")` and returns a confirmation string with a placeholder ID. Phase 5 replaces the log with a DB insert.
- `escalate_to_director` validates `request_type` against known values (`ESCALATION`, `STATUS_REPORT`, `RESOURCE_REQUEST`, `PATTERN_ALERT`) and `priority` against known values (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`). Returns a confirmation with a placeholder ID. Phase 5 replaces with Director queue DB insert.
- `select_ready_batch` accepts a `project_id` and returns `"No deliverables configured for project {project_id}"`. Phase 8 replaces this with actual dependency resolution.
- All other management tools return appropriate placeholder messages indicating which phase provides the real backend.

This ensures the tools are callable from within an ADK LlmAgent (completion contract item 1), schemas are correct (item 2), and the toolset can vend them per role (item 3).

### DD-5: Cascading Permission Config Format
Permission config is a Python dict mapping role names to sets of allowed tool names. The config is defined in `app/tools/_toolset.py` as a module-level constant. Roles have explicit tool lists — no deep hierarchy.

```python
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "default": {"file_read", "file_glob", "file_grep", "directory_list", "git_status", "git_diff"},
    "planner": {
        "file_read", "file_glob", "file_grep", "directory_list",
        "code_symbols", "run_diagnostics",
        "git_status", "git_diff", "git_log", "git_show",
        "web_search", "web_fetch",
        "todo_read", "todo_write", "todo_list",
    },
    "coder": {
        "file_read", "file_write", "file_edit", "file_insert", "file_multi_edit",
        "file_glob", "file_grep", "file_move", "file_delete", "directory_list",
        "code_symbols", "run_diagnostics",
        "bash_exec", "http_request",
        "git_status", "git_commit", "git_branch", "git_diff",
        "git_log", "git_show", "git_worktree", "git_apply",
        "web_search", "web_fetch",
        "todo_read", "todo_write", "todo_list",
    },
    "reviewer": {
        "file_read", "file_glob", "file_grep", "directory_list",
        "code_symbols", "run_diagnostics",
        "git_status", "git_diff", "git_log", "git_show",
        "web_search", "web_fetch",
        "todo_read", "todo_write", "todo_list",
    },
    "fix_agent": {
        "file_read", "file_write", "file_edit", "file_insert", "file_multi_edit",
        "file_glob", "file_grep", "file_move", "file_delete", "directory_list",
        "code_symbols", "run_diagnostics",
        "bash_exec",
        "git_status", "git_diff", "git_log", "git_show",
        "web_search", "web_fetch",
        "todo_read", "todo_write", "todo_list",
    },
    "pm": {
        "select_ready_batch", "escalate_to_director", "update_deliverable",
        "query_deliverables", "reorder_deliverables", "manage_dependencies",
        "task_create", "task_update", "task_query",
        "todo_read", "todo_write", "todo_list",
    },
    "director": {
        "escalate_to_ceo", "list_projects", "query_project_status",
        "override_pm", "get_project_context", "query_dependency_graph",
        "task_create", "task_update", "task_query",
        "todo_read", "todo_write", "todo_list",
    },
}
```

Cascading restriction: a parent tier can further restrict children by providing an `excluded_tools` override. Default is permissive — all tools in the role set are available unless explicitly excluded. This is config-driven (dict), not code-driven (class hierarchy).

### DD-6: Role Resolution from ReadonlyContext
`resolve_role(readonly_context)` maps agent names to roles via a configurable dict. Convention: agent names encode their role (`plan_agent` -> `"planner"`, `code_agent` -> `"coder"`, `review_agent` -> `"reviewer"`, `fix_agent` -> `"fix_agent"`, `pm_*` -> `"pm"`, `director` -> `"director"`). Unknown agents get a `"default"` role with read-only tools. The mapping is a module-level dict in `_toolset.py`, extensible without code changes via settings in later phases.

```python
AGENT_ROLE_MAP: dict[str, str] = {
    "plan_agent": "planner",
    "code_agent": "coder",
    "review_agent": "reviewer",
    "fix_agent": "fix_agent",
    "director": "director",
}
# PM agents matched via prefix: name.startswith("pm_") -> "pm"
# Unknown agents -> "default" (read-only)
```

### DD-7: ToolContext Import and State Access
ADK's `ToolContext` enables tools to access session state. Import path: `from google.adk.tools import ToolContext`. Tools that need state declare `tool_context: ToolContext` as a parameter — ADK auto-injects it (excluded from the LLM-visible schema).

State reads: `tool_context.state.get("key", default)` — works immediately.
State writes: `tool_context.actions.state_delta["key"] = value` — persists via ADK's event system.

This is used by todo tools (read/write task lists in state) and bash_exec (idempotency key tracking in `temp:` scope).

## Deliverables

### P4.D1: Filesystem Tools
**Files:** `app/tools/filesystem.py`, `app/tools/__init__.py` (update)
**Depends on:** —
**Description:** Ten FunctionTool-compatible functions for filesystem operations within agent worktrees. Each function has full type hints and a docstring for ADK schema auto-generation. Operations are naturally idempotent per DD-2. All paths are validated to prevent directory traversal (must be within the working directory or configured project root).
**BOM Components:**
- [ ] `T01` — `file_read` FunctionTool
- [ ] `T02` — `file_write` FunctionTool
- [ ] `T03` — `file_edit` FunctionTool
- [ ] `T04` — `file_glob` FunctionTool
- [ ] `T04b` — `file_grep` FunctionTool
- [ ] `T05` — `directory_list` FunctionTool
- [ ] `T18` — `file_insert` FunctionTool
- [ ] `T19` — `file_multi_edit` FunctionTool
- [ ] `T20` — `file_move` FunctionTool
- [ ] `T21` — `file_delete` FunctionTool
- [ ] `TM01` — `app/tools/filesystem.py` module
**Requirements:**
- [ ] `file_read(path: str, offset: int | None = None, limit: int | None = None) -> str` reads and returns file contents with optional line offset and limit; returns error message for non-existent files (no exception to LLM)
- [ ] `file_write(path: str, content: str) -> str` creates or overwrites a file; creates parent directories if needed; returns confirmation with byte count
- [ ] `file_edit(path: str, old: str, new: str, replace_all: bool = False) -> str` performs targeted string replacement; returns error if `old` not found in file (idempotent — if `old` not found but `new` is present, reports already edited)
- [ ] `file_insert(path: str, line: int, content: str) -> str` inserts content at a specific line number, shifting existing lines down; returns confirmation
- [ ] `file_multi_edit(path: str, edits: list[dict[str, str]]) -> str` applies multiple non-overlapping edits atomically in a single pass; returns confirmation with edit count
- [ ] `file_glob(pattern: str, path: str | None = None) -> str` searches for files by glob pattern; returns matching file paths sorted by modification time
- [ ] `file_grep(pattern: str, path: str | None = None, glob: str | None = None, context: int | None = None) -> str` searches file contents by regex pattern with optional file filtering and context lines; returns matching lines with file paths and line numbers
- [ ] `file_move(src: str, dst: str) -> str` moves or renames a file; returns confirmation
- [ ] `file_delete(path: str) -> str` deletes a file; returns confirmation or error if not found
- [ ] `directory_list(path: str, depth: int | None = None) -> str` lists directory contents as a formatted tree with optional depth control (default 2 levels)
- [ ] All functions validate paths — reject absolute paths outside configured project root, reject `..` traversal
- [ ] All functions return `str` (error messages for failures, not exceptions)
- [ ] Module importable as `from app.tools.filesystem import file_read, file_write, file_edit, file_insert, file_multi_edit, file_glob, file_grep, file_move, file_delete, directory_list`
**Validation:**
- `uv run pyright app/tools/filesystem.py`
- `python -c "from app.tools.filesystem import file_read, file_write, file_edit, file_insert, file_multi_edit, file_glob, file_grep, file_move, file_delete, directory_list"`
- `uv run pytest tests/tools/test_filesystem.py -v`

---

### P4.D2: Execution Tools
**Files:** `app/tools/execution.py`
**Depends on:** —
**Description:** Shell execution tool with timeout, output capture, error reporting, and idempotency guards. Uses `asyncio.create_subprocess_shell` for async subprocess management. Includes the idempotency mechanism (E11) that checks `temp:tool_runs:{key}` in session state before executing when an idempotency key is provided. Also includes `http_request` for structured HTTP calls (API testing, webhooks).
**BOM Components:**
- [ ] `T06` — `bash_exec` FunctionTool
- [ ] `T24` — `http_request` FunctionTool
- [ ] `TM03` — `app/tools/execution.py` module
- [ ] `E11` — Idempotent tool execution guards
**Requirements:**
- [ ] `bash_exec(command: str, cwd: str | None = None, timeout: int = 120, idempotency_key: str | None = None, tool_context: ToolContext | None = None) -> str` runs a shell command via `asyncio.create_subprocess_shell`
- [ ] Returns combined stdout + stderr output, truncated to 10000 characters with truncation notice
- [ ] On timeout: kills the process and returns error message with the timeout value
- [ ] On non-zero exit code: returns output prefixed with `"Exit code: {code}\n"`
- [ ] When `idempotency_key` is provided and `tool_context` is available: checks `temp:tool_runs:{key}` in state; if present, returns cached result without executing; after execution, stores result in state via `tool_context.actions.state_delta`
- [ ] When `cwd` is provided: validates directory exists before execution
- [ ] `http_request(method: str, url: str, headers: dict[str, str] | None = None, body: str | None = None) -> str` makes a structured HTTP call via `httpx.AsyncClient`; returns status code + response body; truncates to 10000 characters
- [ ] Module importable as `from app.tools.execution import bash_exec, http_request`
**Validation:**
- `uv run pyright app/tools/execution.py`
- `python -c "from app.tools.execution import bash_exec, http_request"`
- `uv run pytest tests/tools/test_execution.py -v`

---

### P4.D3: Git Tools
**Files:** `app/tools/git.py`, `app/models/enums.py` (update)
**Depends on:** —
**Description:** Eight git operation tools for agent-managed repositories. All operations use `asyncio.create_subprocess_exec` with `git` CLI (not a Python git library). State-checking before mutation per DD-2 (idempotency). Adds `GitBranchAction` enum to `app/models/enums.py`.
**BOM Components:**
- [ ] `T07` — `git_status` FunctionTool
- [ ] `T08` — `git_commit` FunctionTool
- [ ] `T09` — `git_branch` FunctionTool
- [ ] `T10` — `git_diff` FunctionTool
- [ ] `T25` — `git_log` FunctionTool
- [ ] `T26` — `git_show` FunctionTool
- [ ] `T27` — `git_worktree` FunctionTool
- [ ] `T28` — `git_apply` FunctionTool
- [ ] `TM02` — `app/tools/git.py` module
**Requirements:**
- [ ] `git_status(path: str) -> str` returns `git status --porcelain` output; returns clean message if working tree is clean
- [ ] `git_commit(path: str, message: str, files: list[str] | None = None) -> str` stages changes and commits; when `files` provided, stages only those files; otherwise stages all changes (`git add -A`); returns error if nothing to commit (checks status first — idempotent)
- [ ] `GitBranchAction` enum (StrEnum) in `app/models/enums.py`: `CREATE = "CREATE"`, `SWITCH = "SWITCH"`, `DELETE = "DELETE"` — values match names (uppercase)
- [ ] `git_branch(path: str, name: str, action: GitBranchAction) -> str` checks branch existence before create (idempotent — returns success if branch already exists for create)
- [ ] `git_diff(path: str, ref: str | None = None) -> str` shows diff against `ref` (default: `HEAD`); truncates output to 10000 characters
- [ ] `git_log(path: str, count: int | None = None, ref: str | None = None) -> str` shows commit history with optional count limit and ref filter
- [ ] `git_show(path: str, ref: str) -> str` inspects a specific commit (message, diff, metadata)
- [ ] `git_worktree(path: str, action: str, branch: str | None = None) -> str` manages git worktrees for parallel execution across branches (add, remove, list)
- [ ] `git_apply(path: str, patch: str) -> str` applies a unified diff patch to the working tree
- [ ] All functions validate `path` is a git repository (contains `.git`)
- [ ] All git commands use `cwd=path` for subprocess execution
- [ ] Module importable as `from app.tools.git import git_status, git_commit, git_branch, git_diff, git_log, git_show, git_worktree, git_apply`
**Validation:**
- `uv run pyright app/tools/git.py`
- `python -c "from app.tools.git import git_status, git_commit, git_branch, git_diff, git_log, git_show, git_worktree, git_apply"`
- `uv run pytest tests/tools/test_git.py -v`

---

### P4.D4: Web Tools
**Files:** `app/tools/web.py`, `app/config/settings.py` (update)
**Depends on:** —
**Description:** URL fetching via `httpx` with HTML-to-text extraction, and web search via configurable provider (Tavily primary, Brave fallback per DD-3). Settings extended with `search_provider` field. `web_fetch` extracts text from HTML using `beautifulsoup4`. `web_search` dispatches to the configured provider's REST API.
**BOM Components:**
- [ ] `T11` — `web_search` FunctionTool
- [ ] `T12` — `web_fetch` FunctionTool
- [ ] `TM04` — `app/tools/web.py` module
**Requirements:**
- [ ] `web_fetch(url: str) -> str` fetches URL content via `httpx.AsyncClient` with 30s timeout; extracts text from HTML via `beautifulsoup4` `.get_text()`; returns raw content for non-HTML responses; truncates to 10000 characters
- [ ] `web_search(query: str, num_results: int = 5) -> str` calls the configured search provider API; returns formatted results (title, URL, snippet per result)
- [ ] `web_search` returns clear error message if the provider's API key is not configured
- [ ] `Settings` has `search_provider: str` defaulting to `"tavily"` (env var: `AUTOBUILDER_SEARCH_PROVIDER`)
- [ ] API keys read from env directly: `TAVILY_API_KEY`, `BRAVE_API_KEY` (not `AUTOBUILDER_` prefixed — aligns with `.env`)
- [ ] Tavily provider: POST to `https://api.tavily.com/search` with `api_key`, `query`, `max_results`; parse response `results` array
- [ ] Brave provider: GET to `https://api.search.brave.com/res/v1/web/search` with `X-Subscription-Token` header, `q` and `count` params; parse response `web.results` array
- [ ] Module importable as `from app.tools.web import web_search, web_fetch`
**Validation:**
- `uv run pyright app/tools/web.py app/config/settings.py`
- `python -c "from app.tools.web import web_search, web_fetch"`
- `uv run pytest tests/tools/test_web.py -v`

---

### P4.D5: Task Management Tools
**Files:** `app/tools/task.py`, `app/models/enums.py` (update)
**Depends on:** —
**Description:** Six task management tools operating at two tiers: session-scoped todos (via ADK `ToolContext` for state access, DD-7) and cross-session shared tasks (placeholder backend until Phase 5). Session todos are stored in session state under the key `"tasks"` as a list of dicts. Each todo has `id`, `content`, `status` (TodoStatus enum). ToolContext provides read access via `tool_context.state` and write access via `tool_context.actions.state_delta`. Shared tasks (`task_create`, `task_update`, `task_query`) have correct signatures but return placeholder responses until Phase 5 provides the DB backend. Adds `TodoAction` and `TodoStatus` enums to `app/models/enums.py`.
**BOM Components:**
- [ ] `T13` — `todo_read` FunctionTool
- [ ] `T14` — `todo_write` FunctionTool
- [ ] `T15` — `todo_list` FunctionTool
- [ ] `T29` — `task_create` FunctionTool
- [ ] `T30b` — `task_update` FunctionTool
- [ ] `T30c` — `task_query` FunctionTool
- [ ] `TM05` — `app/tools/task.py` module
**Requirements:**
- [ ] `todo_read(task_id: str, tool_context: ToolContext) -> str` reads a specific task by ID from session state; returns task content and status; returns error message if not found
- [ ] `TodoAction` enum (StrEnum) in `app/models/enums.py`: `ADD = "ADD"`, `UPDATE = "UPDATE"`, `COMPLETE = "COMPLETE"`, `REMOVE = "REMOVE"` — values match names
- [ ] `TodoStatus` enum (StrEnum) in `app/models/enums.py`: `PENDING = "PENDING"`, `DONE = "DONE"` — values match names
- [ ] `todo_write(action: TodoAction, task_id: str, content: str, tool_context: ToolContext) -> str` writes updated task list to state via `tool_context.actions.state_delta["tasks"]`; generates UUID-based `task_id` for `ADD` action (ignores provided `task_id`); returns confirmation
- [ ] `todo_list(status_filter: TodoStatus | None = None, tool_context: ToolContext) -> str` lists all tasks with optional status filter; returns formatted list
- [ ] `task_create(title: str, description: str, assignee: str | None = None, tags: list[str] | None = None) -> str` creates a cross-session task; placeholder backend returns confirmation with generated UUID
- [ ] `task_update(task_id: str, status: str | None = None, notes: str | None = None) -> str` updates a shared task; placeholder backend returns confirmation
- [ ] `task_query(filter: str | None = None, assignee: str | None = None) -> str` queries shared tasks; placeholder backend returns "No shared tasks configured (Phase 5)"
- [ ] `tool_context` parameter excluded from LLM-visible tool schema (ADK auto-injection)
- [ ] Module importable as `from app.tools.task import todo_read, todo_write, todo_list, task_create, task_update, task_query`
**Validation:**
- `uv run pyright app/tools/task.py`
- `python -c "from app.tools.task import todo_read, todo_write, todo_list, task_create, task_update, task_query"`
- `uv run pytest tests/tools/test_task.py -v`

---

### P4.D6: Management Tools
**Files:** `app/tools/management.py`
**Depends on:** —
**Description:** PM-level (6) and Director-level (6) management tools for batch operations, escalation, deliverable lifecycle, project oversight, and CEO communication. Per DD-4, all tools have correct signatures and validation but use placeholder backends. PM escalates via `escalate_to_director`; Director escalates via `escalate_to_ceo`. Real backends arrive in Phase 5 (CEO queue table, Director queue table, project configs) and Phase 8 (deliverable dependency resolution).
**BOM Components:**
- [ ] `T16` — `select_ready_batch` FunctionTool
- [ ] `T17` — `escalate_to_ceo` FunctionTool
- [ ] `T31` — `escalate_to_director` FunctionTool
- [ ] `T32b` — `update_deliverable` FunctionTool
- [ ] `T33b` — `query_deliverables` FunctionTool
- [ ] `T34b` — `reorder_deliverables` FunctionTool
- [ ] `T35b` — `manage_dependencies` FunctionTool
- [ ] `T36b` — `list_projects` FunctionTool
- [ ] `T37b` — `query_project_status` FunctionTool
- [ ] `T38` — `override_pm` FunctionTool
- [ ] `T39` — `get_project_context` FunctionTool
- [ ] `T40` — `query_dependency_graph` FunctionTool
- [ ] `TM06` — `app/tools/management.py` module
**Requirements:**
- [ ] **PM tools (6):**
- [ ] `select_ready_batch(project_id: str) -> str` accepts a project ID; returns `"No deliverables configured for project {project_id}. Batch selection requires deliverable infrastructure (Phase 8)."`
- [ ] `escalate_to_director(priority: str, context: str, request_type: str) -> str` validates `request_type` is one of `"ESCALATION"`, `"STATUS_REPORT"`, `"RESOURCE_REQUEST"`, `"PATTERN_ALERT"`; validates `priority` is one of `"LOW"`, `"NORMAL"`, `"HIGH"`, `"CRITICAL"`; returns validation error for invalid values; logs via `get_logger("tools.management")` and returns confirmation with a generated UUID placeholder ID
- [ ] `update_deliverable(deliverable_id: str, status: str, notes: str | None = None) -> str` validates parameters; returns placeholder confirmation
- [ ] `query_deliverables(project_id: str, status: str | None = None) -> str` returns placeholder "No deliverable infrastructure (Phase 5)"
- [ ] `reorder_deliverables(project_id: str, order: list[str]) -> str` validates parameters; returns placeholder confirmation
- [ ] `manage_dependencies(action: str, source_id: str, target_id: str | None = None) -> str` validates `action` is one of `"ADD"`, `"REMOVE"`, `"QUERY"`; returns placeholder response
- [ ] **Director tools (6):**
- [ ] `escalate_to_ceo(item_type: str, priority: str, message: str, metadata: str) -> str` validates `item_type` is one of `"NOTIFICATION"`, `"APPROVAL"`, `"ESCALATION"`, `"TASK"`; validates `priority` is one of `"LOW"`, `"NORMAL"`, `"HIGH"`, `"CRITICAL"`; returns validation error message for invalid values; logs via `get_logger("tools.management")` and returns confirmation with a generated UUID placeholder ID
- [ ] `list_projects(status: str | None = None) -> str` returns placeholder "No project infrastructure (Phase 5)"
- [ ] `query_project_status(project_id: str) -> str` returns placeholder response with project ID
- [ ] `override_pm(project_id: str, action: str, reason: str) -> str` validates `action` is one of `"PAUSE"`, `"RESUME"`, `"REORDER"`, `"CORRECT"`; returns placeholder confirmation
- [ ] `get_project_context(path: str | None = None) -> str` detects project type from filesystem (reads `package.json`, `pyproject.toml`, etc.); functional even in Phase 4
- [ ] `query_dependency_graph(project_id: str, deliverable_id: str | None = None) -> str` returns placeholder "No dependency infrastructure (Phase 8)"
- [ ] Validation uses string comparison against known values (not enum imports — CEO/Director queue enums arrive in Phase 5)
- [ ] Module importable as `from app.tools.management import select_ready_batch, escalate_to_director, update_deliverable, query_deliverables, reorder_deliverables, manage_dependencies, escalate_to_ceo, list_projects, query_project_status, override_pm, get_project_context, query_dependency_graph`
**Validation:**
- `uv run pyright app/tools/management.py`
- `python -c "from app.tools.management import select_ready_batch, escalate_to_ceo, escalate_to_director"`
- `uv run pytest tests/tools/test_management.py -v`

---

### P4.D6b: Code Intelligence Tools
**Files:** `app/tools/code.py`
**Depends on:** —
**Description:** Two code intelligence tools: tree-sitter-based symbol extraction and on-demand diagnostics (lint/type-check). `code_symbols` uses tree-sitter to parse source files and extract classes, functions, and imports. Language is auto-detected from file extension. `run_diagnostics` runs configurable lint/type-check tools on a file.
**BOM Components:**
- [ ] `T22` — `code_symbols` FunctionTool
- [ ] `T23` — `run_diagnostics` FunctionTool
- [ ] `TM07` — `app/tools/code.py` module
**Requirements:**
- [ ] `code_symbols(path: str, language: str | None = None) -> str` extracts symbols (classes, functions, imports) via tree-sitter; language auto-detected from file extension; returns formatted symbol list
- [ ] `run_diagnostics(path: str, tool: str | None = None) -> str` runs lint or type-check on a file; tool selection configurable per project; returns diagnostics output
- [ ] All functions validate paths within project root
- [ ] Module importable as `from app.tools.code import code_symbols, run_diagnostics`
**Validation:**
- `uv run pyright app/tools/code.py`
- `python -c "from app.tools.code import code_symbols, run_diagnostics"`
- `uv run pytest tests/tools/test_code.py -v`

---

### P4.D7: GlobalToolset + Role Permissions
**Files:** `app/tools/_toolset.py`
**Depends on:** P4.D1, P4.D2, P4.D3, P4.D4, P4.D5, P4.D6, P4.D6b
**Description:** ADK-native `BaseToolset` subclass that vends per-role tool subsets. `GlobalToolset` wraps all tool functions as `FunctionTool` instances and filters them based on the requesting agent's role (resolved from `ReadonlyContext`). Includes `resolve_role()` function, `ROLE_PERMISSIONS` config, and `AGENT_ROLE_MAP` for agent-name-to-role resolution per DD-5 and DD-6.
**BOM Components:**
- [ ] `TS01` — `GlobalToolset` (BaseToolset)
- [ ] `TS02` — `resolve_role()` (role from ReadonlyContext)
- [ ] `TS03` — Cascading permission config
- [ ] `TS04` — Role scoping: `plan_agent` (read-only)
- [ ] `TS05` — Role scoping: `code_agent` (full tools)
- [ ] `TS06` — Role scoping: `review_agent` (read-only)
- [ ] `TS07` — Role scoping: `fix_agent` (full FS, limited exec/git)
- [ ] `TS08` — Role scoping: PM (management + shared)
- [ ] `TS09` — Role scoping: Director (governance + shared)
**Requirements:**
- [ ] `GlobalToolset` extends `BaseToolset` from `google.adk.tools.base_toolset`
- [ ] Constructor creates exactly 42 `FunctionTool` instances (one per tool function from D1-D6b modules); accepts optional `excluded_tools: set[str]` for cascading restriction
- [ ] `get_tools(readonly_context: ReadonlyContext | None = None) -> list[BaseTool]` returns filtered tool list based on resolved role; returns all tools if `readonly_context` is `None`
- [ ] `resolve_role(readonly_context: ReadonlyContext) -> str` maps agent name to role via `AGENT_ROLE_MAP`; PM agents matched via `name.startswith("pm_")` prefix; unknown agents return `"default"`
- [ ] `"default"` role has read-only tools: `{"file_read", "file_glob", "file_grep", "directory_list", "git_status", "git_diff"}`
- [ ] `"planner"` role: read-only filesystem + code intelligence + git read + web + session todos
- [ ] `"coder"` role: full filesystem (10) + code intelligence (2) + full execution (2) + full git (8) + web (2) + session todos (3) = 27 tools
- [ ] `"reviewer"` role: read-only filesystem + code intelligence + git read + web + session todos (same as planner)
- [ ] `"fix_agent"` role: full filesystem (10) + code intelligence (2) + `bash_exec` only (no `http_request`) + read-only git (no commit/branch/worktree/apply) + web (2) + session todos (3)
- [ ] `"pm"` role: PM management (6) + shared tasks (3) + session todos (3) = 12 tools
- [ ] `"director"` role: Director management (6) + shared tasks (3) + session todos (3) = 12 tools
- [ ] `excluded_tools` parameter removes tools from the role's allowed set (cascading restriction)
- [ ] Module importable as `from app.tools._toolset import GlobalToolset, resolve_role`
**Validation:**
- `uv run pyright app/tools/_toolset.py`
- `python -c "from app.tools._toolset import GlobalToolset, resolve_role"`
- `uv run pytest tests/tools/test_toolset.py -v`

---

### P4.D8: Test Suite
**Files:** `tests/tools/__init__.py`, `tests/tools/conftest.py`, `tests/tools/test_filesystem.py`, `tests/tools/test_execution.py`, `tests/tools/test_git.py`, `tests/tools/test_web.py`, `tests/tools/test_task.py`, `tests/tools/test_management.py`, `tests/tools/test_code.py`, `tests/tools/test_toolset.py`
**Depends on:** P4.D7
**Description:** Tests covering all Phase 4 deliverables. Tool function tests use real filesystem/subprocess (per project testing standards — never mock local infrastructure). Web search tests mock external API calls (Tavily). ToolContext-dependent tests construct real ToolContext objects or test the underlying logic separately. Toolset tests verify role-based filtering with constructed ReadonlyContext objects.
**BOM Components:** *(none — testing infrastructure, not a BOM component)*
**Requirements:**
- [ ] **Filesystem tests**: `file_read` returns content of existing file (with and without offset/limit); returns error for non-existent file; `file_write` creates file and returns byte count; `file_edit` replaces content; `file_edit` reports "already edited" when `old` not found but `new` present; `file_insert` inserts at correct line; `file_multi_edit` applies multiple edits atomically; `file_glob` finds files by pattern; `file_grep` searches content with regex; `file_move` moves file; `file_delete` removes file; `directory_list` returns tree output with depth control; path traversal (`../`) is rejected
- [ ] **Execution tests**: `bash_exec("echo hello")` returns `"hello\n"`; `bash_exec` with timeout=1 on `sleep 10` returns timeout error; non-zero exit code includes exit code in output; output truncation at 10000 chars; `http_request` returns status code and response body (mock httpx)
- [ ] **Git tests** (use `tmp_path` fixture with `git init`): `git_status` on clean repo returns clean message; `git_commit` after file creation returns success; `git_commit` with selective `files` parameter stages only specified files; `git_commit` on clean repo returns nothing-to-commit; `git_branch` create + switch works; `git_diff` shows changes; `git_log` returns commit history; `git_show` displays commit details; `git_worktree` add/list/remove works; `git_apply` applies patch
- [ ] **Web tests**: `web_fetch` returns extracted text from HTML (mock httpx response); `web_fetch` truncates output at 10000 chars; `web_fetch` returns raw content for non-HTML; `web_search` with valid API key returns formatted results (mock Tavily API); `web_search` with Brave provider returns formatted results (mock Brave API); `web_search` without API key returns error message
- [ ] **Task tests**: `todo_write` add creates task; `todo_list` returns all tasks; `todo_read` returns specific task; `todo_write` complete marks task done; `todo_list` with filter returns filtered results; `task_create` returns placeholder confirmation; `task_update` returns placeholder confirmation; `task_query` returns placeholder message
- [ ] **Management tests**: `select_ready_batch` returns placeholder message; `escalate_to_ceo` with valid params returns confirmation; `escalate_to_ceo` with invalid `item_type` returns validation error; `escalate_to_director` with valid params returns confirmation; `escalate_to_director` with invalid `request_type` returns validation error; `get_project_context` detects project type from filesystem; all other management tools return appropriate placeholder responses
- [ ] **Code intelligence tests**: `code_symbols` extracts symbols from Python file; `code_symbols` auto-detects language from extension; `run_diagnostics` runs lint tool and returns output
- [ ] **Toolset tests**: `GlobalToolset` constructor creates 42 `FunctionTool` instances; `get_tools(None)` returns all tools; planner role gets read-only + code intelligence + web + todos; coder role gets 27 tools (full set minus management); reviewer role matches planner; fix_agent role gets full FS + limited exec/git; PM role includes 12 tools (PM management + shared tasks + todos); Director role includes 12 tools (Director management + shared tasks + todos); `excluded_tools={"bash_exec"}` removes bash from coder role; `resolve_role` maps `"plan_agent"` -> `"planner"`, `"code_agent"` -> `"coder"`, `"fix_agent"` -> `"fix_agent"`, unknown -> `"default"`
- [ ] **Schema generation tests**: Each `FunctionTool(func)` produces a schema where `name` matches `func.__name__`, description is a non-empty string derived from `func.__doc__`, and parameter names match the function signature (excluding `tool_context`)
- [ ] All Phase 2-3 tests continue to pass (no regressions)
- [ ] All quality gates exit 0: `uv run ruff check .`, `uv run pyright`, `uv run pytest`
**Validation:**
- `uv run pytest tests/tools/ -v`
- `uv run pytest tests/ --ignore=tests/phase1 --cov=app -v`

---

## Build Order

```
Batch 1 (parallel): P4.D1, P4.D2, P4.D3, P4.D4, P4.D5, P4.D6, P4.D6b
  D1:  Filesystem tools — app/tools/filesystem.py (10 tools)
  D2:  Execution tools — app/tools/execution.py (2 tools)
  D3:  Git tools — app/tools/git.py (8 tools)
  D4:  Web tools — app/tools/web.py, app/config/settings.py (2 tools)
  D5:  Task management tools — app/tools/task.py (6 tools)
  D6:  Management tools — app/tools/management.py (12 tools)
  D6b: Code intelligence tools — app/tools/code.py (2 tools)

Batch 2: P4.D7
  D7: Toolset — app/tools/_toolset.py (depends D1-D6b, wraps 42 tools)

Batch 3: P4.D8
  D8: Test suite — tests/tools/ (depends D7)
```

## Completion Contract Traceability

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | All 42 tools callable from within an ADK LlmAgent | P4.D1-D6b, P4.D7, P4.D8 | Schema generation tests verify FunctionTool wrapping; toolset vends tools to agents |
| 2 | Tool schemas auto-generated from type hints + docstrings | P4.D1-D6b, P4.D8 | Schema generation tests verify each tool produces correct schema with name, description, parameters |
| 3 | Toolset vends correct tool subsets per role configuration | P4.D7, P4.D8 | Toolset tests verify per-role filtering for planner, coder, reviewer, fix_agent, PM, Director |
| 4 | bash_exec handles timeout, output capture, error reporting | P4.D2, P4.D8 | Execution tests: timeout kills process, output captured, exit code reported |
| 5 | Code intelligence tools extract symbols and run diagnostics | P4.D6b, P4.D8 | Code intelligence tests verify tree-sitter extraction and diagnostics execution |
| 6 | Three-tier task system (todos/tasks/deliverables) has correct interfaces | P4.D5, P4.D6, P4.D8 | Task + management tests verify all 6 task-tier tools |
| 7 | PM escalation path uses Director queue | P4.D6, P4.D7, P4.D8 | PM role includes `escalate_to_director`; Director role includes `escalate_to_ceo` |
| 8 | Director management tools have correct signatures for Phase 5 integration | P4.D6, P4.D8 | Management tests verify all 6 Director tools accept correct params |
| 9 | fix_agent role has distinct permissions from coder (no git commit, no http_request) | P4.D7, P4.D8 | Toolset tests verify fix_agent has limited exec/git vs coder's full set |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| T01 | `file_read` FunctionTool | P4.D1 |
| T02 | `file_write` FunctionTool | P4.D1 |
| T03 | `file_edit` FunctionTool | P4.D1 |
| T04 | `file_glob` FunctionTool | P4.D1 |
| T04b | `file_grep` FunctionTool | P4.D1 |
| T05 | `directory_list` FunctionTool | P4.D1 |
| T18 | `file_insert` FunctionTool | P4.D1 |
| T19 | `file_multi_edit` FunctionTool | P4.D1 |
| T20 | `file_move` FunctionTool | P4.D1 |
| T21 | `file_delete` FunctionTool | P4.D1 |
| T06 | `bash_exec` FunctionTool | P4.D2 |
| T24 | `http_request` FunctionTool | P4.D2 |
| T07 | `git_status` FunctionTool | P4.D3 |
| T08 | `git_commit` FunctionTool | P4.D3 |
| T09 | `git_branch` FunctionTool | P4.D3 |
| T10 | `git_diff` FunctionTool | P4.D3 |
| T25 | `git_log` FunctionTool | P4.D3 |
| T26 | `git_show` FunctionTool | P4.D3 |
| T27 | `git_worktree` FunctionTool | P4.D3 |
| T28 | `git_apply` FunctionTool | P4.D3 |
| T11 | `web_search` FunctionTool | P4.D4 |
| T12 | `web_fetch` FunctionTool | P4.D4 |
| T13 | `todo_read` FunctionTool | P4.D5 |
| T14 | `todo_write` FunctionTool | P4.D5 |
| T15 | `todo_list` FunctionTool | P4.D5 |
| T29 | `task_create` FunctionTool | P4.D5 |
| T30b | `task_update` FunctionTool | P4.D5 |
| T30c | `task_query` FunctionTool | P4.D5 |
| T16 | `select_ready_batch` FunctionTool | P4.D6 |
| T17 | `escalate_to_ceo` FunctionTool | P4.D6 |
| T31 | `escalate_to_director` FunctionTool | P4.D6 |
| T32b | `update_deliverable` FunctionTool | P4.D6 |
| T33b | `query_deliverables` FunctionTool | P4.D6 |
| T34b | `reorder_deliverables` FunctionTool | P4.D6 |
| T35b | `manage_dependencies` FunctionTool | P4.D6 |
| T36b | `list_projects` FunctionTool | P4.D6 |
| T37b | `query_project_status` FunctionTool | P4.D6 |
| T38 | `override_pm` FunctionTool | P4.D6 |
| T39 | `get_project_context` FunctionTool | P4.D6 |
| T40 | `query_dependency_graph` FunctionTool | P4.D6 |
| T22 | `code_symbols` FunctionTool | P4.D6b |
| T23 | `run_diagnostics` FunctionTool | P4.D6b |
| TM01 | `app/tools/filesystem.py` | P4.D1 |
| TM02 | `app/tools/git.py` | P4.D3 |
| TM03 | `app/tools/execution.py` | P4.D2 |
| TM04 | `app/tools/web.py` | P4.D4 |
| TM05 | `app/tools/task.py` | P4.D5 |
| TM06 | `app/tools/management.py` | P4.D6 |
| TM07 | `app/tools/code.py` | P4.D6b |
| TS01 | `GlobalToolset` (BaseToolset) | P4.D7 |
| TS02 | `resolve_role()` | P4.D7 |
| TS03 | Cascading permission config | P4.D7 |
| TS04 | Role scoping: `plan_agent` (read-only) | P4.D7 |
| TS05 | Role scoping: `code_agent` (full tools) | P4.D7 |
| TS06 | Role scoping: `review_agent` (read-only) | P4.D7 |
| TS07 | Role scoping: `fix_agent` (full FS, limited exec/git) | P4.D7 |
| TS08 | Role scoping: PM (management + shared) | P4.D7 |
| TS09 | Role scoping: Director (governance + shared) | P4.D7 |
| V20 | Director queue type enum | P4.D6 |
| V21 | Director queue priority enum | P4.D6 |
| V22 | Director queue status enum | P4.D6 |
| E11 | Idempotent tool execution guards | P4.D2 |

*All 62 BOM components assigned to Phase 4 in `07-COMPONENTS.md` are mapped above. Zero unmapped.*

## Research Notes

### ADK Import Paths (Verified via Phase 3 Research + Phase 1 Findings)
```python
# FunctionTool — MUST use this path, not google.adk.tools
from google.adk.tools.function_tool import FunctionTool

# BaseToolset and BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.base_tool import BaseTool

# ToolContext — for state access within tool functions
from google.adk.tools import ToolContext

# ReadonlyContext — for role resolution in get_tools()
from google.adk.agents.readonly_context import ReadonlyContext
```

### FunctionTool Usage Pattern
```python
from google.adk.tools.function_tool import FunctionTool

# ADK auto-generates schema from type hints + docstring
tool = FunctionTool(file_read)

# Or pass plain functions to agent's tools list — ADK auto-wraps
agent = LlmAgent(name="coder", tools=[file_read, file_write])

# For require_confirmation support (Phase 11):
tool = FunctionTool(bash_exec, require_confirmation=True)
```

### BaseToolset.get_tools() API
```python
class BaseToolset:
    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        ...
```
ADK calls `get_tools()` during agent construction. `ReadonlyContext` provides:
- `agent_name: str` — name of the requesting agent
- `state: dict` — session state (read-only)
- `session: object` — current session
- `user_id: str` — user identifier

### ToolContext State Access Pattern
```python
from google.adk.tools import ToolContext

def my_tool(param: str, tool_context: ToolContext) -> str:
    # Read state (works immediately)
    value = tool_context.state.get("key", "default")

    # Write state (persists via ADK event system)
    tool_context.actions.state_delta["key"] = new_value

    return "result"
```
The `tool_context` parameter is auto-injected by ADK — not visible in the tool schema sent to the LLM.

### Existing Code Patterns to Follow
- **Enums**: `enum.StrEnum` with values matching names (`app/models/enums.py`)
- **BaseModel**: Inherit from `app.models.base.BaseModel` (`from_attributes=True`, `strict=True`)
- **Settings**: Access via `get_settings()` singleton from `app.config`
- **Logging**: `get_logger("tools.{category}")` from `app.lib.logging`
- **Exceptions**: Raise `AutoBuilderError` subclasses from `app.lib.exceptions`
- **Testing**: Real infrastructure, skip when unavailable; mock only external APIs

### Dependencies to Add
```
# pyproject.toml — new dependencies for Phase 4
beautifulsoup4  # HTML text extraction for web_fetch
httpx           # Already present (gateway tests) — verify
tree-sitter     # Code intelligence — symbol extraction
```

### Phase 3 Interfaces Phase 4 Depends On
- **ADK App Container**: `create_app_container(root_agent)` in `app/workers/adk.py`
- **Worker Context**: Shared resources in `ctx` dict (session_service, llm_router, redis)
- **Settings**: `get_settings()` from `app.config` — Phase 4 extends with `search_provider` field
- **Logging**: `get_logger()` from `app.lib.logging`
- **Exceptions**: `AutoBuilderError` hierarchy from `app.lib.exceptions`

### Tavily Search API Reference
```
POST https://api.tavily.com/search
Headers: Content-Type: application/json
Body: {
    "api_key": "...",
    "query": "search query",
    "max_results": 5,
    "search_depth": "basic"
}
Response: {
    "results": [
        {"title": "...", "url": "...", "content": "..."},
        ...
    ]
}
```

### Brave Search API Reference
```
GET https://api.search.brave.com/res/v1/web/search
Headers: X-Subscription-Token: <BRAVE_API_KEY>, Accept: application/json
Params: q=<query>&count=<num_results>
Response: {
    "web": {
        "results": [
            {"title": "...", "url": "...", "description": "..."},
            ...
        ]
    }
}
```
