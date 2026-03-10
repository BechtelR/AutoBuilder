[← Architecture Overview](../02-ARCHITECTURE.md)

# Observability

## 1. Phased Approach

| Phase | Tool | Purpose |
|-------|------|---------|
| Phase 1 | **OpenTelemetry** | ADK-native tracing (auto-traces agents, tools, runner) |
| Phase 1 | **Python logging** | Structured logs under `app.*` hierarchy |
| Phase 1 | **Redis Streams** | Pipeline events (also serves as operational observability) |
| Phase 2 | **Langfuse** | LLM-specific tracing (token usage, latency, quality) |
| Phase 3 | **Custom dashboard** | Integrated observability views in the web dashboard |

### Event Stream

Every agent (LLM or deterministic) emits `Event` objects into ADK's unified chronological stream. The anti-corruption layer translates these to gateway events and publishes to Redis Streams. This provides full pipeline visibility from plan to execution to validation to review.

`adk web` remains available as a local development tool for detailed ADK-level debugging, but is not part of the production observability stack.

---

## 2. Context Management

For context window management, budgeting, knowledge loading, and context recreation, see [context.md](./context.md).

---

## See Also

- [Architecture Overview](../02-ARCHITECTURE.md) -- full system architecture
- [Context](./context.md) -- context assembly, budgeting, knowledge loading, recreation
- [Engine](./engine.md) -- ADK engine, App container, LiteLLM routing
- [Agents](./agents.md) -- hierarchical agent structure and pipeline composition
- [Data](./data.md) -- database, Redis, and filesystem infrastructure

---

*Document Version: 4.0*
*Last Updated: 2026-03-10*
