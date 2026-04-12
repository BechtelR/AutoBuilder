"""Phase 7 pre-build validation tests.

Verify that design artifacts are well-formed and existing infrastructure
is ready for the workflow composition build. Run these BEFORE starting
Phase 7 implementation to catch issues early.

Usage:
    uv run pytest tests/workflows/test_phase7_readiness.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_EXAMPLE = ROOT / ".dev" / "build-phase" / "phase-7" / "reference" / "workflow-manifest-example.yaml"
WORKFLOWS_DIR = ROOT / "app" / "workflows"
AGENTS_DIR = ROOT / "app" / "agents"
SKILLS_DIR = ROOT / "app" / "skills"


# ===========================================================================
# 1. Manifest Example Validation
# ===========================================================================


class TestManifestExample:
    """Validate the reference manifest is well-formed and internally consistent."""

    @pytest.fixture(scope="class")
    def manifest(self) -> dict[str, Any]:
        assert MANIFEST_EXAMPLE.exists(), f"Manifest example not found: {MANIFEST_EXAMPLE}"
        content = MANIFEST_EXAMPLE.read_text(encoding="utf-8")
        data: dict[str, Any] = yaml.safe_load(content)
        assert isinstance(data, dict)
        return data

    def test_required_fields_present(self, manifest: dict[str, Any]) -> None:
        assert "name" in manifest
        assert "description" in manifest
        assert isinstance(manifest["name"], str)
        assert isinstance(manifest["description"], str)

    def test_name_is_kebab_case(self, manifest: dict[str, Any]) -> None:
        name = str(manifest["name"])
        assert name == name.lower(), f"Name must be lowercase: {name}"
        assert " " not in name, f"Name must not contain spaces: {name}"
        # Kebab-case: only lowercase letters, digits, and hyphens
        assert all(c.isalnum() or c == "-" for c in name), f"Name must be kebab-case: {name}"

    def test_pipeline_type_valid(self, manifest: dict[str, Any]) -> None:
        valid_types = {"single_pass", "sequential", "batch_parallel"}
        pipeline_type = manifest.get("pipeline_type", "single_pass")
        assert pipeline_type in valid_types, f"Invalid pipeline_type: {pipeline_type}"

    def test_stages_have_unique_names(self, manifest: dict[str, Any]) -> None:
        stages: list[dict[str, Any]] = manifest.get("stages", [])
        names: list[str] = [s["name"] for s in stages]
        assert len(names) == len(set(names)), f"Duplicate stage names: {names}"

    def test_stages_have_required_fields(self, manifest: dict[str, Any]) -> None:
        stages = manifest.get("stages", [])
        for stage in stages:
            assert "name" in stage, f"Stage missing 'name': {stage}"
            assert "description" in stage, f"Stage missing 'description': {stage}"

    def test_validator_names_unique_across_manifest(self, manifest: dict[str, Any]) -> None:
        names: list[str] = []
        for stage in manifest.get("stages", []):
            for v in stage.get("validators", []):
                names.append(v["name"])
        assert len(names) == len(set(names)), f"Duplicate validator names: {names}"

    def test_validator_types_valid(self, manifest: dict[str, Any]) -> None:
        valid_types = {"deterministic", "llm", "approval"}
        for stage in manifest.get("stages", []):
            for v in stage.get("validators", []):
                assert v["type"] in valid_types, f"Invalid validator type '{v['type']}' on {v['name']}"

    def test_validator_schedules_valid(self, manifest: dict[str, Any]) -> None:
        valid_schedules = {"per_deliverable", "per_batch", "per_taskgroup", "per_stage"}
        for stage in manifest.get("stages", []):
            for v in stage.get("validators", []):
                assert v["schedule"] in valid_schedules, f"Invalid schedule '{v['schedule']}' on {v['name']}"

    def test_approval_values_valid(self, manifest: dict[str, Any]) -> None:
        valid_approvals = {"director", "ceo", "auto"}
        for stage in manifest.get("stages", []):
            approval = stage.get("approval")
            if approval is not None:
                assert approval in valid_approvals, f"Invalid approval '{approval}' on stage {stage['name']}"

    def test_required_tools_are_strings(self, manifest: dict[str, Any]) -> None:
        tools: list[Any] = manifest.get("required_tools", [])
        assert isinstance(tools, list)
        for t in tools:
            assert isinstance(t, str), f"Tool must be string: {t}"

    def test_default_models_have_valid_roles(self, manifest: dict[str, Any]) -> None:
        valid_roles = {"PLAN", "CODE", "REVIEW", "FAST"}
        models = manifest.get("default_models", {})
        for role in models:
            assert role in valid_roles, f"Invalid model role: {role}"

    def test_deliverable_types_reference_declared_validators(self, manifest: dict[str, Any]) -> None:
        """Every validator referenced in deliverable.types[].verification must exist."""
        all_validators: set[str] = set()
        for stage in manifest.get("stages", []):
            for v in stage.get("validators", []):
                all_validators.add(v["name"])

        deliverable = manifest.get("deliverable", {})
        for dtype in deliverable.get("types", []):
            for vname in dtype.get("verification", []):
                assert vname in all_validators, (
                    f"Deliverable type '{dtype['name']}' references undeclared validator '{vname}'. "
                    f"Declared: {sorted(all_validators)}"
                )

    def test_triggers_not_too_broad(self, manifest: dict[str, Any]) -> None:
        """Trigger keywords should not contain overly generic words."""
        too_broad = {"create", "make", "do", "run", "start", "go"}
        for trigger in manifest.get("triggers", []):
            keywords = trigger.get("keywords", [])
            overlap = set(keywords) & too_broad
            assert not overlap, f"Trigger keywords too broad: {overlap}"

    def test_completion_report_layers_have_names(self, manifest: dict[str, Any]) -> None:
        report = manifest.get("completion_report", {})
        for layer in report.get("layers", []):
            assert "name" in layer, f"Completion report layer missing 'name': {layer}"

    def test_resources_credentials_listed(self, manifest: dict[str, Any]) -> None:
        """Production workflow should declare required credentials."""
        resources = manifest.get("resources", {})
        credentials = resources.get("credentials", [])
        assert len(credentials) > 0, "Production manifest should declare at least one credential"

    def test_auto_code_has_5_stages(self, manifest: dict[str, Any]) -> None:
        stages = manifest.get("stages", [])
        assert len(stages) == 5, f"auto-code should have 5 stages, got {len(stages)}"
        names = [s["name"] for s in stages]
        assert names == ["shape", "design", "plan", "build", "integrate"]


# ===========================================================================
# 2. Workflow Directory Structure
# ===========================================================================


class TestWorkflowDirectoryStructure:
    """Verify the workflow directories are ready for Phase 7."""

    def test_workflows_dir_exists(self) -> None:
        assert WORKFLOWS_DIR.exists(), f"Missing: {WORKFLOWS_DIR}"

    def test_auto_code_dir_exists(self) -> None:
        assert (WORKFLOWS_DIR / "auto-code").exists(), "Missing: app/workflows/auto-code/"

    def test_auto_code_has_no_pipeline_yet(self) -> None:
        """Pipeline.py does not exist yet — Phase 7 creates it."""
        pipeline = WORKFLOWS_DIR / "auto-code" / "pipeline.py"
        assert not pipeline.exists(), (
            f"auto-code/pipeline.py already exists at {pipeline}. "
            "Phase 7 should create this file."
        )


# ===========================================================================
# 3. Existing Infrastructure Readiness
# ===========================================================================


class TestInfrastructureReadiness:
    """Verify Phase 5/6 infrastructure that Phase 7 builds on is intact."""

    def test_agent_registry_importable(self) -> None:
        from app.agents._registry import AgentRegistry
        assert AgentRegistry is not None

    def test_agent_registry_has_build(self) -> None:
        from app.agents._registry import AgentRegistry
        assert hasattr(AgentRegistry, "build")
        assert hasattr(AgentRegistry, "scan")

    def test_definition_scope_has_workflow(self) -> None:
        from app.models.enums import DefinitionScope
        assert hasattr(DefinitionScope, "WORKFLOW")

    def test_skill_library_importable(self) -> None:
        from app.skills.library import SkillLibrary
        assert SkillLibrary is not None

    def test_skill_library_has_scan_and_match(self) -> None:
        from app.skills.library import SkillLibrary
        assert hasattr(SkillLibrary, "scan")
        assert hasattr(SkillLibrary, "match")

    def test_instruction_context_importable(self) -> None:
        from app.agents.assembler import InstructionContext
        assert InstructionContext is not None

    def test_existing_pipeline_exists(self) -> None:
        """The old pipeline.py exists (Phase 7 will migrate it)."""
        pipeline = AGENTS_DIR / "pipeline.py"
        assert pipeline.exists(), "app/agents/pipeline.py should exist (Phase 7 migrates it)"

    def test_existing_pipeline_has_stage_names(self) -> None:
        from app.agents.pipeline import PIPELINE_STAGE_NAMES
        assert isinstance(PIPELINE_STAGE_NAMES, list)
        assert len(PIPELINE_STAGE_NAMES) > 0

    def test_review_cycle_agent_exists(self) -> None:
        from app.agents.custom.review_cycle import ReviewCycleAgent
        assert ReviewCycleAgent is not None

    def test_context_recreation_importable(self) -> None:
        from app.agents.context_recreation import recreate_context
        assert recreate_context is not None

    def test_gateway_settings_importable(self) -> None:
        from app.config.settings import Settings
        assert Settings is not None


# ===========================================================================
# 4. Enum Readiness (Phase 7 will add new enums)
# ===========================================================================


class TestEnumReadiness:
    """Verify existing enums are compatible with Phase 7 additions."""

    def test_enums_follow_value_equals_name(self) -> None:
        """All existing enums follow VALUE = 'VALUE' convention."""
        from app.models import enums

        for name in dir(enums):
            obj = getattr(enums, name)
            if isinstance(obj, type) and issubclass(obj, enums.enum.StrEnum) and obj is not enums.enum.StrEnum:
                for member in obj:
                    assert member.value == member.name, (
                        f"{name}.{member.name} has value '{member.value}' "
                        f"but should be '{member.name}'"
                    )

    def test_no_pipeline_type_enum_yet(self) -> None:
        """PipelineType enum does not exist yet — Phase 7 creates it."""
        from app.models import enums
        assert not hasattr(enums, "PipelineType"), "PipelineType already exists — Phase 7 should create it"

    def test_no_stage_status_enum_yet(self) -> None:
        from app.models import enums
        assert not hasattr(enums, "StageStatus"), "StageStatus already exists — Phase 7 should create it"

    def test_no_validator_type_enum_yet(self) -> None:
        from app.models import enums
        assert not hasattr(enums, "ValidatorType"), "ValidatorType already exists — Phase 7 should create it"


# ===========================================================================
# 5. Agent Definitions Readiness
# ===========================================================================


class TestAgentDefinitionsReadiness:
    """Verify global agent definitions exist for agents referenced in auto-code manifest."""

    EXPECTED_AGENTS = [
        "planner",
        "coder",
        "reviewer",
        "fixer",
        "formatter",
        "linter",
        "tester",
        "diagnostics",
    ]

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_global_agent_definition_exists(self, agent_name: str) -> None:
        agent_file = AGENTS_DIR / f"{agent_name}.md"
        assert agent_file.exists(), f"Missing global agent definition: {agent_file}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_definition_has_frontmatter(self, agent_name: str) -> None:
        agent_file = AGENTS_DIR / f"{agent_name}.md"
        content = agent_file.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{agent_file} must start with YAML frontmatter delimiter"
        # Find closing delimiter
        second_delim = content.index("---", 3)
        frontmatter_str = content[3:second_delim].strip()
        frontmatter = yaml.safe_load(frontmatter_str)
        assert isinstance(frontmatter, dict)
        assert "name" in frontmatter, f"{agent_file} frontmatter missing 'name'"


# ===========================================================================
# 6. Skills Readiness
# ===========================================================================


class TestSkillsReadiness:
    """Verify skill infrastructure is ready for three-tier merge."""

    def test_global_skills_dir_exists(self) -> None:
        assert SKILLS_DIR.exists()

    def test_global_skills_not_empty(self) -> None:
        skills = list(SKILLS_DIR.rglob("SKILL.md"))
        assert len(skills) > 0, "No global skills found"

    def test_skill_library_constructor_signature(self) -> None:
        """SkillLibrary.__init__ currently takes global_dir and project_dir.
        Phase 7 adds workflow_dir parameter."""
        import inspect

        from app.skills.library import SkillLibrary

        sig = inspect.signature(SkillLibrary.__init__)
        params = list(sig.parameters.keys())
        assert "global_dir" in params
        assert "project_dir" in params
        # workflow_dir should NOT exist yet — Phase 7 adds it
        assert "workflow_dir" not in params, "workflow_dir already exists — Phase 7 should add it"
