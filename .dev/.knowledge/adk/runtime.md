# Runtime
> Base: https://google.github.io/adk-docs

- **Event loop** `/runtime/event-loop/` — core execution loop, how agents process events
- **Resume** `/runtime/resume/` — resuming interrupted agent runs
- **RunConfig** `/runtime/runconfig/` — runtime configuration, model overrides, safety settings
- **Command line** `/runtime/command-line/` — `adk` CLI, run/deploy/eval commands
- **API server** `/runtime/api-server/` — built-in REST server for agent serving
- **Web interface** `/runtime/web-interface/` — dev UI for testing agents

## Key Classes
`Runner` `InMemoryRunner` `RunConfig` `AppConfig`

## See Also
→ ERRATA.md #2: InMemoryRunner auto_create_session
→ events-streaming.md: event processing in the loop
