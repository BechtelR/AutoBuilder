"""Director lifecycle routes — pause and resume backlog processing."""

from typing import Annotated

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends

from app.gateway.deps import get_arq_pool

router = APIRouter(prefix="/director", tags=["director"])

ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


@router.post("/pause", status_code=202)
async def pause_director(
    arq: ArqPool,
    reason: str | None = None,
) -> dict[str, str]:
    """Pause Director backlog processing. Cascades to active projects."""
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "pause_director",
        reason=reason,
    )
    return {"status": "accepted", "message": "Director pause requested"}


@router.post("/resume", status_code=202)
async def resume_director(
    arq: ArqPool,
) -> dict[str, str]:
    """Resume Director backlog processing and paused projects."""
    await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "resume_director",
    )
    return {"status": "accepted", "message": "Director resume requested"}
