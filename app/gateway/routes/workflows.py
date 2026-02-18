"""Workflow routes — enqueue and track workflow execution."""

from typing import Annotated

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_202_ACCEPTED

from app.db.models import Workflow
from app.gateway.deps import get_arq_pool, get_db_session
from app.gateway.models.workflows import WorkflowRunRequest, WorkflowRunResponse
from app.models.enums import WorkflowStatus

router = APIRouter(tags=["workflows"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


@router.post("/workflows/run", status_code=HTTP_202_ACCEPTED)
async def run_workflow(
    request: WorkflowRunRequest,
    session: DbSession,
    arq_pool: ArqPool,
) -> WorkflowRunResponse:
    """Create a workflow record and enqueue it for execution."""
    workflow = Workflow(
        workflow_type=request.workflow_type,
        status=WorkflowStatus.PENDING,
        params=request.params,
    )
    session.add(workflow)
    await session.commit()

    await arq_pool.enqueue_job("run_workflow", str(workflow.id))  # type: ignore[reportUnknownMemberType]

    return WorkflowRunResponse(
        workflow_id=str(workflow.id),
        status=WorkflowStatus.PENDING,
    )
