[← Architecture Overview](../02-ARCHITECTURE.md)

# Event System

### Redis Streams

Redis Streams serve as the persistent, replayable event bus. All pipeline events flow through streams.

| Feature | Implementation |
|---------|---------------|
| Publish | Workers publish translated ADK events to a per-workflow stream |
| Persistence | Events are stored in Redis with configurable retention |
| Replay | Consumers can read from any point in the stream (by ID) |
| Consumer groups | Multiple independent consumers process the same stream |
| Delivery guarantees | At-least-once via consumer group acknowledgment |

### Consumers

| Consumer | Purpose | Mechanism |
|----------|---------|-----------|
| **SSE endpoint** | Push real-time events to connected clients | Gateway reads stream, pushes via SSE |
| **Webhook dispatcher** | Notify external systems | Reads events, dispatches via httpx to registered listeners (stored in DB) |
| **Audit logger** | Compliance and debugging | Reads events, writes to database |

### SSE Reconnection

```
1. Client connects:   GET /events/stream
2. Server streams:    event: pipeline.step.completed (id: 1707-001)
3. Connection drops
4. Client reconnects: GET /events/stream  (Last-Event-ID: 1707-001)
5. Server replays:    all events after 1707-001 from Redis Stream
6. Server resumes:    live streaming from current position
```

No events are lost. Redis Stream IDs map directly to SSE event IDs.

### Event Listeners (Webhooks)

- Registered hooks stored in database (URL, event filter, secret)
- Redis Stream consumer reads matching events
- Dispatches via httpx with HMAC signature
- Retry with exponential backoff on failure

### Unified CEO Queue

A single DB-backed queue that aggregates all items requiring CEO attention across all projects. Items are **not injected into chat sessions** -- they live in a separate queryable/dismissable queue with SSE push for real-time notification.

| Field | Purpose |
|-------|---------|
| `type` | `NOTIFICATION`, `APPROVAL`, `ESCALATION`, `TASK` |
| `priority` | `LOW`, `NORMAL`, `HIGH`, `CRITICAL` |
| `source_project` | Which project produced this item |
| `source_agent` | Which agent (Director, PM) enqueued it |
| `metadata` | Structured JSON payload (approval choices, escalation context, task details) |
| `status` | `PENDING`, `SEEN`, `RESOLVED`, `DISMISSED` |

**Write path**: Director enqueues items via `enqueue_ceo_item` FunctionTool. PMs no longer write directly to the CEO queue — they escalate to the Director queue via `escalate_to_director`. Redis Streams events can also trigger queue entries via a consumer.

**Read path**: Dashboard polls `GET /ceo/queue` or subscribes to `GET /ceo/queue/stream` (SSE). CEO resolves items via `PATCH /ceo/queue/{id}`. Resolved approvals are written back to the relevant session's state for the agent to observe on next invocation.

### Director Queue

A DB-backed queue for PM-to-Director escalation. Parallel design to the CEO queue.

| Field | Purpose |
|-------|---------|
| `type` | `ESCALATION`, `STATUS_REPORT`, `RESOURCE_REQUEST`, `PATTERN_ALERT` |
| `priority` | `LOW`, `NORMAL`, `HIGH`, `CRITICAL` |
| `status` | `PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO` |
| `source_project` | Which project produced this item |
| `source_agent` | Which PM agent enqueued it |
| `metadata` | Structured JSON payload (escalation context, status details, resource needs) |

**Write path**: PM agents enqueue items via `escalate_to_director` FunctionTool.

**Read path**: Director processes items during work sessions. Director can resolve locally or forward to CEO queue via `enqueue_ceo_item`.

#### Escalation Path

```
PM → Director Queue → Director → resolves OR → CEO Queue → CEO
```

---

## See Also

- [Gateway](./gateway.md) -- SSE endpoints and CEO queue routes
- [Workers](./workers.md) -- workers publish events to Redis Streams
- [Clients](./clients.md) -- CLI and dashboard consume events

---

*Document Version: 2.0*
*Last Updated: 2026-02-18*
*Extracted from [02-ARCHITECTURE.md](../02-ARCHITECTURE.md) v2.9*
