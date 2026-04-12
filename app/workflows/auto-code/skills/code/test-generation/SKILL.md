---
name: test-generation
description: Test generation patterns for the auto-code workflow — unit tests, integration tests, test fixtures
version: "1.0"
triggers:
  - deliverable_type: test
  - file_pattern: "*/tests/*.py"
tags: [testing, pytest, auto-code]
applies_to: [coder]
priority: 7
---

# Test Generation Patterns

This skill covers how to write tests for code generated in the auto-code workflow. Tests are a first-class deliverable — every implementation deliverable has a corresponding test deliverable or includes tests inline.

## pytest Patterns for AutoBuilder's Python Stack

AutoBuilder uses pytest with `pytest-asyncio` for all async tests. Mark async test functions with `@pytest.mark.asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_my_function() -> None:
    result = await my_async_function()
    assert result == expected
```

Configure `asyncio_mode = "auto"` in `pyproject.toml` to avoid marking every test individually:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Use `pytest-asyncio`'s `asyncio_mode = "auto"` — it is already configured in this project.

## Test Structure

Tests mirror the `app/` directory structure under `tests/`:

```
app/
  gateway/
    routes/
      workflows.py
  workers/
    tasks/
      run_pipeline.py
tests/
  gateway/
    routes/
      test_workflows.py
  workers/
    tasks/
      test_run_pipeline.py
```

Name test files `test_{module}.py` to match the module being tested. Place tests for `app/foo/bar.py` in `tests/foo/test_bar.py`.

One test file per module. If a test file exceeds 300 lines, split by grouping related test functions into focused files (e.g., `test_bar_create.py`, `test_bar_query.py`).

## Real Infrastructure vs Mocks

AutoBuilder's test philosophy: never mock local infrastructure.

| Infrastructure | Approach | Why |
|----------------|----------|-----|
| PostgreSQL | Real database via `AUTOBUILDER_DB_URL` | Async SQLAlchemy behavior is non-trivial to mock correctly |
| Redis | Real Redis via `AUTOBUILDER_REDIS_URL` | ARQ task queuing and Streams require real behavior |
| LLM calls | Mock — `unittest.mock.AsyncMock` | Expensive, non-deterministic, not available in CI without keys |
| External webhooks | Mock — `respx` or `httpx_mock` | Third-party services should never be called from tests |

Skip infrastructure-dependent tests gracefully when the service is unavailable:

```python
import pytest
from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.db_url.startswith("postgresql"),
    reason="Requires live PostgreSQL",
)
```

## Factory Fixtures

Use factory fixtures from `tests/conftest.py` to create test data. Factory fixtures return async callables:

```python
# tests/conftest.py pattern
@pytest.fixture
async def create_project(db_session: AsyncSession):
    async def _create(**kwargs: object) -> Project:
        project = Project(**kwargs)
        db_session.add(project)
        await db_session.flush()
        return project
    return _create

# Usage in tests
async def test_project_workflow(create_project) -> None:
    project = await create_project(name="test", status=ProjectStatus.ACTIVE)
    assert project.id is not None
```

Always use factories — never create model instances directly in test bodies. Factories ensure required fields have valid defaults and reduce test fragility when schema changes.

## Testing Pydantic Models at API Boundaries

Pydantic models at gateway API boundaries should be tested for:
- Valid input round-trips correctly
- Invalid input raises `ValidationError` with a useful message
- Enum coercion works (string input → enum member)

```python
from pydantic import ValidationError
from app.gateway.models import CreateWorkflowRequest

def test_valid_request_parses() -> None:
    req = CreateWorkflowRequest.model_validate({"name": "my-wf", "type": "code"})
    assert req.name == "my-wf"

def test_invalid_type_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CreateWorkflowRequest.model_validate({"name": "my-wf", "type": "unknown"})
    assert "type" in str(exc_info.value)
```

Never use `strict=True` on gateway models — FastAPI's `model_validate()` coerces string inputs to enums and datetime fields.

## Testing ADK CustomAgent State Writes

ADK CustomAgent state writes must use `Event` with `state_delta` — direct `session.state["key"] = val` does not persist. Test that agents yield the correct events:

```python
from google.adk.events import Event
from unittest.mock import AsyncMock, MagicMock

async def test_agent_writes_state_via_event() -> None:
    agent = MyCustomAgent(name="test-agent")
    ctx = MagicMock()
    ctx.session.state = {}

    events: list[Event] = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    # Find the event with state_delta
    state_events = [e for e in events if e.actions and e.actions.state_delta]
    assert len(state_events) >= 1
    assert state_events[0].actions.state_delta.get("my_result_key") is not None
```

Do not assert `ctx.session.state["key"]` directly — this bypasses the persistence mechanism and gives false confidence.

## Test Naming Conventions

| Pattern | Example |
|---------|---------|
| `test_{module}.py` | `test_pipeline.py` |
| `test_{function_name}` | `test_create_pipeline` |
| `test_{function_name}_{scenario}` | `test_create_pipeline_missing_manifest` |
| `test_{function_name}_{expected_outcome}` | `test_validate_manifest_returns_none_on_missing_name` |

Use descriptive names — the test name is the error message when CI fails. Avoid generic names like `test_it_works` or `test_case_1`.

## Checklist

- [ ] Async tests use `@pytest.mark.asyncio` or `asyncio_mode = "auto"`
- [ ] Test file is at `tests/{same path as app module}/test_{module}.py`
- [ ] PostgreSQL and Redis tests skip gracefully when unavailable
- [ ] LLM calls are mocked with `AsyncMock`
- [ ] Test data uses factory fixtures from `tests/conftest.py`
- [ ] Pydantic model tests cover valid, invalid, and enum coercion cases
- [ ] ADK CustomAgent tests assert `state_delta` on yielded events, not direct state mutation
