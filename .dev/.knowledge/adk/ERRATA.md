# ADK Errata
> Empirical gotchas discovered through real usage. These supplement/contradict official docs.

## #1 CustomAgent state_delta persistence (CRITICAL)
Direct `ctx.session.state["key"] = value` inside `_run_async_impl` does NOT persist across turns.
Must yield `Event(actions=EventActions(state_delta={"key": val}))` for all state writes.
Direct reads from `ctx.session.state` work fine (ADK applies incoming state_delta from sub-agents).

## #2 InMemoryRunner auto_create_session
`auto_create_session=True` is not exposed in the `InMemoryRunner` constructor.
Set `runner.auto_create_session = True` after construction.

## #7 FunctionTool import path
Use `from google.adk.tools.function_tool import FunctionTool` — not `from google.adk.tools`.
