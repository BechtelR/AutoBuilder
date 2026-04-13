---
name: performance-review
description: This skill provides a performance review checklist for code changes, covering async patterns, database query optimization, caching strategies, and resource management.
triggers:
  - tag_match: performance
tags: [performance, optimization, async, caching, database]
applies_to: [reviewer]
priority: 10
---

# Performance Review

This skill provides a focused performance review process for AutoBuilder code changes. Apply it to any change that touches database queries, async I/O, caching, or background task processing.

## Async Patterns

AutoBuilder is async throughout — blocking calls in async context are the most common performance defect.

- Every `async def` function must only call async I/O — no sync blocking
- SQLAlchemy queries use `await session.execute(...)`, not synchronous session methods
- Redis operations use `await redis_client.get(...)` — not synchronous `redis` library
- Sync SDK calls must be wrapped: `await asyncio.to_thread(sync_client.invoke, ...)`
- Never `time.sleep()` in async code — use `await asyncio.sleep()` or eliminate the sleep
- ARQ tasks are `async def` — they run in async worker context

Scan for any `def` (not `async def`) functions that call `await` — this is a syntax error. Scan for sync calls inside `async def` that touch I/O.

## N+1 Query Detection

N+1 queries are the most common database performance defect. Flag these patterns:

- Loop that calls `await session.get(Model, id)` for each item in a list — use `selectinload` or a single `IN` query
- Relationship access inside a loop without eager loading configured
- Repeated `SELECT` for the same resource without caching

Preferred patterns:

```python
# Batch load related objects
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(Project).options(selectinload(Project.deliverables)).where(...)
)
```

For lists, use `WHERE id IN (...)` rather than individual queries:

```python
result = await session.execute(
    select(Deliverable).where(Deliverable.id.in_(ids))
)
```

## Index Usage

Verify that queries filter on indexed columns:

- Foreign key columns must have indexes (`ix_deliverables_project_id`)
- Status columns used in WHERE filters should be indexed if cardinality warrants
- Composite indexes for multi-column filters applied together

Check that new migrations create indexes for foreign key columns and high-frequency filter columns.

## Connection Pooling

SQLAlchemy async engine uses a connection pool. Verify:

- Sessions are obtained via dependency injection (`Depends(get_db_session)`) — never create ad-hoc engines or sessions
- Sessions are closed/released after use — the dependency context manager handles this
- Long-running transactions (e.g., iterating a large result set) are chunked or streamed rather than holding a connection for the duration

## Redis Caching Patterns

Redis is available for caching expensive lookups. When reviewing code that repeatedly fetches the same data:

- Check if a cache layer exists or should be added
- Cache keys must be deterministic and invalidated on mutation
- TTL must be set on all cached values — no indefinite caching
- Cache-aside pattern: check cache, on miss load from DB, populate cache

```python
cache_key = f"project:{project_id}"
cached = await redis.get(cache_key)
if cached:
    return ProjectResponse.model_validate_json(cached)
project = await load_from_db(project_id)
await redis.set(cache_key, project.model_dump_json(), ex=300)
```

## Memory Management

- Streaming large result sets: use `yield_per()` on SQLAlchemy queries rather than loading all rows at once
- Agent context size: skill bodies and agent instructions should stay under token limits — SKILL.md under 3000 words
- Redis Streams: consumers should use `XREAD COUNT N` with a bounded count, not unbounded reads
- ARQ job payloads should carry IDs, not full objects — workers load from DB

## Background Task Sizing

ARQ tasks that process agent pipelines should be bounded:

- One deliverable pipeline per task — never batch multiple deliverables in one ARQ job
- Tasks that fan out (Phase 8a concurrency) respect `AUTOBUILDER_MAX_CONCURRENCY`
- Long-running tasks should checkpoint state to Redis/DB so they can be resumed on worker restart

## Checklist

- [ ] No sync I/O inside `async def` functions
- [ ] No `time.sleep()` in async context
- [ ] Loops do not contain individual DB queries — use batch/IN queries
- [ ] Relationships are eagerly loaded when accessed in loops
- [ ] New foreign key columns have indexes
- [ ] No ad-hoc SQLAlchemy engine creation — use dependency injection
- [ ] Cached values have TTL set
- [ ] Large result sets use pagination or `yield_per()`, not full load
