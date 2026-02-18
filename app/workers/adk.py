"""ADK Engine — factory functions for App container, session service, and plugins.

All ADK interaction is encapsulated here. Gateway code never imports from this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.adk.agents import BaseAgent, LlmAgent
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
