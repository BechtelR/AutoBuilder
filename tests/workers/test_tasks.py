"""Tests for ARQ worker tasks."""

import pytest

from app.workers.tasks import heartbeat
from app.workers.tasks import test_task as worker_test_task


class TestTestTask:
    @pytest.mark.asyncio
    async def test_returns_completed_status(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "hello")
        assert result == {"status": "completed", "payload": "hello"}

    @pytest.mark.asyncio
    async def test_returns_payload(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "world")
        assert result["payload"] == "world"

    @pytest.mark.asyncio
    async def test_status_is_completed(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "anything")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_empty_payload(self) -> None:
        ctx: dict[str, object] = {}
        result = await worker_test_task(ctx, "")
        assert result == {"status": "completed", "payload": ""}


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_runs_without_error(self) -> None:
        ctx: dict[str, object] = {}
        # Should not raise
        result = await heartbeat(ctx)
        assert result is None
