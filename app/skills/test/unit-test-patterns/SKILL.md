---
name: unit-test-patterns
description: This skill provides patterns for writing unit and integration tests in AutoBuilder, including fixture patterns, mock strategies, and test organization conventions.
triggers:
  - deliverable_type: test
  - file_pattern: "*/tests/*.py"
tags: [testing, pytest, fixtures, mocking]
applies_to: [coder]
priority: 10
---

# Unit and Integration Test Patterns

This skill covers the conventions for writing tests in AutoBuilder. The fundamental rule: never mock local infrastructure. Tests run against real PostgreSQL and real Redis. Only external services (LLMs, third-party APIs) are mocked.

## Test Organization

Mirror the `app/` structure under `tests/`:

```
tests/
├── conftest.py            # Shared fixtures (db engine, redis, http client)
├── gateway/
│   ├── routes/
│   │   └── test_projects.py
│   └── models/
├── workers/
│   └── test_pipeline.py
├── skills/
│   └── test_parser.py
└── agents/
    └── test_instruction_assembler.py
```

Test file names: `test_<module_name>.py`. Test class names: `TestClassName`. Function names: `test_<what>_<condition>_<expected>`.

## Fixtures

Define shared fixtures in `tests/conftest.py`. Scope determines lifecycle:

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Session-scoped engine — one per test run."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped session — fresh transaction per test, rolled back after."""
    async with AsyncSession(db_engine) as session:
        async with session.begin():
            yield session
            await session.rollback()
```

Fixture scopes:
- `scope="session"` — database engine, Redis connection (expensive to create)
- `scope="function"` (default) — database sessions, HTTP client (isolate per test)
- `scope="module"` — rarely used; justified for read-only fixture data

## Real Infrastructure

Never mock PostgreSQL or Redis. Skip tests when infrastructure is unavailable:

```python
import pytest
from sqlalchemy.exc import OperationalError

@pytest.fixture
def maybe_skip_db(db_engine):
    """Skip test if database is unavailable."""
    try:
        # connection tested in db_engine fixture
        pass
    except OperationalError:
        pytest.skip("Database unavailable")
```

Use broken connection URLs for degraded-path tests — not mock objects:

```python
BAD_DB_URL = "postgresql+asyncpg://invalid:invalid@localhost:9999/nonexistent"

async def test_graceful_db_failure():
    engine = create_async_engine(BAD_DB_URL)
    with pytest.raises(OperationalError):
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
```

## Mocking External APIs

Mock LLM calls and third-party webhooks with `unittest.mock`:

```python
from unittest.mock import AsyncMock, patch

async def test_pipeline_calls_llm():
    mock_response = create_mock_llm_response("result text")
    with patch("app.agents.pipeline.litellm.acompletion", new=AsyncMock(return_value=mock_response)):
        result = await run_pipeline(project_id="test-123")
    assert result.status == PipelineStatus.COMPLETE
```

For ADK-based agents, mock at the `litellm.acompletion` level — not at ADK internals. ADK's LlmAgent calls litellm internally.

## Async Test Patterns

Use `pytest-asyncio`. Configure asyncio mode in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Mark async test functions with the module-level asyncio mode or explicit marker:

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

With `asyncio_mode = "auto"`, the marker is optional but explicit markers are acceptable.

## HTTP Client Fixtures

For gateway route tests, use `httpx.AsyncClient` with FastAPI's `ASGITransport`:

```python
import httpx
from app.gateway.main import app

@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
```

Test routes end-to-end through HTTP — this validates routing, request parsing, response serialization, and status codes.

## Factory Patterns

Create factory helpers for test data rather than duplicating construction:

```python
def make_project(
    *,
    name: str = "Test Project",
    status: ProjectStatus = ProjectStatus.ACTIVE,
    **kwargs: object,
) -> Project:
    return Project(
        id=str(uuid4()),
        name=name,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **kwargs,
    )
```

Place factories in `tests/factories.py` or a `factories/` subdirectory. Never duplicate field construction inline.

## Assertions

Prefer specific assertions over broad `assert result`:

```python
# Vague
assert result

# Specific
assert result.status == ProjectStatus.ACTIVE
assert result.name == "Expected Name"
assert len(result.deliverables) == 3
```

For HTTP responses, assert both status code and body structure:

```python
response = await client.post("/projects", json={"name": "My Project"})
assert response.status_code == 201
data = response.json()
assert data["name"] == "My Project"
assert data["status"] == "ACTIVE"
```

## Checklist

- Tests mirror `app/` directory structure under `tests/`
- Real PostgreSQL and Redis used — never mocked
- External APIs (LLM, webhooks) mocked at the integration boundary
- Shared fixtures in `conftest.py` with correct scope
- Async tests use `pytest-asyncio`
- Route tests use `httpx.AsyncClient` via ASGI transport
- Factory helpers used for test data construction
- Assertions are specific, not just truthiness checks
