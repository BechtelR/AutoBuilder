# Part 3: Event Handling with run_live() - Complete Content

## Overview

This documentation covers ADK's event handling system for bidirectional streaming conversations. The `run_live()` method is "an async generator that streams conversation events in real-time" without internal buffering.

## Core Concepts

### How run_live() Works

The method signature requires keyword-only arguments including `user_id`, `session_id`, `live_request_queue`, and optional `run_config`. It returns an `AsyncGenerator[Event, None]` that yields events continuously.

**Connection lifecycle:**
- Initialization when called
- Active streaming via bidirectional communication
- Graceful closure when `live_request_queue.close()` is called
- Support for transparent session resumption via `RunConfig.session_resumption`

### Event Types Yielded

| Type | Purpose |
|------|---------|
| Text Events | Model responses with `response_modalities=["TEXT"]` |
| Audio Events | Raw audio bytes when using `["AUDIO"]` mode |
| Audio File Events | Aggregated audio with file references |
| Metadata Events | Token usage (`prompt_token_count`, `candidates_token_count`) |
| Transcription Events | Speech-to-text for input/output |
| Tool Call Events | Function execution requests |
| Error Events | Failures with `error_code` and `error_message` |

## The Event Class

ADK's `Event` extends `LlmResponse` and serves as the unified communication container. Key fields include:

- **Identity**: `event.id` (unique per event), `event.invocation_id` (shared across session)
- **Content**: Text, audio, or function calls via `content.parts`
- **Control flags**: `partial`, `turn_complete`, `interrupted`
- **Metadata**: `usage_metadata`, `cache_metadata`, `finish_reason`
- **Author semantics**: Agent name for responses; "user" for transcriptions

## Text Event Handling

### The partial Flag

- `partial=True`: Incremental text since last event
- `partial=False`: Complete merged text

"ADK internally accumulates all text from `partial=True` events" for seamless streaming display.

### turn_complete Flag

Signals when the model finishes its complete response, enabling you to update UI state (enable input controls, hide typing indicators).

### interrupted Flag

Indicates user interruption mid-response, allowing applications to "stop rendering outdated content immediately."

## Error Handling Strategy

**Decision framework:**
- Use `break` for terminal errors: `SAFETY`, `PROHIBITED_CONTENT`, `MAX_TOKENS`
- Use `continue` for transient errors: `UNAVAILABLE`, `DEADLINE_EXCEEDED`, `RESOURCE_EXHAUSTED`

Always include error checking before processing content and implement cleanup in `finally` blocks.

## Serialization

### model_dump_json()

Convert events to JSON for network transport:

```python
event_json = event.model_dump_json(exclude_none=True, by_alias=True)
await websocket.send_text(event_json)
```

**Parameters:**
- `exclude_none=True`: Reduce payload by omitting None fields
- `by_alias=True`: Use camelCase field names
- `exclude={}`: Skip specific fields (e.g., large binary audio)

### Audio Optimization

"Base64-encoded binary audio in JSON significantly increases payload size." Solution: send audio via WebSocket binary frames, metadata via text frames.

## Automatic Tool Execution

Unlike raw Live API usage, ADK handles tool execution automatically:

1. Detects function calls in streaming responses
2. Executes tools in parallel
3. Formats responses per Live API requirements
4. Sends responses back seamlessly
5. Yields function call and response events

**Key advantage:** "The difference between raw Live API tool use and ADK is stark" in developer experience—ADK transforms manual orchestration into declarative function definitions.

### Streaming Tools

Tools accepting `input_stream: LiveRequestQueue` can send real-time updates during execution. ADK automatically injects dedicated queues for each streaming tool via `invocation_context.active_streaming_tools`.

## InvocationContext

Represents a complete interaction cycle and contains:
- `invocation_id`: Current invocation identifier
- `session`: Access to events, state, user identity
- `run_config`: Streaming configuration
- `end_invocation`: Flag to terminate conversation

**Not typically created by developers** but received as parameter in custom tools and callbacks for sophisticated behaviors.

## Multi-Agent Workflows

### SequentialAgent Pattern

Recommended approach with bidirectional streaming:

1. Create single `LiveRequestQueue` shared across all agents
2. Run background task capturing user input continuously
3. Process all events in single loop—transitions happen transparently
4. Check `event.author` to identify current agent

"Agent transitions happen transparently within the same `run_live()` event stream."

### Event Flow During Transitions

- Agent completes and calls `task_completed()` function
- Automatic transition to next agent (invisible to application)
- Events continue flowing from subsequent agents
- Loop exits only when last agent completes

## Best Practices

- **Always use async context** for `run_live()` code
- **Check errors first** before processing content
- **Implement cleanup** in finally blocks
- **Use camelCase in JSON** serialization via `by_alias=True`
- **Send audio separately** for production applications
- **Log with context** (session_id, user_id) for debugging
- **Distinguish retryable vs terminal errors** for proper recovery

---

**Source**: https://google.github.io/adk-docs/streaming/dev-guide/part3/
**Downloaded**: 2026-02-11
