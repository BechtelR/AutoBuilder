"""DeliverablePipeline factory -- composes agents into a deliverable execution pipeline."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.adk.agents import SequentialAgent

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent
    from google.adk.memory import BaseMemoryService

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionContext
    from app.agents.protocols import SkillLibraryProtocol

logger = logging.getLogger(__name__)

# Canonical ordered list of pipeline stage names
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


def create_deliverable_pipeline(
    registry: AgentRegistry,
    ctx: InstructionContext,
    *,
    skill_library: SkillLibraryProtocol,
    memory_service: BaseMemoryService,
    before_model_callback: object | None = None,
    max_review_iterations: int = 3,
    stages: list[str] | None = None,
) -> SequentialAgent:
    """Construct the DeliverablePipeline.

    Pipeline sequence (full):
    SkillLoader -> MemoryLoader -> planner -> coder -> Formatter -> Linter
    -> TestRunner -> Diagnostics -> ReviewCycle

    When ``stages`` is provided, only the named stages are included.

    ReviewCycle (ReviewCycleAgent — CustomAgent wrapper):
    reviewer -> fixer -> Linter (re-lint) -> TestRunner (re-test)
    Terminates on review_passed=True in state or max_iterations (spec DD-6).
    """
    # Import custom agents to ensure they're registered in CLASS_REGISTRY.
    # The import triggers register_custom_agent() calls in __init__.py.
    __import__("app.agents.custom")

    include_all = stages is None
    stage_set: set[str] = set(stages) if stages is not None else set[str]()

    # Build custom agents with their dependencies
    skill_loader: BaseAgent = registry.build(
        "skill_loader",
        ctx,
        skill_library=skill_library,
    )

    memory_loader: BaseAgent = registry.build(
        "memory_loader",
        ctx,
        memory_service=memory_service,
    )

    # Build LLM agents — pass before_model_callback for model routing
    planner: BaseAgent = registry.build("planner", ctx, before_model_callback=before_model_callback)
    coder: BaseAgent = registry.build("coder", ctx, before_model_callback=before_model_callback)

    # Build deterministic agents for initial pass
    formatter: BaseAgent = registry.build("formatter", ctx)
    linter: BaseAgent = registry.build("linter", ctx)
    test_runner: BaseAgent = registry.build("tester", ctx)
    diagnostics: BaseAgent = registry.build("diagnostics", ctx)

    # Build ReviewCycle agents
    reviewer: BaseAgent = registry.build(
        "reviewer", ctx, before_model_callback=before_model_callback
    )
    fixer: BaseAgent = registry.build("fixer", ctx, before_model_callback=before_model_callback)
    # Separate instances for re-lint/re-test within review cycle
    review_linter: BaseAgent = registry.build("review_linter", ctx, definition="linter")
    review_tester: BaseAgent = registry.build("review_tester", ctx, definition="tester")

    # ReviewCycle (CustomAgent) — ADK LoopAgent only terminates on event.actions.escalate,
    # which LlmAgents cannot produce. ReviewCycleAgent reads review_passed from state
    # after each reviewer pass to decide whether to continue (spec DD-6 alternative).
    from app.agents.custom.review_cycle import ReviewCycleAgent

    review_cycle = ReviewCycleAgent(
        name="review_cycle",
        sub_agents=[reviewer, fixer, review_linter, review_tester],
        max_iterations=max_review_iterations,
    )

    # Stage name -> built agent mapping (ordered)
    stage_agents: dict[str, BaseAgent] = {
        "skill_loader": skill_loader,
        "memory_loader": memory_loader,
        "planner": planner,
        "coder": coder,
        "formatter": formatter,
        "linter": linter,
        "tester": test_runner,
        "diagnostics": diagnostics,
        "review_cycle": review_cycle,
    }

    # Filter to requested stages (preserving canonical order)
    if include_all:
        sub_agents = list(stage_agents.values())
        pipeline_name = "deliverable_pipeline"
    else:
        sub_agents = [agent for name, agent in stage_agents.items() if name in stage_set]
        pipeline_name = "deliverable_pipeline_partial"
        logger.info(
            "Building partial pipeline with %d/%d stages: %s",
            len(sub_agents),
            len(stage_agents),
            [n for n in stage_agents if n in stage_set],
        )

    pipeline = SequentialAgent(
        name=pipeline_name,
        sub_agents=sub_agents,
    )

    return pipeline
