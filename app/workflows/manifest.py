"""Workflow manifest schema -- Pydantic models for WORKFLOW.yaml parsing."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - required at runtime for Pydantic field
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    CompletionCondition,
    PipelineType,
    StageApproval,
    ValidatorSchedule,
    ValidatorType,
)


def _upper(v: object) -> object:
    """Normalize YAML lowercase enum values to UPPERCASE for StrEnum coercion."""
    return v.upper() if isinstance(v, str) else v


# Type aliases for case-insensitive enum fields in YAML-facing models
_CIPipelineType = Annotated[PipelineType, BeforeValidator(_upper)]
_CIValidatorType = Annotated[ValidatorType, BeforeValidator(_upper)]
_CIValidatorSchedule = Annotated[ValidatorSchedule, BeforeValidator(_upper)]
_CIStageApproval = Annotated[StageApproval, BeforeValidator(_upper)]
_CICompletionCondition = Annotated[CompletionCondition, BeforeValidator(_upper)]


class StageToolsDef(BaseModel):
    """Tool overrides for a workflow stage."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    required: list[str] = Field(default_factory=lambda: list[str]())
    add: list[str] = Field(default_factory=lambda: list[str]())
    remove: list[str] = Field(default_factory=lambda: list[str]())


class ValidatorDefinition(BaseModel):
    """A validator that checks work quality at a given schedule."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    type: _CIValidatorType
    schedule: _CIValidatorSchedule
    agent: str = ""
    config: dict[str, object] = Field(default_factory=dict)
    required: bool = True


class CompletionLayerDef(BaseModel):
    """Definition for a completion verification layer."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    evidence_sources: list[str] = Field(default_factory=lambda: list[str]())


class StageDef(BaseModel):
    """Definition of a single workflow stage."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    agents: list[str] = Field(default_factory=lambda: list[str]())
    skills: list[str] = Field(default_factory=lambda: list[str]())
    tools: StageToolsDef = Field(default_factory=StageToolsDef)
    models: dict[str, str] = Field(default_factory=dict)
    validators: list[ValidatorDefinition] = Field(
        default_factory=lambda: list[ValidatorDefinition]()
    )
    completion_criteria: _CICompletionCondition = CompletionCondition.ALL_VERIFIED
    approval: _CIStageApproval = StageApproval.DIRECTOR


class ResourcesDef(BaseModel):
    """External resources required by a workflow."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    credentials: list[str] = Field(default_factory=lambda: list[str]())
    services: list[str] = Field(default_factory=lambda: list[str]())
    knowledge: list[str] = Field(default_factory=lambda: list[str]())


class McpServerDef(BaseModel):
    """MCP server dependency for a workflow."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    required: bool = False


class DeliverableTypeDef(BaseModel):
    """Definition of a deliverable type produced by a workflow."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    verification: list[str] = Field(default_factory=lambda: list[str]())


class EditOperationDef(BaseModel):
    """Definition of a workflow-specific edit operation."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    entry_stage: str = ""  # Which stage to enter on edit; empty = first stage
    requires_approval: bool = True


class WorkflowManifest(BaseModel):
    """Root model for WORKFLOW.yaml -- progressive disclosure (only name + description required)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str
    version: str = "1"
    triggers: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())
    pipeline_type: _CIPipelineType = PipelineType.SINGLE_PASS
    required_tools: list[str] = Field(default_factory=lambda: list[str]())
    optional_tools: list[str] = Field(default_factory=lambda: list[str]())
    default_models: dict[str, str] = Field(default_factory=dict)
    mcp_servers: list[McpServerDef] = Field(default_factory=lambda: list[McpServerDef]())
    stages: list[StageDef] = Field(default_factory=lambda: list[StageDef]())
    validators: list[ValidatorDefinition] = Field(
        default_factory=lambda: list[ValidatorDefinition]()
    )
    resources: ResourcesDef = Field(default_factory=ResourcesDef)
    deliverable: dict[str, object] = Field(default_factory=dict)
    outputs: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())
    completion_report: dict[str, object] = Field(default_factory=dict)
    brief_template: dict[str, object] = Field(default_factory=dict)
    conventions: list[str] = Field(default_factory=lambda: list[str]())
    director_guidance: dict[str, object] = Field(default_factory=dict)
    edit_operations: list[EditOperationDef] = Field(
        default_factory=lambda: list[EditOperationDef]()
    )
    config: dict[str, object] = Field(default_factory=dict)

    @field_validator("description")
    @classmethod
    def _validate_description_non_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "Workflow description must not be empty"
            raise ValueError(msg)
        return v

    @field_validator("name")
    @classmethod
    def _validate_kebab_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", v):
            msg = f"Workflow name must be kebab-case (lowercase, digits, hyphens): {v}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _validate_unique_names(self) -> WorkflowManifest:
        """Ensure stage names and validator names are unique within the manifest."""
        # Stage name uniqueness
        stage_names: list[str] = []
        for stage in self.stages:
            if stage.name in stage_names:
                msg = f"Duplicate stage name: '{stage.name}'"
                raise ValueError(msg)
            stage_names.append(stage.name)

        # Validator name uniqueness across all stages + top-level validators
        validator_names: list[str] = []
        for v in self.validators:
            if v.name in validator_names:
                msg = f"Duplicate validator name: '{v.name}'"
                raise ValueError(msg)
            validator_names.append(v.name)
        for stage in self.stages:
            for v in stage.validators:
                if v.name in validator_names:
                    msg = f"Duplicate validator name: '{v.name}' (in stage '{stage.name}')"
                    raise ValueError(msg)
                validator_names.append(v.name)

        return self


class WorkflowEntry(BaseModel):
    """Lightweight index record for discovered workflows."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    directory: Path
    pipeline_type: _CIPipelineType = PipelineType.SINGLE_PASS
    triggers: list[dict[str, object]] = Field(default_factory=lambda: list[dict[str, object]]())


class RunConfig(BaseModel):
    """Workflow execution request."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    workflow_name: str
    project_id: str | None = None
    specification: str | None = None
    config_overrides: dict[str, object] = Field(default_factory=dict)


class CompletionCriteria(BaseModel):
    """Runtime evaluation model constructed from stage config."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    deliverables: _CICompletionCondition = CompletionCondition.ALL_VERIFIED
    validators: list[str] = Field(default_factory=lambda: list[str]())
    approval: _CIStageApproval = StageApproval.DIRECTOR


class ValidatorResult(BaseModel):
    """DTO for validator output (distinct from future DB table F31)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    validator_name: str
    passed: bool
    evidence: dict[str, object] = Field(default_factory=dict)
    message: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VerificationLayer(BaseModel):
    """Single layer in a completion report."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    passed: bool = False
    validator_results: list[ValidatorResult] = Field(
        default_factory=lambda: list[ValidatorResult]()
    )
    summary: str = ""


class ReportSection(BaseModel):
    """Additional domain-specific section in a completion report."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    title: str
    content: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class CompletionReport(BaseModel):
    """Full completion report for a workflow execution."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    scope: str
    layers: list[VerificationLayer] = Field(default_factory=lambda: list[VerificationLayer]())
    additional_sections: list[ReportSection] = Field(default_factory=lambda: list[ReportSection]())
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
