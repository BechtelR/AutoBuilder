# Design Patterns and Best Practices for Callbacks

## Design Patterns

The page outlines eight key patterns for leveraging callbacks in the Agent Development Kit:

### 1. Guardrails & Policy Enforcement
Intercept requests before reaching the LLM or tools. Use `before_model_callback` to inspect prompts or `before_tool_callback` to examine arguments, returning predefined responses if policy violations occur.

### 2. Dynamic State Management
Read and write to session state within callbacks. "Modifications (`state['key'] = value`) are automatically tracked in the subsequent `Event.actions.state_delta`" and persist through the `SessionService`.

### 3. Logging and Monitoring
Implement callbacks at lifecycle points to add structured logging containing agent names, tool names, and invocation IDs for observability.

### 4. Caching
Generate cache keys in `before_model_callback` or `before_tool_callback` to check for existing results, returning cached data when available rather than re-executing operations.

### 5. Request/Response Modification
Alter data before sending to LLM/tools or after receiving results. "Modify `llm_request` (e.g., add system instructions based on `state`)" or adjust tool responses.

### 6. Conditional Skipping of Steps
"Return a value from a `before_` callback to skip the normal execution" - returning `Content`, `LlmResponse`, or `dict` prevents standard operations from running.

### 7. Tool-Specific Actions
Handle authentication via `tool_context.request_credential(auth_config)` and control LLM summarization by setting `tool_context.actions.skip_summarization = True`.

### 8. Artifact Handling
Use `callback_context.save_artifact` and `load_artifact` to manage files and data blobs during the agent lifecycle.

## Best Practices

**Design Principles:** Keep callbacks focused on single purposes and avoid long-running operations that block the processing loop.

**Error Handling:** Use try-catch blocks and handle errors gracefully without crashing the process.

**State Management:** "Be deliberate about reading from and writing to `context.state`" and use specific state keys to avoid unintended side effects.

**Reliability:** Design callbacks as idempotent when they involve external side effects.

**Testing:** Unit test callbacks with mock contexts and perform integration testing within full agent flows.

---

**Source**: https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/
**Downloaded**: 2026-02-11
