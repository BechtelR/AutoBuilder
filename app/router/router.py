"""LLM Router — maps task types to LiteLLM model strings with fallback chains."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.lib.cache import cache_set
from app.lib.logging import get_logger
from app.models.enums import TaskType

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from redis.asyncio import Redis

    from app.config.settings import Settings

logger = get_logger("router")

# Maps agent names to their task types for before_model_callback routing
AGENT_TASK_TYPES: dict[str, TaskType] = {
    "echo_agent": TaskType.FAST,
}

# 3-step fallback chains keyed by model string
_FALLBACK_CHAINS: dict[str, list[str]] = {
    "anthropic/claude-opus-4-6": [
        "anthropic/claude-sonnet-4-5-20250929",
        "anthropic/claude-haiku-4-5-20251001",
    ],
    "anthropic/claude-sonnet-4-5-20250929": [
        "anthropic/claude-haiku-4-5-20251001",
    ],
    "anthropic/claude-haiku-4-5-20251001": [],
}


class LlmRouter:
    """Routes task types to LiteLLM model strings with fallback resolution."""

    def __init__(self, defaults: dict[TaskType, str]) -> None:
        self._defaults = defaults

    @classmethod
    def from_settings(cls, settings: Settings) -> LlmRouter:
        """Create a router from application settings."""
        return cls(
            defaults={
                TaskType.CODE: settings.default_code_model,
                TaskType.PLAN: settings.default_plan_model,
                TaskType.REVIEW: settings.default_review_model,
                TaskType.FAST: settings.default_fast_model,
            }
        )

    def select_model(self, task_type: TaskType, user_override: str | None = None) -> str:
        """Select model string for a task type. User override wins if provided."""
        if user_override is not None:
            return user_override
        return self._defaults[task_type]

    def get_fallbacks(self, model: str) -> list[str]:
        """Return ordered fallback list for a model string. Empty for unknown."""
        return list(_FALLBACK_CHAINS.get(model, []))

    def to_dict(self) -> dict[str, object]:
        """Serialize routing table for caching."""
        return {
            "defaults": {k.value: v for k, v in self._defaults.items()},
            "fallback_chains": {k: list(v) for k, v in _FALLBACK_CHAINS.items()},
        }

    async def cache_to_redis(self, redis: Redis) -> None:  # type: ignore[type-arg]
        """Store routing config in Redis with 1-hour TTL."""
        import json

        await cache_set(redis, "llm_router:config", json.dumps(self.to_dict()))


def create_model_override_callback(
    router: LlmRouter,
) -> Callable[[CallbackContext, LlmRequest], LlmResponse | None]:
    """Factory: returns a before_model_callback that routes models via LlmRouter."""

    def before_model_callback(
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> LlmResponse | None:
        agent_name: str = callback_context.agent_name
        task_type = AGENT_TASK_TYPES.get(agent_name)
        if task_type is None:
            return None

        raw_override: object = callback_context.state.get("user:model_override")
        user_override: str | None = str(raw_override) if isinstance(raw_override, str) else None
        model = router.select_model(task_type, user_override=user_override)
        llm_request.model = model
        logger.debug(
            "Model override",
            extra={"agent": agent_name, "task_type": task_type, "model": model},
        )
        return None

    return before_model_callback
