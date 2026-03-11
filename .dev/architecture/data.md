[← Architecture Overview](../02-ARCHITECTURE.md)

# Data Layer & Infrastructure

## 1. Data Layer

### Single Database

All persistent data lives in one database, accessed only through the gateway (and workers via shared SQLAlchemy models).

| Concern | Implementation |
|---------|---------------|
| ORM | **SQLAlchemy 2.0 async** (native async sessions, modern 2.0-style queries) |
| Migrations | **Alembic** (version-controlled schema evolution) |
| Driver | `asyncpg` (PostgreSQL) -- all environments |
| Access pattern | Gateway and workers share the same SQLAlchemy models |

No separate dashboard database. No separate session database. One schema, one migration history.

### Key Tables (Conceptual)

| Table | Purpose |
|-------|---------|
| `specifications` | Submitted specs and their decomposition status |
| `workflows` | Workflow execution records (status, params, timestamps) |
| `deliverables` | Individual deliverable records within a workflow |
| `project_configs` | Per-project configuration (limits, conventions, model overrides) -- DB entity, not state |
| `sessions` | ADK session state (persisted via DatabaseSessionService adapter) |
| `chats` | Chat sessions — Settings (formation/evolution), Director conversations, and project-scoped chats (session_id, type, status, title) |
| `chat_messages` | Individual messages within a chat session (role: USER or DIRECTOR, content) |
| `ceo_queue` | Unified queue: notifications, approvals, escalations, tasks (type + priority + structured metadata) |
| `events` | Audit log (subset of events written by audit consumer) |
| `webhook_listeners` | Registered webhook endpoints and filters |
| `skills` | Skill index and metadata |

---

## 2. Infrastructure

### Redis Roles

Redis serves four distinct roles from day one. This is fundamental infrastructure, not a Phase 2 optimization.

| Role | Mechanism | Purpose |
|------|-----------|---------|
| **Task queue** | ARQ (Redis lists) | Enqueue and dequeue workflow execution jobs |
| **Event bus** | Redis Streams | Persistent, replayable pipeline event distribution |
| **Cron store** | ARQ cron | Scheduled job definitions and execution tracking |
| **Cache** | Redis key/value | LLM response caching, skill index caching, session state caching |

### Database

| Concern | Choice |
|---------|--------|
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Driver | PostgreSQL (`asyncpg`) -- all environments |
| Access | Gateway + workers (shared models, single schema) |

### Filesystem

| Concern | Purpose |
|---------|---------|
| Git worktrees | Filesystem isolation for parallel code generation |
| Artifacts | Large data (generated code, reports, files) |
| Skills | Markdown + YAML frontmatter files |

---

## See Also

- [Architecture Overview](../02-ARCHITECTURE.md) -- full system architecture
- [Engine](./engine.md) -- ADK engine, App container, LiteLLM routing
- [Gateway](./gateway.md) -- API routes, type safety chain, transport
- [Observability](./observability.md) -- tracing, logging, event stream monitoring
- [Context](./context.md) -- context assembly, budgeting, knowledge loading, recreation

---

*Extracted from 02-ARCHITECTURE.md v2.9*
*Last Updated: 2026-02-28*
