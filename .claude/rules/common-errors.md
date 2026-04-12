# Common Errors to Avoid

**IMPORTANT: KEEP EXTREMELY COMPACT**: Loaded into context. ZERO verbose examples.

## Backwards Compatibility Shims
Early development phase = zero regression technical debt. Don't create it. Delete when found deprecated code, obsolete elements. When in question, ask user.

## `Any` Type at Boundaries (CRITICAL)
External data → Pydantic v2. Internal DTOs → `dataclass`/`TypedDict`. Never `Any`.
```python
# ❌ response: dict[str, Any] = api.get_data()
# ✅ items = [MyModel.model_validate(item) for item in response]
```

**Allowed `Any` exceptions** (use `# type: ignore` where needed):
- SQLAlchemy TypeDecorator: interface requires it
- Redis deserialize: `cast(T, json.loads(...))` — explicit assertion
- ADK callback signatures: framework stubs incomplete
- LiteLLM response internals: provider-agnostic wrapper types
- Design-time or development-time tests where type safety isn't critical (mark with `# type: ignore` and comment why)

## Enums & String Literals
All enums live in `app.models.enums`. Never define enums inline unless they are strictly private to a class.
Never use magic strings— use enums, constants, or helpers.
Compare enum members directly, never via `.value` string matching.
```python
# ❌ if status == "running":  |  channel = f"workflow:{id}"
# ✅ if status == WorkflowStatus.RUNNING:
```

## Async Patterns
```python
# ARQ task: already async
async def my_task(ctx: dict) -> None: ...

# Sync SDK in async context
await asyncio.to_thread(client.invoke)

# Redis client is instance
await redis_client.publish(channel, msg)  # not redis_client()
```

## Datetime (Python 3.11+)
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)  # not utcnow()
```

## Frontend Patterns
- `type="button"` on non-submit buttons
- Semantic colors: use CSS variables, not hardcoded values
- Verbose UI text: Button labels 1-3 words max. Use icons to convey meaning.

## Ref Declaration Order
Refs must be declared before callbacks that use them. `useRef` isn't hoisted.
- ❌ `const handleChange = useCallback(() => { isMountedRef.current }, []); const isMountedRef = useRef(true)`
- ✅ `const isMountedRef = useRef(true); const handleChange = useCallback(() => { isMountedRef.current }, [])`

## Debug Code in Production
Never commit temporary debug logging. Use `logger.debug()` for persistent diagnostics.
- ❌ `import logging as _dbg_logging` + `_dbg_logger.warning("DEBUG: ...")`
- ❌ `# Temporary debug:` comments with `logger.warning()` for debug output
- ✅ `logger.debug(...)` with the module's existing logger

## Task Completion
Never mark `[x]` with `NotImplementedError` or unresolved `TODO`. Verify: `grep -n "TODO\|NotImplementedError" file.py`

## Incomplete API Refactoring
Import alias preserves import compat only, not API compat. When refactoring class APIs:
1. Search ALL consumers: `grep -rn "\.old_method\|old_param=" app/ tests/`
2. Update consumers BEFORE marking task complete
3. Run FULL test suite, not just direct tests

## External Data Validation (TypeScript)
Never `as` cast `JSON.parse()` or `unknown` without validation.
- ❌ `JSON.parse(raw) as MyType`
- ✅ `const parsed: unknown = JSON.parse(raw); if (!parsed || typeof parsed !== 'object') return`

Applies to: drag-drop, localStorage, SSE messages, backend `unknown` fields.

## Escape Key Layering in Nested Popups
Inner layer consumes Escape when it has dismissable state. Propagate only when inner state is already closed.
- ❌ `case 'Escape': onParentKeyDown?.(e); setIsOpen(false)` (collapses all layers)
- ✅ `if (isOpen) { setIsOpen(false) } else { onParentKeyDown?.(e) }` (layered)

## SVG `id` Collisions
SVG `id` is document-global. Multiple component instances with same ID → rendering corruption.
- ✅ `const id = useId(); <linearGradient id={`grad-${id}`}>`

## Unstable Render Data
`Math.random()` or non-memoized generators in render cause flicker on every re-render.
- ✅ `const data = useMemo(() => generate(), [dep])`

## Terminology Consistency (Docs)
Canonical term is "deliverable" (not "feature"). Code examples, state keys, class names must match.
- ❌ `FeaturePipeline`, `current_feature_spec`, `incomplete_features_exist`
- ✅ `DeliverablePipeline`, `current_deliverable_spec`, `incomplete_deliverables_exist`

## Documentation Debt via Static References
Never embed values that change — counts, dates, versions, totals. Each is silent debt. Link to the source or use unquantified language.
- ❌ `67 decisions`, `14 architecture files`, `as of 2026-03-11`
- ✅ `all decisions`, `see .decision-log.md`

## Doc-Code Constant Drift
When a standard value changes (e.g., module line limit), grep ALL docs for the old value and batch/script replace.

## Decision Cascade Propagation
When updating a primary architecture doc, grep ALL satellite docs for changed constructs (counts, stage lists, decision numbers, data flow paths, state key usage patterns). They silently go stale.

## Pydantic `strict=True` on API Models
Never use `strict=True` on gateway models. FastAPI uses `model_validate()` (dict), not `model_validate_json()` — strict rejects `str→enum`/`str→datetime` coercion, breaking any model with those fields.

## `hasattr()` on Pydantic Models
Pydantic v2 fields always exist on the class. `hasattr()` is always `True` — use direct access + None check.
- ❌ `if hasattr(model, "field") and model.field:`
- ✅ `if model.field is not None:`

## AutoBuilderError Hierarchy
Each subclass has a hardcoded `ErrorCode`. Never pass `code=` to a subclass — use the correct subclass.
- ❌ `WorkerError(message=..., code=ErrorCode.NOT_FOUND)`
- ✅ `NotFoundError(message=...)` (uses `ErrorCode.NOT_FOUND` internally)

## ADK CustomAgent: State Writes (CRITICAL)
Direct `ctx.session.state["key"] = val` does NOT persist. Only `state_delta` on yielded Events persists. Reads work normally.
- ❌ `ctx.session.state["key"] = val`
- ✅ `yield Event(author=self.name, actions=EventActions(state_delta={"key": val}))`

## ADK Session State: External Mutation (CRITICAL)
`session.state` from `get_session()` is a snapshot — mutation doesn't persist. Delete + `create_session()` with merged state.
