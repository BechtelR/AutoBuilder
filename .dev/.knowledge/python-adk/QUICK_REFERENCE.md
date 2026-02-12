# Google ADK Quick Reference for AutoBuilder

Quick reference guide for the most commonly used ADK primitives in AutoBuilder.

## Core Agent Types

### LlmAgent
**File**: `google-adk-agents-LlmAgent.md`

LLM-based agent for probabilistic tasks requiring model judgment.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

agent = LlmAgent(
    name="code_agent",                    # Required: Python identifier
    model="gemini-2.0-flash-exp",        # Model string or BaseLlm instance
    instruction="You are a code writer", # Agent-specific system instruction
    global_instruction="...",            # Shared across all agents
    static_instruction="...",            # Static context (files, docs)
    tools=[                              # List of FunctionTool instances
        FunctionTool(func=file_read),
        FunctionTool(func=file_write),
    ],
    generate_content_config={            # Generation parameters
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    before_model_callback=inject_context,  # Pre-LLM hook
    after_model_callback=log_response,     # Post-LLM hook
)
```

### SequentialAgent
**File**: `google-adk-agents-SequentialAgent.md`

Executes sub-agents in linear sequence.

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="feature_pipeline",
    description="Execute feature development pipeline",
    sub_agents=[
        plan_agent,
        code_agent,
        lint_agent,
        test_agent,
    ]
)
```

### LoopAgent
**File**: `google-adk-agents-LoopAgent.md`

Executes sub-agent in loop until condition met or max iterations reached.

```python
from google.adk.agents import LoopAgent

def should_continue(ctx):
    return not ctx.state.get("review_passed")

review_loop = LoopAgent(
    name="review_fix_loop",
    sub_agent=review_fix_pipeline,
    max_iterations=3,
    should_continue=should_continue,
)
```

### ParallelAgent
**File**: `google-adk-agents-ParallelAgent.md`

Executes sub-agents concurrently.

```python
from google.adk.agents import ParallelAgent

batch_executor = ParallelAgent(
    name="batch_executor",
    description="Execute multiple features in parallel",
    sub_agents=[
        feature_agent_1,
        feature_agent_2,
        feature_agent_3,
    ]
)
```

### CustomAgent (BaseAgent)
**File**: `google-adk-agents.md`

Subclass for deterministic agents (linters, test runners, skill loaders).

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event

class LinterAgent(BaseAgent):
    async def run_async(self, parent_context):
        # Deterministic logic
        lint_result = await run_linter()

        # Store in state
        parent_context.state["lint_result"] = lint_result

        # Yield events for observability
        yield Event(
            agent_name=self.name,
            content={"text": f"Lint complete: {lint_result}"}
        )
```

## Application Setup

### App
**File**: `google-adk-apps.md`

Top-level application container.

```python
from google.adk.apps import App, ResumabilityConfig
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import FileArtifactService

app = App(
    name="autobuilder",
    root_agent=root_agent,
    plugins=[debug_logging_plugin],
    resumability_config=ResumabilityConfig(
        enable_checkpointing=True,
        checkpoint_interval=5,
    )
)
```

### Runner
**File**: `google-adk-runners.md`

Execute agents.

```python
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(app=app)

async for event in runner.run_async(
    user_content="Build feature X",
    user_id="user123",
    session_id="session456",
):
    print(event)
```

## State Management

### Session State
**File**: `google-adk-sessions.md`

Four-scope state system:

```python
# Access in agent via parent_context
context.state["feature_spec"]           # Session scope (no prefix)
context.state["user:preferences"]       # User scope (cross-session)
context.state["app:coding_standards"]   # App scope (global)
context.state["temp:scratch_data"]      # Temp scope (current invocation only)
```

Scopes:
- **Session**: Per-run, persists across checkpoints
- **User**: Per-user, persists across sessions
- **App**: Global, shared across all users/sessions
- **Temp**: Current invocation only, not persisted

### Artifacts
**File**: `google-adk-artifacts.md`

File storage for code, documents, etc.

```python
from google.adk.artifacts import FileArtifactService

artifact_service = FileArtifactService(base_path="./artifacts")

# Save artifact
await artifact_service.save_artifact(
    app_name="autobuilder",
    user_id="user123",
    session_id="session456",
    filename="feature.py",
    artifact={"text": "def feature(): pass"},
)

# Load artifact
artifact = await artifact_service.load_artifact(
    app_name="autobuilder",
    user_id="user123",
    session_id="session456",
    filename="feature.py",
)
```

### Memory
**File**: `google-adk-memory.md`

Cross-session searchable knowledge.

```python
# Memory service for long-term knowledge storage
# (VertexAiMemoryBankService, VertexAiRagMemoryService)
# AutoBuilder implements custom SqliteFtsMemoryService
```

## Tools

### FunctionTool
**File**: `google-adk-tools-function-tool.md`

Wrap Python functions as LLM-callable tools.

```python
from google.adk.tools import FunctionTool

def file_read(file_path: str) -> str:
    """Read a file from the filesystem.

    Args:
        file_path: Absolute path to the file

    Returns:
        File contents
    """
    return Path(file_path).read_text()

tool = FunctionTool(
    func=file_read,
    # name and description auto-extracted from function
    require_confirmation=False,
)
```

Schema is auto-generated from type hints and docstring.

## Events

### Event Stream
**File**: `google-adk-events.md`

Unified observability for all agent execution.

```python
from google.adk.events import Event

async for event in runner.run_async(...):
    # Event types:
    # - Agent start/end
    # - Model request/response
    # - Tool call/result
    # - State changes
    # - Errors

    if event.agent_name == "code_agent":
        print(f"Code agent: {event.content}")
```

## Callbacks

### Model Callbacks
```python
async def before_model_callback(ctx):
    """Inject context before LLM call."""
    # Load skills, check token budget, etc.
    ctx.context.append({"text": "Additional context..."})
    return None  # Return content to skip LLM call

async def after_model_callback(ctx):
    """Process LLM response."""
    # Log, validate, transform response
    return None  # Return content to append to response
```

### Tool Callbacks
```python
async def before_tool_callback(ctx):
    """Before tool execution."""
    # Validate, log, modify args
    return None

async def after_tool_callback(ctx):
    """After tool execution."""
    # Validate result, log, transform
    return None
```

## InvocationContext

```python
# Available in all callbacks and CustomAgent.run_async()
context = parent_context

context.invocation_id      # Unique invocation ID
context.agent              # Current agent instance
context.user_content       # User input
context.session            # Session object (id, user_id, app_name)
context.state             # State dict (all scopes)
context.agent_states      # Per-agent state storage
context.end_invocation    # Set to True to end invocation
context.run_config        # Execution parameters
```

## AutoBuilder-Specific Patterns

### Deterministic + LLM Pipeline

```python
pipeline = SequentialAgent(
    name="feature_pipeline",
    sub_agents=[
        SkillLoaderAgent(name="load_skills"),  # CustomAgent - deterministic
        LlmAgent(name="planner", ...),          # LLM - probabilistic
        LlmAgent(name="coder", ...),            # LLM - probabilistic
        LinterAgent(name="linter"),             # CustomAgent - deterministic
        TestRunnerAgent(name="test_runner"),    # CustomAgent - deterministic
        LoopAgent(                              # Review loop
            name="review_loop",
            sub_agent=SequentialAgent(
                name="review_fix",
                sub_agents=[
                    LlmAgent(name="reviewer", ...),
                    LlmAgent(name="fixer", ...),
                ]
            ),
            max_iterations=3,
        ),
    ]
)
```

### Batch Orchestration

```python
outer_loop = BatchOrchestrator(  # CustomAgent
    inner_pipeline=ParallelAgent(
        name="batch_executor",
        sub_agents=[
            # Dynamically created feature pipelines
        ]
    )
)
```

---

*Quick reference based on ADK Python API documentation - 2026-02-11*
