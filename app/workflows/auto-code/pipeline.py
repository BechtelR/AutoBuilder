"""Auto-code workflow pipeline -- composes agents into a deliverable execution pipeline.

Migrated from app/agents/pipeline.py to use PipelineContext.
Produces the same agent tree: skill_loader -> memory_loader -> planner -> coder
-> formatter -> linter -> tester -> diagnostics -> review_cycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.adk.agents import SequentialAgent

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent

    from app.workflows.context import PipelineContext

logger = logging.getLogger(__name__)

# Default max review iterations (configurable via manifest config)
_DEFAULT_MAX_REVIEW_ITERATIONS = 3

# ---------------------------------------------------------------------------
# Canonical auto-code pipeline stage names and completion keys
# ---------------------------------------------------------------------------

PIPELINE_STAGE_NAMES: list[str] = [
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

# Stage name -> state key that indicates completion
STAGE_COMPLETION_KEYS: dict[str, str] = {
    "skill_loader": "loaded_skill_names",
    "memory_loader": "memory_context",
    "planner": "implementation_plan",
    "coder": "code_output",
    "formatter": "formatter_results",
    "linter": "lint_results",
    "tester": "test_results",
    "diagnostics": "diagnostics_analysis",
    "review_cycle": "review_passed",
}


def _build_agent(
    ctx: PipelineContext,
    name: str,
    *,
    definition: str | None = None,
    **overrides: object,
) -> BaseAgent:
    """Build a single agent, forwarding before_model_callback when present."""
    kwargs: dict[str, object] = dict(overrides)
    if ctx.before_model_callback is not None:
        kwargs.setdefault("before_model_callback", ctx.before_model_callback)
    return ctx.registry.build(name, ctx.instruction_ctx, definition=definition, **kwargs)


def _get_manifest_stage_agents(ctx: PipelineContext, stage_name: str) -> set[str]:
    """Read the agents list from a manifest stage by name.

    Returns the set of agent names declared in the specified stage,
    or an empty set if the stage is not found.
    """
    for stage in ctx.manifest.stages:
        if stage.name == stage_name:
            return set(stage.agents)
    return set()


async def create_pipeline(ctx: PipelineContext) -> BaseAgent:
    """Construct the auto-code DeliverablePipeline from PipelineContext.

    Pipeline sequence:
    SkillLoader -> MemoryLoader -> Planner -> Coder -> Formatter -> Linter
    -> TestRunner -> Diagnostics -> ReviewCycle

    ReviewCycle (ReviewCycleAgent -- CustomAgent wrapper):
    Reviewer -> Fixer -> Linter (re-lint) -> TestRunner (re-test)
    Terminates on review_passed=True in state or max_iterations.

    The pipeline reads the manifest's BUILD stage agents list for validation
    and logs any discrepancies between the canonical pipeline composition and
    the manifest declaration.
    """
    # Import custom agents to ensure they are registered in CLASS_REGISTRY.
    __import__("app.agents.custom")

    # Read max_review_iterations from manifest config (if specified)
    max_review_iterations = _DEFAULT_MAX_REVIEW_ITERATIONS
    config_val = ctx.manifest.config.get("max_review_cycles")
    if isinstance(config_val, int):
        max_review_iterations = config_val

    # Read the build stage's agents list from the manifest for validation.
    # The canonical pipeline order is fixed (matching PIPELINE_STAGE_NAMES),
    # but the manifest's build stage agents are consulted for consistency.
    manifest_build_agents = _get_manifest_stage_agents(ctx, "build")
    if manifest_build_agents:
        # Log agents declared in manifest but not in canonical pipeline
        canonical_agents = set(PIPELINE_STAGE_NAMES)
        undeclared = (
            canonical_agents
            - manifest_build_agents
            - {
                "skill_loader",
                "memory_loader",
                "review_cycle",
            }
        )
        if undeclared:
            logger.debug(
                "Pipeline agents not in manifest BUILD stage: %s (infrastructure/composite)",
                sorted(undeclared),
            )

    # -- Custom agents (deterministic, need extra dependencies) --
    skill_loader: BaseAgent = _build_agent(ctx, "skill_loader", skill_library=ctx.skill_library)
    memory_loader: BaseAgent = _build_agent(
        ctx,
        "memory_loader",
        memory_service=None,  # Phase 7 degraded mode
    )

    # -- LLM agents --
    planner: BaseAgent = _build_agent(ctx, "planner")
    coder: BaseAgent = _build_agent(ctx, "coder")

    # -- Deterministic agents (initial pass) --
    formatter: BaseAgent = _build_agent(ctx, "formatter")
    linter: BaseAgent = _build_agent(ctx, "linter")
    test_runner: BaseAgent = _build_agent(ctx, "tester")
    diagnostics: BaseAgent = _build_agent(ctx, "diagnostics")

    # -- ReviewCycle sub-agents --
    reviewer: BaseAgent = _build_agent(ctx, "reviewer")
    fixer: BaseAgent = _build_agent(ctx, "fixer")
    review_linter: BaseAgent = _build_agent(ctx, "review_linter", definition="linter")
    review_tester: BaseAgent = _build_agent(ctx, "review_tester", definition="tester")

    # ReviewCycle (CustomAgent) -- reads review_passed from state after each
    # reviewer pass to decide whether to continue (spec DD-6 alternative).
    from app.agents.custom.review_cycle import ReviewCycleAgent

    review_cycle = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, review_linter, review_tester],
        max_iterations=max_review_iterations,
    )

    # Assemble the full pipeline in canonical order
    sub_agents: list[BaseAgent] = [
        skill_loader,
        memory_loader,
        planner,
        coder,
        formatter,
        linter,
        test_runner,
        diagnostics,
        review_cycle,
    ]

    pipeline = SequentialAgent(
        name="deliverable_pipeline",
        sub_agents=sub_agents,
    )

    logger.info(
        "Built auto-code pipeline with %d agents (max_review_iterations=%d)",
        len(sub_agents),
        max_review_iterations,
    )

    return pipeline
