"""Tests for workflow routes."""

import pytest
from httpx import AsyncClient

from tests.conftest import require_infra


@require_infra
class TestWorkflowEndpoint:
    @pytest.mark.asyncio
    async def test_run_workflow_returns_202(self, test_client: AsyncClient) -> None:
        response = await test_client.post(
            "/workflows/run",
            json={"workflow_type": "echo"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_run_workflow_with_params(self, test_client: AsyncClient) -> None:
        response = await test_client.post(
            "/workflows/run",
            json={"workflow_type": "echo", "params": {"prompt": "test"}},
        )
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_run_workflow_creates_unique_ids(self, test_client: AsyncClient) -> None:
        r1 = await test_client.post("/workflows/run", json={"workflow_type": "echo"})
        r2 = await test_client.post("/workflows/run", json={"workflow_type": "echo"})
        assert r1.status_code == 202
        assert r2.status_code == 202
        assert r1.json()["workflow_id"] != r2.json()["workflow_id"]

    @pytest.mark.asyncio
    async def test_run_workflow_missing_type_returns_422(self, test_client: AsyncClient) -> None:
        response = await test_client.post(
            "/workflows/run",
            json={},
        )
        assert response.status_code == 422
