"""ARQ task definitions for AutoBuilder workers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from google.genai.types import Content, Part
from sqlalchemy import select

from app.db.models import CeoQueueItem, Chat, ChatMessage, ProjectConfig, Workflow
from app.events.publisher import EventPublisher
from app.lib import NotFoundError, get_logger
from app.models.constants import APP_NAME, APPROVAL_RESOLUTION_PREFIX, SYSTEM_USER_ID
from app.models.enums import (
    CeoItemType,
    ChatMessageRole,
    EscalationPriority,
    ModelRole,
    PipelineEventType,
    WorkflowStatus,
)
from app.router import LlmRouter, create_model_override_callback
from app.workers.adk import (
    build_chat_session_agent,
    build_work_session_agents,
    create_app_container,
    create_echo_agent,
    create_runner,
    create_workflow_pipeline,
)

if TYPE_CHECKING:
    from arq.connections import ArqRedis
    from google.adk.sessions.base_session_service import BaseSessionService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.skills.library import SkillLibrary
    from app.workflows.registry import WorkflowRegistry

logger = get_logger("workers.tasks")


def _resolve_workflow_stages(
    workflow_name: str,
) -> tuple[list[str] | None, dict[str, str] | None]:
    """Resolve PIPELINE_STAGE_NAMES and STAGE_COMPLETION_KEYS from a loaded workflow module.

    Returns (stages, stage_completion_keys). Both are None if the workflow module
    has not been dynamically imported yet (i.e., pipeline was not created via
    WorkflowRegistry.create_pipeline()).
    """
    import sys as _sys

    module_name = f"_autobuilder_workflow_{workflow_name.replace('-', '_')}"
    module = _sys.modules.get(module_name)
    if module is None:
        return None, None

    stages: list[str] | None = getattr(module, "PIPELINE_STAGE_NAMES", None)
    stage_keys: dict[str, str] | None = getattr(module, "STAGE_COMPLETION_KEYS", None)
    return stages, stage_keys


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

        pipeline_type = str(workflow_params.get("pipeline_type", "echo"))

        if pipeline_type == "deliverable":
            from app.agents.assembler import InstructionContext
            from app.agents.context_monitor import ContextRecreationRequired

            instruction_ctx = InstructionContext(
                project_config=str(workflow_params["project_config"])
                if "project_config" in workflow_params
                else None,
                task_context=str(workflow_params["task_context"])
                if "task_context" in workflow_params
                else None,
                agent_name="pipeline",
            )

            workflow_name = str(workflow_params.get("workflow_name", "auto-code"))
            try:
                pipeline = await create_workflow_pipeline(workflow_name, ctx, instruction_ctx)
                app_container = create_app_container(root_agent=pipeline)
                runner = create_runner(app_container, session_service)

                # Create or resume session
                session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
                    app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=workflow_id
                )
                if session is None:
                    session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                        app_name=APP_NAME,
                        user_id=SYSTEM_USER_ID,
                        session_id=workflow_id,
                    )

                prompt_text = str(workflow_params.get("prompt", "Execute deliverable pipeline"))
                message = Content(parts=[Part(text=prompt_text)])

                async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
                    user_id=SYSTEM_USER_ID,
                    session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                    new_message=message,
                ):
                    translated = publisher.translate(event, workflow_id)
                    if translated is not None:
                        await publisher.publish(translated)
                await publisher.flush_violations()

            except ContextRecreationRequired as e:
                await publisher.flush_violations()
                logger.warning(
                    "Context recreation required for workflow %s: %.1f%% usage (threshold %.1f%%)",
                    workflow_id,
                    e.usage_pct,
                    e.threshold_pct,
                )
                from app.agents.context_recreation import recreate_context

                # Resolve workflow-specific stages for recreation
                _stages, _stage_keys = _resolve_workflow_stages(workflow_name)

                recreation_result = await recreate_context(
                    session_service=session_service,
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    old_session_id=workflow_id,
                    publisher=publisher,
                    memory_service=None,
                    stages=_stages,
                    stage_completion_keys=_stage_keys,
                )
                logger.info(
                    "Context recreation completed for workflow %s: "
                    "new_session=%s, remaining=%d stages",
                    workflow_id,
                    recreation_result.new_session_id,
                    len(recreation_result.remaining_stages),
                )

        else:
            # Existing echo pipeline logic
            callback = create_model_override_callback(router)
            echo_agent = create_echo_agent(
                model=router.select_model(ModelRole.FAST),
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
                    app_name=APP_NAME,
                    user_id=SYSTEM_USER_ID,
                    session_id=workflow_id,
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
            await publisher.flush_violations()

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


async def process_director_queue(ctx: dict[str, object]) -> None:
    """ARQ cron: scan for pending Director Queue items in idle projects.

    Enqueues run_director_turn for projects with pending items
    and no active work session.
    """
    from app.db.models import DirectorQueueItem
    from app.models.enums import DirectorQueueStatus

    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]

    async with factory() as db_session:
        stmt = (
            select(DirectorQueueItem.source_project_id)
            .where(DirectorQueueItem.status == DirectorQueueStatus.PENDING)
            .where(DirectorQueueItem.source_project_id.is_not(None))
            .group_by(DirectorQueueItem.source_project_id)
        )
        result = await db_session.execute(stmt)
        project_ids: list[uuid.UUID] = [
            row[0]
            for row in result.all()  # type: ignore[misc]
        ]

    if not project_ids:
        return

    for project_id in project_ids:
        key = f"{_WORK_SESSION_KEY_PREFIX}{project_id}"
        active = await redis.exists(key)
        if active:
            logger.debug(
                "Skipping project %s — active work session",
                project_id,
            )
            continue

        await redis.enqueue_job(
            "run_director_turn",
            project_id=str(project_id),
            _queue_name="arq:queue",
        )
        logger.info(
            "Enqueued director queue evaluation for idle project %s",
            project_id,
        )


async def run_director_turn(
    ctx: dict[str, object],
    chat_id: str | None = None,
    message_id: str | None = None,
    *,
    project_id: str | None = None,
) -> dict[str, str]:
    """Run a single Director turn.

    Two invocation modes:
    - **Chat mode** (chat_id + message_id): CEO sends a message through chat.
      Director processes the message and persists a response ChatMessage.
    - **Queue mode** (project_id): Cron triggers Director to evaluate pending
      Director Queue items for an idle project. Director runs with a synthetic
      prompt summarizing the pending items. No ChatMessage persistence.

    For SETTINGS chats, injects formation or evolution instructions based on
    formation status. For DIRECTOR/PROJECT chats, runs standard Director.
    """
    from pathlib import Path

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionAssembler, InstructionContext
    from app.agents.formation import (
        EVOLUTION_INSTRUCTION,
        FORMATION_INSTRUCTION,
        ensure_formation_state,
    )
    from app.models.enums import ChatType, DefinitionScope, FormationStatus
    from app.tools._toolset import GlobalToolset

    # Validate invocation mode
    chat_mode = chat_id is not None and message_id is not None
    queue_mode = project_id is not None
    if not chat_mode and not queue_mode:
        raise ValueError("run_director_turn requires (chat_id + message_id) or project_id")

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)
    adk_session_id: str = chat_id or f"director_queue_{project_id}"

    try:
        # 1. Resolve prompt and session context based on mode
        prompt_text: str
        chat_type: object = None  # ChatType or None for queue mode

        if chat_mode:
            assert chat_id is not None
            assert message_id is not None
            async with factory() as db_session:
                msg_result = await db_session.execute(
                    select(ChatMessage).where(
                        ChatMessage.id == message_id  # type: ignore[reportArgumentType]
                    )
                )
                user_message = msg_result.scalar_one_or_none()
                if user_message is None:
                    raise NotFoundError(message=f"ChatMessage {message_id} not found")
                prompt_text = user_message.content

                chat_result = await db_session.execute(
                    select(Chat).where(
                        Chat.id == chat_id  # type: ignore[reportArgumentType]
                    )
                )
                chat = chat_result.scalar_one_or_none()
                if chat is None:
                    raise NotFoundError(message=f"Chat {chat_id} not found")
                adk_session_id = chat.session_id
                chat_type = chat.type
        else:
            # Queue mode: build prompt from pending Director Queue items
            from app.db.models import DirectorQueueItem
            from app.models.enums import DirectorQueueStatus

            assert project_id is not None
            async with factory() as db_session:
                stmt = (
                    select(DirectorQueueItem)
                    .where(DirectorQueueItem.status == DirectorQueueStatus.PENDING)
                    .where(
                        DirectorQueueItem.source_project_id == uuid.UUID(project_id)  # type: ignore[reportArgumentType]
                    )
                    .order_by(DirectorQueueItem.created_at)
                )
                result = await db_session.execute(stmt)
                items = list(result.scalars().all())

            if not items:
                logger.info(
                    "No pending queue items for project %s, skipping",
                    project_id,
                )
                return {"status": "skipped", "project_id": project_id}

            item_summaries = [
                f"- [{item.priority.value}] {item.title}: {item.context}" for item in items
            ]
            prompt_text = (
                f"You have {len(items)} pending escalation(s) from PM "
                f"for project {project_id}. Evaluate each and decide whether "
                f"to resolve locally or forward to the CEO queue.\n\n" + "\n".join(item_summaries)
            )

        # 2. Determine formation state and task context
        formation_status = await ensure_formation_state(session_service, SYSTEM_USER_ID)  # type: ignore[reportArgumentType]

        task_context: str | None = None
        if chat_type == ChatType.SETTINGS:
            if formation_status != FormationStatus.COMPLETE:
                task_context = FORMATION_INSTRUCTION
            else:
                task_context = EVOLUTION_INSTRUCTION

        instruction_ctx = InstructionContext(
            task_context=task_context,
            agent_name="director",
        )

        # 3. Build Director from AgentRegistry (no sub_agents for chat/queue)
        assembler = InstructionAssembler()
        toolset = GlobalToolset()
        registry = AgentRegistry(
            assembler=assembler,
            router=router,
            toolset=toolset,
        )
        global_agents_dir = Path(__file__).resolve().parent.parent / "agents"
        registry.scan((global_agents_dir, DefinitionScope.GLOBAL))

        # Resolve Director skills at build time (FR-6.46, FR-6.49)
        skill_library: SkillLibrary | None = ctx.get("skill_library")  # type: ignore[assignment]
        director = build_chat_session_agent(registry, instruction_ctx, skill_library=skill_library)
        app_container = create_app_container(root_agent=director)
        runner = create_runner(app_container, session_service)

        # 4. Create or resume ADK session
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id=SYSTEM_USER_ID,
            session_id=adk_session_id,
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=adk_session_id,
            )

        # 5. Run single Director turn
        message = Content(parts=[Part(text=prompt_text)])
        response_text = ""
        async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
            user_id=SYSTEM_USER_ID,
            session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            new_message=message,
        ):
            content = getattr(event, "content", None)
            if content is not None:
                content_parts = getattr(content, "parts", None)
                if content_parts is not None:
                    for part in content_parts:
                        text = getattr(part, "text", None)
                        if text:
                            response_text += text

        # 6. Persist Director response (chat mode only)
        if chat_mode:
            if not response_text:
                response_text = "(No response from Director)"

            assert chat_id is not None
            async with factory() as db_session:
                director_message = ChatMessage(
                    chat_id=uuid.UUID(chat_id),
                    role=ChatMessageRole.DIRECTOR,
                    content=response_text,
                )
                db_session.add(director_message)
                await db_session.commit()

        # 7. Publish audit event
        await publisher.publish_lifecycle(
            adk_session_id,
            PipelineEventType.AGENT_COMPLETED,
            metadata={
                "agent": "director",
                "mode": "chat" if chat_mode else "queue",
                "chat_type": str(chat_type) if chat_type else None,
            },
        )

        log_id = chat_id if chat_mode else project_id
        logger.info("Director turn completed", extra={"id": log_id})
        return {"status": "completed", "id": str(log_id)}

    except NotFoundError:
        raise
    except Exception as exc:
        log_id = chat_id if chat_mode else project_id
        logger.error(
            "Director turn failed",
            extra={"id": log_id},
            exc_info=True,
        )

        # Persist error as Director message (chat mode only)
        if chat_mode and chat_id is not None:
            try:
                async with factory() as db_session:
                    error_message = ChatMessage(
                        chat_id=uuid.UUID(chat_id),
                        role=ChatMessageRole.DIRECTOR,
                        content=f"(Director error: {exc})",
                    )
                    db_session.add(error_message)
                    await db_session.commit()
            except Exception:
                logger.error("Failed to persist error message", exc_info=True)

        # Publish error event (FR-5b.33)
        try:
            await publisher.publish_lifecycle(
                adk_session_id,
                PipelineEventType.ERROR,
                metadata={"agent": "director", "error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish director error event", exc_info=True)

        raise


_WORK_SESSION_KEY_PREFIX = "director:work_session:"
_WORK_SESSION_TTL = 300  # seconds


async def run_work_session(
    ctx: dict[str, object],
    project_id: str,
    params: dict[str, object] | None = None,
) -> dict[str, str]:
    """Execute a work session: Director delegates to PM for autonomous execution.

    Director is root_agent with PM as sub_agent. PM runs deliverable pipelines.
    Hard limits (retry_budget, cost_ceiling) loaded from project_configs table.
    """
    from pathlib import Path

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionAssembler, InstructionContext
    from app.agents.context_monitor import ContextRecreationRequired
    from app.agents.formation import ensure_formation_state
    from app.config import get_settings
    from app.models.enums import DefinitionScope
    from app.tools._toolset import GlobalToolset

    session_service: BaseSessionService = ctx["session_service"]  # type: ignore[assignment]
    router: LlmRouter = ctx["llm_router"]  # type: ignore[assignment]
    redis: ArqRedis = ctx["redis"]  # type: ignore[assignment]
    factory: async_sessionmaker[AsyncSession] = ctx["db_session_factory"]  # type: ignore[assignment]

    publisher = EventPublisher(redis)
    settings = get_settings()
    session_id = f"work_session_{project_id}"
    redis_key = f"{_WORK_SESSION_KEY_PREFIX}{project_id}"

    try:
        # 1. Load project config from DB (or use defaults)
        retry_budget = settings.default_retry_budget
        cost_ceiling = settings.default_cost_ceiling

        async with factory() as db_session:
            result = await db_session.execute(
                select(ProjectConfig).where(
                    ProjectConfig.project_name == project_id  # type: ignore[reportArgumentType]
                )
            )
            project_config = result.scalar_one_or_none()
            if project_config is not None:
                config_dict: dict[str, object] = dict(project_config.config)
                raw_budget = config_dict.get("retry_budget")
                if isinstance(raw_budget, int):
                    retry_budget = raw_budget
                raw_ceiling = config_dict.get("cost_ceiling")
                if isinstance(raw_ceiling, (int, float)):
                    cost_ceiling = float(raw_ceiling)

        # 2. Ensure formation state for the system user
        await ensure_formation_state(session_service, SYSTEM_USER_ID)  # type: ignore[reportArgumentType]

        # 3. Create instruction context
        resolved_params = params or {}
        instruction_ctx = InstructionContext(
            project_config=str(resolved_params["project_config"])
            if "project_config" in resolved_params
            else None,
            task_context=str(resolved_params["task_context"])
            if "task_context" in resolved_params
            else None,
            agent_name="director",
        )

        # 4. Build agent tree (Director + PM with supervision callbacks)
        assembler = InstructionAssembler()
        toolset = GlobalToolset()
        registry = AgentRegistry(
            assembler=assembler,
            router=router,
            toolset=toolset,
        )
        global_agents_dir = Path(__file__).resolve().parent.parent / "agents"
        registry.scan((global_agents_dir, DefinitionScope.GLOBAL))

        # Create pipeline callbacks (model routing, budget monitor, system reminders)
        from app.workers.adk import create_pipeline_callbacks

        pipeline_callbacks = create_pipeline_callbacks(
            router, float(settings.context_budget_threshold)
        )

        # Resolve Director + PM skills at build time (FR-6.46, FR-6.47, FR-6.48)
        work_skill_library: SkillLibrary | None = ctx.get("skill_library")  # type: ignore[assignment]
        work_workflow_registry: WorkflowRegistry | None = ctx.get("workflow_registry")  # type: ignore[assignment]
        director = await build_work_session_agents(
            registry=registry,
            ctx=instruction_ctx,
            project_id=project_id,
            publisher=publisher,
            skill_library=work_skill_library,
            before_model_callback=pipeline_callbacks,
            workflow_registry=work_workflow_registry,
        )

        # 5. Create App container and Runner
        app_container = create_app_container(root_agent=director)
        runner = create_runner(app_container, session_service)

        # 6. Create or resume ADK session with hard limits in state
        session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id=SYSTEM_USER_ID, session_id=session_id
        )
        if session is None:
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=session_id,
                state={
                    "project_config": {
                        "retry_budget": retry_budget,
                        "cost_ceiling": cost_ceiling,
                    },
                    "workflow_id": session_id,
                },
            )

        # 6b. Write approval resolution to session state if resuming from approval.
        # Must recreate session with merged state — in-memory dict mutation does not
        # persist in DatabaseSessionService.
        approval_item_id = resolved_params.get("approval_item_id")
        approval_resolution = resolved_params.get("approval_resolution")
        if isinstance(approval_item_id, str) and isinstance(approval_resolution, str):
            approval_key = f"{APPROVAL_RESOLUTION_PREFIX}{approval_item_id}"
            existing_state: dict[str, object] = {}
            raw_state: object = getattr(session, "state", None)
            if isinstance(raw_state, dict):
                existing_state = dict(raw_state)  # type: ignore[arg-type]
            existing_state[approval_key] = approval_resolution
            session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                session_id=session_id,
                state=existing_state,
            )
            logger.info(
                "Wrote approval resolution to session state: %s",
                approval_key,
            )

        # 7. Set active work session Redis key with TTL
        await redis.set(redis_key, session_id, ex=_WORK_SESSION_TTL)

        # 8. Publish session started
        await publisher.publish_lifecycle(session_id, PipelineEventType.WORKFLOW_STARTED)

        # 9. Run the session
        prompt_text = str(resolved_params.get("prompt", "Begin work session."))
        message = Content(parts=[Part(text=prompt_text)])

        try:
            async for event in runner.run_async(  # type: ignore[reportUnknownMemberType]
                user_id=SYSTEM_USER_ID,
                session_id=session.id,  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                new_message=message,
            ):
                translated = publisher.translate(event, session_id)
                if translated is not None:
                    await publisher.publish(translated)
            await publisher.flush_violations()
        except ContextRecreationRequired as e:
            await publisher.flush_violations()
            logger.warning(
                "Context recreation required for work session %s: %.1f%% usage (threshold %.1f%%)",
                project_id,
                e.usage_pct,
                e.threshold_pct,
            )
            from app.agents.context_recreation import recreate_context

            # Resolve workflow-specific stages from the work session's workflow
            _ws_wf_name = str(resolved_params.get("workflow_name", "auto-code"))
            _ws_stages, _ws_stage_keys = _resolve_workflow_stages(_ws_wf_name)

            recreation_result = await recreate_context(
                session_service=session_service,
                app_name=APP_NAME,
                user_id=SYSTEM_USER_ID,
                old_session_id=session_id,
                publisher=publisher,
                memory_service=None,
                stages=_ws_stages,
                stage_completion_keys=_ws_stage_keys,
            )
            # Update session_id so cleanup uses the fresh session
            session_id = recreation_result.new_session_id
            logger.info(
                "Context recreation completed for %s: new_session=%s, remaining=%d stages",
                project_id,
                recreation_result.new_session_id,
                len(recreation_result.remaining_stages),
            )
            # Phase 8: full resume loop — rebuild pipeline with
            # stages=recreation_result.remaining_stages and re-run.
            # Phase 5b: log success and let the session complete.

        # 10. Clean up Redis key and publish completion
        await redis.delete(redis_key)
        await publisher.publish_lifecycle(session_id, PipelineEventType.WORKFLOW_COMPLETED)

        logger.info("Work session completed", extra={"project_id": project_id})
        return {"status": "completed", "project_id": project_id}

    except Exception as exc:
        logger.error(
            "Work session failed",
            extra={"project_id": project_id},
            exc_info=True,
        )

        # Clean up Redis key on failure
        try:
            await redis.delete(redis_key)
        except Exception:
            logger.error("Failed to clean up work session Redis key", exc_info=True)

        # Publish failure event
        try:
            await publisher.publish_lifecycle(
                session_id,
                PipelineEventType.WORKFLOW_FAILED,
                metadata={"error": str(exc)},
            )
        except Exception:
            logger.error("Failed to publish WORKFLOW_FAILED event", exc_info=True)

        # Create CEO queue item for failure escalation
        try:
            async with factory() as db_session:
                # Attempt to parse project_id as UUID for traceability
                try:
                    source_pid = uuid.UUID(project_id)
                except ValueError:
                    source_pid = None
                ceo_item = CeoQueueItem(
                    type=CeoItemType.ESCALATION,
                    priority=EscalationPriority.HIGH,
                    title=f"Work session failed: {project_id}",
                    source_project_id=source_pid,
                    source_agent="director",
                    metadata_={"error": str(exc), "project_id": project_id},
                    session_id=session_id,
                )
                db_session.add(ceo_item)
                await db_session.commit()
        except Exception:
            logger.error("Failed to create CEO queue item", exc_info=True)

        raise
