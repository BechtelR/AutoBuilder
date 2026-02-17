# Tools & Tool Registry

## Overview

AutoBuilder's tool layer consists of **FunctionTools** — thin Python wrappers that LLM agents call at their discretion. ADK auto-generates tool schemas from type hints and docstrings, so tools are just annotated functions.

This document covers FunctionTools only. For custom agents (deterministic pipeline participants like `SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`), see [05-AGENTS.md](./05-AGENTS.md). The key distinction: tools are passive (LLM decides when to call them), agents are active (pipeline structure determines when they run).

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

Decision rationale: See consolidated planning doc, Decision #16.

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

Web search provider selection (SearXNG vs Brave vs Tavily) is an open question for Phase 1. See consolidated planning doc, Open Questions #7.

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

### 3.6 FunctionTool Registration Example

```python
from google.adk.tools import FunctionTool

# ADK auto-generates the tool schema from type hints + docstring
tools = [
    FunctionTool(file_read),
    FunctionTool(file_write),
    FunctionTool(file_edit),
    FunctionTool(file_search),
    FunctionTool(directory_list),
    FunctionTool(bash_exec),
    FunctionTool(web_search),
    FunctionTool(web_fetch),
    FunctionTool(todo_read),
    FunctionTool(todo_write),
    FunctionTool(todo_list),
    FunctionTool(git_status),
    FunctionTool(git_commit),
    FunctionTool(git_branch),
    FunctionTool(git_diff),
]
```

Workflows declare which tools they require in their `WORKFLOW.yaml` manifest via `required_tools` and `optional_tools`. The tool registry provides the subset each workflow needs.

### 3.7 PM Project Management Tools

These tools support PM-level batch orchestration. The PM (LlmAgent) calls them as part of its outer loop -- selecting batches, running regression tests, and checkpointing progress.

```python
def select_ready_batch(project_id: str) -> str:
    """Dependency-aware batch selection via topological sort. Returns the next
    set of deliverables whose prerequisites are satisfied."""

def run_regression_tests(project_id: str) -> str:
    """Run cross-deliverable regression suite after a batch completes.
    Validates that new deliverables have not broken previously completed ones."""

def checkpoint_project(project_id: str) -> str:
    """Persist current project state for resume. Captures batch progress,
    deliverable statuses, and session state snapshot."""
```

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

Custom agents (`SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`) are defined in [05-AGENTS.md](./05-AGENTS.md). The entire pipeline runs inside a worker process, with events published to Redis Streams for external consumption.

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

## 7. Tool Restrictions by Agent Role

All agent tiers (Director, PM, Workers) have access to tools and skills. Tool restrictions are role-based, not tier-based — the principle is that read-only agents prevent scope creep regardless of where they sit in the hierarchy. Phase 2 implements enforcement. Examples:

- `plan_agent` (worker) -- read-only filesystem tools, no file_write or bash_exec
- `code_agent` (worker) -- full filesystem and execution tools
- `review_agent` (worker) -- read-only tools, no mutation
- PM -- project management tools (`select_ready_batch`, `run_regression_tests`, `checkpoint_project`)
- Director -- governance tools, resource management, cross-project tools

This pattern is adopted from oh-my-opencode's architecture. See consolidated planning doc, Decision #6.

---

## 8. Related Documents

- Consolidated planning doc: `.dev/.discussion/260211_plan-shaping.md` (Section 8)
- State and memory: `.dev/08-STATE_MEMORY.md`
- Skills system: `.dev/06-SKILLS.md`
- Agents (including custom agents): `.dev/05-AGENTS.md`
- ADK tools documentation: https://google.github.io/adk-docs/tools/
- ADK custom agents: https://google.github.io/adk-docs/agents/custom-agents/

---

*Document Version: 2.1*
*Last Updated: 2026-02-16*
