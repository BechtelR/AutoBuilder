"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db import async_session_factory, create_engine
from app.gateway.middleware.errors import ErrorHandlingMiddleware
from app.gateway.middleware.logging import RequestLoggingMiddleware
from app.gateway.routes.health import router as health_router
from app.lib import get_logger, setup_logging
from app.models.constants import APP_VERSION

logger = get_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown of DB engine and Redis client."""
    settings = get_settings()
    setup_logging(settings.log_level)

    # Create DB engine and session factory
    engine = create_engine(settings.db_url)
    app.state.engine = engine
    app.state.session_factory = async_session_factory(engine)

    # Create Redis client
    redis: Redis = Redis.from_url(settings.redis_url)  # type: ignore[type-arg]
    app.state.redis = redis

    # Verify connectivity (warn but don't crash)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.warning("Database connection failed -- starting in degraded mode", exc_info=True)

    try:
        await redis.ping()  # type: ignore[reportUnknownMemberType]
        logger.info("Redis connection verified")
    except Exception:
        logger.warning("Redis connection failed -- starting in degraded mode", exc_info=True)

    yield

    # Shutdown
    await redis.aclose()
    await engine.dispose()
    logger.info("Gateway shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="AutoBuilder", version=APP_VERSION, lifespan=lifespan)

    # Middleware (order matters -- last added = outermost)
    # Request flow: CORS -> logging -> error_handler -> route
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health_router)

    return app


app = create_app()
