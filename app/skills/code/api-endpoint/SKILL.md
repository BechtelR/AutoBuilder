---
name: api-endpoint
description: This skill provides conventions and patterns for implementing REST API endpoints in the AutoBuilder gateway layer, including route structure, request/response models, dependency injection, and error handling.
triggers:
  - deliverable_type: api_endpoint
  - file_pattern: "*/routes/*.py"
tags: [api, http, routing, fastapi]
applies_to: [coder, reviewer]
priority: 10
---

# API Endpoint Conventions

This skill covers the patterns and conventions for implementing REST API endpoints in AutoBuilder's gateway layer. The gateway is the single point of entry for all external clients — never expose ADK internals through it.

## Route Structure

Organize routes using `APIRouter` with a consistent prefix and tag:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["projects"])
```

Register routers in `app/gateway/main.py` via `app.include_router(router)`. Each domain gets its own module under `app/gateway/routes/`.

Use RESTful naming: plural nouns for collections (`/projects`), specific resource by ID (`/projects/{project_id}`), nested resources for tight ownership (`/projects/{project_id}/deliverables`).

HTTP verbs map to operations:
- `GET` — read, never mutate
- `POST` — create
- `PATCH` — partial update (prefer over PUT)
- `DELETE` — remove

## Request and Response Models

Define Pydantic models in `app/gateway/models/` (not in routes). Every endpoint has explicit `response_model`:

```python
from pydantic import BaseModel

class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    status: ProjectStatus
    created_at: datetime
```

- Request models: validate inbound data, convert strings to enums/datetimes via Pydantic coercion
- Response models: never expose raw SQLAlchemy objects — always convert via `.model_validate(db_obj, from_attributes=True)`
- Use `ConfigDict(from_attributes=True)` on response models to support ORM → Pydantic conversion
- Never use `strict=True` on gateway models — FastAPI uses dict-based validation where strict breaks coercion

Enums in response models must use `str` enum values matching the `WorkflowStatus = "RUNNING"` convention (value equals name, uppercase). The TypeScript client receives these as strings.

## Dependency Injection

Use FastAPI's `Depends()` for cross-cutting concerns:

```python
from fastapi import Depends
from app.gateway.deps import get_db_session, get_redis

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    redis: ArqRedis = Depends(get_redis),
) -> ProjectResponse:
    ...
```

Standard dependencies in `app/gateway/deps.py`:
- `get_db_session` — yields `AsyncSession`, commits on success, rolls back on exception
- `get_redis` — returns shared `ArqRedis` client (superset of Redis, single client for jobs + cache)
- `get_current_user` — auth header extraction (Phase 7a+)

Prefer thin route handlers — move business logic into service functions or ARQ tasks. A route should read request, call service, return response.

## Error Handling

Raise `HTTPException` with structured detail:

```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
)
```

Map to status codes:
- `400` — validation error (Pydantic handles automatically), bad request logic
- `404` — resource not found
- `409` — conflict (e.g., duplicate name)
- `422` — unprocessable entity (FastAPI default for Pydantic errors)
- `500` — unexpected internal error (log and raise)

Translate `AutoBuilderError` subclasses to HTTP codes in a global exception handler registered in `main.py`. Never leak stack traces to clients.

## Async Patterns

All route handlers must be `async def`. Database and Redis calls are async. Never call sync I/O inside an async route — wrap with `asyncio.to_thread()` if an SDK forces sync.

```python
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await project_service.create(db, request)
    return ProjectResponse.model_validate(project, from_attributes=True)
```

## OpenAPI Generation

FastAPI auto-generates OpenAPI from route signatures. Ensure:
- `response_model` is always set (drives TypeScript codegen)
- `status_code` matches actual response (201 for creates)
- Route has a docstring (becomes OpenAPI description)
- Tags group routes logically in Swagger UI

After adding routes, regenerate TypeScript client from `dashboard/` with `npm run generate`.

## Enqueuing Work

Routes that trigger heavy operations enqueue ARQ tasks — they do not run pipelines inline:

```python
job = await redis.enqueue_job("run_deliverable_pipeline", deliverable_id=str(deliverable.id))
return AcceptedResponse(job_id=job.job_id)
```

Return `202 Accepted` for async operations. The client polls status via a separate endpoint or subscribes via SSE.

## Checklist

- Route uses `APIRouter` with correct prefix and tag
- Request and response models are explicit Pydantic classes
- `response_model` set on every endpoint
- `Depends()` used for db/redis, not module-level singletons
- Business logic not inline — delegated to service or ARQ task
- Errors raised as `HTTPException` with structured detail dict
- All handlers are `async def`
- No ADK types in response models
