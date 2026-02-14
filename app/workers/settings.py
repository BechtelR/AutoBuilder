"""ARQ WorkerSettings for AutoBuilder workers."""

from urllib.parse import urlparse

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.lib import setup_logging
from app.workers.tasks import heartbeat, test_task


def _parse_redis_settings() -> RedisSettings:
    """Parse AUTOBUILDER_REDIS_URL into ARQ RedisSettings."""
    parsed = urlparse(get_settings().redis_url)
    database = 0
    if parsed.path and parsed.path.strip("/").isdigit():
        database = int(parsed.path.strip("/"))
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        username=parsed.username,
    )


async def startup(ctx: dict[str, object]) -> None:
    """Worker startup: initialize structured logging."""
    settings = get_settings()
    setup_logging(settings.log_level)


async def shutdown(ctx: dict[str, object]) -> None:
    """Worker shutdown: cleanup resources."""


class WorkerSettings:
    """ARQ worker settings -- entry point: ``arq app.workers.settings.WorkerSettings``."""

    functions = [test_task]
    redis_settings = _parse_redis_settings()
    cron_jobs = [cron(heartbeat, second=0)]  # every minute at :00
    on_startup = startup
    on_shutdown = shutdown
