# State & Sessions
> Base: https://google.github.io/adk-docs

- **State overview** `/sessions/state/` — 4 scopes: temp, run, session, app; state_delta for persistence
- **Session management** `/sessions/session/` — session creation, lifecycle, InMemorySessionService, DatabaseSessionService
- **Session rewind** `/sessions/session/rewind/` — replay from checkpoint, undo last N events
- **Session migration** `/sessions/session/migrate/` — cross-service session transfer

## Key Classes
`Session` `State` `SessionService` `InMemorySessionService` `DatabaseSessionService`

## See Also
→ ERRATA.md #1: state_delta persistence in CustomAgent (CRITICAL)
→ ERRATA.md #2: InMemoryRunner auto_create_session
→ memory.md: cross-session memory
