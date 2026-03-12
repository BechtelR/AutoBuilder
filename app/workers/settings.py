"""ARQ WorkerSettings for AutoBuilder workers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from arq import cron
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings, parse_redis_settings
from app.lib import get_logger, setup_logging
from app.models.constants import APP_NAME, INIT_SESSION_ID, SYSTEM_USER_ID
from app.router import LlmRouter
from app.workers.adk import create_session_service
from app.workers.tasks import (
    heartbeat,
    process_director_queue,
    run_director_turn,
    run_work_session,
    run_workflow,
    test_task,
)

if TYPE_CHECKING:
    from arq.connections import ArqRedis
    from google.adk.sessions.base_session_service import BaseSessionService
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("workers.settings")


async def startup(ctx: dict[str, object]) -> None:
    """Worker startup: initialize logging, session service, LLM router, and app scope."""
    settings = get_settings()
    setup_logging(settings.log_level)

    # Initialize shared DB engine and session factory (reused across all tasks)
    engine = create_async_engine(settings.db_url)
    ctx["db_engine"] = engine
    ctx["db_session_factory"] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Initialize DatabaseSessionService (shared across all task invocations)
    ctx["session_service"] = create_session_service(settings.db_url)

    # Initialize LLM Router
    router = LlmRouter.from_settings(settings)
    ctx["llm_router"] = router

    # Cache routing config to Redis (M22)
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    await router.cache_to_redis(redis)

    # Initialize SkillLibrary (shared across all task invocations)
    from pathlib import Path

    from app.skills.library import SkillLibrary

    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    skill_library = SkillLibrary(global_dir=skills_dir, redis=redis)

    # Try loading from cache first, fall back to filesystem scan
    cache_hit = await skill_library.load_from_cache()
    if not cache_hit:
        skill_library.scan()
        try:
            await skill_library.save_to_cache()
        except Exception:
            logger.debug("Skill index cache save skipped (non-critical)")
    ctx["skill_library"] = skill_library

    # Initialize app: scope state (E14) — idempotent

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    try:
        # Try to get an existing session to check if app: scope keys exist
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=INIT_SESSION_ID
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=INIT_SESSION_ID,
                state={
                    "app:skill_index": {},
                    "app:workflow_registry": {},
                },
            )
            logger.info("Initialized app: scope state")
        else:
            logger.info("App: scope state already initialized")
    except Exception:
        logger.warning("Failed to initialize app: scope state", exc_info=True)

    logger.info("Worker startup complete")


async def shutdown(ctx: dict[str, object]) -> None:
    """Worker shutdown: cleanup resources."""
    # Close ADK session service (disposes its internal engine)
    session_service: BaseSessionService | None = ctx.get("session_service")  # type: ignore[assignment]
    if session_service is not None:
        close_fn = getattr(session_service, "close", None)
        if close_fn is not None and callable(close_fn):
            await close_fn()  # type: ignore[reportUnknownMemberType]

    engine: AsyncEngine | None = ctx.get("db_engine")  # type: ignore[assignment]
    if engine is not None:
        await engine.dispose()
    logger.info("Worker shutdown complete")


class WorkerSettings:
    """ARQ worker settings -- entry point: ``arq app.workers.settings.WorkerSettings``."""

    functions = [test_task, run_workflow, run_director_turn, run_work_session]
    redis_settings = parse_redis_settings(get_settings().redis_url)
    cron_jobs = [
        cron(heartbeat, second=0),  # every minute at :00
        cron(process_director_queue, second=0),  # scan for idle project escalations
    ]
    on_startup = startup
    on_shutdown = shutdown
