# Types of Callbacks - Agent Development Kit

## Overview

The Agent Development Kit provides callbacks that trigger at various execution stages. These hooks enable monitoring, modification, and control of agent behavior throughout its lifecycle.

## Agent Lifecycle Callbacks

Available on any agent inheriting from `BaseAgent` (including `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`).

### Before Agent Callback

**Timing:** Executes immediately before the agent's core logic begins, after the `InvocationContext` is created.

**Key Capabilities:**
- Setup resources specific to the agent's execution
- Validate session state before processing starts
- Log entry points for activity tracking
- Potentially skip execution by returning content

**Return Behavior:** Returning `None`/`empty()` allows normal execution. Returning a `Content` object bypasses the agent and uses that content as the final response.

### After Agent Callback

**Timing:** Runs immediately after successful agent execution, before results finalize. Does not execute if the agent was skipped or if `end_invocation` was set.

**Use Cases:**
- Cleanup operations
- Post-execution validation
- State modification
- Output augmentation or replacement

**Return Behavior:** `None`/`empty()` preserves the original output. Returning `Content` replaces the agent's response.

## LLM Interaction Callbacks

Specific to `LlmAgent`, these callbacks wrap the Large Language Model interaction.

### Before Model Callback

**Timing:** Triggers just before `generate_content_async` sends the request to the LLM.

**Purposes:**
- Inspect and modify outgoing requests
- Implement guardrails (profanity filters, request validation)
- Inject dynamic instructions or few-shot examples
- Cache responses at the request level
- Skip LLM calls conditionally

**Return Behavior:** `None` allows the (possibly modified) request to proceed. Returning an `LlmResponse` object skips the actual LLM call and uses the returned response directly.

### After Model Callback

**Timing:** Executes immediately after receiving the LLM response, before returning results to the agent.

**Applications:**
- Response validation and filtering
- Post-processing of generated content
- Response caching
- Logging and monitoring of model interactions
- Replacement or modification of responses

## Tool Execution Callbacks

### Before Tool Callback

**Timing:** Fires just before a tool executes.

**Functions:**
- Validate tool inputs
- Log tool invocations
- Modify parameters dynamically
- Skip execution conditionally

### After Tool Callback

**Timing:** Executes immediately after tool completion.

**Uses:**
- Validate tool outputs
- Transform results
- Handle errors gracefully
- Update state based on tool results

## Key Design Patterns

Callbacks enable:
- **State-driven logic:** Inspect session state to control execution flow
- **Request/response modification:** Transform data at critical points
- **Conditional execution:** Skip steps based on custom logic
- **Observability:** Add logging and monitoring throughout execution
- **Security:** Implement guardrails and input validation

All callback types receive a `CallbackContext` containing agent metadata, invocation details, and current session state, enabling context-aware decision-making.

---

**Source**: https://google.github.io/adk-docs/callbacks/types-of-callbacks/
**Downloaded**: 2026-02-11
