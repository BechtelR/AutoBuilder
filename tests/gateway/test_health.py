"""Tests for health endpoint."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_ok(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["services"]["postgres"] == "ok"
        assert data["services"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_degraded_db(
        self,
        test_client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        mock_db_session.execute.side_effect = Exception("DB down")
        response = await test_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "unavailable"
        assert data["services"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_health_degraded_redis(
        self,
        test_client: AsyncClient,
        mock_redis: AsyncMock,
    ) -> None:
        mock_redis.ping.side_effect = Exception("Redis down")
        response = await test_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "ok"
        assert data["services"]["redis"] == "unavailable"

    @pytest.mark.asyncio
    async def test_health_both_degraded(
        self,
        test_client: AsyncClient,
        mock_db_session: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        mock_db_session.execute.side_effect = Exception("DB down")
        mock_redis.ping.side_effect = Exception("Redis down")
        response = await test_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["postgres"] == "unavailable"
        assert data["services"]["redis"] == "unavailable"
