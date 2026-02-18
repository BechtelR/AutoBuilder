"""ARQ task definitions for AutoBuilder workers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from google.genai.types import Content, Part
from sqlalchemy import select

from app.db.models import Workflow
from app.events.publisher import EventPublisher
from app.lib import NotFoundError, get_logger
from app.models.constants import APP_NAME, SYSTEM_USER_ID
from app.models.enums import PipelineEventType, TaskType, WorkflowStatus
from app.router import LlmRouter, create_model_override_callback
from app.workers.adk import create_app_container, create_echo_agent, create_runner

if TYPE_CHECKING:
    from arq.connections import ArqRedis
    from google.adk.sessions.base_session_service import BaseSessionService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = get_logger("workers.tasks")


async def test_task(ctx: dict[str, object], payload: str) -> dict[str, str]:
    """Minimal ARQ job for gateway-to-worker round-trip validation."""
    logger.info("Processing test_task", extra={"payload": payload})
    return {"status": "completed", "payload": payload}


async def heartbeat(ctx: dict[str, object]) -> None:
    """Cron job: logs 'worker alive' every 60 seconds."""
    logger.info("worker alive")


async def run_workflow(ctx: dict[str, object], workflow_id: str) -> dict[str, str]:
    """Execute a workflow via ADK pipeline."""

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)

    try:
        # Read workflow record and extract params in a single query
        workflow_params: dict[str, object] = {}
        async with factory() as db_session:
            result = await db_session.execute(
                select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                raise NotFoundError(message=f"Workflow {workflow_id} not found")

            # Update status to RUNNING
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(UTC)
            if workflow.params is not None:
                workflow_params = dict(workflow.params)
            await db_session.commit()

        # Publish WORKFLOW_STARTED
        await publisher.publish_lifecycle(workflow_id, PipelineEventType.WORKFLOW_STARTED)

        # Create ADK pipeline
        callback = create_model_override_callback(router)
        echo_agent = create_echo_agent(
            model=router.select_model(TaskType.FAST),
            before_model_callback=callback,
        )
        app_container = create_app_container(root_agent=echo_agent)
        runner = create_runner(app_container, session_service)

        # Create or resume session
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=workflow_id
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=workflow_id
            )

        # Construct the prompt from workflow params
        prompt_text = str(workflow_params.get("prompt", "Hello, echo agent!"))
        message = Content(parts=[Part(text=prompt_text)])

        # Execute and stream events
        async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
            user_id=SYSTEM_USER_ID,
            session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            new_message=message,
        ):
            translated = publisher.translate(event, workflow_id)
            if translated is not None:
                await publisher.publish(translated)

        # Update status to COMPLETED
        async with factory() as db_session:
            result = await db_session.execute(
                select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
            )
            workflow = result.scalar_one_or_none()
            if workflow is not None:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now(UTC)
                await db_session.commit()

        await publisher.publish_lifecycle(workflow_id, PipelineEventType.WORKFLOW_COMPLETED)

        logger.info("Workflow completed", extra={"workflow_id": workflow_id})
        return {"status": "completed", "workflow_id": workflow_id}

    except NotFoundError:
        raise
    except Exception as exc:
        logger.error(
            "Workflow failed",
            extra={"workflow_id": workflow_id},
            exc_info=True,
        )
        # Update status to FAILED
        try:
            async with factory() as db_session:
                result = await db_session.execute(
                    select(Workflow).where(Workflow.id == workflow_id)  # type: ignore[reportArgumentType]
                )
                workflow = result.scalar_one_or_none()
                if workflow is not None:
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now(UTC)
                    workflow.error_message = str(exc)
                    await db_session.commit()
        except Exception:
            logger.error("Failed to update workflow status", exc_info=True)

        try:
            await publisher.publish_lifecycle(
                workflow_id,
                PipelineEventType.WORKFLOW_FAILED,
                metadata={"error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish WORKFLOW_FAILED event", exc_info=True)
        raise
