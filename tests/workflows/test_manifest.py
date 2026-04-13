"""Tests for workflow manifest Pydantic models and progressive disclosure."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import enum

import pytest
import yaml
from pydantic import ValidationError

from app.models.enums import (
    CompletionCondition,
    PipelineType,
    StageApproval,
    StageStatus,
    ValidatorSchedule,
    ValidatorType,
)
from app.workflows.manifest import (
    CompletionCriteria,
    CompletionReport,
    DeliverableTypeDef,
    EditOperationDef,
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
from tests.workflows.conftest import TIER1_MANIFEST, TIER2_MANIFEST, TIER3_MANIFEST


class TestProgressiveDisclosure:
    """Progressive disclosure: 2-field minimum to full manifest."""

    def test_tier1_two_fields_only(self) -> None:
        """A manifest with only name + description is valid."""
        m = WorkflowManifest.model_validate(TIER1_MANIFEST)
        assert m.name == "minimal-test"
        assert m.description == "Two-field minimum"

    def test_tier1_defaults(self) -> None:
        """Tier 1 manifest gets sensible defaults for all optional fields."""
        m = WorkflowManifest.model_validate(TIER1_MANIFEST)
        assert m.pipeline_type == PipelineType.SINGLE_PASS
        assert m.stages == []
        assert m.validators == []
        assert m.triggers == []
        assert m.required_tools == []
        assert m.optional_tools == []
        assert m.mcp_servers == []
        assert m.default_models == {}
        assert m.conventions == []

    def test_tier2_with_stages(self) -> None:
        """Adding stages still validates."""
        m = WorkflowManifest.model_validate(TIER2_MANIFEST)
        assert len(m.stages) == 2
        assert m.stages[0].name == "alpha"
        assert m.stages[1].name == "beta"

    def test_tier3_full_manifest(self) -> None:
        """Full manifest with all fields parses correctly."""
        m = WorkflowManifest.model_validate(TIER3_MANIFEST)
        assert len(m.stages) == 3
        assert m.pipeline_type == PipelineType.SEQUENTIAL
        assert len(m.required_tools) == 2
        assert len(m.conventions) == 2
        # Nested validators parsed
        assert m.stages[1].validators[0].name == "lint_check"
        assert m.stages[1].validators[0].type == ValidatorType.DETERMINISTIC

    def test_extra_fields_ignored(self) -> None:
        """Unknown fields are silently ignored (extra='ignore')."""
        data = {**TIER1_MANIFEST, "unknown_field": "ignored"}
        m = WorkflowManifest.model_validate(data)
        assert m.name == "minimal-test"

    def test_yaml_roundtrip(self) -> None:
        """YAML -> model -> dict -> YAML consistency."""
        m = WorkflowManifest.model_validate(TIER1_MANIFEST)
        dumped = m.model_dump(mode="json", exclude_defaults=True)
        assert dumped["name"] == "minimal-test"
        assert dumped["description"] == "Two-field minimum"

    def test_yaml_file_roundtrip(self, tmp_path: Path) -> None:
        """Write YAML to disk, read back, parse to model."""
        from tests.workflows.conftest import write_workflow

        workflow_dir = write_workflow(tmp_path, "roundtrip-test", description="Roundtrip")
        yaml_path = workflow_dir / "WORKFLOW.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        m = WorkflowManifest.model_validate(data)
        assert m.name == "roundtrip-test"


class TestNameValidation:
    """Workflow name must be kebab-case."""

    def test_simple_name(self) -> None:
        m = WorkflowManifest(name="auto-code", description="OK")
        assert m.name == "auto-code"

    def test_single_word(self) -> None:
        m = WorkflowManifest(name="simple", description="OK")
        assert m.name == "simple"

    def test_with_digits(self) -> None:
        m = WorkflowManifest(name="auto-code-2", description="OK")
        assert m.name == "auto-code-2"

    def test_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="MyWorkflow", description="Bad")

    def test_spaces_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="my workflow", description="Bad")

    def test_underscores_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="my_workflow", description="Bad")

    def test_leading_hyphen_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="-leading", description="Bad")

    def test_trailing_hyphen_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="trailing-", description="Bad")

    def test_leading_digit_rejected(self) -> None:
        with pytest.raises(ValidationError, match="kebab-case"):
            WorkflowManifest(name="2auto", description="Bad")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowManifest(name="", description="Bad")


class TestRequiredFields:
    """Name and description are required."""

    def test_name_missing_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowManifest.model_validate({"description": "No name"})

    def test_description_missing_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowManifest.model_validate({"name": "no-desc"})

    def test_both_missing_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowManifest.model_validate({})


class TestPipelineType:
    def test_all_valid_types(self) -> None:
        for pt in PipelineType:
            m = WorkflowManifest(name="test", description="T", pipeline_type=pt)
            assert m.pipeline_type == pt

    def test_string_coercion(self) -> None:
        """String values coerce to enum (FastAPI/Pydantic pattern)."""
        m = WorkflowManifest.model_validate(
            {"name": "test", "description": "T", "pipeline_type": "SEQUENTIAL"}
        )
        assert m.pipeline_type == PipelineType.SEQUENTIAL

    def test_invalid_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowManifest.model_validate(
                {"name": "test", "description": "T", "pipeline_type": "INVALID"}
            )


class TestStageDef:
    def test_minimal_stage(self) -> None:
        s = StageDef(name="build", description="Build stage")
        assert s.agents == []
        assert s.validators == []
        assert s.approval == StageApproval.DIRECTOR
        assert s.completion_criteria == CompletionCondition.ALL_VERIFIED

    def test_stage_with_all_fields(self) -> None:
        s = StageDef(
            name="build",
            description="Build",
            agents=["coder", "reviewer"],
            skills=["code-review"],
            tools=StageToolsDef(add=["web_search"], remove=["bash_exec"]),
            models={"CODE": "anthropic/claude-sonnet-4-6"},
            validators=[
                ValidatorDefinition(
                    name="lint",
                    type=ValidatorType.DETERMINISTIC,
                    schedule=ValidatorSchedule.PER_DELIVERABLE,
                ),
            ],
            completion_criteria=CompletionCondition.ALL_VERIFIED,
            approval=StageApproval.AUTO,
        )
        assert len(s.agents) == 2
        assert len(s.validators) == 1
        assert s.completion_criteria == CompletionCondition.ALL_VERIFIED
        assert "web_search" in s.tools.add
        assert "bash_exec" in s.tools.remove

    def test_stage_tools_defaults(self) -> None:
        s = StageDef(name="test", description="Test")
        assert s.tools.required == []
        assert s.tools.add == []
        assert s.tools.remove == []


class TestValidatorDefinition:
    def test_required_fields(self) -> None:
        v = ValidatorDefinition(
            name="lint_check",
            type=ValidatorType.DETERMINISTIC,
            schedule=ValidatorSchedule.PER_DELIVERABLE,
        )
        assert v.required is True  # default
        assert v.agent == ""  # default
        assert v.config == {}  # default

    def test_advisory_validator(self) -> None:
        v = ValidatorDefinition(
            name="advisory",
            type=ValidatorType.LLM,
            schedule=ValidatorSchedule.PER_STAGE,
            required=False,
        )
        assert v.required is False

    def test_with_config(self) -> None:
        v = ValidatorDefinition(
            name="review",
            type=ValidatorType.DETERMINISTIC,
            schedule=ValidatorSchedule.PER_DELIVERABLE,
            config={"max_cycles": 3},
        )
        assert v.config["max_cycles"] == 3

    def test_with_agent(self) -> None:
        v = ValidatorDefinition(
            name="lint",
            type=ValidatorType.DETERMINISTIC,
            agent="linter",
            schedule=ValidatorSchedule.PER_DELIVERABLE,
        )
        assert v.agent == "linter"


class TestValidatorResult:
    def test_result_defaults(self) -> None:
        r = ValidatorResult(validator_name="lint_check", passed=True)
        assert r.evidence == {}
        assert r.message == ""
        assert r.evaluated_at is not None

    def test_result_with_evidence(self) -> None:
        r = ValidatorResult(
            validator_name="test_suite",
            passed=False,
            evidence={"total": 10, "passed": 8, "failed": 2},
            message="2 tests failed",
        )
        assert r.passed is False
        assert r.evidence["failed"] == 2


class TestCompletionModels:
    def test_completion_criteria_defaults(self) -> None:
        c = CompletionCriteria()
        assert c.deliverables == CompletionCondition.ALL_VERIFIED
        assert c.validators == []
        assert c.approval == StageApproval.DIRECTOR

    def test_verification_layer(self) -> None:
        v = VerificationLayer(name="functional", description="Does it work?", passed=True)
        assert v.passed is True
        assert v.validator_results == []

    def test_completion_report(self) -> None:
        r = CompletionReport(
            scope="stage:build",
            layers=[VerificationLayer(name="functional", passed=True)],
        )
        assert r.scope == "stage:build"
        assert len(r.layers) == 1
        assert r.generated_at is not None

    def test_report_section(self) -> None:
        s = ReportSection(title="code_quality", content="All good")
        assert s.title == "code_quality"


class TestResourceModels:
    def test_resources_defaults(self) -> None:
        r = ResourcesDef()
        assert r.credentials == []
        assert r.services == []
        assert r.knowledge == []

    def test_mcp_server(self) -> None:
        m = McpServerDef(name="test-server")
        assert m.required is False

    def test_mcp_server_explicit_required(self) -> None:
        m = McpServerDef(name="req-server", required=True)
        assert m.required is True

    def test_mcp_server_optional(self) -> None:
        m = McpServerDef(name="opt-server", required=False)
        assert m.required is False


class TestDeliverableTypeDef:
    def test_minimal(self) -> None:
        d = DeliverableTypeDef(name="implementation")
        assert d.description == ""
        assert d.verification == []

    def test_with_verification(self) -> None:
        d = DeliverableTypeDef(
            name="implementation",
            description="Source code",
            verification=["lint_check", "test_suite"],
        )
        assert len(d.verification) == 2


class TestRunConfig:
    def test_minimal(self) -> None:
        r = RunConfig(workflow_name="auto-code")
        assert r.project_id is None
        assert r.specification is None
        assert r.config_overrides == {}

    def test_full(self) -> None:
        r = RunConfig(
            workflow_name="auto-code",
            project_id="proj-123",
            specification="Build a REST API",
            config_overrides={"max_review_cycles": 5},
        )
        assert r.project_id == "proj-123"


class TestWorkflowEntry:
    def test_minimal(self, tmp_path: Path) -> None:
        e = WorkflowEntry(name="test", description="Test", directory=tmp_path / "test")
        assert e.pipeline_type == PipelineType.SINGLE_PASS
        assert e.triggers == []

    def test_with_triggers(self, tmp_path: Path) -> None:
        e = WorkflowEntry(
            name="test",
            description="Test",
            directory=tmp_path / "test",
            triggers=[{"keywords": ["build"]}],
        )
        assert len(e.triggers) == 1


class TestEnumValuesMatchNames:
    """Verify all new enums follow VALUE = NAME convention."""

    @pytest.mark.parametrize(
        "enum_cls",
        [
            PipelineType,
            StageStatus,
            ValidatorType,
            ValidatorSchedule,
            StageApproval,
            CompletionCondition,
        ],
    )
    def test_values_match_names(self, enum_cls: type[enum.StrEnum]) -> None:
        for member in enum_cls:
            assert member.value == member.name, (
                f"{enum_cls.__name__}.{member.name} has value '{member.value}' "
                f"but should be '{member.name}'"
            )


class TestReferenceManifest:
    """Validate the reference manifest example parses into our models."""

    @pytest.fixture
    def reference_manifest(self) -> dict[str, Any]:
        ref_path = (
            Path(__file__).resolve().parent.parent.parent
            / ".dev"
            / "build-phase"
            / "phase-7a"
            / "reference"
            / "workflow-manifest-example.yaml"
        )
        if not ref_path.exists():
            pytest.skip(f"Reference manifest not found: {ref_path}")
        return yaml.safe_load(ref_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def test_reference_parses(self, reference_manifest: dict[str, Any]) -> None:
        """The reference manifest successfully parses into WorkflowManifest."""
        m = WorkflowManifest.model_validate(reference_manifest)
        assert m.name == "auto-code"

    def test_reference_has_5_stages(self, reference_manifest: dict[str, Any]) -> None:
        m = WorkflowManifest.model_validate(reference_manifest)
        assert len(m.stages) == 5
        stage_names = [s.name for s in m.stages]
        assert stage_names == ["shape", "design", "plan", "build", "integrate"]

    def test_reference_validators_unique(self, reference_manifest: dict[str, Any]) -> None:
        m = WorkflowManifest.model_validate(reference_manifest)
        all_names: list[str] = []
        for stage in m.stages:
            for v in stage.validators:
                all_names.append(v.name)
        assert len(all_names) == len(set(all_names))


class TestEditOperationDef:
    """EditOperationDef model — default and explicit values."""

    def test_requires_approval_defaults_false(self) -> None:
        """spec: requires_approval defaults to False (not True)."""
        op = EditOperationDef(name="fix_bug")
        assert op.requires_approval is False

    def test_explicit_requires_approval_true(self) -> None:
        op = EditOperationDef(name="add_feature", requires_approval=True)
        assert op.requires_approval is True

    def test_entry_stage_defaults_empty(self) -> None:
        op = EditOperationDef(name="refactor")
        assert op.entry_stage == ""

    def test_description_defaults_empty(self) -> None:
        op = EditOperationDef(name="remove_feature")
        assert op.description == ""

    def test_all_fields(self) -> None:
        op = EditOperationDef(
            name="add_feature",
            description="Add a new feature",
            entry_stage="shape",
            requires_approval=True,
        )
        assert op.name == "add_feature"
        assert op.description == "Add a new feature"
        assert op.entry_stage == "shape"
        assert op.requires_approval is True

    def test_parsed_from_dict(self) -> None:
        op = EditOperationDef.model_validate(
            {"name": "fix_bug", "entry_stage": "plan", "requires_approval": False}
        )
        assert op.name == "fix_bug"
        assert op.entry_stage == "plan"
        assert op.requires_approval is False

    def test_manifest_with_edit_operations(self) -> None:
        """WorkflowManifest accepts a list of EditOperationDef."""
        m = WorkflowManifest.model_validate(
            {
                "name": "test-workflow",
                "description": "Test",
                "edit_operations": [
                    {"name": "fix_bug", "entry_stage": "plan"},
                    {"name": "add_feature", "requires_approval": True},
                ],
            }
        )
        assert len(m.edit_operations) == 2
        assert m.edit_operations[0].name == "fix_bug"
        assert m.edit_operations[0].requires_approval is False  # default
        assert m.edit_operations[1].name == "add_feature"
        assert m.edit_operations[1].requires_approval is True

    def test_manifest_without_edit_operations_valid(self) -> None:
        """Manifests without edit_operations field are valid; default is empty list."""
        m = WorkflowManifest.model_validate(
            {"name": "minimal-workflow", "description": "No edit ops"}
        )
        assert m.edit_operations == []


class TestAutoCodeWorkflowYaml:
    """Parse the auto-code WORKFLOW.yaml and verify key invariants."""

    @pytest.fixture
    def auto_code_manifest(self) -> WorkflowManifest:
        yaml_path = (
            Path(__file__).resolve().parent.parent.parent
            / "app"
            / "workflows"
            / "auto-code"
            / "WORKFLOW.yaml"
        )
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        return WorkflowManifest.model_validate(data)

    def test_parses_successfully(self, auto_code_manifest: WorkflowManifest) -> None:
        assert auto_code_manifest.name == "auto-code"

    def test_resources_has_credentials(self, auto_code_manifest: WorkflowManifest) -> None:
        assert len(auto_code_manifest.resources.credentials) >= 1

    def test_resources_contains_anthropic_key(self, auto_code_manifest: WorkflowManifest) -> None:
        assert "ANTHROPIC_API_KEY" in auto_code_manifest.resources.credentials

    def test_edit_operations_present(self, auto_code_manifest: WorkflowManifest) -> None:
        assert len(auto_code_manifest.edit_operations) > 0

    def test_fix_bug_edit_operation(self, auto_code_manifest: WorkflowManifest) -> None:
        ops_by_name = {op.name: op for op in auto_code_manifest.edit_operations}
        assert "fix_bug" in ops_by_name
        fix_bug = ops_by_name["fix_bug"]
        assert fix_bug.requires_approval is False
        assert fix_bug.entry_stage == "plan"

    def test_add_feature_requires_approval(self, auto_code_manifest: WorkflowManifest) -> None:
        ops_by_name = {op.name: op for op in auto_code_manifest.edit_operations}
        assert "add_feature" in ops_by_name
        assert ops_by_name["add_feature"].requires_approval is True
