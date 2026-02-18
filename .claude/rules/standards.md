# Engineering Standards
*Version: 2.2602.1.0*

## Philosophy

**"Start simple, stay simple"** - Complexity solves proven problems, not potential ones.

**"Human oversight by default"** - System proposes, user decides. Automation is configurable.

## Core Principles

### 1. Simplicity First
- What's the simplest solution for TODAY's problem?
- Don't let 5% edge cases complicate 95% of code
- Abstract only after third occurrence (DRY at 3)

### 2. Single Source of Truth
- SQLAlchemy models → Pydantic → OpenAPI → generated TypeScript (hey-api)
- Configuration in database/env, not hardcoded
- TanStack Query for server state, Zustand for UI state only

### 3. Fail Safe, Not Silent
- Errors in automated pipelines are expensive
- Make failures loud and recoverable
- Never fail silently on state transitions

### 4. Async by Default
- All I/O operations asynchronous
- ARQ for scheduled/heavy tasks (Redis-backed, native asyncio)
- SSE for real-time event streaming

### 5. Security
- Credentials encrypted at rest, never logged
- Input validation at gateway boundaries via Pydantic
- Audit trail for all significant state changes via Redis Streams

## Implementation Rules

### Zero Backwards-Compatibility Shims
Early development = zero regression technical debt. Don't create it. Delete when found, deprecated code, obsolete elements. Ask user if in question.

### Migrations
Sequential `NNN_description.py` naming. Never hash-based IDs. `--rev-id NNN` on every `alembic revision`.

### Avoid
- Abstractions for single use cases
- Factories with <3 implementations
- Inheritance deeper than 2 levels
- `Any` type (use explicit types, `TypedDict`, or `object`)
- Hardcoded configuration values

### Prefer
- Direct function calls over indirection
- Data + functions over deep hierarchies
- Protocol classes for multi-implementation interfaces
- Explicit code over clever abstractions
- CSS variables for theming (not hardcoded colors)

## Testing: Real Infrastructure, Never Mocked

- **Never mock** local infrastructure (PostgreSQL, Redis) — use real services; skip when unavailable
- Only mock **external** APIs (LLM, third-party webhooks)
- Degraded-path tests use broken connection URLs, not mock objects

## Common Violations to Watch

- **String Literals**: Use enums/constants, not magic strings.
- **DRY**: Search for existing code before implementing. Check shared utilities and hooks.

## Boundary Type Safety

**External boundaries → Pydantic v2 models:**
- LLM responses, webhooks, external services, env config
- Validates + normalizes untrusted data at ingress

**Internal DTOs → dataclass/TypedDict:**
- No `Any`; use explicit types, `TypedDict`, or `object` for proven dynamic
- `Generic[T]` for reusable patterns
- pyright strict mode enforced

## Enum Convention (CRITICAL)

Values MUST match names (uppercase). OpenAPI serializes enum values directly.
```python
class WorkflowStatus(str, enum.Enum):
    RUNNING = "RUNNING"  # ✅ Value = name
    # RUNNING = "running"  # ❌ Breaks type flow
```

## Quick Reference

### Decision Checklist
- [ ] What's the simplest solution that works?
- [ ] Is this configurable via UI where it should be?
- [ ] Do I have 3+ real implementations TODAY?
- [ ] What happens when this fails?
- [ ] Are credentials protected?
- [ ] Did I check for existing reusable code?
- [ ] Am I using enums/constants instead of string literals?

### Over-Engineering Signals
You're over-engineering if:
1. Creating abstractions for <3 implementations that exist TODAY
2. Optimizing for edge cases (5%) over common cases (95%)
3. Adding indirection "just in case"
4. Building for 1M users when we have 10

### Exceptions
When breaking standards, document why:
```python
# EXCEPTION: Sync call - external SDK doesn't support async
# Review: Phase 2
```

## Keywords
`SIMPLE` | `CONFIGURABLE` | `DRY` | `ASYNC` | `AUDITABLE`
