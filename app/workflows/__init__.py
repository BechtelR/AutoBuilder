"""Workflow composition -- registry, manifest, pipeline context."""

from app.workflows.context import (
    BeforeModelCallback,
    PipelineContext,
    PipelineFactory,
    batch_parallel_pipeline,
    sequential_pipeline,
    single_pass_pipeline,
)
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
    "BeforeModelCallback",
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
    "batch_parallel_pipeline",
    "generate_completion_report",
    "initialize_stage_state",
    "reconfigure_stage",
    "sequential_pipeline",
    "single_pass_pipeline",
    "verify_stage_completion",
    "verify_taskgroup_completion",
]
