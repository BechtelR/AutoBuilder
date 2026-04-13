"""Integration tests for Project routes (real PostgreSQL + Redis)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import DeliverableStatus, ProjectStatus
from tests.conftest import require_infra
from tests.gateway.conftest import insert_deliverable, insert_project, insert_workflow


@require_infra
class TestProjectEndpoints:
    @pytest.mark.asyncio
    async def test_list_projects_with_items(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await insert_project(async_session, name="Project A")
        await insert_project(async_session, name="Project B")

        response = await test_client.get("/projects")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_projects_filter_by_status(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        await insert_project(async_session, name="Active", status=ProjectStatus.ACTIVE)
        await insert_project(async_session, name="Shaping", status=ProjectStatus.SHAPING)

        response = await test_client.get("/projects", params={"status": "ACTIVE"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["name"] == "Active"

    @pytest.mark.asyncio
    async def test_get_project_detail(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, name="Detail Project")
        workflow = await insert_workflow(async_session)

        await insert_deliverable(
            async_session,
            workflow_id=workflow.id,
            project_id=project.id,
            name="D1",
            status=DeliverableStatus.COMPLETED,
        )
        await insert_deliverable(
            async_session,
            workflow_id=workflow.id,
            project_id=project.id,
            name="D2",
            status=DeliverableStatus.PENDING,
        )
        await insert_deliverable(
            async_session,
            workflow_id=workflow.id,
            project_id=project.id,
            name="D3",
            status=DeliverableStatus.FAILED,
        )

        response = await test_client.get(f"/projects/{project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Project"
        assert data["deliverable_total"] == 3
        assert data["deliverable_completed"] == 1
        assert data["deliverable_failed"] == 1
        assert data["deliverable_pending"] == 1
        assert data["deliverable_in_progress"] == 0
        assert data["accumulated_cost"] == "0.0000"


@require_infra
class TestProjectPauseResume:
    @pytest.mark.asyncio
    async def test_pause_active_project_returns_202(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, status=ProjectStatus.ACTIVE)
        response = await test_client.post(f"/projects/{project.id}/pause")
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert str(project.id) in data["message"]

    @pytest.mark.asyncio
    async def test_pause_paused_project_returns_409(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, status=ProjectStatus.PAUSED)
        response = await test_client.post(f"/projects/{project.id}/pause")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_resume_paused_project_returns_202(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, status=ProjectStatus.PAUSED)
        response = await test_client.post(f"/projects/{project.id}/resume")
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert str(project.id) in data["message"]

    @pytest.mark.asyncio
    async def test_resume_active_project_returns_409(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, status=ProjectStatus.ACTIVE)
        response = await test_client.post(f"/projects/{project.id}/resume")
        assert response.status_code == 409


@require_infra
class TestProjectAbort:
    @pytest.mark.asyncio
    async def test_abort_project_returns_202(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        project = await insert_project(async_session, status=ProjectStatus.ACTIVE)
        response = await test_client.post(
            f"/projects/{project.id}/abort",
            json={"reason": "budget exhausted"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert str(project.id) in data["message"]
