"""Tests for DeliverablePipeline factory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import BaseAgent, SequentialAgent

from app.agents.assembler import InstructionContext
from app.agents.custom.review_cycle import ReviewCycleAgent
from app.agents.pipeline import create_deliverable_pipeline
from app.agents.protocols import NullSkillLibrary

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.events import Event

    from app.agents._registry import AgentRegistry


class _StubAgent(BaseAgent):
    """Minimal real BaseAgent for testing pipeline composition."""

    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        return
        yield  # pragma: no cover


def _make_stub_agent(name: str) -> BaseAgent:
    """Create a stub agent with the given name."""
    return _StubAgent(name=name)


def _make_mock_registry() -> AgentRegistry:
    """Create a mock AgentRegistry that returns named stub agents."""

    def _build_side_effect(
        name: str,
        ctx: InstructionContext,
        **overrides: object,
    ) -> BaseAgent:
        return _make_stub_agent(name)

    registry = MagicMock()
    registry.build = MagicMock(side_effect=_build_side_effect)
    return registry  # type: ignore[return-value]


@pytest.fixture
def mock_registry() -> AgentRegistry:
    return _make_mock_registry()


@pytest.fixture
def instruction_ctx() -> InstructionContext:
    return InstructionContext(agent_name="pipeline")


@pytest.fixture
def mock_memory_service() -> MagicMock:
    return MagicMock()


class TestCreateDeliverablePipeline:
    def test_returns_sequential_agent(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        assert isinstance(pipeline, SequentialAgent)

    def test_pipeline_name(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        assert pipeline.name == "deliverable_pipeline"

    def test_pipeline_sub_agent_count(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        """Pipeline has 9 sub_agents: 8 agents + review_cycle."""
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        assert len(pipeline.sub_agents) == 9

    def test_pipeline_agent_order(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        """Sub_agents in correct order."""
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        names = [a.name for a in pipeline.sub_agents]
        expected = [
            "skill_loader",
            "memory_loader",
            "planner",
            "coder",
            "formatter",
            "linter",
            "tester",
            "diagnostics",
            "review_cycle",
        ]
        assert names == expected

    def test_review_cycle_is_loop_agent(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)

    def test_review_cycle_max_iterations(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)
        assert review_cycle.max_iterations == 3

    def test_review_cycle_sub_agents(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
        )
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)
        review_names = [a.name for a in review_cycle.sub_agents]
        assert review_names == ["reviewer", "fixer", "review_linter", "review_tester"]

    def test_pipeline_with_custom_max_review(
        self,
        mock_registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        mock_memory_service: MagicMock,
    ) -> None:
        pipeline = create_deliverable_pipeline(
            mock_registry,
            instruction_ctx,
            skill_library=NullSkillLibrary(),
            memory_service=mock_memory_service,
            max_review_iterations=5,
        )
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)
        assert review_cycle.max_iterations == 5


class TestPipelineCallbacksChain:
    def test_compose_callbacks_chain(self) -> None:
        """Verify pipeline callbacks chain works (router -> context -> monitor)."""
        from unittest.mock import MagicMock as MM

        from app.workers.adk import create_pipeline_callbacks

        mock_router = MM()
        mock_router.select_model = MM(return_value="anthropic/claude-haiku-4-5-20251001")

        # Should not raise during creation
        callback = create_pipeline_callbacks(mock_router, threshold_pct=80.0)

        # The result should be callable
        assert callable(callback)

    def test_compose_callbacks_returns_none_for_unknown_agent(self) -> None:
        """Composed callback returns None when no individual callback short-circuits."""
        from unittest.mock import MagicMock as MM

        from app.workers.adk import create_pipeline_callbacks

        mock_router = MM()
        mock_router.select_model = MM(return_value="anthropic/claude-haiku-4-5-20251001")

        callback = create_pipeline_callbacks(mock_router, threshold_pct=99.0)

        # Create mock callback_context and request
        mock_ctx = MM()
        mock_ctx.agent_name = "unknown_agent"
        mock_ctx.state = {}

        mock_req = MM()
        mock_req.model = "anthropic/claude-haiku-4-5-20251001"
        mock_req.contents = []
        mock_req.config = None

        # router callback returns None for unknown agent, context injection returns None,
        # budget monitor needs content to estimate tokens — with empty content + high
        # threshold it should return None
        with patch("app.agents.context_monitor._token_counter", return_value=0):
            result = callback(mock_ctx, mock_req)

        assert result is None
