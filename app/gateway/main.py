"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from arq.connections import ArqRedis, create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings, parse_redis_settings
from app.db import async_session_factory, create_engine
from app.gateway.middleware.errors import ErrorHandlingMiddleware
from app.gateway.middleware.logging import RequestLoggingMiddleware
from app.gateway.routes.ceo_queue import router as ceo_queue_router
from app.gateway.routes.chat import router as chat_router
from app.gateway.routes.health import router as health_router
from app.gateway.routes.skills import router as skills_router
from app.gateway.routes.workflows import router as workflow_router
from app.lib import get_logger, setup_logging
from app.models.constants import APP_VERSION
from app.skills.library import SkillLibrary
from app.workflows.registry import WorkflowRegistry

logger = get_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown of DB engine and ArqRedis pool."""
    settings = get_settings()
    setup_logging(settings.log_level)

    # Create DB engine and session factory
    engine = create_engine(settings.db_url)
    app.state.engine = engine
    app.state.session_factory = async_session_factory(engine)

    # Create ArqRedis pool (superset of redis.asyncio.Redis)
    arq_pool: ArqRedis = await create_pool(parse_redis_settings(settings.redis_url))
    app.state.arq_pool = arq_pool

    # Verify connectivity (warn but don't crash)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.warning("Database connection failed -- starting in degraded mode", exc_info=True)

    try:
        await arq_pool.ping()  # type: ignore[reportUnknownMemberType]
        logger.info("Redis connection verified")
    except Exception:
        logger.warning("Redis connection failed -- starting in degraded mode", exc_info=True)

    # Initialize SkillLibrary with global skills directory
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    skill_library = SkillLibrary(global_dir=skills_dir, redis=arq_pool)
    cache_hit = await skill_library.load_from_cache()
    if not cache_hit:
        skill_library.scan()
        try:
            await skill_library.save_to_cache()
        except Exception:
            logger.debug("Skill index cache save skipped (non-critical)")
    app.state.skill_library = skill_library

    # Initialize WorkflowRegistry with built-in and user-level workflow directories
    builtin_workflows_dir = Path(__file__).resolve().parent.parent / "workflows"
    workflow_registry = WorkflowRegistry(
        workflows_dir=builtin_workflows_dir,
        user_workflows_dir=settings.workflows_dir,
        redis=arq_pool,
    )
    cache_hit = await workflow_registry.load_from_cache()
    if not cache_hit:
        workflow_registry.scan()
        try:
            await workflow_registry.save_to_cache()
        except Exception:
            logger.debug("Workflow index cache save skipped (non-critical)")
    logger.info("Workflow registry ready (%d workflows)", len(workflow_registry.list_available()))
    app.state.workflow_registry = workflow_registry

    yield

    # Shutdown
    await arq_pool.aclose()
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
    app.include_router(workflow_router)
    app.include_router(chat_router)
    app.include_router(ceo_queue_router)
    app.include_router(skills_router)

    return app


app = create_app()
