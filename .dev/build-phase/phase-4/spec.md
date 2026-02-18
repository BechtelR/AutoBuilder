# Phase 4 Spec: Core Toolset
*Generated: 2026-02-17*

## Overview

Phase 4 builds the complete FunctionTool layer that LLM agents use to interact with the environment — filesystem, shell, git, web, task management, and project management operations — plus the ADK-native `AutoBuilderToolset` that vends per-role tool subsets based on cascading permission configuration. After this phase, any ADK LlmAgent can be constructed with role-appropriate tools whose schemas are auto-generated from type hints and docstrings.

This phase directly advances three core vision differentiators: **Deterministic + probabilistic composition** (#3) — tools are the deterministic side of the equation, providing reliable environment interaction that LLM agents invoke at their discretion. **Autonomous completion** (#1) — agents cannot "run until done" without filesystem, git, and execution tools. **Structured quality gates** (#6) — role-based tool restrictions (read-only for planners/reviewers, full access for coders) are enforced by the toolset at agent construction time, not by LLM prompting.

Key constraints: All tools execute in ARQ worker processes, never in the gateway. Tool functions are pure Python with full type hints — ADK auto-generates tool schemas from signatures and docstrings. The `AutoBuilderToolset` uses ADK's native `BaseToolset.get_tools(readonly_context)` mechanism for context-sensitive tool vending. Project management tools (`select_ready_batch`, `enqueue_ceo_item`) have correct signatures and validation but operate against placeholder backends until Phases 5/8 provide the DB infrastructure.

## Features

- **Filesystem tools** — Read, write, edit, search, and list files/directories within agent worktrees
- **Shell execution** — Run shell commands with timeout, output capture, error reporting, and idempotency guards for ADK Resume
- **Git operations** — Status, commit, branch, and diff for agent-managed repositories
- **Web tools** — Fetch URL content and search the web (Tavily primary, Brave fallback)
- **Task management** — Session-state-backed todo list for agent work tracking via ADK ToolContext
- **Project management tools** — Batch selection and CEO queue communication (placeholder backends, full integration in Phase 5/8)
- **AutoBuilderToolset** — ADK-native `BaseToolset` subclass with per-role tool vending via `get_tools(readonly_context)`
- **Cascading permission config** — Role-based tool restrictions: read-only for planners/reviewers, full tools for coders, batch tools for PM, governance tools for Director

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
def file_read(path: str) -> str:
    """Read file contents. Returns the file content as text."""
    # ...
```

### DD-2: Idempotent Tool Execution Guards (E11)
ADK's Resume feature may re-execute tools that already completed successfully. All tools must be safe to re-run:

- **Filesystem tools**: Naturally idempotent — `file_write` overwrites, `file_read` is pure, `file_edit` validates `old` content exists before replacing (fails gracefully if already edited).
- **`bash_exec`**: Not inherently idempotent. Includes an optional `idempotency_key` parameter. When provided, the tool checks `temp:tool_runs:{key}` in session state before executing. If the key exists, returns the cached result. After execution, stores the result under that key. This enables callers to ensure one-shot commands (like `npm install`) don't re-run.
- **Git tools**: Check current state before acting — `git_commit` verifies there are staged changes, `git_branch` checks if branch exists before creating.
- **Todo tools**: Session state operations are naturally idempotent (set overwrites).

### DD-3: Web Search Provider
Q7 resolved: **Tavily primary, Brave fallback**. Simple `if/elif` dispatch — no abstract class hierarchy.

- `web_fetch(url: str) -> str` — Direct URL fetching via `httpx` + HTML-to-text extraction via `beautifulsoup4` with `html.parser`. No provider dependency.
- `web_search(query: str, num_results: int = 5) -> str` — Dispatches to configured search provider. Settings: `AUTOBUILDER_SEARCH_PROVIDER` (default: `"tavily"`, fallback: `"brave"`), `TAVILY_API_KEY`, `BRAVE_API_KEY` (read from env directly, not `AUTOBUILDER_` prefixed — aligns with `.env`).

Tavily is the default (simple REST API, designed for AI agents, returns clean results). Brave Search API is the fallback provider. If the configured provider's API key is missing, returns a clear error message. Adding a new provider is adding an `elif` branch and a function.

Q8 resolved: Vercel `agent-browser` CLI (npm package). Agents invoke it via `bash_exec("agent-browser <command>")`. Implementation is workflow-specific (Phase 7/13) — no Phase 4 tooling needed beyond `bash_exec`.

### DD-4: Project Tools — Placeholder Backends
`select_ready_batch` and `enqueue_ceo_item` require DB infrastructure that arrives in Phase 5 (CEO queue table D05) and Phase 8 (deliverable dependency resolution). In Phase 4:

- Both tools have correct signatures, type hints, docstrings, and parameter validation.
- `enqueue_ceo_item` validates `item_type` against known values (`NOTIFICATION`, `APPROVAL`, `ESCALATION`, `TASK`) and `priority` against known values (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`). Logs the enqueued item via `get_logger("tools.project")` and returns a confirmation string with a placeholder ID. Phase 5 replaces the log with a DB insert.
- `select_ready_batch` accepts a `project_id` and returns `"No deliverables configured for project {project_id}"`. Phase 8 replaces this with actual dependency resolution.

This ensures the tools are callable from within an ADK LlmAgent (completion contract item 1), schemas are correct (item 2), and the toolset can vend them per role (item 3).

### DD-5: Cascading Permission Config Format
Permission config is a Python dict mapping role names to sets of allowed tool names. The config is defined in `app/tools/toolset.py` as a module-level constant. Roles inherit from a base set — no deep hierarchy, just explicit tool lists per role.

```python
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "default": {"file_read", "file_search", "directory_list", "git_status", "git_diff"},
    "planner": {"file_read", "file_search", "directory_list", "web_search", "web_fetch", "todo_read", "todo_list", "git_status", "git_diff"},
    "coder": {"file_read", "file_write", "file_edit", "file_search", "directory_list", "bash_exec", "git_status", "git_commit", "git_branch", "git_diff", "web_search", "web_fetch", "todo_read", "todo_write", "todo_list"},
    "reviewer": {"file_read", "file_search", "directory_list", "git_status", "git_diff", "web_search", "web_fetch", "todo_read", "todo_list"},
    "pm": {"file_read", "file_search", "directory_list", "git_status", "git_diff", "todo_read", "todo_write", "todo_list", "select_ready_batch", "enqueue_ceo_item"},
    "director": {"file_read", "file_search", "directory_list", "git_status", "git_diff", "todo_read", "todo_list", "enqueue_ceo_item"},
}
```

Cascading restriction: a parent tier can further restrict children by providing an `excluded_tools` override. Default is permissive — all tools in the role set are available unless explicitly excluded. This is config-driven (dict), not code-driven (class hierarchy).

### DD-6: Role Resolution from ReadonlyContext
`resolve_role(readonly_context)` maps agent names to roles via a configurable dict. Convention: agent names encode their role (`plan_agent` → `"planner"`, `code_agent` → `"coder"`, `review_agent` → `"reviewer"`, `fix_agent` → `"coder"`, `pm_*` → `"pm"`, `director` → `"director"`). Unknown agents get a `"default"` role with read-only tools. The mapping is a module-level dict in `toolset.py`, extensible without code changes via settings in later phases.

```python
AGENT_ROLE_MAP: dict[str, str] = {
    "plan_agent": "planner",
    "code_agent": "coder",
    "review_agent": "reviewer",
    "fix_agent": "coder",
    "director": "director",
}
# PM agents matched via prefix: name.startswith("pm_") → "pm"
# Unknown agents → "default" (read-only)
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
**Description:** Five FunctionTool-compatible functions for filesystem operations within agent worktrees. Each function has full type hints and a docstring for ADK schema auto-generation. Operations are naturally idempotent per DD-2. All paths are validated to prevent directory traversal (must be within the working directory or configured project root).
**BOM Components:**
- [ ] `T01` — `file_read` FunctionTool
- [ ] `T02` — `file_write` FunctionTool
- [ ] `T03` — `file_edit` FunctionTool
- [ ] `T04` — `file_search` FunctionTool
- [ ] `T05` — `directory_list` FunctionTool
- [ ] `T20` — `app/tools/filesystem.py` module
**Requirements:**
- [ ] `file_read(path: str) -> str` reads and returns file contents; returns error message for non-existent files (no exception to LLM)
- [ ] `file_write(path: str, content: str) -> str` creates or overwrites a file; creates parent directories if needed; returns confirmation with byte count
- [ ] `file_edit(path: str, old: str, new: str) -> str` performs targeted string replacement; returns error if `old` not found in file (idempotent — if `old` not found but `new` is present, reports already edited)
- [ ] `file_search(pattern: str, path: str, content_pattern: str | None = None) -> str` searches for files by glob pattern; when `content_pattern` is provided, also greps file contents by regex returning matching file paths and line numbers
- [ ] `directory_list(path: str) -> str` lists directory contents as a formatted tree (max 2 levels deep by default)
- [ ] All functions validate paths — reject absolute paths outside configured project root, reject `..` traversal
- [ ] All functions return `str` (error messages for failures, not exceptions)
- [ ] Module importable as `from app.tools.filesystem import file_read, file_write, file_edit, file_search, directory_list`
**Validation:**
- `uv run pyright app/tools/filesystem.py`
- `python -c "from app.tools.filesystem import file_read, file_write, file_edit, file_search, directory_list"`
- `uv run pytest tests/tools/test_filesystem.py -v`

---

### P4.D2: Execution Tools
**Files:** `app/tools/execution.py`
**Depends on:** —
**Description:** Shell execution tool with timeout, output capture, error reporting, and idempotency guards. Uses `asyncio.create_subprocess_shell` for async subprocess management. Includes the idempotency mechanism (E11) that checks `temp:tool_runs:{key}` in session state before executing when an idempotency key is provided.
**BOM Components:**
- [ ] `T06` — `bash_exec` FunctionTool
- [ ] `T22` — `app/tools/execution.py` module
- [ ] `E11` — Idempotent tool execution guards
**Requirements:**
- [ ] `bash_exec(command: str, cwd: str | None = None, timeout: int = 120, idempotency_key: str | None = None, tool_context: ToolContext | None = None) -> str` runs a shell command via `asyncio.create_subprocess_shell`
- [ ] Returns combined stdout + stderr output, truncated to 10000 characters with truncation notice
- [ ] On timeout: kills the process and returns error message with the timeout value
- [ ] On non-zero exit code: returns output prefixed with `"Exit code: {code}\n"`
- [ ] When `idempotency_key` is provided and `tool_context` is available: checks `temp:tool_runs:{key}` in state; if present, returns cached result without executing; after execution, stores result in state via `tool_context.actions.state_delta`
- [ ] When `cwd` is provided: validates directory exists before execution
- [ ] Module importable as `from app.tools.execution import bash_exec`
**Validation:**
- `uv run pyright app/tools/execution.py`
- `python -c "from app.tools.execution import bash_exec"`
- `uv run pytest tests/tools/test_execution.py -v`

---

### P4.D3: Git Tools
**Files:** `app/tools/git.py`, `app/models/enums.py` (update)
**Depends on:** —
**Description:** Four git operation tools for agent-managed repositories. All operations use `asyncio.create_subprocess_exec` with `git` CLI (not a Python git library). State-checking before mutation per DD-2 (idempotency). Adds `GitBranchAction` enum to `app/models/enums.py`.
**BOM Components:**
- [ ] `T07` — `git_status` FunctionTool
- [ ] `T08` — `git_commit` FunctionTool
- [ ] `T09` — `git_branch` FunctionTool
- [ ] `T10` — `git_diff` FunctionTool
- [ ] `T21` — `app/tools/git.py` module
**Requirements:**
- [ ] `git_status(path: str) -> str` returns `git status --porcelain` output; returns clean message if working tree is clean
- [ ] `git_commit(path: str, message: str) -> str` stages all changes (`git add -A`) and commits; returns error if nothing to commit (checks status first — idempotent)
- [ ] `GitBranchAction` enum (StrEnum) in `app/models/enums.py`: `CREATE = "CREATE"`, `SWITCH = "SWITCH"`, `DELETE = "DELETE"` — values match names (uppercase)
- [ ] `git_branch(path: str, name: str, action: GitBranchAction) -> str` checks branch existence before create (idempotent — returns success if branch already exists for create)
- [ ] `git_diff(path: str, ref: str | None = None) -> str` shows diff against `ref` (default: `HEAD`); truncates output to 10000 characters
- [ ] All functions validate `path` is a git repository (contains `.git`)
- [ ] All git commands use `cwd=path` for subprocess execution
- [ ] Module importable as `from app.tools.git import git_status, git_commit, git_branch, git_diff`
**Validation:**
- `uv run pyright app/tools/git.py`
- `python -c "from app.tools.git import git_status, git_commit, git_branch, git_diff"`
- `uv run pytest tests/tools/test_git.py -v`

---

### P4.D4: Web Tools
**Files:** `app/tools/web.py`, `app/config/settings.py` (update)
**Depends on:** —
**Description:** URL fetching via `httpx` with HTML-to-text extraction, and web search via configurable provider (Tavily primary, Brave fallback per DD-3). Settings extended with `search_provider` field. `web_fetch` extracts text from HTML using `beautifulsoup4`. `web_search` dispatches to the configured provider's REST API.
**BOM Components:**
- [ ] `T11` — `web_search` FunctionTool
- [ ] `T12` — `web_fetch` FunctionTool
- [ ] `T23` — `app/tools/web.py` module
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
**Description:** Session-state-backed task management tools using ADK `ToolContext` for state access (DD-7). Tasks are stored in session state under the key `"tasks"` as a list of dicts. Each task has `id`, `content`, `status` (TodoStatus enum). ToolContext provides read access via `tool_context.state` and write access via `tool_context.actions.state_delta`. Adds `TodoAction` and `TodoStatus` enums to `app/models/enums.py`.
**BOM Components:**
- [ ] `T13` — `todo_read` FunctionTool
- [ ] `T14` — `todo_write` FunctionTool
- [ ] `T15` — `todo_list` FunctionTool
- [ ] `T24` — `app/tools/task.py` module
**Requirements:**
- [ ] `todo_read(task_id: str, tool_context: ToolContext) -> str` reads a specific task by ID from session state; returns task content and status; returns error message if not found
- [ ] `TodoAction` enum (StrEnum) in `app/models/enums.py`: `ADD = "ADD"`, `UPDATE = "UPDATE"`, `COMPLETE = "COMPLETE"`, `REMOVE = "REMOVE"` — values match names
- [ ] `TodoStatus` enum (StrEnum) in `app/models/enums.py`: `PENDING = "PENDING"`, `DONE = "DONE"` — values match names
- [ ] `todo_write(action: TodoAction, task_id: str, content: str, tool_context: ToolContext) -> str` writes updated task list to state via `tool_context.actions.state_delta["tasks"]`; generates UUID-based `task_id` for `ADD` action (ignores provided `task_id`); returns confirmation
- [ ] `todo_list(status_filter: TodoStatus | None = None, tool_context: ToolContext) -> str` lists all tasks with optional status filter; returns formatted list
- [ ] `tool_context` parameter excluded from LLM-visible tool schema (ADK auto-injection)
- [ ] Module importable as `from app.tools.task import todo_read, todo_write, todo_list`
**Validation:**
- `uv run pyright app/tools/task.py`
- `python -c "from app.tools.task import todo_read, todo_write, todo_list"`
- `uv run pytest tests/tools/test_task.py -v`

---

### P4.D6: Project Management Tools
**Files:** `app/tools/project.py`
**Depends on:** —
**Description:** PM-level and Director-level tools for batch management and CEO communication. Per DD-4, both tools have correct signatures and validation but use placeholder backends — `enqueue_ceo_item` logs and returns a confirmation, `select_ready_batch` returns a "no deliverables" message. Real backends arrive in Phase 5 (CEO queue table) and Phase 8 (deliverable dependency resolution).
**BOM Components:**
- [ ] `T16` — `select_ready_batch` FunctionTool
- [ ] `T17` — `enqueue_ceo_item` FunctionTool
- [ ] `V16` — `enqueue_ceo_item` FunctionTool (events.md source — same tool as T17)
- [ ] `T25` — `app/tools/project.py` module
**Requirements:**
- [ ] `select_ready_batch(project_id: str) -> str` accepts a project ID; returns `"No deliverables configured for project {project_id}. Batch selection requires deliverable infrastructure (Phase 8)."`
- [ ] `enqueue_ceo_item(item_type: str, priority: str, message: str, metadata: str) -> str` validates `item_type` is one of `"NOTIFICATION"`, `"APPROVAL"`, `"ESCALATION"`, `"TASK"`; validates `priority` is one of `"LOW"`, `"NORMAL"`, `"HIGH"`, `"CRITICAL"`; returns validation error message for invalid values; logs via `get_logger("tools.project")` and returns confirmation with a generated UUID placeholder ID
- [ ] Validation uses string comparison against known values (not enum imports — CEO queue enums arrive in Phase 5)
- [ ] Module importable as `from app.tools.project import select_ready_batch, enqueue_ceo_item`
**Validation:**
- `uv run pyright app/tools/project.py`
- `python -c "from app.tools.project import select_ready_batch, enqueue_ceo_item"`
- `uv run pytest tests/tools/test_project.py -v`

---

### P4.D7: AutoBuilderToolset + Role Permissions
**Files:** `app/tools/toolset.py`
**Depends on:** P4.D1, P4.D2, P4.D3, P4.D4, P4.D5, P4.D6
**Description:** ADK-native `BaseToolset` subclass that vends per-role tool subsets. `AutoBuilderToolset` wraps all tool functions as `FunctionTool` instances and filters them based on the requesting agent's role (resolved from `ReadonlyContext`). Includes `resolve_role()` function, `ROLE_PERMISSIONS` config, and `AGENT_ROLE_MAP` for agent-name-to-role resolution per DD-5 and DD-6.
**BOM Components:**
- [ ] `T30` — `AutoBuilderToolset` (BaseToolset)
- [ ] `T31` — `resolve_role()` (role from ReadonlyContext)
- [ ] `T32` — Cascading permission config
- [ ] `T33` — Role scoping: `plan_agent` (read-only)
- [ ] `T34` — Role scoping: `code_agent` (full tools)
- [ ] `T35` — Role scoping: `review_agent` (read-only)
- [ ] `T36` — Role scoping: PM (batch + shared)
- [ ] `T37` — Role scoping: Director (governance + shared)
**Requirements:**
- [ ] `AutoBuilderToolset` extends `BaseToolset` from `google.adk.tools.base_toolset`
- [ ] Constructor creates exactly 17 `FunctionTool` instances (one per tool function from D1-D6 modules); accepts optional `excluded_tools: set[str]` for cascading restriction
- [ ] `get_tools(readonly_context: ReadonlyContext | None = None) -> list[BaseTool]` returns filtered tool list based on resolved role; returns all tools if `readonly_context` is `None`
- [ ] `resolve_role(readonly_context: ReadonlyContext) -> str` maps agent name to role via `AGENT_ROLE_MAP`; PM agents matched via `name.startswith("pm_")` prefix; unknown agents return `"default"`
- [ ] `"default"` role has read-only tools: `{"file_read", "file_search", "directory_list", "git_status", "git_diff"}`
- [ ] `"planner"` role: read-only filesystem + web + todo read + git read (no `file_write`, `file_edit`, `bash_exec`, `git_commit`, `git_branch`)
- [ ] `"coder"` role: full filesystem + execution + git + web + todo (no project tools)
- [ ] `"reviewer"` role: read-only filesystem + web + todo read + git read (same as planner)
- [ ] `"pm"` role: read-only filesystem + git read + todo + `select_ready_batch` + `enqueue_ceo_item`
- [ ] `"director"` role: read-only filesystem + git read + todo read + `enqueue_ceo_item`
- [ ] `excluded_tools` parameter removes tools from the role's allowed set (cascading restriction)
- [ ] Module importable as `from app.tools.toolset import AutoBuilderToolset, resolve_role`
**Validation:**
- `uv run pyright app/tools/toolset.py`
- `python -c "from app.tools.toolset import AutoBuilderToolset, resolve_role"`
- `uv run pytest tests/tools/test_toolset.py -v`

---

### P4.D8: Test Suite
**Files:** `tests/tools/__init__.py`, `tests/tools/conftest.py`, `tests/tools/test_filesystem.py`, `tests/tools/test_execution.py`, `tests/tools/test_git.py`, `tests/tools/test_web.py`, `tests/tools/test_task.py`, `tests/tools/test_project.py`, `tests/tools/test_toolset.py`
**Depends on:** P4.D7
**Description:** Tests covering all Phase 4 deliverables. Tool function tests use real filesystem/subprocess (per project testing standards — never mock local infrastructure). Web search tests mock external API calls (Tavily). ToolContext-dependent tests construct real ToolContext objects or test the underlying logic separately. Toolset tests verify role-based filtering with constructed ReadonlyContext objects.
**BOM Components:** *(none — testing infrastructure, not a BOM component)*
**Requirements:**
- [ ] **Filesystem tests**: `file_read` returns content of existing file; returns error for non-existent file; `file_write` creates file and returns byte count; `file_edit` replaces content; `file_edit` reports "already edited" when `old` not found but `new` present; `file_search` finds files by glob; `directory_list` returns tree output; path traversal (`../`) is rejected
- [ ] **Execution tests**: `bash_exec("echo hello")` returns `"hello\n"`; `bash_exec` with timeout=1 on `sleep 10` returns timeout error; non-zero exit code includes exit code in output; output truncation at 10000 chars
- [ ] **Git tests** (use `tmp_path` fixture with `git init`): `git_status` on clean repo returns clean message; `git_commit` after file creation returns success; `git_commit` on clean repo returns nothing-to-commit; `git_branch` create + switch works; `git_diff` shows changes
- [ ] **Web tests**: `web_fetch` returns extracted text from HTML (mock httpx response); `web_fetch` truncates output at 10000 chars; `web_fetch` returns raw content for non-HTML; `web_search` with valid API key returns formatted results (mock Tavily API); `web_search` with Brave provider returns formatted results (mock Brave API); `web_search` without API key returns error message
- [ ] **Task tests**: `todo_write` add creates task; `todo_list` returns all tasks; `todo_read` returns specific task; `todo_write` complete marks task done; `todo_list` with filter returns filtered results
- [ ] **Project tests**: `select_ready_batch` returns placeholder message; `enqueue_ceo_item` with valid params returns confirmation; `enqueue_ceo_item` with invalid `item_type` returns validation error
- [ ] **Toolset tests**: `AutoBuilderToolset` constructor creates 17 `FunctionTool` instances; `get_tools(None)` returns all tools; planner role gets exactly the read-only tool set; coder role gets full tools minus project tools; reviewer role matches planner; PM role includes `select_ready_batch`; Director role includes `enqueue_ceo_item`; `excluded_tools={"bash_exec"}` removes bash from coder role; `resolve_role` maps `"plan_agent"` → `"planner"`, `"code_agent"` → `"coder"`, unknown → `"default"`
- [ ] **Schema generation tests**: Each `FunctionTool(func)` produces a schema where `name` matches `func.__name__`, description is a non-empty string derived from `func.__doc__`, and parameter names match the function signature (excluding `tool_context`)
- [ ] All Phase 2-3 tests continue to pass (no regressions)
- [ ] All quality gates exit 0: `uv run ruff check .`, `uv run pyright`, `uv run pytest`
**Validation:**
- `uv run pytest tests/tools/ -v`
- `uv run pytest tests/ --ignore=tests/phase1 --cov=app -v`

---

## Build Order

```
Batch 1 (parallel): P4.D1, P4.D2, P4.D3, P4.D4, P4.D5, P4.D6
  D1: Filesystem tools — app/tools/filesystem.py
  D2: Execution tools — app/tools/execution.py
  D3: Git tools — app/tools/git.py
  D4: Web tools — app/tools/web.py, app/config/settings.py
  D5: Task management tools — app/tools/task.py
  D6: Project management tools — app/tools/project.py

Batch 2: P4.D7
  D7: AutoBuilderToolset — app/tools/toolset.py (depends D1-D6)

Batch 3: P4.D8
  D8: Test suite — tests/tools/ (depends D7)
```

## Completion Contract Traceability

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | All tools callable from within an ADK LlmAgent | P4.D1-D6, P4.D7, P4.D8 | Schema generation tests verify FunctionTool wrapping; toolset vends tools to agents |
| 2 | Tool schemas auto-generated from type hints + docstrings | P4.D1-D6, P4.D8 | Schema generation tests verify each tool produces correct schema with name, description, parameters |
| 3 | AutoBuilderToolset vends correct tool subsets per role configuration | P4.D7, P4.D8 | Toolset tests verify per-role filtering for planner, coder, reviewer, PM, Director |
| 4 | bash_exec handles timeout, output capture, error reporting | P4.D2, P4.D8 | Execution tests: timeout kills process, output captured, exit code reported |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| T01 | `file_read` FunctionTool | P4.D1 |
| T02 | `file_write` FunctionTool | P4.D1 |
| T03 | `file_edit` FunctionTool | P4.D1 |
| T04 | `file_search` FunctionTool | P4.D1 |
| T05 | `directory_list` FunctionTool | P4.D1 |
| T06 | `bash_exec` FunctionTool | P4.D2 |
| T07 | `git_status` FunctionTool | P4.D3 |
| T08 | `git_commit` FunctionTool | P4.D3 |
| T09 | `git_branch` FunctionTool | P4.D3 |
| T10 | `git_diff` FunctionTool | P4.D3 |
| T11 | `web_search` FunctionTool | P4.D4 |
| T12 | `web_fetch` FunctionTool | P4.D4 |
| T13 | `todo_read` FunctionTool | P4.D5 |
| T14 | `todo_write` FunctionTool | P4.D5 |
| T15 | `todo_list` FunctionTool | P4.D5 |
| T16 | `select_ready_batch` FunctionTool | P4.D6 |
| T17 | `enqueue_ceo_item` FunctionTool | P4.D6 |
| T20 | `app/tools/filesystem.py` | P4.D1 |
| T21 | `app/tools/git.py` | P4.D3 |
| T22 | `app/tools/execution.py` | P4.D2 |
| T23 | `app/tools/web.py` | P4.D4 |
| T24 | `app/tools/task.py` | P4.D5 |
| T25 | `app/tools/project.py` | P4.D6 |
| T30 | `AutoBuilderToolset` (BaseToolset) | P4.D7 |
| T31 | `resolve_role()` | P4.D7 |
| T32 | Cascading permission config | P4.D7 |
| T33 | Role scoping: `plan_agent` (read-only) | P4.D7 |
| T34 | Role scoping: `code_agent` (full tools) | P4.D7 |
| T35 | Role scoping: `review_agent` (read-only) | P4.D7 |
| T36 | Role scoping: PM (batch + shared) | P4.D7 |
| T37 | Role scoping: Director (governance + shared) | P4.D7 |
| E11 | Idempotent tool execution guards | P4.D2 |
| V16 | `enqueue_ceo_item` FunctionTool | P4.D6 |

*All 33 BOM components assigned to Phase 4 in `07-COMPONENTS.md` are mapped above. Zero unmapped.*

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
