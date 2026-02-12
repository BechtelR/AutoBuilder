# AutoBuilder Tools & Deterministic Agents

## Overview

AutoBuilder's tool architecture has two distinct layers: **FunctionTools** (thin Python wrappers that LLM agents call at their discretion) and **Deterministic Agents** (workflow-level participants that execute unconditionally at specific pipeline points). Both are first-class citizens in ADK's composition model. Which tools and deterministic agents are used depends on the workflow type.

**Tools execute in ARQ worker processes, not the FastAPI gateway.** The gateway exposes high-level REST endpoints (e.g., "run workflow", "get status"). It does not expose raw tool operations. FunctionTools and deterministic agents run inside the ADK pipeline, which executes in worker processes. Tools have access to the worker's filesystem, subprocess environment, and git worktrees.

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

Each of these is a thin Python function (~5-30 lines) that ADK auto-wraps via `FunctionTool`. ADK generates the tool schema automatically from type hints and docstrings -- no manual schema definition required.

All FunctionTools execute inside worker processes. They have direct access to the worker's filesystem and subprocess environment. The gateway never calls these tools directly — it only enqueues workflow jobs that workers execute.

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

---

## 4. Gateway vs. Worker Tool Boundary

The gateway and workers have distinct roles with respect to tools:

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **Gateway (FastAPI)** | High-level REST endpoints. Enqueue jobs, query status, stream events. | `POST /workflows/run`, `GET /workflows/{id}/status`, `GET /workflows/{id}/events` (SSE) |
| **Worker (ARQ + ADK)** | Execute ADK pipelines. FunctionTools and deterministic agents run here. | `file_write`, `bash_exec`, `git_commit`, `LinterAgent`, `TestRunnerAgent` |

The gateway does not proxy raw tool calls. A client never sends "write this file" to the gateway — it sends "run this workflow with this spec." The worker's ADK pipeline decides which tools to invoke and when.

This boundary matters because:

1. **Security** — filesystem/subprocess access is contained to workers, not exposed via API
2. **Scalability** — workers can scale independently of the gateway
3. **Isolation** — a misbehaving tool (infinite loop, memory leak) affects only its worker, not the gateway
4. **Swappability** — ADK is an internal engine; the gateway could theoretically swap it out without changing the API surface

---

## 5. Deterministic Agents (CustomAgent / BaseAgent)

These are **workflow-level participants**, not LLM-callable tools. They inherit from ADK's `BaseAgent` and execute unconditionally at specific pipeline points. They cannot be skipped by LLM judgment -- they are workflow steps, not suggestions.

Key properties of deterministic agents:

- Participate in the same state system as LLM agents
- Visible to tracing/observability (same Event stream)
- Compose naturally with LLM agents in Sequential/Parallel/Loop workflows
- Re-run deterministically in loops without LLM re-invocation
- Execute inside worker processes alongside LLM agents

### 5.1 SkillLoaderAgent

Resolves and loads relevant skills into session state. Runs as the first step in the feature pipeline.

```python
class SkillLoaderAgent(BaseAgent):
    """Deterministic: resolve and load relevant skills into state."""

    async def _run_async_impl(self, ctx):
        matched = skill_library.match(context_from_state(ctx))
        loaded = [skill_library.load(entry) for entry in matched]
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": {s.entry.name: s.content for s in loaded},
                "loaded_skill_names": [s.entry.name for s in loaded],
            })
        )
```

### 5.2 LinterAgent

Runs the project linter against generated code. Writes structured results to session state.

```python
class LinterAgent(BaseAgent):
    """Deterministic: run project linter, write results to state."""

    async def _run_async_impl(self, ctx):
        # Run linter subprocess, parse output
        results = await run_linter(ctx)
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "lint_results": results,
                "lint_status": "passed" if results["errors"] == 0 else "failed",
            })
        )
```

### 5.3 TestRunnerAgent

Runs the test suite against generated code. Writes structured results to session state.

```python
class TestRunnerAgent(BaseAgent):
    """Deterministic: run test suite, write results to state."""

    async def _run_async_impl(self, ctx):
        results = await run_tests(ctx)
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "test_results": results,
                "test_status": "passed" if results["failures"] == 0 else "failed",
            })
        )
```

### 5.4 FormatterAgent

Runs the code formatter (e.g., ruff format, prettier) against generated code. No LLM involvement.

### 5.5 DependencyResolverAgent

Performs topological sort of features based on declared dependencies. Determines execution order and identifies parallelizable batches.

### 5.6 RegressionTestAgent

Runs cross-feature regression suite after a batch completes. Validates that newly implemented features have not broken previously completed features.

Regression strategy (random sampling or dependency-aware) is an open question for Phase 1. See consolidated planning doc, Open Questions #3.

### 5.7 ContextBudgetAgent

Checks token usage via token-counting the assembled `LlmRequest`. Writes usage percentage to state. Triggers compression if threshold is exceeded.

This agent addresses ADK's gap: no built-in context-window usage metric. Implementation is approximately 50 lines.

---

## 6. How Tools and Agents Compose in the Pipeline

FunctionTools and deterministic agents serve different roles in the pipeline:

```python
# Inner deliverable pipeline -- declarative composition
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # Deterministic
        plan_agent,                                # LLM (uses FunctionTools)
        code_agent,                                # LLM (uses FunctionTools)
        LinterAgent(name="Lint"),                  # Deterministic
        TestRunnerAgent(name="Test"),               # Deterministic
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM
                fix_agent,                         # LLM (uses FunctionTools)
                LinterAgent(name="ReLint"),        # Deterministic
                TestRunnerAgent(name="ReTest"),     # Deterministic
            ]
        )
    ]
)
```

- **LLM agents** (`plan_agent`, `code_agent`, `review_agent`, `fix_agent`) have FunctionTools available and decide when/how to use them.
- **Deterministic agents** (`SkillLoaderAgent`, `LinterAgent`, `TestRunnerAgent`) execute unconditionally at their position in the pipeline.
- **Both types** communicate via session state (`output_key` writes, `{key}` template reads) and emit events into the same unified stream.
- **The entire pipeline** runs inside a worker process. Events are published to Redis Streams for external consumption.

---

## 7. LLM Router (Dynamic Model Selection)

Different tasks have different optimal models. The LLM Router is a centralized lookup that selects the model for each LLM agent invocation.

### 7.1 Routing Dimensions

| Dimension | Description |
|-----------|-------------|
| Task type | coding, planning, reviewing, summarizing, classifying |
| Complexity | simple boilerplate vs. complex architecture decisions |
| Cost/speed | batch operations use cheaper models; critical-path uses best available |
| Fallback chains | if primary model is unavailable/rate-limited, fall back gracefully |

### 7.2 Phase 1 Implementation

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

### 7.3 ADK Integration

Each `LlmAgent` can have its model set dynamically. The router runs as part of agent construction (in the `BatchOrchestrator`) or via `before_model_callback` to override the model on the `LlmRequest` at invocation time. Routing logic is centralized rather than scattered across agent definitions.

Phase 2 will add cost tracking, latency monitoring, and adaptive selection.

---

## 8. Tool Restrictions by Agent Role

Agent role-based tool restrictions are a Phase 2 capability. The principle: read-only agents for exploration prevent scope creep. For example:

- `plan_agent` -- read-only filesystem tools, no file_write or bash_exec
- `code_agent` -- full filesystem and execution tools
- `review_agent` -- read-only tools, no mutation

This pattern is adopted from oh-my-opencode's architecture. See consolidated planning doc, Decision #6.

---

## 9. Related Documents

- Consolidated planning doc: `.dev/.discussion/260211_plan-shaping.md` (Section 8)
- State and memory: `.dev/08-STATE_MEMORY.md`
- Skills system: `.dev/06-SKILLS.md`
- Agents: `.dev/05-AGENTS.md`
- ADK tools documentation: https://google.github.io/adk-docs/tools/
- ADK custom agents: https://google.github.io/adk-docs/agents/custom-agents/

---

*Document Version: 2.0*
*Last Updated: 2026-02-11*
