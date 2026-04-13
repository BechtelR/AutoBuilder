"""Director queue routes — internal escalation handling."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CeoQueueItem, DirectorQueueItem
from app.gateway.deps import get_db_session
from app.gateway.models.director_queue import (
    DirectorQueueItemResponse,
    ResolveDirectorQueueItemRequest,
)
from app.lib import ConflictError, NotFoundError
from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    DirectorQueueAction,
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
)

router = APIRouter(prefix="/director/queue", tags=["director-queue"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("")
async def list_director_queue(
    db: DbSession,
    type: EscalationRequestType | None = None,
    priority: EscalationPriority | None = None,
    status: DirectorQueueStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[DirectorQueueItemResponse]:
    """List Director queue items with optional filters."""
    priority_rank = case(
        (DirectorQueueItem.priority == EscalationPriority.CRITICAL, 4),
        (DirectorQueueItem.priority == EscalationPriority.HIGH, 3),
        (DirectorQueueItem.priority == EscalationPriority.NORMAL, 2),
        (DirectorQueueItem.priority == EscalationPriority.LOW, 1),
        else_=0,
    )
    stmt = select(DirectorQueueItem).order_by(
        priority_rank.desc(),
        DirectorQueueItem.created_at.asc(),
    )
    if type is not None:
        stmt = stmt.where(DirectorQueueItem.type == type)
    if priority is not None:
        stmt = stmt.where(DirectorQueueItem.priority == priority)
    if status is not None:
        stmt = stmt.where(DirectorQueueItem.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [_item_to_response(item) for item in items]


@router.patch("/{item_id}")
async def resolve_director_queue_item(
    item_id: UUID,
    request: ResolveDirectorQueueItemRequest,
    db: DbSession,
) -> DirectorQueueItemResponse:
    """Resolve a Director queue item or forward it to the CEO queue."""
    item = await _get_item_by_id(db, item_id)

    if item.status in (DirectorQueueStatus.RESOLVED, DirectorQueueStatus.FORWARDED_TO_CEO):
        raise ConflictError(
            message=f"Queue item '{item_id}' is already {item.status.value}",
        )

    now = datetime.now(UTC)

    if request.action == DirectorQueueAction.RESOLVE:
        item.status = DirectorQueueStatus.RESOLVED
        item.resolution = request.resolution
        item.resolved_at = now
        item.resolved_by = "director"
    else:
        # FORWARD_TO_CEO: create a CeoQueueItem and mark this item forwarded
        ceo_item = CeoQueueItem(
            type=CeoItemType.ESCALATION,
            priority=item.priority,
            status=CeoQueueStatus.PENDING,
            title=item.title,
            source_project_id=item.source_project_id,
            source_agent=item.source_agent,
            metadata_={
                "forwarded_from_director_queue": str(item.id),
                "original_context": item.context,
                "forward_rationale": request.rationale,
            },
        )
        db.add(ceo_item)
        item.status = DirectorQueueStatus.FORWARDED_TO_CEO
        item.resolved_at = now
        item.resolved_by = "director"

    await db.commit()
    await db.refresh(item)
    return _item_to_response(item)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_item_by_id(db: AsyncSession, item_id: UUID) -> DirectorQueueItem:
    """Load a Director queue item by ID or raise NotFoundError."""
    result = await db.execute(select(DirectorQueueItem).where(DirectorQueueItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError(message=f"Director queue item '{item_id}' not found")
    return item


def _item_to_response(item: DirectorQueueItem) -> DirectorQueueItemResponse:
    """Convert a DirectorQueueItem ORM model to response.

    Explicit construction required: SQLAlchemy's DeclarativeBase exposes a
    ``metadata`` attribute (MetaData object) that collides with our JSONB column
    aliased to ``metadata_``.
    """
    return DirectorQueueItemResponse(
        id=item.id,
        type=item.type,
        priority=item.priority,
        status=item.status,
        title=item.title,
        source_project_id=item.source_project_id,
        source_agent=item.source_agent,
        context=item.context,
        metadata=item.metadata_,
        resolution=item.resolution,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
