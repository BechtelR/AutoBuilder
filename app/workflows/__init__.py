"""Workflow composition -- registry, manifest, pipeline context."""

from app.workflows.context import PipelineContext, PipelineFactory
from app.workflows.manifest import (
    CompletionCriteria,
    CompletionLayerDef,
    CompletionReport,
    DeliverableTypeDef,
    McpServerDef,
    ReportSection,
    ResourcesDef,
    RunConfig,
    StageDef,
    StageToolsDef,
    ValidatorDefinition,
    ValidatorResult,
    VerificationLayer,
    WorkflowEntry,
    WorkflowManifest,
)
from app.workflows.registry import WorkflowRegistry
from app.workflows.stages import initialize_stage_state, reconfigure_stage
from app.workflows.validators import (
    DEFAULT_VERIFICATION_LAYERS,
    ValidatorRunner,
    generate_completion_report,
    verify_stage_completion,
    verify_taskgroup_completion,
)

__all__ = [
    "CompletionCriteria",
    "CompletionLayerDef",
    "CompletionReport",
    "DEFAULT_VERIFICATION_LAYERS",
    "DeliverableTypeDef",
    "McpServerDef",
    "PipelineContext",
    "PipelineFactory",
    "ReportSection",
    "ResourcesDef",
    "RunConfig",
    "StageDef",
    "StageToolsDef",
    "ValidatorDefinition",
    "ValidatorResult",
    "ValidatorRunner",
    "VerificationLayer",
    "WorkflowEntry",
    "WorkflowManifest",
    "WorkflowRegistry",
    "generate_completion_report",
    "initialize_stage_state",
    "reconfigure_stage",
    "verify_stage_completion",
    "verify_taskgroup_completion",
]
