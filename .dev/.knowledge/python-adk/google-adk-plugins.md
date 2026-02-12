# google.adk.plugins - Plugin System

**Module**: `google.adk.plugins`
**Purpose**: Global lifecycle hooks and custom code execution at workflow stages
**Documentation Source**: https://google.github.io/adk-docs/plugins/

---

## Overview

ADK's plugin architecture enables custom code execution at various lifecycle stages. A plugin extends the `BasePlugin` class and uses callback methods to intercept agent workflow events.

**Definition**: "A Plugin in Agent Development Kit (ADK) is a custom code module that can be executed at various stages of an agent workflow lifecycle using callback hooks."

---

## Key Distinctions from Callbacks

Plugins differ from standard Agent Callbacks in fundamental ways:

| Aspect | Plugins | Agent Callbacks |
|--------|---------|-----------------|
| **Scope** | Global - operate across all agents/tools/LLMs in a Runner | Local - specific to individual instances |
| **Precedence** | Execute *before* corresponding Agent Callbacks | Execute after plugin hooks |
| **Configuration** | Register once on the Runner | Configure individually on each agent |
| **Registration** | `Runner(plugins=[...])` | `agent.before_agent_callback = ...` |

---

## Creating Plugins

### Plugin Class Structure

Extend `BasePlugin` and implement callback methods:

```python
from google.adk.plugins import BasePlugin

class CountInvocationPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="count_invocation")
        self.count = 0

    async def before_agent_callback(self, *, agent, callback_context):
        self.count += 1
        print(f"Agent invoked {self.count} times")
```

### Required Constructor

All plugins must:
- Call `super().__init__(name="plugin_name")` in constructor
- Provide a unique name for the plugin

---

## Registration

Register plugins during Runner initialization:

```python
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(
    agent=root_agent,
    plugins=[
        CountInvocationPlugin(),
        LoggingPlugin(),
        CachingPlugin()
    ]
)
```

**Note**: Plugins apply globally to all agents in the workflow tree.

---

## Plugin Callback Hooks

Plugins support **seven callback categories**:

### 1. User Message
**Hook**: `on_user_message_callback`
**Purpose**: Inspect/modify initial user input
**Timing**: Before workflow begins

```python
async def on_user_message_callback(self, *, message, callback_context):
    # Inspect or transform user message
    pass
```

### 2. Runner Start
**Hook**: `before_run_callback`
**Purpose**: Global setup before agent logic
**Timing**: At runner initialization

```python
async def before_run_callback(self, *, callback_context):
    # Initialize resources, set up logging, etc.
    pass
```

### 3. Agent Execution
**Hooks**: `before_agent_callback`, `after_agent_callback`
**Purpose**: Surrounds agent processing
**Timing**: Before and after each agent invocation

```python
async def before_agent_callback(self, *, agent, callback_context):
    # Pre-processing, logging, validation
    pass

async def after_agent_callback(self, *, agent, callback_context):
    # Post-processing, metrics collection
    pass
```

### 4. Model Operations
**Hooks**: `before_model_callback`, `after_model_callback`, `on_model_error_callback`
**Purpose**: Intercept LLM calls
**Timing**: Around model API requests

```python
async def before_model_callback(self, *, model, callback_context):
    # Log prompts, check token budgets
    pass

async def after_model_callback(self, *, model, callback_context):
    # Cache responses, log completions
    pass

async def on_model_error_callback(self, *, model, error, callback_context):
    # Handle rate limits, retries
    pass
```

### 5. Tool Execution
**Hooks**: `before_tool_callback`, `after_tool_callback`, `on_tool_error_callback`
**Purpose**: Monitor tool operations
**Timing**: Around tool execution

```python
async def before_tool_callback(self, *, tool, callback_context):
    # Validate parameters, log tool calls
    pass

async def after_tool_callback(self, *, tool, callback_context):
    # Log results, cache outputs
    pass

async def on_tool_error_callback(self, *, tool, error, callback_context):
    # Error handling, fallback logic
    pass
```

### 6. Event Handling
**Hook**: `on_event_callback`
**Purpose**: Modify output events
**Timing**: When events are emitted

```python
async def on_event_callback(self, *, event, callback_context):
    # Transform or filter events
    pass
```

### 7. Runner End
**Hook**: `after_run_callback`
**Purpose**: Cleanup and finalization
**Timing**: After workflow completes

```python
async def after_run_callback(self, *, callback_context):
    # Save metrics, close connections
    pass
```

---

## Operation Modes

Plugins operate in three modes:

### 1. Observe Mode
**Behavior**: No return value
**Effect**: Allows workflow continuation unchanged
**Use Case**: Logging, metrics collection

```python
async def before_agent_callback(self, *, agent, callback_context):
    log.info(f"Agent {agent.name} starting")
    # No return - observe only
```

### 2. Intervene Mode
**Behavior**: Return a value to short-circuit
**Effect**: Replaces the intended action
**Use Case**: Caching, policy enforcement

```python
async def before_model_callback(self, *, model, callback_context):
    cached = get_cached_response(callback_context.prompt)
    if cached:
        return cached  # Short-circuit LLM call
```

### 3. Amend Mode
**Behavior**: Modify Context objects
**Effect**: Changes workflow without interrupting
**Use Case**: Adding metadata, transforming inputs

```python
async def before_agent_callback(self, *, agent, callback_context):
    callback_context.metadata["timestamp"] = time.time()
    # Context modified, workflow continues
```

---

## Common Use Cases

### 1. Logging and Tracing
Track agent/tool/model activity for debugging and monitoring.

```python
class LoggingPlugin(BasePlugin):
    async def before_agent_callback(self, *, agent, callback_context):
        logger.info(f"[{agent.name}] Starting execution")

    async def after_agent_callback(self, *, agent, callback_context):
        logger.info(f"[{agent.name}] Completed execution")
```

### 2. Policy Enforcement and Security Guardrails
Validate inputs, filter sensitive data, enforce business rules.

```python
class SecurityPlugin(BasePlugin):
    async def on_user_message_callback(self, *, message, callback_context):
        if contains_pii(message):
            raise SecurityError("PII detected in user message")
```

### 3. Monitoring and Metrics Collection
Track performance, token usage, error rates.

```python
class MetricsPlugin(BasePlugin):
    async def after_model_callback(self, *, model, callback_context):
        metrics.record_tokens(callback_context.token_count)
        metrics.record_latency(callback_context.duration)
```

### 4. Response Caching
Cache LLM responses to reduce costs and latency.

```python
class CachingPlugin(BasePlugin):
    async def before_model_callback(self, *, model, callback_context):
        cached = cache.get(callback_context.prompt)
        if cached:
            return cached

    async def after_model_callback(self, *, model, callback_context):
        cache.set(callback_context.prompt, callback_context.response)
```

### 5. Request/Response Modification
Transform inputs or outputs based on business logic.

```python
class TransformPlugin(BasePlugin):
    async def before_agent_callback(self, *, agent, callback_context):
        # Add context or transform input
        callback_context.input = sanitize(callback_context.input)
```

---

## Prebuilt Plugins

ADK provides ready-to-use plugins:

| Plugin | Purpose |
|--------|---------|
| **Reflect and Retry Tools** | Automatic error recovery with reflection |
| **BigQuery Analytics** | Query performance tracking to BigQuery |
| **Context Filter** | Filter sensitive information from context |
| **Global Instruction** | Inject global instructions to all agents |
| **Save Files as Artifacts** | Automatically save agent outputs as artifacts |
| **Logging** | Comprehensive logging of all workflow events |

---

## Limitations

**Web Interface Incompatibility**:
> "Plugins are not supported by the ADK web interface. If your ADK workflow uses Plugins, you must run your workflow without the web interface."

**Workaround**: Run workflows programmatically using `Runner.run()` instead of `adk web`.

---

## BasePlugin Class Reference

### Constructor

```python
class BasePlugin:
    def __init__(self, name: str):
        """
        Initialize plugin with unique name.

        Args:
            name: Unique identifier for the plugin
        """
```

### Callback Methods

All callback methods are optional - implement only what you need:

```python
# User message
async def on_user_message_callback(
    self, *, message: str, callback_context: CallbackContext
) -> Optional[str]: ...

# Runner lifecycle
async def before_run_callback(
    self, *, callback_context: CallbackContext
) -> None: ...

async def after_run_callback(
    self, *, callback_context: CallbackContext
) -> None: ...

# Agent lifecycle
async def before_agent_callback(
    self, *, agent: BaseAgent, callback_context: CallbackContext
) -> Optional[Any]: ...

async def after_agent_callback(
    self, *, agent: BaseAgent, callback_context: CallbackContext
) -> None: ...

# Model lifecycle
async def before_model_callback(
    self, *, model: BaseModel, callback_context: CallbackContext
) -> Optional[Any]: ...

async def after_model_callback(
    self, *, model: BaseModel, callback_context: CallbackContext
) -> None: ...

async def on_model_error_callback(
    self, *, model: BaseModel, error: Exception, callback_context: CallbackContext
) -> None: ...

# Tool lifecycle
async def before_tool_callback(
    self, *, tool: BaseTool, callback_context: CallbackContext
) -> Optional[Any]: ...

async def after_tool_callback(
    self, *, tool: BaseTool, callback_context: CallbackContext
) -> None: ...

async def on_tool_error_callback(
    self, *, tool: BaseTool, error: Exception, callback_context: CallbackContext
) -> None: ...

# Event handling
async def on_event_callback(
    self, *, event: Event, callback_context: CallbackContext
) -> Optional[Event]: ...
```

---

## Best Practices

1. **Unique names**: Ensure each plugin has a unique name
2. **Minimize overhead**: Keep plugin logic lightweight
3. **Error handling**: Don't let plugin errors crash workflows
4. **Async operations**: Use `await` for I/O operations
5. **State management**: Be careful with shared state across invocations
6. **Documentation**: Document what each plugin does and when it intervenes
7. **Testing**: Test plugins in isolation before integration

---

## Related Documentation

- [Callbacks Overview](https://google.github.io/adk-docs/callbacks/)
- [Types of Callbacks](https://google.github.io/adk-docs/callbacks/types-of-callbacks/)
- [Callback Design Patterns](https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/)
- [Runners](https://google.github.io/adk-docs/api-reference/python/google-adk-runners.html)

---

**Last Updated**: 2026-02-11
**API Stability**: Stable
