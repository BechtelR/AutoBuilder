"""ARQ task definitions for AutoBuilder workers."""

from app.lib import get_logger

logger = get_logger("workers.tasks")


async def test_task(ctx: dict[str, object], payload: str) -> dict[str, str]:
    """Minimal ARQ job for gateway-to-worker round-trip validation."""
    logger.info("Processing test_task", extra={"payload": payload})
    return {"status": "completed", "payload": payload}


async def heartbeat(ctx: dict[str, object]) -> None:
    """Cron job: logs 'worker alive' every 60 seconds."""
    logger.info("worker alive")
