# Test Suite

Uses pytest with asyncio, real PostgreSQL and Redis — never mocked for local infrastructure. Run `uv run pytest --co -q` to see current test count.

## Quick Commands

```bash
uv run pytest                             # Full suite
uv run pytest tests/gateway/              # Gateway API tests only
uv run pytest tests/agents/               # Agent tests only
uv run pytest tests/workers/              # Worker tests only
uv run pytest tests/workflows/            # Workflow tests only
uv run pytest tests/tools/                # Tool tests only
uv run pytest tests/path/to/test_file.py  # Single file
uv run pytest -k "test_name"              # Single test by name
uv run pytest --co -q                     # List tests without running
uv run pytest --cov=app                   # With coverage
```

## Infrastructure Requirements

| Service | Address | Notes |
|---------|---------|-------|
| PostgreSQL | localhost:5432 | DB `autobuilder_test` (auto-created) |
| Redis | localhost:6379 | DB 1 (isolated from dev) |

Start infrastructure: `docker compose up -d postgres redis`

Tests skip automatically when services are unavailable — they never fail due to missing infra.

For E2E testing (full workflow execution), start the full stack:
```bash
docker compose up -d                  # gateway + worker + postgres + redis
docker compose run --rm migrate       # apply migrations
```

## Markers

| Marker | Requires | Defined in |
|--------|----------|------------|
| `require_infra` | PostgreSQL + Redis | `tests/conftest.py` |
| `require_postgres` | PostgreSQL only | `tests/conftest.py` |
| `require_redis` | Redis only | `tests/conftest.py` |
| `require_llm` | `ANTHROPIC_API_KEY` env var | `tests/conftest.py` |
| `require_tavily_key` | `TAVILY_API_KEY` env var | `tests/tools/conftest.py` |

All markers work as both class and method decorators.

## Key Fixtures (`tests/conftest.py`)

| Fixture | Scope | What it provides |
|---------|-------|-----------------|
| `engine` | function | AsyncEngine with schema, truncates all tables on teardown |
| `async_session` | function | AsyncSession for DB operations |
| `redis_client` | function | Redis client on DB 1, flushed after each test |
| `test_client` | function | httpx AsyncClient wired to FastAPI app with real DB + Redis |

## Writing New Tests

Pattern for infrastructure tests:

```python
from tests.conftest import require_infra

@require_infra
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_something(
        self,
        test_client: AsyncClient,      # for HTTP tests
        async_session: AsyncSession,    # for DB seeding
    ) -> None:
        # Seed data via async_session
        # Make request via test_client
        # Assert response
```

For unit tests (no infra needed): write normal test classes with no marker.

### Gateway Helpers (`tests/gateway/conftest.py`)

| Helper | Signature |
|--------|-----------|
| `insert_project` | `(session, *, name, brief, workflow_type, status) -> Project` |
| `insert_workflow` | `(session, *, workflow_type) -> Workflow` |
| `insert_deliverable` | `(session, *, workflow_id, project_id, name, status) -> Deliverable` |
| `insert_artifact` | `(session, *, entity_type, entity_id, path, content_type, size_bytes) -> Artifact` |

### Tool Fixtures (`tests/tools/conftest.py`)

Provides `project_dir`, `git_repo`, and `FakeToolContext` for ADK tool tests.

## Directory Layout

```
tests/
  conftest.py          # Shared fixtures, markers, DB bootstrap
  test_scaffold.py     # Project structure validation
  agents/              # Agent unit + integration tests
  db/                  # ORM model tests
  events/              # Event publisher + stream tests
  gateway/             # HTTP API endpoint tests
    conftest.py        # Gateway-specific helpers (insert_*)
  lib/                 # Library utility tests
  router/              # LLM router tests
  skills/              # Skill loading + cache tests
  tools/               # ADK tool tests
    conftest.py        # Tool-specific fixtures
  workers/             # ARQ worker tests
  workflows/           # Workflow composition + validation tests
  user-journey/        # E2E user journey tests (shell scripts, not pytest)
    fixtures/          # Test input data (committed)
    .output/           # Runtime results (gitignored)
  phase1/              # Phase 1 prototype tests (excluded from default run)
```

## User Journey Tests

Full E2E tests that drive real workflows through the system (Director → PM → Workers).
Requires the full Docker stack + LLM API keys.

```bash
docker compose up -d && docker compose run --rm migrate
bash tests/user-journey/e2e-workflow-runner.sh   # Run
bash tests/user-journey/e2e-cleanup.sh           # Cleanup (always run after)
```

Results are written to `tests/user-journey/.output/e2e-results.json`.

## Rules

- **Never mock** PostgreSQL or Redis — use real services, skip when unavailable
- Only mock **external** APIs (LLM, third-party); leave a comment explaining why
- Full type hints on all test functions
- `@require_infra` on the class, `@pytest.mark.asyncio` on each async method
