"""Context budget monitoring for ADK agent sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import litellm
from litellm import token_counter as _token_counter  # type: ignore[reportUnknownVariableType]

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_WINDOW = 100_000  # Conservative fallback (FR-5a.46)
DEFAULT_FALLBACK_MODEL = "claude-sonnet-4-6"  # Fallback when request has no model


class ContextRecreationRequired(Exception):
    """Control flow signal: context budget exceeded, session needs recreation.

    Not an AutoBuilderError — this is an expected control flow event, not a fault.
    """

    def __init__(self, *, usage_pct: float, model: str, threshold_pct: float) -> None:
        super().__init__(
            f"Context budget {usage_pct:.1f}% exceeds threshold {threshold_pct:.1f}% "
            f"for model {model}"
        )
        self.usage_pct = usage_pct
        self.model = model
        self.threshold_pct = threshold_pct

    def __str__(self) -> str:
        return (
            f"ContextRecreationRequired(usage_pct={self.usage_pct:.1f}, "
            f"model={self.model!r}, threshold_pct={self.threshold_pct:.1f})"
        )


class ContextBudgetMonitor:
    """before_model_callback that tracks token usage and triggers context recreation."""

    def __init__(self, threshold_pct: float = 80.0) -> None:
        if not 0 <= threshold_pct <= 100:
            from app.lib.exceptions import ConfigurationError

            raise ConfigurationError(
                message=f"context_budget_threshold must be 0-100, got {threshold_pct}"
            )
        self._threshold_pct = threshold_pct

    def __call__(
        self, callback_context: CallbackContext, request: LlmRequest
    ) -> LlmResponse | None:
        """Estimate token count, write usage % to state, raise if over threshold."""
        model = self._get_model(request)
        max_tokens = self._get_context_window(model)
        text = self._serialize_request(request)
        estimated_tokens: int = _token_counter(model=model, text=text)

        usage_pct = (estimated_tokens / max_tokens) * 100.0 if max_tokens > 0 else 0.0

        callback_context.state["context_budget_used_pct"] = round(usage_pct, 1)

        if usage_pct > self._threshold_pct:
            raise ContextRecreationRequired(
                usage_pct=round(usage_pct, 1),
                model=model,
                threshold_pct=self._threshold_pct,
            )

        return None

    def _get_model(self, request: LlmRequest) -> str:
        """Extract model string from request."""
        model = getattr(request, "model", None)
        if model and isinstance(model, str):
            return model
        config = getattr(request, "config", None)
        if config:
            model_str = getattr(config, "model", None)
            if model_str and isinstance(model_str, str):
                return model_str
        return DEFAULT_FALLBACK_MODEL

    def _get_context_window(self, model: str) -> int:
        """Get context window size from LiteLLM registry."""
        try:
            model_info: dict[str, object] | None = litellm.model_cost.get(  # type: ignore[union-attr]
                model
            ) or litellm.model_cost.get(  # type: ignore[union-attr]
                f"anthropic/{model}"
            )
            if model_info and "max_input_tokens" in model_info:
                return int(model_info["max_input_tokens"])  # type: ignore[arg-type]
        except Exception:
            pass
        logger.warning(
            "Could not determine context window for model '%s', using default %d",
            model,
            DEFAULT_CONTEXT_WINDOW,
        )
        return DEFAULT_CONTEXT_WINDOW

    def _serialize_request(self, request: LlmRequest) -> str:
        """Serialize request contents to text for token counting."""
        parts: list[str] = []

        config = getattr(request, "config", None)
        if config:
            sys_instr = getattr(config, "system_instruction", None)
            if sys_instr:
                if isinstance(sys_instr, str):
                    parts.append(sys_instr)
                else:
                    parts.append(str(sys_instr))

        if request.contents:
            for content in request.contents:
                if hasattr(content, "parts"):
                    for part in content.parts:  # type: ignore[union-attr]
                        text = getattr(part, "text", None)
                        if text:
                            parts.append(str(text))
                elif isinstance(content, str):
                    parts.append(content)
                else:
                    parts.append(str(content))

        return "\n".join(parts)
