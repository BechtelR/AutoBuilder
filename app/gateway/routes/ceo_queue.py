"""CEO queue routes — human oversight of escalation items."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CeoQueueItem
from app.gateway.deps import get_arq_pool, get_db_session
from app.gateway.models.ceo_queue import (
    CeoQueueItemResponse,
    ResolveCeoQueueItemRequest,
)
from app.lib import ConflictError, NotFoundError
from app.models.enums import (
    CeoItemType,
    CeoQueueAction,
    CeoQueueStatus,
    EscalationPriority,
)

router = APIRouter(prefix="/ceo/queue", tags=["ceo-queue"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


@router.get("")
async def list_ceo_queue(
    db: DbSession,
    type: CeoItemType | None = None,
    priority: EscalationPriority | None = None,
    status: CeoQueueStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[CeoQueueItemResponse]:
    """List CEO queue items with optional filters."""
    # StrEnum values sort alphabetically, not by severity.
    # Map to numeric rank so CRITICAL > HIGH > NORMAL > LOW.
    priority_rank = case(
        (CeoQueueItem.priority == EscalationPriority.CRITICAL, 4),
        (CeoQueueItem.priority == EscalationPriority.HIGH, 3),
        (CeoQueueItem.priority == EscalationPriority.NORMAL, 2),
        (CeoQueueItem.priority == EscalationPriority.LOW, 1),
        else_=0,
    )
    stmt = select(CeoQueueItem).order_by(
        priority_rank.desc(),
        CeoQueueItem.created_at.asc(),
    )
    if type is not None:
        stmt = stmt.where(CeoQueueItem.type == type)
    if priority is not None:
        stmt = stmt.where(CeoQueueItem.priority == priority)
    if status is not None:
        stmt = stmt.where(CeoQueueItem.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [_item_to_response(item) for item in items]


@router.patch("/{item_id}")
async def resolve_ceo_queue_item(
    item_id: UUID,
    request: ResolveCeoQueueItemRequest,
    db: DbSession,
    arq: ArqPool,
) -> CeoQueueItemResponse:
    """Resolve or dismiss a CEO queue item."""
    item = await _get_item_by_id(db, item_id)

    if item.status in (CeoQueueStatus.RESOLVED, CeoQueueStatus.DISMISSED):
        raise ConflictError(
            message=f"Queue item '{item_id}' is already {item.status.value}",
        )

    now = datetime.now(UTC)

    if request.action == CeoQueueAction.RESOLVE:
        item.status = CeoQueueStatus.RESOLVED
        item.resolution = request.resolution
    else:
        item.status = CeoQueueStatus.DISMISSED

    item.resolved_at = now
    item.resolved_by = request.resolver

    await db.commit()
    await db.refresh(item)

    # For APPROVAL items that are resolved, enqueue work session resumption (FR-5b.24)
    if (
        request.action == CeoQueueAction.RESOLVE
        and item.type == CeoItemType.APPROVAL
        and item.source_project_id is not None
    ):
        await arq.enqueue_job(  # type: ignore[reportUnknownMemberType]
            "run_work_session",
            str(item.source_project_id),
            {"approval_item_id": str(item.id), "approval_resolution": request.resolution},
        )

    return _item_to_response(item)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_item_by_id(db: AsyncSession, item_id: UUID) -> CeoQueueItem:
    """Load a CEO queue item by ID or raise NotFoundError."""
    result = await db.execute(select(CeoQueueItem).where(CeoQueueItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError(message=f"CEO queue item '{item_id}' not found")
    return item


def _item_to_response(item: CeoQueueItem) -> CeoQueueItemResponse:
    """Convert a CeoQueueItem ORM model to a CeoQueueItemResponse.

    Explicit construction required: SQLAlchemy's DeclarativeBase exposes a
    ``metadata`` attribute (MetaData object) that collides with our JSONB column
    aliased to ``metadata_``.  ``model_validate(item)`` would read the wrong one.
    """
    return CeoQueueItemResponse(
        id=item.id,
        type=item.type,
        priority=item.priority,
        status=item.status,
        title=item.title,
        source_project_id=item.source_project_id,
        source_agent=item.source_agent,
        metadata=item.metadata_,
        session_id=item.session_id,
        resolution=item.resolution,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
