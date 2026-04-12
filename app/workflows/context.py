"""Pipeline context and factory protocol for workflow composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent

    from app.agents._registry import AgentRegistry
    from app.agents.assembler import InstructionContext
    from app.skills.library import SkillLibrary
    from app.workflows.manifest import WorkflowManifest


@dataclass(frozen=True)
class PipelineContext:
    """Immutable bundle of shared infrastructure for pipeline composition."""

    registry: AgentRegistry
    instruction_ctx: InstructionContext
    manifest: WorkflowManifest
    skill_library: SkillLibrary
    toolset: object  # GlobalToolset -- not yet typed
    before_model_callback: object | None = None  # No BeforeModelCallback type yet


@runtime_checkable
class PipelineFactory(Protocol):
    """Protocol for workflow pipeline.py interface contract."""

    async def __call__(self, ctx: PipelineContext) -> BaseAgent: ...
