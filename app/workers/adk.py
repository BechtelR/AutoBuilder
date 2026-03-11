"""ADK Engine — factory functions for App container, session service, and plugins.

All ADK interaction is encapsulated here. Gateway code never imports from this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models.lite_llm import LiteLlm
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner

from app.lib.logging import get_logger
from app.models.constants import APP_NAME

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.adk.sessions.base_session_service import BaseSessionService

    from app.agents.assembler import InstructionContext
    from app.router.router import LlmRouter

logger = get_logger("engine")
_plugin_logger = get_logger("engine.plugins")


# ---------------------------------------------------------------------------
# Session Service
# ---------------------------------------------------------------------------


def create_session_service(db_url: str) -> BaseSessionService:
    """Create a DatabaseSessionService connected to PostgreSQL.

    ADK auto-creates its own tables on first operation.
    """
    from google.adk.sessions.database_session_service import (
        DatabaseSessionService,
    )

    return DatabaseSessionService(db_url=db_url)  # type: ignore[reportReturnType]


# ---------------------------------------------------------------------------
# Echo Agent (test pipeline)
# ---------------------------------------------------------------------------


def create_echo_agent(
    model: str,
    before_model_callback: (
        Callable[[CallbackContext, LlmRequest], LlmResponse | None] | None
    ) = None,
) -> LlmAgent:
    """Create a minimal test agent for infrastructure validation."""
    return LlmAgent(
        name="echo_agent",
        model=LiteLlm(model=model),
        instruction="You are a helpful echo agent. Respond concisely to the user's message.",
        output_key="agent_response",
        before_model_callback=before_model_callback,
    )


# ---------------------------------------------------------------------------
# Director Agent (stub — real implementation in Phase 5)
# ---------------------------------------------------------------------------


def create_director_agent(
    model: str,
    before_model_callback: (
        Callable[[CallbackContext, LlmRequest], LlmResponse | None] | None
    ) = None,
) -> LlmAgent:
    """Create a Director agent stub.

    Returns a simple echo agent until Phase 5 implements the real Director
    with hierarchical supervision capabilities.
    """
    return LlmAgent(
        name="director_agent",
        model=LiteLlm(model=model),
        instruction=(
            "You are the AutoBuilder Director. You help the CEO manage projects and "
            "coordinate work. Respond concisely and helpfully to the user's message."
        ),
        output_key="director_response",
        before_model_callback=before_model_callback,
    )


# ---------------------------------------------------------------------------
# Logging Plugin
# ---------------------------------------------------------------------------


class LoggingPlugin(BasePlugin):
    """Emits structured log entries for agent and tool lifecycle events."""

    def __init__(self) -> None:
        super().__init__(name="logging_plugin")

    async def before_agent_callback(  # type: ignore[override]
        self,
        callback_context: CallbackContext,
        **kwargs: object,
    ) -> None:
        _plugin_logger.info(
            "Agent started",
            extra={"agent": callback_context.agent_name},
        )

    async def after_agent_callback(  # type: ignore[override]
        self,
        callback_context: CallbackContext,
        **kwargs: object,
    ) -> None:
        _plugin_logger.info(
            "Agent completed",
            extra={"agent": callback_context.agent_name},
        )

    async def before_tool_callback(  # type: ignore[override]
        self,
        callback_context: CallbackContext,
        **kwargs: object,
    ) -> None:
        tool_name = str(kwargs.get("tool", ""))
        _plugin_logger.info(
            "Tool called",
            extra={"agent": callback_context.agent_name, "tool": tool_name},
        )

    async def after_tool_callback(  # type: ignore[override]
        self,
        callback_context: CallbackContext,
        **kwargs: object,
    ) -> None:
        tool_name = str(kwargs.get("tool", ""))
        _plugin_logger.info(
            "Tool result",
            extra={"agent": callback_context.agent_name, "tool": tool_name},
        )


# ---------------------------------------------------------------------------
# App Container
# ---------------------------------------------------------------------------


def create_app_container(
    root_agent: BaseAgent,
    plugins: list[BasePlugin] | None = None,
) -> App:
    """Create an ADK App container with compaction, resumability, and caching."""
    resolved_plugins: list[BasePlugin] = plugins if plugins is not None else [LoggingPlugin()]

    summarizer_llm = LiteLlm(model="anthropic/claude-haiku-4-5-20251001")

    return App(
        name=APP_NAME,
        root_agent=root_agent,
        plugins=resolved_plugins,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5,
            overlap_size=1,
            summarizer=LlmEventSummarizer(llm=summarizer_llm),
        ),
        resumability_config=ResumabilityConfig(is_resumable=True),
        context_cache_config=ContextCacheConfig(
            min_tokens=1000,
            ttl_seconds=300,
            cache_intervals=5,
        ),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def create_runner(app: App, session_service: BaseSessionService) -> Runner:
    """Create a Runner from an App and session service."""
    return Runner(
        app=app,
        session_service=session_service,
        auto_create_session=False,
    )


# ---------------------------------------------------------------------------
# Pipeline Callbacks
# ---------------------------------------------------------------------------


def create_pipeline_callbacks(
    router: LlmRouter,
    threshold_pct: float = 80.0,
) -> Callable[[CallbackContext, LlmRequest], LlmResponse | None]:
    """Create the composed before_model_callback chain for pipeline agents.

    Chain: router override -> context injection -> budget monitor.
    """
    from app.agents.context_monitor import ContextBudgetMonitor
    from app.agents.state_helpers import compose_callbacks, create_context_injection_callback
    from app.router.router import create_model_override_callback

    router_callback = create_model_override_callback(router)
    context_callback = create_context_injection_callback()
    budget_monitor = ContextBudgetMonitor(threshold_pct=threshold_pct)

    return compose_callbacks(router_callback, context_callback, budget_monitor)


# ---------------------------------------------------------------------------
# Deliverable Pipeline Factory
# ---------------------------------------------------------------------------


def create_deliverable_pipeline_from_context(
    worker_ctx: dict[str, object],
    instruction_ctx: InstructionContext,
) -> SequentialAgent:
    """Create a DeliverablePipeline from worker context.

    Uses worker_ctx dependencies: llm_router, toolset, etc.
    """
    from pathlib import Path

    from google.adk.memory import InMemoryMemoryService

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionAssembler
    from app.agents.pipeline import create_deliverable_pipeline
    from app.agents.protocols import NullSkillLibrary
    from app.config import get_settings
    from app.models.enums import DefinitionScope

    settings = get_settings()
    router: LlmRouter = worker_ctx["llm_router"]  # type: ignore[assignment]
    toolset = worker_ctx.get("toolset")

    # Create assembler and registry
    assembler = InstructionAssembler()

    if toolset is None:
        from app.tools._toolset import GlobalToolset

        toolset = GlobalToolset()

    registry = AgentRegistry(
        assembler=assembler,
        router=router,
        toolset=toolset,  # type: ignore[arg-type]
    )

    # Scan agent definition directories
    registry.scan((Path("app/agents"), DefinitionScope.GLOBAL))

    # Create callbacks
    callbacks = create_pipeline_callbacks(router, float(settings.context_budget_threshold))

    return create_deliverable_pipeline(
        registry=registry,
        ctx=instruction_ctx,
        skill_library=NullSkillLibrary(),
        memory_service=InMemoryMemoryService(),
        before_model_callback=callbacks,
    )
