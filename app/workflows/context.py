"""Pipeline context and factory protocol for workflow composition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionContext
    from app.skills.library import SkillLibrary
    from app.tools._toolset import GlobalToolset
    from app.workflows.manifest import WorkflowManifest

# Type alias for ADK before_model_callback signature
BeforeModelCallback = Callable[["CallbackContext", "LlmRequest"], "LlmResponse | None"]


@dataclass(frozen=True)
class PipelineContext:
    """Immutable bundle of shared infrastructure for pipeline composition."""

    registry: AgentRegistry
    instruction_ctx: InstructionContext
    manifest: WorkflowManifest
    skill_library: SkillLibrary
    toolset: GlobalToolset
    before_model_callback: BeforeModelCallback | None = None

    @classmethod
    def build(
        cls,
        *,
        registry: AgentRegistry,
        instruction_ctx: InstructionContext,
        manifest: WorkflowManifest,
        skill_library: SkillLibrary,
        toolset: GlobalToolset,
        before_model_callback: BeforeModelCallback | None = None,
    ) -> PipelineContext:
        """Convenience factory for constructing a PipelineContext."""
        return cls(
            registry=registry,
            instruction_ctx=instruction_ctx,
            manifest=manifest,
            skill_library=skill_library,
            toolset=toolset,
            before_model_callback=before_model_callback,
        )


@runtime_checkable
class PipelineFactory(Protocol):
    """Protocol for workflow pipeline.py interface contract."""

    async def __call__(self, ctx: PipelineContext) -> BaseAgent: ...


# ---------------------------------------------------------------------------
# Standard pipeline pattern functions (conform to PipelineFactory)
# ---------------------------------------------------------------------------


def _build_agent(ctx: PipelineContext, agent_name: str) -> BaseAgent:
    """Build a single agent from the registry, forwarding before_model_callback if set."""
    if ctx.before_model_callback is not None:
        return ctx.registry.build(
            agent_name,
            ctx.instruction_ctx,
            before_model_callback=ctx.before_model_callback,
        )
    return ctx.registry.build(agent_name, ctx.instruction_ctx)


async def single_pass_pipeline(ctx: PipelineContext) -> BaseAgent:
    """Single-agent pass: build the first agent from the first stage.

    Falls back to building an agent keyed by the workflow name if no stages
    or agent names are declared in the manifest.
    """
    stages = ctx.manifest.stages
    agent_name: str | None = None
    if stages and stages[0].agents:
        agent_name = stages[0].agents[0]
    if agent_name is None:
        agent_name = ctx.manifest.name
    return _build_agent(ctx, agent_name)


async def sequential_pipeline(ctx: PipelineContext) -> BaseAgent:
    """Sequential pipeline: SequentialAgent wrapping all agents in stage order.

    Each stage's agent list is flattened into a single ordered sequence.
    Falls back to a single agent keyed by the workflow name when no stages
    (or no agents within stages) are declared.
    """
    from google.adk.agents import SequentialAgent

    sub_agents: list[BaseAgent] = []
    for stage in ctx.manifest.stages:
        for agent_name in stage.agents:
            sub_agents.append(_build_agent(ctx, agent_name))

    if not sub_agents:
        # Manifest has no stage/agent declarations — build a single fallback agent.
        sub_agents.append(_build_agent(ctx, ctx.manifest.name))

    return SequentialAgent(
        name=f"{ctx.manifest.name}_pipeline",
        sub_agents=sub_agents,
    )


async def batch_parallel_pipeline(ctx: PipelineContext) -> BaseAgent:
    """Batch-parallel pipeline: stages run sequentially; agents within each stage run in parallel.

    Each stage with multiple agents is wrapped in a ParallelAgent. Stages with a
    single agent are inserted directly. The resulting stage-level agents are wrapped
    in a SequentialAgent.

    Falls back to a single agent keyed by the workflow name when no stages
    (or no agents within stages) are declared.
    """
    from google.adk.agents import ParallelAgent, SequentialAgent

    stage_agents: list[BaseAgent] = []
    for stage in ctx.manifest.stages:
        batch: list[BaseAgent] = [_build_agent(ctx, name) for name in stage.agents]
        if len(batch) == 0:
            continue
        if len(batch) == 1:
            stage_agents.append(batch[0])
        else:
            stage_agents.append(
                ParallelAgent(
                    name=f"{stage.name}_batch",
                    sub_agents=batch,
                )
            )

    if not stage_agents:
        # No stages with agents declared — fall back to a single agent.
        stage_agents.append(_build_agent(ctx, ctx.manifest.name))

    return SequentialAgent(
        name=f"{ctx.manifest.name}_pipeline",
        sub_agents=stage_agents,
    )
