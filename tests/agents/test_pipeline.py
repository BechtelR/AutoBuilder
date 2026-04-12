"""Tests for auto-code DeliverablePipeline factory (migrated from app.agents.pipeline).

The pipeline creation logic now lives in app/workflows/auto-code/pipeline.py
and is invoked via WorkflowRegistry.create_pipeline() or directly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import BaseAgent, SequentialAgent

from app.agents.assembler import InstructionContext
from app.agents.custom.review_cycle import ReviewCycleAgent
from app.agents.protocols import NullSkillLibrary
from app.models.enums import PipelineType
from app.workflows.context import PipelineContext
from app.workflows.manifest import WorkflowManifest

if TYPE_CHECKING:
    import types
    from collections.abc import AsyncGenerator

    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.events import Event

    from app.agents._registry import AgentRegistry

# ---------------------------------------------------------------------------
# Load the auto-code pipeline module (directory name has a hyphen)
# ---------------------------------------------------------------------------

_AUTO_CODE_PIPELINE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "app"
    / "workflows"
    / "auto-code"
    / "pipeline.py"
)


def _load_auto_code_pipeline() -> types.ModuleType:
    """Dynamically load the auto-code pipeline module."""
    module_name = "_test_auto_code_pipeline"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _AUTO_CODE_PIPELINE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


async def _create_pipeline(ctx: PipelineContext) -> BaseAgent:
    """Call create_pipeline from the auto-code pipeline module."""
    mod = _load_auto_code_pipeline()
    factory = mod.create_pipeline  # type: ignore[attr-defined]
    result: BaseAgent = await factory(ctx)
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


def _make_pipeline_context(
    registry: AgentRegistry | None = None,
    manifest: WorkflowManifest | None = None,
) -> PipelineContext:
    """Create a PipelineContext with sensible defaults for testing."""
    if registry is None:
        registry = _make_mock_registry()
    if manifest is None:
        manifest = WorkflowManifest(
            name="auto-code",
            description="test auto-code workflow",
            pipeline_type=PipelineType.SEQUENTIAL,
        )
    return PipelineContext(
        registry=registry,
        instruction_ctx=InstructionContext(agent_name="pipeline"),
        manifest=manifest,
        skill_library=NullSkillLibrary(),  # type: ignore[arg-type]
        toolset=MagicMock(),
    )


@pytest.fixture
def mock_registry() -> AgentRegistry:
    return _make_mock_registry()


@pytest.fixture
def pipeline_ctx(mock_registry: AgentRegistry) -> PipelineContext:
    return _make_pipeline_context(mock_registry)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateAutoCodePipeline:
    @pytest.mark.asyncio
    async def test_returns_sequential_agent(self, pipeline_ctx: PipelineContext) -> None:
        pipeline = await _create_pipeline(pipeline_ctx)
        assert isinstance(pipeline, SequentialAgent)

    @pytest.mark.asyncio
    async def test_pipeline_name(self, pipeline_ctx: PipelineContext) -> None:
        pipeline = await _create_pipeline(pipeline_ctx)
        assert pipeline.name == "deliverable_pipeline"

    @pytest.mark.asyncio
    async def test_pipeline_sub_agent_count(self, pipeline_ctx: PipelineContext) -> None:
        """Pipeline has 9 sub_agents: 8 agents + review_cycle."""
        pipeline = await _create_pipeline(pipeline_ctx)
        assert len(pipeline.sub_agents) == 9

    @pytest.mark.asyncio
    async def test_pipeline_agent_order(self, pipeline_ctx: PipelineContext) -> None:
        """Sub_agents in correct order."""
        pipeline = await _create_pipeline(pipeline_ctx)
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

    @pytest.mark.asyncio
    async def test_review_cycle_is_loop_agent(self, pipeline_ctx: PipelineContext) -> None:
        pipeline = await _create_pipeline(pipeline_ctx)
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)

    @pytest.mark.asyncio
    async def test_review_cycle_max_iterations(self, pipeline_ctx: PipelineContext) -> None:
        pipeline = await _create_pipeline(pipeline_ctx)
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)
        assert review_cycle.max_iterations == 3

    @pytest.mark.asyncio
    async def test_review_cycle_sub_agents(self, pipeline_ctx: PipelineContext) -> None:
        pipeline = await _create_pipeline(pipeline_ctx)
        review_cycle = pipeline.sub_agents[-1]
        assert isinstance(review_cycle, ReviewCycleAgent)
        review_names = [a.name for a in review_cycle.sub_agents]
        assert review_names == ["reviewer", "fixer", "review_linter", "review_tester"]

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_max_review(self, mock_registry: AgentRegistry) -> None:
        manifest = WorkflowManifest(
            name="auto-code",
            description="test auto-code workflow",
            pipeline_type=PipelineType.SEQUENTIAL,
            config={"max_review_cycles": 5},
        )
        ctx = _make_pipeline_context(mock_registry, manifest)
        pipeline = await _create_pipeline(ctx)
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
