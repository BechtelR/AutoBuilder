"""Tests for LLM Router."""

from app.config.settings import Settings
from app.models.enums import TaskType
from app.router.router import AGENT_TASK_TYPES, LlmRouter, create_model_override_callback


class TestLlmRouter:
    def test_from_settings(self) -> None:
        settings = Settings()
        router = LlmRouter.from_settings(settings)
        assert router.select_model(TaskType.CODE) == "anthropic/claude-sonnet-4-5-20250929"

    def test_select_code_model(self) -> None:
        router = LlmRouter.from_settings(Settings())
        assert router.select_model(TaskType.CODE) == "anthropic/claude-sonnet-4-5-20250929"

    def test_select_plan_model(self) -> None:
        router = LlmRouter.from_settings(Settings())
        assert router.select_model(TaskType.PLAN) == "anthropic/claude-opus-4-6"

    def test_select_review_model(self) -> None:
        router = LlmRouter.from_settings(Settings())
        assert router.select_model(TaskType.REVIEW) == "anthropic/claude-sonnet-4-5-20250929"

    def test_select_fast_model(self) -> None:
        router = LlmRouter.from_settings(Settings())
        assert router.select_model(TaskType.FAST) == "anthropic/claude-haiku-4-5-20251001"

    def test_user_override_wins(self) -> None:
        router = LlmRouter.from_settings(Settings())
        result = router.select_model(TaskType.CODE, user_override="openai/gpt-5")
        assert result == "openai/gpt-5"

    def test_get_fallbacks_opus(self) -> None:
        router = LlmRouter.from_settings(Settings())
        fallbacks = router.get_fallbacks("anthropic/claude-opus-4-6")
        assert len(fallbacks) == 2
        assert "anthropic/claude-sonnet-4-5-20250929" in fallbacks
        assert "anthropic/claude-haiku-4-5-20251001" in fallbacks

    def test_get_fallbacks_sonnet(self) -> None:
        router = LlmRouter.from_settings(Settings())
        fallbacks = router.get_fallbacks("anthropic/claude-sonnet-4-5-20250929")
        assert len(fallbacks) == 1
        assert "anthropic/claude-haiku-4-5-20251001" in fallbacks

    def test_get_fallbacks_haiku(self) -> None:
        router = LlmRouter.from_settings(Settings())
        fallbacks = router.get_fallbacks("anthropic/claude-haiku-4-5-20251001")
        assert fallbacks == []

    def test_get_fallbacks_unknown(self) -> None:
        router = LlmRouter.from_settings(Settings())
        assert router.get_fallbacks("unknown/model") == []

    def test_to_dict(self) -> None:
        router = LlmRouter.from_settings(Settings())
        d = router.to_dict()
        assert "defaults" in d
        assert "fallback_chains" in d

    def test_agent_task_types_has_echo_agent(self) -> None:
        assert "echo_agent" in AGENT_TASK_TYPES
        assert AGENT_TASK_TYPES["echo_agent"] == TaskType.FAST


class TestModelOverrideCallback:
    def test_callback_maps_echo_agent(self) -> None:
        """Callback maps echo_agent to FAST model via router."""
        router = LlmRouter.from_settings(Settings())
        callback = create_model_override_callback(router)

        # We can't easily construct CallbackContext without ADK internals,
        # so we create a mock-like object with the needed attributes
        class FakeCallbackContext:
            agent_name = "echo_agent"
            state: dict[str, object] = {}

        class FakeLlmRequest:
            model = "original_model"

        ctx = FakeCallbackContext()
        req = FakeLlmRequest()
        result = callback(ctx, req)  # type: ignore[arg-type]

        assert result is None
        assert req.model == "anthropic/claude-haiku-4-5-20251001"

    def test_callback_respects_user_override(self) -> None:
        router = LlmRouter.from_settings(Settings())
        callback = create_model_override_callback(router)

        class FakeCallbackContext:
            agent_name = "echo_agent"
            state: dict[str, object] = {"user:model_override": "custom/model"}

        class FakeLlmRequest:
            model = "original_model"

        ctx = FakeCallbackContext()
        req = FakeLlmRequest()
        result = callback(ctx, req)  # type: ignore[arg-type]

        assert result is None
        assert req.model == "custom/model"

    def test_callback_skips_unknown_agent(self) -> None:
        router = LlmRouter.from_settings(Settings())
        callback = create_model_override_callback(router)

        class FakeCallbackContext:
            agent_name = "unknown_agent"
            state: dict[str, object] = {}

        class FakeLlmRequest:
            model = "original_model"

        ctx = FakeCallbackContext()
        req = FakeLlmRequest()
        result = callback(ctx, req)  # type: ignore[arg-type]

        assert result is None
        assert req.model == "original_model"  # unchanged
