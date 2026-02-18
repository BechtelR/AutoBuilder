# Phase 4 Model: Core Toolset
*Generated: 2026-02-17*

## Component Diagram

```mermaid
flowchart TB
    subgraph ENGINE["ENGINE LAYER (ADK orchestration — runs in workers)"]
        direction TB

        subgraph TOOLSET["AutoBuilderToolset (app/tools/toolset.py)"]
            ABT["AutoBuilderToolset\n(BaseToolset)"]
            RR["resolve_role()"]
            RP["ROLE_PERMISSIONS\nROLE: set[tool_name]"]
            ARM["AGENT_ROLE_MAP\nagent_name → role"]
            ABT --> RR --> ARM
            ABT --> RP
        end

        subgraph TOOLS["Tool Modules (app/tools/)"]
            FS["filesystem.py\nfile_read, file_write,\nfile_edit, file_search,\ndirectory_list"]
            EX["execution.py\nbash_exec"]
            GI["git.py\ngit_status, git_commit,\ngit_branch, git_diff"]
            WB["web.py\nweb_search, web_fetch"]
            TK["task.py\ntodo_read, todo_write,\ntodo_list"]
            PJ["project.py\nselect_ready_batch,\nenqueue_ceo_item"]
        end

        ABT -->|wraps as FunctionTool| FS & EX & GI & WB & TK & PJ
    end

    subgraph INFRA["INFRASTRUCTURE LAYER"]
        SET["Settings\n(app/config/settings.py)\nsearch_provider"]
        FSSYS["Filesystem\n(os, pathlib, glob)"]
        PROC["Subprocess\n(asyncio.create_subprocess_shell)"]
        GIT["Git CLI\n(subprocess)"]
        HTTP["httpx + beautifulsoup4\n(external web)"]
        SEARCH["Tavily / Brave API\n(search providers)"]
    end

    subgraph ADK["ADK FRAMEWORK (google.adk)"]
        FT["FunctionTool"]
        BTS["BaseToolset"]
        BT["BaseTool"]
        TC["ToolContext"]
        RC["ReadonlyContext"]
    end

    FS --> FSSYS
    EX --> PROC
    GI --> GIT
    WB --> HTTP & SEARCH
    TK -->|state via| TC
    EX -->|idempotency via| TC
    ABT -->|extends| BTS
    ABT -->|creates| FT
    ABT -->|returns| BT
    RR -->|reads| RC

    subgraph AGENTS["CONSUMER: LlmAgent (Phase 5)"]
        LA["LlmAgent\ntools=[toolset]"]
    end

    LA -->|get_tools(ctx)| ABT
```

## Deliverable-to-Component Traceability

| Deliverable | Components |
|---|---|
| P4.D1 | `filesystem.py`: `file_read`, `file_write`, `file_edit`, `file_search`, `directory_list`, path validation helper |
| P4.D2 | `execution.py`: `bash_exec`, idempotency guard (`temp:tool_runs:{key}` check/store) |
| P4.D3 | `git.py`: `git_status`, `git_commit`, `git_branch`, `git_diff`, git repo validation helper |
| P4.D4 | `web.py`: `web_fetch`, `web_search`, Tavily/Brave provider dispatch; `Settings` extension (`search_provider`) |
| P4.D5 | `task.py`: `todo_read`, `todo_write`, `todo_list` |
| P4.D6 | `project.py`: `select_ready_batch`, `enqueue_ceo_item`, validation constants |
| P4.D7 | `toolset.py`: `AutoBuilderToolset`, `resolve_role`, `ROLE_PERMISSIONS`, `AGENT_ROLE_MAP` |
| P4.D8 | `tests/tools/`: test modules for all above + schema generation tests + conftest fixtures |

## Major Interfaces

### AutoBuilderToolset — ADK-native tool vending

```python
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.agents.readonly_context import ReadonlyContext

class AutoBuilderToolset(BaseToolset):
    """Vends per-role tool subsets based on cascading permission config."""

    def __init__(
        self,
        *,
        excluded_tools: set[str] | None = None,
    ) -> None:
        """Creates FunctionTool instances for all 17 tool functions.
        excluded_tools removes tools from any role's allowed set."""
        ...

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        """Returns filtered tools for the requesting agent's role.
        Returns all tools when readonly_context is None."""
        ...
```

### Role Resolution

```python
def resolve_role(readonly_context: ReadonlyContext) -> str:
    """Maps agent name to role string via AGENT_ROLE_MAP.
    PM agents matched via prefix (startswith 'pm_').
    Unknown agents → 'default' (read-only)."""
    ...
```

### Tool Function Signatures — Filesystem

```python
# All return str. ADK auto-generates schema from type hints + docstring.

def file_read(path: str) -> str:
    """Read file contents. Returns the file content as text.""" ...

def file_write(path: str, content: str) -> str:
    """Write or create a file with the given content.""" ...

def file_edit(path: str, old: str, new: str) -> str:
    """Targeted string replacement within a file.""" ...

def file_search(pattern: str, path: str, content_pattern: str | None = None) -> str:
    """Search for files by glob pattern. If content_pattern provided,
    also grep file contents by regex, returning matching lines.""" ...

def directory_list(path: str) -> str:
    """List directory contents as a tree.""" ...
```

### Tool Function Signatures — Execution

```python
from google.adk.tools import ToolContext

async def bash_exec(
    command: str,
    cwd: str | None = None,
    timeout: int = 120,
    idempotency_key: str | None = None,
    tool_context: ToolContext | None = None,
) -> str:
    """Run a shell command with timeout and output capture.
    idempotency_key enables dedup via session state on ADK Resume."""
    ...
```

### Tool Function Signatures — Git

```python
async def git_status(path: str) -> str: ...
async def git_commit(path: str, message: str) -> str: ...
async def git_branch(path: str, name: str, action: GitBranchAction) -> str: ...
async def git_diff(path: str, ref: str | None = None) -> str: ...
```

### Tool Function Signatures — Web

```python
async def web_fetch(url: str) -> str:
    """Fetch URL content via httpx. Extracts text from HTML.""" ...

async def web_search(query: str, num_results: int = 5) -> str:
    """Search the web via configured provider (Tavily primary, Brave fallback).""" ...
```

### Tool Function Signatures — Task Management

```python
from google.adk.tools import ToolContext

def todo_read(task_id: str, tool_context: ToolContext) -> str: ...

def todo_write(
    action: TodoAction,
    task_id: str,
    content: str,
    tool_context: ToolContext,
) -> str: ...

def todo_list(
    status_filter: TodoStatus | None = None,
    tool_context: ToolContext,
) -> str: ...
```

### Tool Function Signatures — Project Management

```python
def select_ready_batch(project_id: str) -> str:
    """Placeholder — returns 'no deliverables' until Phase 8.""" ...

def enqueue_ceo_item(
    item_type: str, priority: str, message: str, metadata: str,
) -> str:
    """Validates item_type/priority, logs, returns placeholder ID.
    Real DB backend in Phase 5.""" ...
```

## Key Type Definitions

### Permission Configuration (module-level constants in toolset.py)

```python
# Agent name → role mapping
AGENT_ROLE_MAP: dict[str, str] = {
    "plan_agent": "planner",
    "code_agent": "coder",
    "review_agent": "reviewer",
    "fix_agent": "coder",
    "director": "director",
    # PM agents: matched via name.startswith("pm_")
}

# Role → allowed tool names
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "default":  {"file_read", "file_search", "directory_list", "git_status", "git_diff"},
    "planner":  {"file_read", "file_search", "directory_list", "web_fetch", "web_search",
                 "todo_read", "todo_list", "git_status", "git_diff"},
    "coder":    {"file_read", "file_write", "file_edit", "file_search", "directory_list",
                 "bash_exec", "git_status", "git_commit", "git_branch", "git_diff",
                 "web_fetch", "web_search", "todo_read", "todo_write", "todo_list"},
    "reviewer": {"file_read", "file_search", "directory_list", "git_status", "git_diff",
                 "web_fetch", "web_search", "todo_read", "todo_list"},
    "pm":       {"file_read", "file_search", "directory_list", "git_status", "git_diff",
                 "todo_read", "todo_write", "todo_list",
                 "select_ready_batch", "enqueue_ceo_item"},
    "director": {"file_read", "file_search", "directory_list", "git_status", "git_diff",
                 "todo_read", "todo_list", "enqueue_ceo_item"},
}
```

### CEO Queue Validation Constants (project.py — strings until Phase 5 enums)

```python
VALID_ITEM_TYPES: set[str] = {"NOTIFICATION", "APPROVAL", "ESCALATION", "TASK"}
VALID_PRIORITIES: set[str] = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
```

### Tool Parameter Enums (app/models/enums.py)

```python
import enum

class GitBranchAction(str, enum.Enum):
    CREATE = "CREATE"
    SWITCH = "SWITCH"
    DELETE = "DELETE"

class TodoAction(str, enum.Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    COMPLETE = "COMPLETE"
    REMOVE = "REMOVE"

class TodoStatus(str, enum.Enum):
    PENDING = "PENDING"
    DONE = "DONE"
```

### Role Type (internal to toolset.py)

```python
from typing import Literal

RoleName = Literal["default", "planner", "coder", "reviewer", "pm", "director"]
```

### Task State Schema (stored in session state under key "tasks")

```python
from typing import TypedDict

class TaskItem(TypedDict):
    id: str              # UUID
    content: str         # Task description
    status: TodoStatus   # PENDING or DONE
```

### Settings Extension (app/config/settings.py)

```python
# Added field (Pydantic Settings, env prefix AUTOBUILDER_)
search_provider: str = "tavily"     # AUTOBUILDER_SEARCH_PROVIDER

# API keys read from env directly (not AUTOBUILDER_ prefixed):
# TAVILY_API_KEY — Tavily search (primary)
# BRAVE_API_KEY — Brave search (fallback)
```

### Output Truncation Constant

```python
MAX_OUTPUT_LENGTH: int = 10_000  # Characters. Shared across bash_exec, git_diff, web_fetch.
```

## Data Flow

### Tool Invocation Flow (LLM → Tool → LLM)

```mermaid
sequenceDiagram
    participant LLM as LlmAgent (ADK)
    participant ADK as ADK Runtime
    participant TS as AutoBuilderToolset
    participant TF as FunctionTool
    participant FN as Tool Function
    participant ENV as Environment

    Note over LLM,TS: Agent construction (once)
    LLM->>TS: get_tools(readonly_context)
    TS->>TS: resolve_role(ctx) → role
    TS->>TS: filter by ROLE_PERMISSIONS[role]
    TS-->>LLM: list[BaseTool] (role-filtered)

    Note over LLM,ENV: Tool invocation (per call)
    LLM->>ADK: function_call(name, args)
    ADK->>TF: run_async(args, tool_context)
    TF->>FN: call(args, tool_context?)
    FN->>ENV: filesystem / subprocess / httpx
    ENV-->>FN: raw result
    FN-->>TF: str (formatted, truncated)
    TF-->>ADK: tool_response
    ADK-->>LLM: function_response(str)
```

### State Access Flow (ToolContext)

```mermaid
flowchart LR
    FN["Tool Function"] -->|read| TC_STATE["tool_context.state\n(session state snapshot)"]
    FN -->|write| TC_DELTA["tool_context.actions\n.state_delta[key] = val"]
    TC_DELTA -->|ADK persists via| EVT["Event(actions=\nEventActions(state_delta))"]
    EVT -->|writes to| DSS["DatabaseSessionService"]
```

## Logic / Process Flow

### bash_exec Idempotency Guard

```mermaid
flowchart TD
    START([bash_exec called]) --> HAS_KEY{idempotency_key\nprovided?}
    HAS_KEY -->|No| EXEC[Execute command]
    HAS_KEY -->|Yes| CHECK{"temp:tool_runs:{key}\nin state?"}
    CHECK -->|Yes| CACHED[Return cached result]
    CHECK -->|No| EXEC
    EXEC --> TIMEOUT{Timed out?}
    TIMEOUT -->|Yes| KILL[Kill process] --> ERR_TIMEOUT[Return timeout error]
    TIMEOUT -->|No| EXIT{Exit code?}
    EXIT -->|0| SUCCESS[Return stdout+stderr]
    EXIT -->|≠0| ERR_EXIT[Return "Exit code: N\n" + output]
    SUCCESS --> TRUNC{Length > 10000?}
    ERR_EXIT --> TRUNC
    TRUNC -->|Yes| TRUNCATE[Truncate + notice]
    TRUNC -->|No| STORE
    TRUNCATE --> STORE{Has idempotency_key?}
    STORE -->|Yes| SAVE["state_delta[\ntemp:tool_runs:{key}] = result"] --> DONE([Return result])
    STORE -->|No| DONE
```

### file_edit Idempotency

```
1. Read file content
2. If `old` found in content → replace with `new`, write file → "Edited successfully"
3. If `old` NOT found but `new` IS found → "Already edited" (idempotent)
4. If neither found → "Error: old text not found in file"
```

### Role Resolution

```
1. Look up readonly_context.agent_name in AGENT_ROLE_MAP → return role
2. If not found, check name.startswith("pm_") → return "pm"
3. Otherwise → return "default"
```

### AutoBuilderToolset.get_tools() Logic

```
1. If readonly_context is None → return all 17 tools (minus excluded_tools)
2. role = resolve_role(readonly_context)
3. allowed = ROLE_PERMISSIONS[role] - excluded_tools
4. Return [tool for tool in self._tools if tool.name in allowed]
```

## Integration Points

### Existing System

| Component | Interface | How This Phase Uses It |
|-----------|-----------|----------------------|
| `Settings` (`app/config/settings.py`) | `get_settings()` | Extended with `search_provider` field; API keys via `TAVILY_API_KEY`, `BRAVE_API_KEY` |
| `get_logger()` (`app/lib/logging`) | `get_logger("tools.{category}")` | All tool modules use structured logging |
| `AutoBuilderError` hierarchy (`app/lib/exceptions`) | `ValidationError`, `NotFoundError` | Tool internal errors (path validation, git repo check) — caught and returned as `str` to LLM |
| ADK `FunctionTool` (`google.adk.tools.function_tool`) | `FunctionTool(func)` | Wraps all 17 tool functions for schema auto-generation |
| ADK `BaseToolset` (`google.adk.tools.base_toolset`) | `get_tools(readonly_context)` | `AutoBuilderToolset` extends this for role-based vending |
| ADK `ToolContext` (`google.adk.tools`) | `tool_context.state`, `tool_context.actions.state_delta` | `todo_*` tools and `bash_exec` idempotency |
| ADK `ReadonlyContext` (`google.adk.agents.readonly_context`) | `readonly_context.agent_name` | `resolve_role()` reads agent name for role mapping |

### Future Phase Extensions

| Extension Point | Future Phase | Preparation |
|----------------|-------------|-------------|
| `enqueue_ceo_item` backend | Phase 5 | Correct signature + validation in place; replace log with `INSERT INTO ceo_queue` |
| `select_ready_batch` backend | Phase 8 | Correct signature in place; replace placeholder with topological sort over deliverables |
| `AGENT_ROLE_MAP` | Phase 5+ | New agent names added to map as agents are defined beyond Phase 4 defaults |
| `ROLE_PERMISSIONS` | Phase 5+ | New tool names added to role sets as new tools are created |
| `excluded_tools` cascading | Phase 5 | Director/PM pass `excluded_tools` when constructing subordinate agents' toolsets |
| `require_confirmation` | Phase 11 | `FunctionTool(bash_exec, require_confirmation=True)` for human-in-the-loop |
| Tool authoring by Director | Phase 13+ | Director writes new tool functions; CEO approval gate before activation |
| `web_search` providers | Phase 4+ | Add `elif provider == "new_provider":` branch for new search providers |
| `agent-browser` integration | Phase 7/13 | Vercel `agent-browser` CLI invoked via `bash_exec`. Workflow-specific. |

## Notes

- **All tool functions return `str`** — ADK feeds the return directly to the LLM. Errors are returned as descriptive strings, not raised as exceptions (the LLM needs to see the error to reason about it).
- **`tool_context` is auto-injected** by ADK when declared as a parameter. It does NOT appear in the schema sent to the LLM. Only `todo_*` tools and `bash_exec` (when using idempotency) need it.
- **Async vs sync**: `bash_exec`, `git_*`, `web_*` are `async` (subprocess/network I/O). `todo_*`, `file_*`, `project.*` are sync (filesystem/state reads are fast, no I/O worth awaiting). ADK handles both.
- **Path validation**: Filesystem tools validate that paths don't traverse outside the project root. This is a security boundary — tools run in worker processes with filesystem access.
- **No abstract class hierarchy for search providers** — a simple `if/elif` dispatch suffices. Tavily primary, Brave fallback. Adding a provider is adding a function + branch.
- **`agent-browser` resolved**: Vercel `agent-browser` CLI (Q8). Invoked via `bash_exec`. Workflow-specific, implemented in Phase 7/13.
- **`beautifulsoup4` dependency**: Required for `web_fetch` HTML-to-text extraction. Verify it's in `pyproject.toml` before building.
