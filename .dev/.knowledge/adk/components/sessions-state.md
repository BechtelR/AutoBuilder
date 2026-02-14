# State: The Session's Scratchpad

## Overview

Within each `Session`, the **`state`** attribute functions as the agent's dedicated scratchpad for that specific interaction. While `session.events` maintains full history, `state` stores dynamic details needed during the conversation.

## What is `session.state`?

`session.state` is a collection of key-value pairs designed for information the agent needs to recall during conversation:

- **Personalize Interaction:** Remember user preferences (e.g., `'user_preference_theme': 'dark'`)
- **Track Task Progress:** Monitor multi-turn process steps (e.g., `'booking_step': 'confirm_payment'`)
- **Accumulate Information:** Build lists or summaries (e.g., `'shopping_cart_items': ['book', 'pen']`)
- **Make Informed Decisions:** Store flags influencing responses (e.g., `'user_is_authenticated': True`)

## Key Characteristics

**Structure: Serializable Key-Value Pairs**
- Keys are always strings with clear names (e.g., `'departure_city'`)
- Values must be serializable: basic types like strings, numbers, booleans, and simple lists/dictionaries
- Avoid non-serializable objects, custom class instances, or functions

**Mutability:** State contents change as conversations evolve

**Persistence:** Depends on chosen `SessionService`:
- `InMemorySessionService`: Not persistent (lost on restart)
- `DatabaseSessionService`/`VertexAiSessionService`: Persistent

## State Organization with Prefixes

Prefixes define scope and persistence behavior:

| Prefix | Scope | Persistence | Use Case |
|--------|-------|-------------|----------|
| None | Current session | If service persistent | Track progress in current task |
| `user:` | All sessions for user | If service persistent | User preferences, profile details |
| `app:` | All users/sessions for app | If service persistent | Global settings, shared templates |
| `temp:` | Current invocation only | Never persistent | Intermediate calculations, flags |

## Accessing State in Agent Instructions

Use `{key}` templating to inject session state into `LlmAgent` instructions:

```python
story_generator = LlmAgent(
    name="StoryGenerator",
    model="gemini-2.0-flash",
    instruction="Write a short story about a cat, focusing on the theme: {topic}."
)
```

The framework replaces `{topic}` with the value from `session.state['topic']`.

### Important Considerations

- Ensure referenced keys exist in session state
- Use `{topic?}` for optional keys
- For literal braces, use an `InstructionProvider` function instead

## Updating State: Recommended Methods

### Method 1: Using `output_key` (Simplest)

Automatically save agent responses to state:

```python
greeting_agent = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash",
    instruction="Generate a short, friendly greeting.",
    output_key="last_greeting"
)
```

### Method 2: Manual `EventActions.state_delta` (Complex Updates)

For multiple keys or specific scopes:

```python
state_changes = {
    "task_status": "active",
    "user:login_count": 5,
    "temp:validation_needed": True
}
actions = EventActions(state_delta=state_changes)
system_event = Event(invocation_id="inv_1", author="system", actions=actions)
await session_service.append_event(session, system_event)
```

### Method 3: Via Context Objects (Recommended for Callbacks/Tools)

Modify state within callbacks or tools using provided context:

```python
def my_callback(context: CallbackContext):
    count = context.state.get("user_action_count", 0)
    context.state["user_action_count"] = count + 1
```

## ⚠️ Warning: Direct State Modification

**Avoid directly modifying** `session.state` retrieved from `SessionService` outside managed contexts:

```python
# DON'T DO THIS:
retrieved_session = await session_service.get_session(...)
retrieved_session.state['key'] = value  # Bypasses event tracking
```

**Problems:**
- Bypasses event history (loses auditability)
- Changes won't persist in persistent services
- Not thread-safe
- Ignores timestamps and event logic

**Always use:** `output_key`, `EventActions.state_delta`, or context object modifications.

> **AutoBuilder note (Phase 1 verified):** This warning also applies to `ctx.session.state["key"] = value` inside `BaseAgent._run_async_impl()`. Although `ctx` is a "managed context", direct dict writes on the session state are NOT processed by the session service. Only `state_delta` on yielded `Event` objects persists. See `adk/ERRATA.md` #1.

## Best Practices

- Store only essential, dynamic data
- Use serializable types exclusively
- Apply descriptive key names with appropriate prefixes
- Keep structures shallow with minimal nesting
- Rely on standard `append_event` update flow

---

**Source**: https://google.github.io/adk-docs/sessions/state/
**Downloaded**: 2026-02-11
