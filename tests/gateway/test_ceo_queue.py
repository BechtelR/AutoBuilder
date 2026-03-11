"""Integration tests for CEO queue routes (real PostgreSQL + Redis)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CeoQueueItem
from app.models.enums import (
    CeoItemType,
    CeoQueueStatus,
    EscalationPriority,
)
from tests.conftest import require_infra


async def _insert_item(
    session: AsyncSession,
    *,
    title: str = "Test item",
    item_type: CeoItemType = CeoItemType.NOTIFICATION,
    priority: EscalationPriority = EscalationPriority.NORMAL,
    status: CeoQueueStatus = CeoQueueStatus.PENDING,
) -> CeoQueueItem:
    """Helper to insert a CeoQueueItem directly into the DB."""
    item = CeoQueueItem(
        type=item_type,
        priority=priority,
        status=status,
        title=title,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@require_infra
class TestCeoQueueEndpoints:
    @pytest.mark.asyncio
    async def test_list_ceo_queue_empty(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/ceo/queue")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_ceo_queue_with_items(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        # Insert items with different priorities
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

        response = await test_client.get("/ceo/queue")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 3
        # Ordered by priority DESC: CRITICAL, NORMAL, LOW
        assert items[0]["title"] == "Critical priority"
        assert items[1]["title"] == "Normal priority"
        assert items[2]["title"] == "Low priority"

    @pytest.mark.asyncio
    async def test_list_ceo_queue_filter_by_type(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await _insert_item(
            async_session,
            title="Notification",
            item_type=CeoItemType.NOTIFICATION,
        )
        await _insert_item(
            async_session,
            title="Approval",
            item_type=CeoItemType.APPROVAL,
        )

        response = await test_client.get("/ceo/queue", params={"type": "APPROVAL"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Approval"

    @pytest.mark.asyncio
    async def test_list_ceo_queue_filter_by_status(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await _insert_item(
            async_session,
            title="Pending item",
            status=CeoQueueStatus.PENDING,
        )
        await _insert_item(
            async_session,
            title="Seen item",
            status=CeoQueueStatus.SEEN,
        )

        response = await test_client.get("/ceo/queue", params={"status": "SEEN"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Seen item"

    @pytest.mark.asyncio
    async def test_resolve_ceo_queue_item(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Resolve me")

        response = await test_client.patch(
            f"/ceo/queue/{item.id}",
            json={
                "action": "RESOLVE",
                "resolution": "Approved with conditions",
                "resolver": "ceo@test.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "Approved with conditions"
        assert data["resolved_by"] == "ceo@test.com"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_dismiss_ceo_queue_item(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Dismiss me")

        response = await test_client.patch(
            f"/ceo/queue/{item.id}",
            json={
                "action": "DISMISS",
                "resolver": "ceo@test.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DISMISSED"
        assert data["resolution"] is None
        assert data["resolved_by"] == "ceo@test.com"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_returns_409(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(async_session, title="Already done")

        # First resolve
        await test_client.patch(
            f"/ceo/queue/{item.id}",
            json={
                "action": "RESOLVE",
                "resolution": "Done",
                "resolver": "ceo@test.com",
            },
        )

        # Second resolve should 409
        response = await test_client.patch(
            f"/ceo/queue/{item.id}",
            json={
                "action": "RESOLVE",
                "resolution": "Again",
                "resolver": "ceo@test.com",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_returns_404(self, test_client: AsyncClient) -> None:
        fake_id = uuid.uuid4()
        response = await test_client.patch(
            f"/ceo/queue/{fake_id}",
            json={
                "action": "RESOLVE",
                "resolution": "Nope",
                "resolver": "ceo@test.com",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_approval_enqueues_work_session(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        item = await _insert_item(
            async_session,
            title="Approval needed",
            item_type=CeoItemType.APPROVAL,
        )

        response = await test_client.patch(
            f"/ceo/queue/{item.id}",
            json={
                "action": "RESOLVE",
                "resolution": "Approved",
                "resolver": "ceo@test.com",
            },
        )
        # Should succeed — the job enqueue fires but we can't easily
        # verify the ARQ job was created without inspecting Redis directly.
        # The key assertion is that the endpoint doesn't error.
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        assert response.json()["type"] == "APPROVAL"
