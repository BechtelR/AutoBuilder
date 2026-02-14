"""Health check endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.deps import get_db_session, get_redis
from app.gateway.models import HealthResponse, HealthStatus, ServiceStatus
from app.models.constants import APP_VERSION

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]  # type: ignore[type-arg]


@router.get("/health", response_model=HealthResponse)
async def health_check(
    response: Response,
    db: DbSession,
    redis: RedisClient,
) -> HealthResponse:
    """Return service health with per-dependency status."""
    services: dict[str, ServiceStatus] = {}

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        services["postgres"] = "ok"
    except Exception:
        services["postgres"] = "unavailable"

    # Check Redis
    try:
        await redis.ping()  # type: ignore[reportUnknownMemberType]
        services["redis"] = "ok"
    except Exception:
        services["redis"] = "unavailable"

    all_ok = all(v == "ok" for v in services.values())
    status: HealthStatus = "ok" if all_ok else "degraded"

    if not all_ok:
        response.status_code = 503

    return HealthResponse(status=status, version=APP_VERSION, services=services)
