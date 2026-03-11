"""Tests for ContextBudgetMonitor and ContextRecreationRequired."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.agents.context_monitor import (
    DEFAULT_CONTEXT_WINDOW,
    ContextBudgetMonitor,
    ContextRecreationRequired,
)
from app.config.settings import Settings
from app.lib.exceptions import ConfigurationError


def _make_callback_context() -> SimpleNamespace:
    """Create a mock CallbackContext with .state dict and .agent_name."""
    return SimpleNamespace(state={}, agent_name="test_agent")


def _make_request(
    text: str = "Hello world",
    model: str | None = None,
    system_instruction: str | None = None,
) -> SimpleNamespace:
    """Create a mock LlmRequest."""
    part = SimpleNamespace(text=text)
    content = SimpleNamespace(parts=[part])
    config = SimpleNamespace(
        model=model,
        system_instruction=system_instruction,
    )
    return SimpleNamespace(contents=[content], config=config, model=None)


FAKE_MODEL_COST = {
    "test-model": {"max_input_tokens": 10_000},
}


class TestContextBudgetMonitor:
    @patch("app.agents.context_monitor._token_counter", return_value=500)
    @patch("app.agents.context_monitor.litellm")
    def test_usage_pct_written_to_state(self, mock_litellm: object, mock_counter: object) -> None:
        """Verify context_budget_used_pct appears in state after call."""
        mock_litellm.model_cost = FAKE_MODEL_COST  # type: ignore[union-attr]
        ctx = _make_callback_context()
        req = _make_request(model="test-model")

        monitor = ContextBudgetMonitor(threshold_pct=90.0)
        monitor(ctx, req)  # type: ignore[arg-type]

        assert "context_budget_used_pct" in ctx.state
        assert ctx.state["context_budget_used_pct"] == 5.0  # 500/10000 * 100

    @patch("app.agents.context_monitor._token_counter", return_value=100)
    @patch("app.agents.context_monitor.litellm")
    def test_below_threshold_returns_none(self, mock_litellm: object, mock_counter: object) -> None:
        """Monitor returns None when usage is below threshold."""
        mock_litellm.model_cost = FAKE_MODEL_COST  # type: ignore[union-attr]
        ctx = _make_callback_context()
        req = _make_request(model="test-model")

        monitor = ContextBudgetMonitor(threshold_pct=80.0)
        result = monitor(ctx, req)  # type: ignore[arg-type]

        assert result is None

    @patch("app.agents.context_monitor._token_counter", return_value=9_000)
    @patch("app.agents.context_monitor.litellm")
    def test_above_threshold_raises_recreation(
        self, mock_litellm: object, mock_counter: object
    ) -> None:
        """Raises ContextRecreationRequired when usage exceeds threshold."""
        mock_litellm.model_cost = FAKE_MODEL_COST  # type: ignore[union-attr]
        ctx = _make_callback_context()
        req = _make_request(model="test-model")

        monitor = ContextBudgetMonitor(threshold_pct=80.0)

        with pytest.raises(ContextRecreationRequired):
            monitor(ctx, req)  # type: ignore[arg-type]

    @patch("app.agents.context_monitor._token_counter", return_value=8_500)
    @patch("app.agents.context_monitor.litellm")
    def test_recreation_exception_fields(self, mock_litellm: object, mock_counter: object) -> None:
        """Exception carries usage_pct, model, and threshold_pct."""
        mock_litellm.model_cost = FAKE_MODEL_COST  # type: ignore[union-attr]
        ctx = _make_callback_context()
        req = _make_request(model="test-model")

        monitor = ContextBudgetMonitor(threshold_pct=80.0)

        with pytest.raises(ContextRecreationRequired) as exc_info:
            monitor(ctx, req)  # type: ignore[arg-type]

        exc = exc_info.value
        assert exc.usage_pct == 85.0
        assert exc.model == "test-model"
        assert exc.threshold_pct == 80.0

    def test_threshold_validation_rejects_negative(self) -> None:
        """ContextBudgetMonitor(-1) raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            ContextBudgetMonitor(threshold_pct=-1)

    def test_threshold_validation_rejects_over_100(self) -> None:
        """ContextBudgetMonitor(101) raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            ContextBudgetMonitor(threshold_pct=101)

    @patch("app.agents.context_monitor._token_counter", return_value=500)
    @patch("app.agents.context_monitor.litellm")
    def test_unknown_model_uses_default_window(
        self, mock_litellm: object, mock_counter: object
    ) -> None:
        """Unknown model logs warning and uses DEFAULT_CONTEXT_WINDOW."""
        mock_litellm.model_cost = SimpleNamespace(get=lambda _key: None)  # type: ignore[union-attr]
        ctx = _make_callback_context()
        req = _make_request(model="unknown-model-xyz")

        monitor = ContextBudgetMonitor(threshold_pct=80.0)
        result = monitor(ctx, req)  # type: ignore[arg-type]

        assert result is None
        expected_pct = round((500 / DEFAULT_CONTEXT_WINDOW) * 100.0, 1)
        assert ctx.state["context_budget_used_pct"] == expected_pct

    def test_settings_threshold_validation(self) -> None:
        """Settings rejects context_budget_threshold outside 0-100."""
        with pytest.raises(ValidationError):
            Settings(context_budget_threshold=150)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            Settings(context_budget_threshold=-5)  # type: ignore[call-arg]
