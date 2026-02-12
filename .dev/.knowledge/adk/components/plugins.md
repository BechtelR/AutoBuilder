# Plugins - Agent Development Kit

## Overview

Plugins in ADK are custom code modules executed at various stages of an agent workflow lifecycle using callback hooks. They're designed for functionality applicable across entire agent workflows.

**Supported in:** ADK Python v1.7.0

## Common Use Cases

- **Logging and tracing:** Detailed logs of agent, tool, and AI model activity
- **Policy enforcement:** Security guardrails and authorization checks
- **Monitoring and metrics:** Token usage, execution times, invocation counts
- **Response caching:** Return cached responses, avoiding expensive calls
- **Request/response modification:** Dynamically add information to prompts or standardize outputs

## How Plugins Work

Plugins extend the `BasePlugin` class and contain callback methods indicating where in the agent lifecycle they execute. Key differences from standard callbacks:

- **Scope:** Global - registered once on `Runner`, apply to all agents/tools/LLMs
- **Precedence:** Plugin callbacks execute before corresponding Agent Callbacks
- **Modularity:** Package related functions for cross-workflow use

## Key Architectural Difference: Plugins vs Callbacks

| Aspect | Plugins | Agent Callbacks |
|--------|---------|-----------------|
| Scope | Global to Runner | Local to specific agent |
| Use Case | Horizontal features (logging, policy, monitoring) | Specific agent logic |
| Configuration | Once on Runner | Individual agent instances |
| Execution Order | Run before Agent Callbacks | Run after Plugins |

**Important:** If a Plugin callback returns a non-null value, it short-circuits execution and prevents the corresponding Agent Callback from running.

## Prebuilt Plugins Available

- Reflect and Retry Tools
- BigQuery Analytics
- Context Filter
- Global Instruction
- Save Files as Artifacts
- Logging

## Basic Implementation

### Create Plugin Class

```python
class CountInvocationPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="count_invocation")
        self.agent_count: int = 0
        self.llm_request_count: int = 0

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        self.agent_count += 1

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        self.llm_request_count += 1
```

### Register Plugin

```python
runner = InMemoryRunner(
    agent=root_agent,
    app_name='test_app',
    plugins=[CountInvocationPlugin()],
)
```

## Available Callback Hooks

### 1. **User Message Callback**
- Executes immediately after `runner.run()`
- First opportunity to inspect/modify user input
- Can replace the original message

### 2. **Runner Start Callback**
- Fires before any agent logic begins
- Global setup opportunity

### 3. **Agent Execution Callbacks**
- `before_agent_callback`: Before agent begins work
- `after_agent_callback`: After agent completes

### 4. **Model Callbacks**
- `before_model_callback`: Before model execution
- `after_model_callback`: After successful execution
- `on_model_error_callback`: On model failure (can suppress exception or provide fallback)

### 5. **Tool Callbacks**
- `before_tool_callback`: Before tool execution
- `after_tool_callback`: After successful execution
- `on_tool_error_callback`: On tool failure (can suppress exception with dict return)

### 6. **Event Callbacks**
- `on_event_callback`: After agent yields Event, before streaming to client
- Allows modification or enrichment of events

### 7. **Runner End Callback**
- `after_run_callback`: Final hook after complete execution
- Ideal for cleanup and finalization

## Return Value Modes

**Three modes of operation:**

1. **Observe** (return `None`): Log or collect metrics without interrupting workflow
2. **Intervene** (return value): Short-circuit workflow and use Plugin's return as result
3. **Amend** (modify Context): Adjust context data without interrupting execution

## Important Limitations

- Plugins are **not supported** by ADK web interface
- If using Plugins, must run workflow via command line only
- Plugin callbacks have precedence over object-level callbacks

## Next Steps

- Review [ADK Python repository examples](https://github.com/google/adk-python/tree/main/src/google/adk/plugins)
- Explore [security guardrails implementation](https://cloud.google.com/documentation)
- Check complete [API reference](https://cloud.google.com/documentation)

---

**Source**: https://google.github.io/adk-docs/plugins/
**Downloaded**: 2026-02-11
