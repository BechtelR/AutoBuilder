"""Integration tests for Director queue routes (real PostgreSQL + Redis)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DirectorQueueItem
from app.models.enums import (
    DirectorQueueStatus,
    EscalationPriority,
    EscalationRequestType,
)
from tests.conftest import require_infra


async def _insert_item(
    session: AsyncSession,
    *,
    title: str = "Test item",
    item_type: EscalationRequestType = EscalationRequestType.ESCALATION,
    priority: EscalationPriority = EscalationPriority.NORMAL,
    status: DirectorQueueStatus = DirectorQueueStatus.PENDING,
    context: str = "Test context",
) -> DirectorQueueItem:
    """Helper to insert a DirectorQueueItem directly into the DB."""
    item = DirectorQueueItem(
        type=item_type,
        priority=priority,
        status=status,
        title=title,
        context=context,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@require_infra
class TestDirectorQueueEndpoints:
    @pytest.mark.asyncio
    async def test_list_director_queue_with_items(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await _insert_item(
            async_session,
            title="Low priority",
            priority=EscalationPriority.LOW,
        )
        await _insert_item(
            async_session,
            title="Critical priority",
            priority=EscalationPriority.CRITICAL,
        )
        await _insert_item(
            async_session,
            title="Normal priority",
            priority=EscalationPriority.NORMAL,
        )

        response = await test_client.get("/director/queue")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 3
        assert items[0]["title"] == "Critical priority"
        assert items[1]["title"] == "Normal priority"
        assert items[2]["title"] == "Low priority"

    @pytest.mark.asyncio
    async def test_list_director_queue_filter_by_type(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await _insert_item(
            async_session,
            title="Escalation",
            item_type=EscalationRequestType.ESCALATION,
        )
        await _insert_item(
            async_session,
            title="Status report",
            item_type=EscalationRequestType.STATUS_REPORT,
        )

        response = await test_client.get("/director/queue", params={"type": "STATUS_REPORT"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Status report"

    @pytest.mark.asyncio
    async def test_list_director_queue_filter_by_status(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await _insert_item(
            async_session,
            title="Pending item",
            status=DirectorQueueStatus.PENDING,
        )
        await _insert_item(
            async_session,
            title="Resolved item",
            status=DirectorQueueStatus.RESOLVED,
        )

        response = await test_client.get("/director/queue", params={"status": "RESOLVED"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Resolved item"

    @pytest.mark.asyncio
    async def test_resolve_director_queue_item(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Resolve me")

        response = await test_client.patch(
            f"/director/queue/{item.id}",
            json={
                "action": "RESOLVE",
                "resolution": "Issue addressed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "Issue addressed"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_forward_to_ceo_creates_ceo_item(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Forward me")

        response = await test_client.patch(
            f"/director/queue/{item.id}",
            json={
                "action": "FORWARD_TO_CEO",
                "rationale": "Needs CEO attention",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FORWARDED_TO_CEO"
        assert data["resolved_at"] is not None

        # Verify CEO queue item was created
        ceo_response = await test_client.get("/ceo/queue")
        ceo_items = ceo_response.json()
        assert len(ceo_items) == 1
        assert ceo_items[0]["title"] == "Forward me"
        assert "forward_rationale" in ceo_items[0]["metadata"]

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_returns_409(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Already done")

        await test_client.patch(
            f"/director/queue/{item.id}",
            json={"action": "RESOLVE", "resolution": "Done"},
        )

        response = await test_client.patch(
            f"/director/queue/{item.id}",
            json={"action": "RESOLVE", "resolution": "Again"},
        )
        assert response.status_code == 409
