# ADK Runtime Event Loop Documentation

Source: https://google.github.io/adk-docs/runtime/event-loop/

## Core Concept

The ADK Runtime operates on an **Event Loop** pattern that facilitates communication between the `Runner` component and execution logic (Agents, Tools, Callbacks).

> "The `Runner` receives a user query and asks the main `Agent` to start processing. The `Agent` runs until it has something to report—it then **yields** or **emits** an `Event`."

## Event Loop Flow

1. Runner receives user input and initiates agent processing
2. Agent executes and yields an Event when ready to report results
3. Runner processes the Event and commits state changes via Services
4. Agent resumes execution after Runner completes processing
5. Cycle repeats until agent finishes

## Key Components

**Runner (Orchestrator)**
- Central coordinator for user invocations
- Manages the event loop, processes events, and commits changes
- Forwards events to upstream systems (UI/applications)

**Execution Logic Components**
- Agents: Process information and decide actions
- Tools: External functions called by agents
- Callbacks: User-defined functions hooking into execution points

**Event**
- Messages between Runner and execution logic
- Carries content and intended side effects (state_delta, artifact_delta)

**Services**
- SessionService: Manages session data and event history
- ArtifactService: Stores/retrieves binary data
- MemoryService: Optional long-term semantic memory

**Session**
- Container holding state and event history for one conversation
- Managed by SessionService

**Invocation**
- Single user query response cycle
- Can involve multiple agent runs, LLM calls, and tool executions
- Tied together by invocation_id

## Execution Pattern

### Runner's Role
```python
# Simplified Runner loop
def run(new_query, ...) -> Generator[Event]:
    # 1. Append query to session history
    session_service.append_event(session, Event(author='user', content=new_query))

    # 2. Start agent event generation
    agent_event_generator = agent_to_run.run_async(context)

    async for event in agent_event_generator:
        # 3. Process and commit changes
        session_service.append_event(session, event)

        # 4. Yield for upstream processing
        yield event
```

### Execution Logic's Role
```python
# Simplified agent logic
# ... execute based on current state ...

# 1. Determine change needed, construct event
update_data = {'field_1': 'value_2'}
event_with_state_change = Event(
    author=self.name,
    actions=EventActions(state_delta=update_data),
    content=types.Content(parts=[types.Part(text="State updated.")])
)

# 2. Yield event to Runner
yield event_with_state_change
# <<< EXECUTION PAUSES HERE >>>
# <<< RUNNER PROCESSES & COMMITS >>>

# 3. Resume execution
# State changes are now reliably reflected
val = ctx.session.state['field_1']  # Guaranteed to be "value_2"
print(f"Value is now: {val}")
```

## Simplified Invocation Flow

1. User submits query
2. Runner loads session and records query
3. Agent execution begins
4. Agent determines action needed (e.g., tool call)
5. Agent wraps action in FunctionCall Event and yields
6. Runner records event, pauses agent
7. Agent resumes and executes tool
8. Tool returns result, wrapped in FunctionResponse Event
9. Runner processes and commits any state changes
10. Agent resumes with updated state
11. Agent generates final LLM response
12. Final text Event yielded and processed
13. Agent completes, Runner finishes invocation

## Important Runtime Behaviors

**State Updates & Commitment**
- Local state modifications tracked within InvocationContext
- Only guaranteed persistent after yielded Event is processed by Runner
- Code resuming after yield can safely assume previous changes are committed

> "Code running _after_ resuming from a `yield` can reliably assume that the state changes signaled in the _yielded event_ have been committed."

**"Dirty Reads" of Session State**
- Code can access uncommitted state changes within same invocation before yield/process cycle
- Useful for multi-step coordination within single complex operation
- Risk: uncommitted changes lost if invocation fails before event processing
- Solution: tie critical transitions to successfully-processed events

**Streaming vs. Non-Streaming Output**
- Streaming: LLM generates token-by-token, yields multiple Events with `partial=True`
- Runner forwards partial events upstream but skips processing actions
- Final non-partial Event (`partial=False`) fully processed with state commits
- Non-streaming: single Event processed with complete response

**Asynchronous Foundation**
- Runtime built on async patterns (asyncio, RxJava, Promises)
- `Runner.run_async` is primary entry point
- Synchronous `Runner.run` wraps async for convenience
- Supports both async and sync tools/callbacks
- Async I/O APIs recommended to prevent event loop stalls

## Supported Versions

- Python: v0.1.0+
- TypeScript: v0.2.0+
- Go: v0.1.0+
- Java: v0.1.0+
