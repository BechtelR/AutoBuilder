[← Architecture Overview](../02-ARCHITECTURE.md)

# Tools & GlobalToolset

## Overview

AutoBuilder's tool layer consists of **FunctionTools** -- thin Python wrappers that LLM agents call at their discretion. ADK auto-generates tool schemas from type hints and docstrings, so tools are just annotated functions.

This document covers FunctionTools only. For custom agents (deterministic pipeline participants like `SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`), see [Agents](./agents.md). The key distinction: tools are passive (LLM decides when to call them), agents are active (pipeline structure determines when they run).

**Tools execute in ARQ worker processes, not the FastAPI gateway.** The gateway exposes high-level REST endpoints (e.g., "run workflow", "get status"). It does not expose raw tool operations. FunctionTools run inside the ADK pipeline, which executes in worker processes. Tools have access to the worker's filesystem, subprocess environment, and git worktrees.

---

## 1. What ADK Provides

### 1.1 Usable Built-Ins

ADK provides excellent plumbing for building tools but almost nothing directly usable for AutoBuilder's needs. Most built-in tools are Gemini-only or GCP-specific.

| Tool | Module | Purpose |
|------|--------|---------|
| `load_web_page` | `load_web_page` | Fetch and parse URLs |
| `exit_loop` | `exit_loop_tool` | Break out of LoopAgent cycles |
| `get_user_choice` | `get_user_choice_tool` | Human-in-the-loop intervention points |
| `transfer_to_agent` | `transfer_to_agent_tool` | Dynamic agent delegation |
| `agent_tool` | `agent_tool` | Wrap agent as callable tool |
| `FunctionTool` | `function_tool` | Wrap any Python function as a tool (auto-schema from type hints + docstring) |
| `OpenAPIToolset` | `openapi_tool` | Generate tools from any OpenAPI spec |
| `LangChain adapter` | `langchain_tool` | Wrap any LangChain tool |

### 1.2 Not Usable (Gemini-Only or GCP-Specific)

| Tool | Reason Excluded |
|------|----------------|
| `google_search` | Gemini grounding only |
| `BuiltInCodeExecutor` | Gemini-only |
| `BigQuery` | GCP service |
| `enterprise_search_tool` | GCP service |
| `vertex_ai_search_tool` | GCP service |
| `apihub_tool` | GCP service |
| `application_integration_tool` | GCP service |
| `google_maps_grounding_tool` | GCP service |

---

## 2. MCP Approach

**Use sparingly.** MCPs are notorious for context bloat -- they inject tool schemas and protocol overhead that burns tokens. AutoBuilder prefers lightweight `FunctionTool` wrappers for most needs.

MCP is reserved for cases where a well-maintained server provides substantial value that cannot easily be replicated (e.g., complex database connectors). For browser automation, use agent-browser (purpose-built, lighter footprint) instead of Playwright MCP.

See consolidated planning doc for rationale.

---

## 3. AutoBuilder Core Toolset (FunctionTools)

Each of these is a thin Python function (~5-30 lines) that ADK auto-wraps via `FunctionTool`. ADK generates the tool schema automatically from type hints and docstrings -- no manual schema definition required. These are `FunctionTool` wrappers: the LLM decides when and whether to call them, unlike custom agents which run unconditionally at pipeline positions.

All FunctionTools execute inside worker processes. They have direct access to the worker's filesystem and subprocess environment. The gateway never calls these tools directly -- it only enqueues workflow jobs that workers execute.

**47 tools across 8 categories.**

### 3.1 Filesystem Tools (10 tools)

| Tool | Status | Purpose |
|------|--------|---------|
| `file_read(path, offset?, limit?)` | Keep | Read file contents |
| `file_write(path, content)` | Keep | Create/overwrite file |
| `file_edit(path, old, new, replace_all?)` | Keep | Targeted string replacement |
| `file_insert(path, line, content)` | **New** | Insert content at line number |
| `file_multi_edit(path, edits)` | **New** | Atomic multi-site replacements |
| `file_glob(pattern, path?)` | **New** | Find files by name pattern |
| `file_grep(pattern, path?, glob?, context?)` | **New** | Search file contents by regex |
| `file_move(src, dst)` | **New** | Move/rename file |
| `file_delete(path)` | **New** | Delete file |
| `directory_list(path, depth?)` | Enhanced | Add depth control |

```python
def file_read(path: str, offset: int | None = None, limit: int | None = None) -> str:
    """Read file contents with optional line offset and limit."""

def file_write(path: str, content: str) -> str:
    """Write or create a file with the given content."""

def file_edit(path: str, old: str, new: str, replace_all: bool = False) -> str:
    """Targeted string replacement within a file."""

def file_insert(path: str, line: int, content: str) -> str:
    """Insert content at a specific line number, shifting existing lines down."""

def file_multi_edit(path: str, edits: list[dict[str, str]]) -> str:
    """Apply multiple non-overlapping edits atomically in a single pass."""

def file_glob(pattern: str, path: str | None = None) -> str:
    """Find files by name pattern (glob syntax). Returns matching paths."""

def file_grep(pattern: str, path: str | None = None, glob: str | None = None, context: int | None = None) -> str:
    """Search file contents by regex pattern with optional file filtering and context lines."""

def file_move(src: str, dst: str) -> str:
    """Move or rename a file."""

def file_delete(path: str) -> str:
    """Delete a file."""

def directory_list(path: str, depth: int | None = None) -> str:
    """List directory contents as a tree with optional depth control."""
```

### 3.2 Code Intelligence (2 tools)

| Tool | Purpose |
|------|---------|
| `code_symbols(path, language?)` | Tree-sitter symbol extraction (classes, functions, imports). Language auto-detected. Grammars are runtime config. |
| `run_diagnostics(path, tool?)` | On-demand lint/type-check. Tool selection configurable per project. |

```python
def code_symbols(path: str, language: str | None = None) -> str:
    """Extract symbols (classes, functions, imports) via tree-sitter. Language auto-detected from extension."""

def run_diagnostics(path: str, tool: str | None = None) -> str:
    """Run lint or type-check on a file. Tool selection configurable per project."""
```

### 3.3 Execution Tools (2 tools)

| Tool | Status | Purpose |
|------|--------|---------|
| `bash_exec(command, cwd?, timeout?)` | Keep | Shell execution with timeout/capture |
| `http_request(method, url, headers?, body?)` | **New** | Structured HTTP calls (API testing, webhooks) |

```python
def bash_exec(command: str, cwd: str | None = None, timeout: int | None = None) -> str:
    """Run a shell command. Subprocess wrapper with timeout and output capture."""

def http_request(method: str, url: str, headers: dict[str, str] | None = None, body: str | None = None) -> str:
    """Structured HTTP call for API testing, webhooks, and external service interaction."""
```

Note: `bash_exec` must be idempotent or include duplicate-run protection for compatibility with ADK's Resume feature (tools may run more than once on resume).

### 3.4 Git Tools (8 tools)

| Tool | Status | Purpose |
|------|--------|---------|
| `git_status(path)` | Keep | Repo state |
| `git_commit(path, message, files?)` | Enhanced | Add selective file staging |
| `git_branch(path, name, action: GitBranchAction)` | Keep | Branch management |
| `git_diff(path, ref?)` | Keep | Show changes |
| `git_log(path, count?, ref?)` | **New** | Commit history |
| `git_show(path, ref)` | **New** | Inspect specific commit |
| `git_worktree(path, action: GitWorktreeAction, branch?)` | **New** | Manage worktrees (parallel execution) |
| `git_apply(path, patch)` | **New** | Apply unified diff patch |

```python
def git_status(path: str) -> str:
    """Current repository state."""

def git_commit(path: str, message: str, files: list[str] | None = None) -> str:
    """Stage and commit changes. Optional selective file staging."""

def git_branch(path: str, name: str, action: GitBranchAction) -> str:
    """Create, switch, or delete branches."""

def git_diff(path: str, ref: str | None = None) -> str:
    """Show changes against a reference."""

def git_log(path: str, count: int | None = None, ref: str | None = None) -> str:
    """Show commit history with optional count limit and ref filter."""

def git_show(path: str, ref: str) -> str:
    """Inspect a specific commit (message, diff, metadata)."""

def git_worktree(path: str, action: GitWorktreeAction, branch: str | None = None) -> str:
    """Manage git worktrees for parallel execution across branches."""

def git_apply(path: str, patch: str) -> str:
    """Apply a unified diff patch to the working tree."""
```

### 3.5 Web Tools (2 tools)

```python
def web_search(query: str, num_results: int = 5, provider: str | None = None) -> str:
    """Search the web via SearXNG, Brave, or Tavily API. No Gemini dependency."""

def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL. Supplements ADK's load_web_page if needed."""
```

Search provider defaults to `settings.search_provider` (Tavily). Override per-call via `provider` param.

### 3.6 Task Management (6 tools)

Task management operates at three tiers:

- **Deliverables** (DB truth source) -- PM-managed, dependency-tracked, lifecycle-managed
- **Tasks** (cross-session shared) -- visible across agent sessions within a project
- **Todos** (session-scoped) -- agent scratchpad, dies with session

| Tool | Tier | Status | Purpose |
|------|------|--------|---------|
| `todo_read()` | Session | Keep | Read session todo list |
| `todo_write(action, task_id, content)` | Session | Keep | Modify session todo |
| `todo_list(filter?)` | Session | Keep | List session todos |
| `task_create(title, description, assignee?, tags?)` | Shared | **New** | Create cross-session task |
| `task_update(task_id, status?, notes?)` | Shared | **New** | Update shared task |
| `task_query(filter?, assignee?)` | Shared | **New** | Query shared tasks |

```python
def todo_read() -> str:
    """Read current task list from session state."""

def todo_write(action: TodoAction, task_id: str, content: str) -> str:
    """Add, update, complete, or remove tasks."""

def todo_list(filter: str | None = None) -> str:
    """List tasks with optional status filter."""

def task_create(title: str, description: str, assignee: str | None = None, tags: list[str] | None = None) -> str:
    """Create a cross-session task visible to all agents in the project."""

def task_update(task_id: str, status: TaskStatus | None = None, notes: str | None = None) -> str:
    """Update a shared task's status or add notes."""

def task_query(status: TaskStatus | None = None, assignee: str | None = None) -> str:
    """Query shared tasks with optional status filter and assignee."""
```

### 3.7 PM Management Tools (7 tools)

| Tool | Status | Purpose |
|------|--------|---------|
| `select_ready_batch(project_id)` | Keep | Dependency-aware batch selection |
| `escalate_to_director(priority: EscalationPriority, context, request_type: EscalationRequestType)` | **New** | PM → Director queue |
| `update_deliverable(deliverable_id, status, notes?)` | **New** | Deliverable lifecycle management |
| `query_deliverables(project_id, status?)` | **New** | Query deliverable state |
| `reorder_deliverables(project_id, order)` | **New** | Change execution priority |
| `manage_dependencies(action: DependencyAction, source_id, target_id?)` | **New** | Add/remove/query deliverable deps |
| `reconfigure_stage(target_stage, reason)` | **New** | Advance workflow to next sequential stage |

```python
def select_ready_batch(project_id: str) -> str:
    """Dependency-aware batch selection via topological sort. Returns the next
    set of deliverables whose prerequisites are satisfied."""

def escalate_to_director(priority: EscalationPriority, context: str, request_type: EscalationRequestType) -> str:
    """Escalate an issue from PM to the Director queue for resolution."""

def update_deliverable(deliverable_id: str, status: DeliverableStatus, notes: str | None = None) -> str:
    """Update a deliverable's lifecycle status with optional notes."""

def query_deliverables(project_id: str, status: str | None = None) -> str:
    """Query deliverable state for a project, optionally filtered by status."""

def reorder_deliverables(project_id: str, order: list[str]) -> str:
    """Change execution priority by reordering deliverables."""

def manage_dependencies(action: DependencyAction, source_id: str, target_id: str | None = None) -> str:
    """Add, remove, or query deliverable dependency relationships."""

def reconfigure_stage(target_stage: str, reason: str) -> str:
    """Advance the workflow to the next sequential stage with validation."""
```

**Note:** `checkpoint_project` and `run_regression_tests` are **not FunctionTools** -- they must not be skippable by LLM judgment.

**Two-tier checkpointing** (Phase 8a Decision D3):

- **Tier 1 — Per-deliverable (automatic):** An `after_agent_callback` on DeliverablePipeline fires after each deliverable completes, persisting lightweight state (deliverable status, result data) to the DB via `CallbackContext`. This provides crash safety -- a checkpointed deliverable never re-executes after a system crash (FR-8a.48).
- **Tier 2 — Per-TaskGroup (PM-triggered):** The PM calls `checkpoint_project` explicitly at TaskGroup boundaries to persist a full `CriticalStateSnapshot` (deliverable statuses, batch position, stage progress, accumulated cost, hard limits, loaded skill names, project config, workflow ID, completed stages). This snapshot is what context recreation (Decision D4) uses to rebuild state after budget threshold or crash. The PM drives the outer loop and knows when TaskGroups complete, so explicit invocation is simpler than a callback.

`run_regression_tests` is a `RegressionTestAgent` (CustomAgent) wired into the pipeline after each batch -- it reads the PM's regression policy from session state, runs tests when the policy says to, and no-ops otherwise. Always present in the pipeline, policy-aware. See [Agents](./agents.md) for details.

### 3.8 Director Management Tools (10 tools)

| Tool | Status | Purpose |
|------|--------|---------|
| `validate_brief(brief, workflow_name?)` | **New** (D10) | Validate CEO brief against workflow requirements |
| `create_project(workflow_name, brief, entry_mode)` | **New** (D10) | Create project record bound to workflow type |
| `check_resources(workflow_name, project_id?)` | **New** (D10) | Verify resource availability before execution |
| `delegate_to_pm(project_id)` | **New** (D10) | Delegate project to PM for autonomous execution |
| `escalate_to_ceo(type: CeoItemType, priority: EscalationPriority, message, metadata)` | Keep (Director-only now) | Director → CEO queue |
| `list_projects(status?)` | **New** | Cross-project visibility |
| `query_project_status(project_id)` | **New** | PM status, batch progress, cost |
| `override_pm(project_id, action: PmOverrideAction, reason)` | **New** | Direct PM intervention (pause/resume/reorder/correct) |
| `get_project_context(path?)` | **New** | Detect project type, stack, conventions |
| `query_dependency_graph(project_id, deliverable_id?)` | **New** | Query/visualize dependency graph |

```python
def validate_brief(brief: str, workflow_name: str | None = None) -> str:
    """Validate a CEO brief against workflow requirements. Returns validation
    result with any missing fields or ambiguities. If workflow_name is omitted,
    also resolves the best-matching workflow type."""

def create_project(workflow_name: str, brief: str, entry_mode: EntryMode) -> str:
    """Create a new project record bound to a workflow type. Sets initial status
    to SHAPING. Returns the project ID."""

def check_resources(workflow_name: str, project_id: str | None = None) -> str:
    """Verify that all required resources (credentials, services, knowledge)
    declared in the workflow manifest are available before execution begins."""

def delegate_to_pm(project_id: str) -> str:
    """Delegate a project to a PM agent for autonomous execution. The PM
    receives the project context and begins the execution loop."""

def escalate_to_ceo(item_type: CeoItemType, priority: EscalationPriority, message: str, metadata: str) -> str:
    """Push a notification, approval request, escalation, or task to the unified
    CEO queue. Director-only — PM uses escalate_to_director instead."""

def list_projects(status: str | None = None) -> str:
    """List all projects with optional status filter for cross-project visibility."""

def query_project_status(project_id: str) -> str:
    """Query detailed project status including PM state, batch progress, and cost."""

def override_pm(project_id: str, action: PmOverrideAction, reason: str) -> str:
    """Direct PM intervention: pause, resume, reorder, or correct a PM's behavior."""

def get_project_context(path: str | None = None) -> str:
    """Detect project type, technology stack, and conventions from the codebase."""

def query_dependency_graph(project_id: str, deliverable_id: str | None = None) -> str:
    """Query or visualize the deliverable dependency graph for a project."""
```

### 3.9 FunctionTool Registration

Tools are Python functions in the `app/tools/` module, organized by function type. ADK auto-wraps them via `FunctionTool`:

```python
from google.adk.tools.function_tool import FunctionTool

# ADK auto-generates the tool schema from type hints + docstring
tool = FunctionTool(file_read)
```

`GlobalToolset` (see Section 7) handles per-role tool filtering via ADK's native `BaseToolset.get_tools(readonly_context)`. Workflows declare which tools they require in their `WORKFLOW.yaml` manifest via `required_tools` and `optional_tools`.

---

## 4. Gateway vs. Worker Tool Boundary

The gateway and workers have distinct roles with respect to tools:

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **Gateway (FastAPI)** | High-level REST endpoints. Enqueue jobs, query status, stream events. | `POST /workflows/run`, `GET /workflows/{id}/status`, `GET /workflows/{id}/events` (SSE) |
| **Worker (ARQ + ADK)** | Execute ADK pipelines. FunctionTools and custom agents run here. | `file_write`, `bash_exec`, `git_commit`, `SkillLoaderAgent`, `LinterAgent` |

The gateway does not proxy raw tool calls. A client never sends "write this file" to the gateway -- it sends "run this workflow with this spec." The worker's ADK pipeline decides which tools to invoke and when.

This boundary matters because:

1. **Security** -- filesystem/subprocess access is contained to workers, not exposed via API
2. **Scalability** -- workers can scale independently of the gateway
3. **Isolation** -- a misbehaving tool (infinite loop, memory leak) affects only its worker, not the gateway
4. **Swappability** -- ADK is an internal engine; the gateway could theoretically swap it out without changing the API surface

---

## 5. How Tools and Agents Compose in the Pipeline

FunctionTools and custom agents serve different roles in the pipeline:

- **FunctionTools** are passive: LLM agents decide when to call them during their reasoning steps.
- **Custom agents** are active: they execute unconditionally at their position in the pipeline.

Both participate in the same state system, event stream, and observability infrastructure.

```python
# Inner deliverable pipeline -- declarative composition
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # Custom agent (deterministic)
        planner,                                # LLM agent (uses FunctionTools)
        coder,                                # LLM agent (uses FunctionTools)
        LinterAgent(name="Lint"),                  # Custom agent (deterministic)
        TestRunnerAgent(name="Test"),               # Custom agent (deterministic)
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                reviewer,                      # LLM agent
                fixer,                         # LLM agent (uses FunctionTools)
                LinterAgent(name="ReLint"),        # Custom agent (deterministic)
                TestRunnerAgent(name="ReTest"),     # Custom agent (deterministic)
            ]
        )
    ]
)
```

Custom agents (`SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`) are defined in [Agents](./agents.md). The entire pipeline runs inside a worker process, with events published to Redis Streams for external consumption.

---

## 6. LLM Router (Dynamic Model Selection)

Different tasks have different optimal models. The LLM Router is a centralized lookup that selects the model for each LLM agent invocation.

### 6.1 Routing Dimensions

| Dimension | Description |
|-----------|-------------|
| Task type | coding, planning, reviewing, summarizing, classifying |
| Complexity | simple boilerplate vs. complex architecture decisions |
| Cost/speed | batch operations use cheaper models; critical-path uses best available |
| Fallback chains | if primary model is unavailable/rate-limited, fall back gracefully |

### 6.2 Phase 1 Implementation

Static routing config mapping `model_role` to model. No ML-based routing, no cost optimization. A clean lookup table that is easy to change.

```yaml
routing_rules:
  - model_role: implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-6"
  - model_role: implementation
    complexity: complex
    model: "anthropic/claude-opus-4-6"
  - model_role: planning
    model: "anthropic/claude-opus-4-6"
  - model_role: review
    model: "anthropic/claude-sonnet-4-6"
  - model_role: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - model_role: summarization
    model: "anthropic/claude-haiku-4-5-20251001"

fallback_chains:
  anthropic/claude-opus-4-6: ["anthropic/claude-sonnet-4-6"]
  anthropic/claude-sonnet-4-6: ["anthropic/claude-haiku-4-5-20251001"]
```

### 6.3 ADK Integration

Each `LlmAgent` can have its model set dynamically. The router runs as part of agent construction or via `before_model_callback` to override the model on the `LlmRequest` at invocation time. Routing logic is centralized rather than scattered across agent definitions.

Phase 2 will add cost tracking, latency monitoring, and adaptive selection.

---

## 7. GlobalToolset (ADK-Native Tool Authorization)

Tools live in one place: the `app/tools/` module, organized by function type (filesystem, code, git, execution, web, task, management). Authorization is separate: a config-driven permission layer powered by ADK's native `BaseToolset` mechanism. We use ADK's primitives, not a custom registry.

### 7.1 Architecture

```
Tools (code)          ->  app/tools/filesystem.py, code.py, git.py, execution.py, web.py, task.py, management.py
Authorization (config)->  permission config defining which role gets which tools
Vending (ADK-native)  ->  GlobalToolset(BaseToolset).get_tools(readonly_context)
```

**Separation of concerns:** Tool implementations are pure Python functions. Permission logic is centralized in `GlobalToolset`. ADK's `get_tools(readonly_context)` is the native mechanism for context-sensitive tool vending -- the readonly context carries the agent's role, and the toolset returns only the tools that role is permitted to use.

### 7.2 Tool Registry Summary

| Concern | Mechanism |
|---------|-----------|
| Tool code | `app/tools/` module -- 8 categories: filesystem, code intelligence, execution, git, web, task management, PM management, Director management |
| Per-role filtering | `GlobalToolset.get_tools(readonly_context)` |
| Permission config | Config-driven: CEO restricts Director, Director restricts PM, PM restricts Worker |
| Role scoping | Worker agents get category-specific subsets (see 7.5); PM gets PM management tools; Director gets Director management tools |
| Tool authoring | Director can write new tool functions; CEO approval required by default |

Restrictions cascade downward through the permission config -- a PM cannot access Director tools, a Worker cannot access PM tools. Within each tier, individual agents have further role-based scoping enforced by the toolset at agent construction time.

### 7.3 GlobalToolset Implementation

```python
from google.adk.tools import BaseToolset, BaseTool

class GlobalToolset(BaseToolset):
    """Vends per-role tools based on permission config.

    ADK calls get_tools() during agent construction, passing a
    ReadonlyContext that identifies the requesting agent's role.
    The toolset filters the full tool catalog based on the
    permission config for that role.
    """

    async def get_tools(
        self, readonly_context: ReadonlyContext
    ) -> list[BaseTool]:
        role = resolve_role(readonly_context)
        allowed = self._permission_config.get_allowed_tools(role)
        return [t for t in self._all_tools if t.name in allowed]
```

### 7.4 Cascading Permission Config

Tool access is restricted top-down through the supervision hierarchy via configuration:

```
CEO config    ->  restricts Director's tools  (global config)
Director config ->  restricts PM's tools      (per-project config)
PM config     ->  restricts Worker's tools    (per-workflow config)
```

All restrictions flow through the same config mechanism. A parent tier can disable any tool available to its children. The default is permissive -- all tools are available unless explicitly restricted.

### 7.5 Role-Based Tool Scoping

Within each tier, individual agents have scoping based on their role. The table below shows which tool categories and specific tools each role can access:

| Role | Filesystem | Code Intelligence | Execution | Git | Web | Task Mgmt | Management |
|------|-----------|-------------------|-----------|-----|-----|-----------|------------|
| `planner` | Read-only | Full | -- | Read-only | Full | Session todos | -- |
| `coder` | Full | Full | Full | Full | Full | Session todos | -- |
| `reviewer` | Read-only | Full | -- | Read-only | Full | Session todos | -- |
| `fixer` | Full | Full | `bash_exec` only | Read-only (no commit) | Full | Session todos | -- |
| PM | -- | -- | -- | -- | -- | Shared tasks | PM tools (7) |
| Director | -- | -- | -- | -- | -- | Shared tasks | Director tools (10) |

**Detailed per-role breakdown:**

- **`planner`** (worker): `file_read`, `file_glob`, `file_grep`, `directory_list`, `code_symbols`, `run_diagnostics`, `git_status`, `git_diff`, `git_log`, `git_show`, `web_search`, `web_fetch`, `todo_read`, `todo_write`, `todo_list`
- **`coder`** (worker): Full filesystem (all 10), full code intelligence (2), full execution (`bash_exec`, `http_request`), full git (all 8), full web (2), session todos (3)
- **`reviewer`** (worker): `file_read`, `file_glob`, `file_grep`, `directory_list`, `code_symbols`, `run_diagnostics`, `git_status`, `git_diff`, `git_log`, `git_show`, `web_search`, `web_fetch`, `todo_read`, `todo_write`, `todo_list`
- **`fixer`** (worker): Full filesystem (all 10), full code intelligence (2), `bash_exec` (no `http_request`), read-only git (`git_status`, `git_diff`, `git_log`, `git_show` -- no `git_commit`, `git_branch`, `git_worktree`, `git_apply`; `coder` handles commits), `web_search`, `web_fetch`, `todo_read`, `todo_write`, `todo_list`
- **PM**: `select_ready_batch`, `escalate_to_director`, `update_deliverable`, `query_deliverables`, `reorder_deliverables`, `manage_dependencies`, `reconfigure_stage`, `task_create`, `task_update`, `task_query`, `todo_read`, `todo_write`, `todo_list`. Note: `checkpoint_project` (`after_agent_callback` on DeliverablePipeline) and `run_regression_tests` (`RegressionTestAgent`, CustomAgent in pipeline) are not tools -- they are not LLM-discretionary.
- **Director**: `create_project`, `validate_brief`, `check_resources`, `delegate_to_pm`, `escalate_to_ceo`, `list_projects`, `query_project_status`, `override_pm`, `get_project_context`, `query_dependency_graph`, `task_create`, `task_update`, `task_query`, `todo_read`, `todo_write`, `todo_list`

`GlobalToolset.get_tools()` enforces this scoping at agent construction time, not through directory placement.

### 7.6 Director Tool Authoring

Director can author new tools (writes Python functions to the tools module). **CEO approval is required by default** before newly authored tools become active. This approval gate is configurable in global config (can be relaxed to auto-approve for trusted projects).

### 7.7 ADK Tool Primitives

| Primitive | Purpose | AutoBuilder Use |
|-----------|---------|-----------------|
| `FunctionTool` | Wrap Python function as LLM-callable tool | All core tools (filesystem, git, bash, etc.) |
| `BaseToolset` | Context-sensitive tool vending via `get_tools()` | `GlobalToolset` for role-based filtering |
| `tool_filter` | Additional per-agent tool filtering | Fine-grained restrictions within a role |
| `McpToolset` | Connect MCP servers | Reserved for complex integrations (used sparingly) |
| `OpenAPIToolset` | Generate tools from OpenAPI spec | Potential future use for external API integration |

---

## See Also

- [Agents](./agents.md) -- agent composition, custom agents, supervision hierarchy
- [Skills](./skills.md) -- skill-based knowledge injection, SkillLoaderAgent
- [State](./state.md) -- state scopes, memory architecture, session management
- [Providers](../06-PROVIDERS.md) -- LLM models, pricing, fallback chains
- [Architecture Overview](../02-ARCHITECTURE.md) -- system-level architecture
- ADK tools documentation: https://google.github.io/adk-docs/tools/
- ADK custom agents: https://google.github.io/adk-docs/agents/custom-agents/

---

*Document Version: 4.2*
*Last Updated: 2026-04-13*
