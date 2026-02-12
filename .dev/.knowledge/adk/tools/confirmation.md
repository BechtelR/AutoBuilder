# Action Confirmations - Agent Development Kit Documentation

## Overview

The Tool Confirmation feature allows ADK Tools to pause execution and request confirmation from a human or supervising system before proceeding. This capability supports decision-making verification, security oversight, and workflow approval scenarios.

## Two Implementation Approaches

### 1. Boolean Confirmation

The simplest method uses a yes/no confirmation:

```python
FunctionTool(reimburse, require_confirmation=True)
```

This wraps a tool with the `FunctionTool` class, requiring minimal code for basic approval scenarios.

**Dynamic Confirmation Logic:** You can replace the boolean value with a function that determines when confirmation is needed:

```python
async def confirmation_threshold(amount: int, tool_context: ToolContext) -> bool:
  """Returns true if the amount is greater than 1000."""
  return amount > 1000
```

### 2. Advanced Confirmation

For complex scenarios requiring structured data responses, use the `request_confirmation()` method with:

- **`hint`**: Descriptive message explaining what's needed
- **`payload`**: Expected data structure (serializable to JSON)

**Example Implementation:**

```python
def request_time_off(days: int, tool_context: ToolContext):
  tool_confirmation = tool_context.tool_confirmation
  if not tool_confirmation:
    tool_context.request_confirmation(
      hint='Please approve or reject the tool call...',
      payload={'approved_days': 0}
    )
    return {'status': 'Manager approval is required.'}

  approved_days = tool_confirmation.payload['approved_days']
  return {'status': 'ok', 'approved_days': approved_days}
```

## Remote Confirmation via REST API

Send confirmations through the ADK API server's `/run` or `/run_sse` endpoints using a `FunctionResponse` event with proper structure.

## Known Limitations

- DatabaseSessionService is unsupported
- VertexAiSessionService is unsupported

The feature is currently experimental and available in ADK Python v1.14.0+.

---

*Source: https://google.github.io/adk-docs/tools-custom/confirmation/*
*Downloaded: 2026-02-11*
