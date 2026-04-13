"""Gateway test helpers — shared DB insertion functions."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact, Deliverable, Project, Workflow
from app.models.enums import DeliverableStatus, ProjectStatus


async def insert_project(
    session: AsyncSession,
    *,
    name: str = "Test Project",
    brief: str = "Build something",
    workflow_type: str = "default",
    status: ProjectStatus = ProjectStatus.SHAPING,
) -> Project:
    """Insert a Project directly into the DB."""
    project = Project(
        name=name,
        brief=brief,
        workflow_type=workflow_type,
        status=status,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def insert_workflow(
    session: AsyncSession,
    *,
    workflow_type: str = "default",
) -> Workflow:
    """Insert a Workflow."""
    workflow = Workflow(workflow_type=workflow_type)
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    return workflow


async def insert_deliverable(
    session: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    name: str = "Test Deliverable",
    status: DeliverableStatus = DeliverableStatus.PENDING,
) -> Deliverable:
    """Insert a Deliverable."""
    deliverable = Deliverable(
        workflow_id=workflow_id,
        project_id=project_id,
        name=name,
        status=status,
    )
    session.add(deliverable)
    await session.commit()
    await session.refresh(deliverable)
    return deliverable


async def insert_artifact(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    path: str = "/output/file.txt",
    content_type: str = "text/plain",
    size_bytes: int = 1024,
) -> Artifact:
    """Insert an Artifact."""
    artifact = Artifact(
        entity_type=entity_type,
        entity_id=entity_id,
        path=path,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact
