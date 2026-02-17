[← Architecture Overview](../02-ARCHITECTURE.md)

# Tools & AutoBuilderToolset

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

### 3.1 Filesystem Tools

```python
def file_read(path: str) -> str:
    """Read file contents."""

def file_write(path: str, content: str) -> str:
    """Write or create a file with the given content."""

def file_edit(path: str, old: str, new: str) -> str:
    """Targeted string replacement within a file."""

def file_search(pattern: str, path: str) -> str:
    """Search for files or content across the codebase (grep/find)."""

def directory_list(path: str) -> str:
    """List directory contents as a tree."""
```

### 3.2 Execution Tools

```python
def bash_exec(command: str, cwd: str | None = None) -> str:
    """Run a shell command. Subprocess wrapper with timeout and output capture."""
```

Note: `bash_exec` must be idempotent or include duplicate-run protection for compatibility with ADK's Resume feature (tools may run more than once on resume).

### 3.3 Web Tools

```python
def web_search(query: str) -> str:
    """Search the web via SearXNG, Brave, or Tavily API. No Gemini dependency."""

def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL. Supplements ADK's load_web_page if needed."""
```

Web search provider selection (SearXNG vs Brave vs Tavily) is an open design question. See consolidated planning doc, Open Questions #7.

### 3.4 Task Management Tools

```python
def todo_read() -> str:
    """Read current task list from session state."""

def todo_write(action: str, task_id: str, content: str) -> str:
    """Add, update, complete, or remove tasks."""

def todo_list(filter: str | None = None) -> str:
    """List tasks with optional status filter."""
```

### 3.5 Git Tools

```python
def git_status(path: str) -> str:
    """Current repository state."""

def git_commit(path: str, message: str) -> str:
    """Stage and commit changes."""

def git_branch(path: str, name: str, action: str) -> str:
    """Create, switch, or delete branches."""

def git_diff(path: str, ref: str | None = None) -> str:
    """Show changes against a reference."""
```

### 3.6 FunctionTool Registration

Tools are Python functions in the `app/tools/` module, organized by function type. ADK auto-wraps them via `FunctionTool`:

```python
from google.adk.tools.function_tool import FunctionTool

# ADK auto-generates the tool schema from type hints + docstring
tool = FunctionTool(file_read)
```

`AutoBuilderToolset` (see Section 7) handles per-role tool filtering via ADK's native `BaseToolset.get_tools(readonly_context)`. Workflows declare which tools they require in their `WORKFLOW.yaml` manifest via `required_tools` and `optional_tools`.

### 3.7 PM & Director Tools

The PM uses FunctionTools for batch composition and escalation. The Director uses the same escalation tool for CEO communication.

```python
def select_ready_batch(project_id: str) -> str:
    """Dependency-aware batch selection via topological sort. Returns the next
    set of deliverables whose prerequisites are satisfied."""

def enqueue_ceo_item(item_type: str, priority: str, message: str, metadata: str) -> str:
    """Push a notification, approval request, escalation, or task to the unified
    CEO queue. Used by PM and Director to communicate with the CEO without
    injecting items into chat sessions."""
```

**Note:** `checkpoint_project` and `run_regression_tests` are **not FunctionTools** -- they must not be skippable by LLM judgment. `checkpoint_project` is an `after_agent_callback` on DeliverablePipeline that fires after each deliverable completes, persisting state via `CallbackContext`. `run_regression_tests` is a `RegressionTestAgent` (CustomAgent) wired into the pipeline after each batch -- it reads the PM's regression policy from session state, runs tests when the policy says to, and no-ops otherwise. Always present in the pipeline, policy-aware. See [Agents](./agents.md) for details.

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
        plan_agent,                                # LLM agent (uses FunctionTools)
        code_agent,                                # LLM agent (uses FunctionTools)
        LinterAgent(name="Lint"),                  # Custom agent (deterministic)
        TestRunnerAgent(name="Test"),               # Custom agent (deterministic)
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM agent
                fix_agent,                         # LLM agent (uses FunctionTools)
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

Static routing config mapping `task_type` to model. No ML-based routing, no cost optimization. A clean lookup table that is easy to change.

```yaml
routing_rules:
  - task_type: implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: implementation
    complexity: complex
    model: "anthropic/claude-opus-4-6"
  - task_type: planning
    model: "anthropic/claude-opus-4-6"
  - task_type: review
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - task_type: summarization
    model: "anthropic/claude-haiku-4-5-20251001"

fallback_chains:
  anthropic/claude-opus-4-6: ["anthropic/claude-sonnet-4-5-20250929"]
  anthropic/claude-sonnet-4-5-20250929: ["anthropic/claude-haiku-4-5-20251001"]
```

### 6.3 ADK Integration

Each `LlmAgent` can have its model set dynamically. The router runs as part of agent construction or via `before_model_callback` to override the model on the `LlmRequest` at invocation time. Routing logic is centralized rather than scattered across agent definitions.

Phase 2 will add cost tracking, latency monitoring, and adaptive selection.

---

## 7. AutoBuilderToolset (ADK-Native Tool Authorization)

Tools live in one place: the `app/tools/` module, organized by function type (filesystem, git, execution, web, task, project). Authorization is separate: a config-driven permission layer powered by ADK's native `BaseToolset` mechanism. We use ADK's primitives, not a custom registry.

### 7.1 Architecture

```
Tools (code)          ->  app/tools/filesystem.py, git.py, execution.py, web.py, ...
Authorization (config)->  permission config defining which role gets which tools
Vending (ADK-native)  ->  AutoBuilderToolset(BaseToolset).get_tools(readonly_context)
```

**Separation of concerns:** Tool implementations are pure Python functions. Permission logic is centralized in `AutoBuilderToolset`. ADK's `get_tools(readonly_context)` is the native mechanism for context-sensitive tool vending -- the readonly context carries the agent's role, and the toolset returns only the tools that role is permitted to use.

### 7.2 Tool Registry Summary

| Concern | Mechanism |
|---------|-----------|
| Tool code | `app/tools/` module, organized by function type |
| Per-role filtering | `AutoBuilderToolset.get_tools(readonly_context)` |
| Permission config | Config-driven: CEO restricts Director, Director restricts PM, PM restricts Worker |
| Role scoping | `plan_agent` gets read-only tools, `code_agent` gets full tools, etc. |
| Tool authoring | Director can write new tool functions; CEO approval required by default |

Restrictions cascade downward through the permission config -- a PM cannot access Director tools, a Worker cannot access PM tools. Within each tier, individual agents have further role-based scoping enforced by the toolset at agent construction time.

### 7.3 AutoBuilderToolset Implementation

```python
from google.adk.tools import BaseToolset, BaseTool

class AutoBuilderToolset(BaseToolset):
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

Within each tier, individual agents have further scoping based on their role:

- `plan_agent` (worker) -- read-only filesystem tools, no `file_write` or `bash_exec`
- `code_agent` (worker) -- full filesystem and execution tools
- `review_agent` (worker) -- read-only tools, no mutation
- PM -- batch selection tool (`select_ready_batch`) + shared tools. Note: `checkpoint_project` (`after_agent_callback` on DeliverablePipeline) and `run_regression_tests` (`RegressionTestAgent`, CustomAgent in pipeline) are not tools -- they are not LLM-discretionary.
- Director -- governance tools, resource management, cross-project tools + shared tools

`AutoBuilderToolset.get_tools()` enforces this scoping at agent construction time, not through directory placement.

### 7.6 Director Tool Authoring

Director can author new tools (writes Python functions to the tools module). **CEO approval is required by default** before newly authored tools become active. This approval gate is configurable in global config (can be relaxed to auto-approve for trusted projects).

### 7.7 ADK Tool Primitives

| Primitive | Purpose | AutoBuilder Use |
|-----------|---------|-----------------|
| `FunctionTool` | Wrap Python function as LLM-callable tool | All core tools (filesystem, git, bash, etc.) |
| `BaseToolset` | Context-sensitive tool vending via `get_tools()` | `AutoBuilderToolset` for role-based filtering |
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

*Document Version: 3.0*
*Last Updated: 2026-02-17*
