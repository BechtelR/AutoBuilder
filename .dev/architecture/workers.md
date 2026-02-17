[← Architecture Overview](../02-ARCHITECTURE.md)

# Worker Architecture

### ARQ Workers

Workers execute workflow pipelines out-of-process. The gateway never runs ADK directly.

| Concern | Implementation |
|---------|---------------|
| Worker framework | **ARQ** (native asyncio, Redis-backed) |
| Why not Celery | Celery is sync-first; ARQ is native asyncio, simpler, fits the stack |
| Execution model | Gateway enqueues a job (workflow ID + params) -> ARQ worker picks up -> runs ADK pipeline -> publishes events to Redis Streams |
| Concurrency | Multiple workers can run in parallel; each worker runs one pipeline at a time |
| Cron jobs | **ARQ cron** for scheduled tasks (cleanup, health checks, scheduled workflows) |
| Idempotency | Workers must handle re-delivery; ADK resume helps with crash recovery |

### Worker Lifecycle

```python
# Simplified worker structure
async def run_workflow(ctx: dict, workflow_id: str, params: dict) -> None:
    """ARQ job function -- runs in worker process."""
    # Anti-corruption layer: translate gateway params -> ADK
    runner = create_adk_runner(workflow_id, params)
    session = await create_or_resume_session(workflow_id)

    async for event in runner.run_async(session):
        # Translate ADK event -> gateway event schema
        gateway_event = translate_event(event)
        # Publish to Redis Streams
        await publish_to_stream(workflow_id, gateway_event)
        # Update database state
        await update_workflow_state(workflow_id, event)
```

---

## See Also

- [Gateway](./gateway.md) -- API layer that enqueues work to workers
- [Events](./events.md) -- Redis Streams event distribution (workers publish here)
- [Clients](./clients.md) -- CLI and dashboard (pure API consumers)

---

*Document Version: 1.0*
*Last Updated: 2026-02-17*
*Extracted from [02-ARCHITECTURE.md](../02-ARCHITECTURE.md) v2.9*
