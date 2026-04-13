"""Integration tests for Deliverable routes (real PostgreSQL + Redis)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ValidatorResult
from app.models.enums import DeliverableStatus
from tests.conftest import require_infra
from tests.gateway.conftest import (
    insert_artifact,
    insert_deliverable,
    insert_project,
    insert_workflow,
)


@require_infra
class TestDeliverableEndpoints:
    @pytest.mark.asyncio
    async def test_list_deliverables_with_items(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        workflow = await insert_workflow(async_session)
        await insert_deliverable(async_session, workflow_id=workflow.id, name="D1")
        await insert_deliverable(async_session, workflow_id=workflow.id, name="D2")

        response = await test_client.get("/deliverables")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_deliverables_filter_by_project(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        workflow = await insert_workflow(async_session)
        project = await insert_project(async_session, name="Proj A")
        await insert_deliverable(
            async_session, workflow_id=workflow.id, project_id=project.id, name="D1"
        )
        await insert_deliverable(async_session, workflow_id=workflow.id, name="D2")

        response = await test_client.get("/deliverables", params={"project_id": str(project.id)})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["name"] == "D1"

    @pytest.mark.asyncio
    async def test_list_deliverables_filter_by_status(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        workflow = await insert_workflow(async_session)
        await insert_deliverable(
            async_session,
            workflow_id=workflow.id,
            name="Completed",
            status=DeliverableStatus.COMPLETED,
        )
        await insert_deliverable(
            async_session,
            workflow_id=workflow.id,
            name="Pending",
            status=DeliverableStatus.PENDING,
        )

        response = await test_client.get("/deliverables", params={"status": "COMPLETED"})
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["name"] == "Completed"

    @pytest.mark.asyncio
    async def test_get_deliverable_detail(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        workflow = await insert_workflow(async_session)
        deliverable = await insert_deliverable(
            async_session, workflow_id=workflow.id, name="Detail D"
        )
        await insert_artifact(
            async_session,
            entity_type="deliverable",
            entity_id=deliverable.id,
            path="/output/result.json",
        )

        response = await test_client.get(f"/deliverables/{deliverable.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail D"
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["path"] == "/output/result.json"
        assert data["validator_results"] == []

    @pytest.mark.asyncio
    async def test_get_deliverable_detail_with_validator_results(
        self,
        test_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        workflow = await insert_workflow(async_session)
        deliverable = await insert_deliverable(
            async_session, workflow_id=workflow.id, name="Validated D"
        )

        # Insert validator results for the same workflow
        vr = ValidatorResult(
            workflow_id=workflow.id,
            validator_name="lint",
            passed=True,
            message="All checks passed",
            evidence={"files_checked": 5},
        )
        async_session.add(vr)
        await async_session.commit()
        await async_session.refresh(vr)

        response = await test_client.get(f"/deliverables/{deliverable.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Validated D"
        assert len(data["validator_results"]) == 1
        vr_data = data["validator_results"][0]
        assert vr_data["validator_name"] == "lint"
        assert vr_data["passed"] is True
        assert vr_data["message"] == "All checks passed"
        assert vr_data["evidence"] == {"files_checked": 5}
