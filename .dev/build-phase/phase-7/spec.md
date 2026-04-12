# Phase 7 Spec: Workflow Composition
*Generated: 2026-04-11*

## Overview

Phase 7 delivers the pluggable workflow architecture that makes AutoBuilder a multi-workflow platform rather than a hardcoded code generation system. Before this phase, there is exactly one implicit pipeline (the DeliverablePipeline from Phase 5a) with no formal workflow abstraction, no stage schema, no declarative quality gates, and no mechanism for adding new workflow types. After this phase, workflows are self-contained discoverable units with manifests, stage schemas, validators, and completion reports.

The system introduces WORKFLOW.yaml manifests with progressive disclosure (a valid manifest requires only `name` and `description`; everything else has sensible defaults). The WorkflowRegistry discovers workflows from two tiers: built-in (`app/workflows/`) and user-level (`~/.autobuilder/workflows/`, configurable via `AUTOBUILDER_WORKFLOWS_DIR`). User-level workflows override built-in by name. Stage schemas provide organizational structure within PM sessions — stages are PM-driven transitions following a K8s reconciliation pattern, not separate execution contexts.

Standard validators form an evidence collection framework that evaluates existing agent output and records machine-generated evidence for three-layer completion reports (functional correctness, architectural conformance, contract completion). Validators are manifest-declared quality gates that cannot be skipped by agent judgment. The auto-code workflow ships as the first concrete implementation with a 5-stage schema (SHAPE → DESIGN → PLAN → BUILD → INTEGRATE).

## Pre-Build Validation

Run before starting implementation. All 53 tests must pass:

```bash
uv run pytest tests/workflows/test_phase7_readiness.py -v
```

Validates: manifest example well-formed, workflow directories ready, prerequisite infrastructure intact (AgentRegistry, SkillLibrary, pipeline.py, agent definitions, enums, skills).

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 6: Skills System | MET | SkillLibrary operational, 17 global skills indexed, `applies_to` filtering, skill cache invalidation. All BOM complete. |
| Phase 5b: Supervision & Integration | MET | Director/PM supervision hierarchy operational, CEO queue live, state key authorization enforced, context recreation, PM sequential loop. |
| Phase 5a: Agent Definitions & Pipeline | MET | AgentRegistry with 3-scope cascade, InstructionAssembler, DeliverablePipeline, all agents defined. |

## Design Decisions

### DD-1: WorkflowRegistry File Placement

Infrastructure files (`registry.py`, `models.py`, `validators.py`, `stages.py`) live alongside workflow subdirectories in `app/workflows/`. This mirrors the `app/skills/` pattern where `library.py`, `parser.py`, `matchers.py` coexist with skill category directories. The `__init__.py` re-exports public types.

### DD-2: Validators as Evidence Collection, Not New Agents

Standard validators are NOT new CustomAgent classes duplicating existing work. They are an evidence collection framework:

1. **Wrappers around existing agents**: `lint_check` evaluates `lint_results` state key (produced by LinterAgent). `test_suite` evaluates `test_results` (TestRunnerAgent). `code_review` evaluates `review_passed` (ReviewCycleAgent). `regression_tests` evaluates `regression_results` (RegressionTestAgent).
2. **Deterministic functions**: `dependency_validation` and `deliverable_status_check` are pure functions querying state/DB — no agent invocation needed.
3. **Evidence recording**: Each validator evaluation produces a `ValidatorResult` record with pass/fail status and structured evidence.

The existing agents do the work. The validator framework evaluates their output and records evidence for completion reports. This avoids creating 6+ redundant CustomAgent subclasses that merely read state keys.

```python
class ValidatorRunner:
    """Evaluates validator definitions against pipeline state."""

    def evaluate(self, validator: ValidatorDefinition, state: dict, session: AsyncSession) -> ValidatorResult:
        """Dispatch to the appropriate evaluation strategy."""

    def evaluate_batch(self, validators: list[ValidatorDefinition], schedule: ValidatorSchedule, ...) -> list[ValidatorResult]:
        """Evaluate all validators matching a given schedule."""
```

### DD-3: Stage Reconfiguration Is State-Driven

When PM advances a stage, it calls `reconfigure_stage` which updates state keys (`pm:current_stage`, `pm:stage_index`, `pm:stage_status`). The pipeline reads current stage config from the manifest via state — no agent tree rebuild, no session recreation. This follows the K8s reconciliation pattern: PM observes state, compares to completion criteria, and acts.

Stage state keys are all `pm:` prefixed per Decision #58 (tier-based state key authorization):

```
pm:current_stage          # string: active stage name
pm:stage_index            # int: 0-based index
pm:stage_status           # StageStatus string value (e.g., "PENDING", "ACTIVE", "COMPLETED", "FAILED")
pm:stages_completed       # list[string]: completed stage names
pm:workflow_stages        # list[dict]: full stage schema from manifest
```

### DD-4: Pipeline.py Interface Contract

Every workflow's `pipeline.py` must export a `create_pipeline` function conforming to the `PipelineFactory` Protocol:

```python
class PipelineFactory(Protocol):
    """Interface for workflow pipeline composition functions."""
    async def __call__(self, ctx: PipelineContext) -> BaseAgent: ...
```

`PipelineContext` is a frozen dataclass bundling all shared infrastructure:

```python
@dataclass(frozen=True)
class PipelineContext:
    registry: AgentRegistry
    instruction_ctx: InstructionContext
    manifest: WorkflowManifest
    skill_library: SkillLibrary
    toolset: GlobalToolset
    before_model_callback: BeforeModelCallback | None = None

    @classmethod
    def build(cls, ...) -> PipelineContext:
        """Convenience constructor from gateway dependencies."""
```

The `PipelineFactory` Protocol enables static type checking for built-in workflows and runtime validation for user-level workflows. The `WorkflowRegistry` validates dynamically imported `create_pipeline` functions against this Protocol at import time — signature mismatches raise `ConfigurationError` immediately, not at first invocation.

Three standard pipeline pattern functions conforming to `PipelineFactory` are provided: `single_pass_pipeline()`, `sequential_pipeline()`, `batch_parallel_pipeline()`. Custom `pipeline.py` modules can use these patterns or compose their own agent trees.

For auto-code, `app/workflows/auto-code/pipeline.py` exports `create_pipeline(ctx: PipelineContext)` — this is the migrated and rewritten `app/agents/pipeline.py`, which is deleted.

### DD-5: Three-Tier Skill Merge Mechanism

Skills merge in three tiers for workflow-aware projects: global (`app/skills/`) → workflow (`app/workflows/{name}/skills/`) → project (`.agents/skills/`). This extends the existing two-tier override. The SkillLibrary's `scan()` method gains an optional `workflow_dir` parameter for the middle tier. Override semantics remain: same-name skill in higher tier replaces lower tier entirely.

### DD-6: Completion Report Structure

Completion reports assemble evidence from validator results into configurable layers. If `layers` is omitted from the manifest's `completion_report`, default layers apply. Workflows add domain-specific sections via `additional_sections`.

```python
class CompletionReport(BaseModel):
    """Verification report with configurable layers (PR-22)."""
    scope: str                           # "stage:build" or "taskgroup:2"
    layers: list[VerificationLayer]      # Default: functional, architectural, contract
    additional_sections: list[ReportSection]
    generated_at: datetime

DEFAULT_VERIFICATION_LAYERS: list[str] = ["functional", "architectural", "contract"]
```

### DD-7: AUTOBUILDER_WORKFLOWS_DIR Default

The user-level workflows directory defaults to `~/.autobuilder/workflows/`. This is configurable via `AUTOBUILDER_WORKFLOWS_DIR` environment variable. If the directory doesn't exist, the registry operates with built-in workflows only (no error).

## Deliverables

### P7.D1: Workflow Enums and Pydantic Models
**Files:** `app/models/enums.py`, `app/workflows/__init__.py`, `app/workflows/models.py`
**Depends on:** —
**Description:** Define all foundation types for the workflow composition system. Add new enums to the canonical enum location. Create the Pydantic model hierarchy for WORKFLOW.yaml manifests with progressive disclosure (all optional fields have defaults). Models cover: manifest root fields, trigger definitions, stage definitions, validator definitions, completion criteria, completion reports, resource definitions, run configuration, and workflow entry (lightweight index record).
**BOM Components:**
- [ ] `F06` — `WorkflowEntry` Pydantic model
- [ ] `F07` — `WORKFLOW.yaml` manifest schema (progressive disclosure)
- [ ] `F11` — `RunConfig` model
- [ ] `F19` — `WorkflowManifest` Pydantic model (all fields)
- [ ] `F22` — `StageDef` Pydantic model
- [ ] `F23` — `CompletionCriteria` Pydantic model
- [ ] `F24` — `ValidatorDefinition` Pydantic model
- [ ] `F38` — `CompletionReport` Pydantic model
- [ ] `F39` — `StageStatus` enum
- [ ] `F40` — `ValidatorType` enum
- [ ] `F41` — `ValidatorSchedule` enum
- [ ] `F43` — `ResourcesDef` validation (credentials, services, knowledge)
- [ ] `F58` — `PipelineContext` frozen dataclass
- [ ] `F58b` — `PipelineFactory` Protocol
- [ ] `F59` — `McpServerDef` Pydantic model
**Requirements:**
- [ ] `PipelineType` enum in `app/models/enums.py` with values: `SINGLE_PASS`, `SEQUENTIAL`, `BATCH_PARALLEL`
- [ ] `StageStatus` enum with values: `PENDING`, `ACTIVE`, `COMPLETED`, `FAILED`
- [ ] `ValidatorType` enum with values: `DETERMINISTIC`, `LLM`, `APPROVAL`
- [ ] `ValidatorSchedule` enum with values: `PER_DELIVERABLE`, `PER_BATCH`, `PER_TASKGROUP`, `PER_STAGE`
- [ ] `WorkflowManifest` is a Pydantic `BaseModel` with only `name` (str) and `description` (str) required; all other fields have defaults
- [ ] A manifest with only `name` and `description` validates successfully (progressive disclosure tier 1)
- [ ] `StageToolsDef` model has: `required` (list[str], default []), `add` (list[str], default []), `remove` (list[str], default []) — tool scoping relative to workflow baseline
- [ ] `StageDef` model has: `name` (required), `description`, `agents`, `skills`, `tools` (StageToolsDef), `models`, `validators`, `completion_criteria`, `approval`
- [ ] `CompletionCriteria` model has: `deliverables` (str, default `"all_verified"`), `validators` (list[str], default []), `approval` (str, default `"director"`) — three types compose via AND. Note: `CompletionCriteria` is the runtime evaluation model constructed from `StageDef.completion_criteria` + `StageDef.validators` + `StageDef.approval`.
- [ ] `ValidatorDefinition` model has: `name` (required), `type` (required), `agent`, `schedule` (required), `config`, `required` (default True)
- [ ] `CompletionLayerDef` model has: `name` (str, required), `description` (str), `evidence_sources` (list[str], default []) — manifest-side layer declaration (what to measure)
- [ ] `VerificationLayer` model has: `name` (str), `description` (str), `passed` (bool), `validator_results` (list of ValidatorResult references), `summary` (str) — runtime result (what was measured)
- [ ] `ReportSection` model has: `title` (str), `content` (str), `metadata` (dict[str, object], default {})
- [ ] `CompletionReport` model has `layers: list[VerificationLayer]` plus `additional_sections` (list[ReportSection]). A `DEFAULT_VERIFICATION_LAYERS` constant provides the three standard layers (functional, architectural, contract) used when manifest omits `layers`.
- [ ] `ResourcesDef` model has: `credentials` (list of env var names), `services` (list with health_check URLs), `knowledge` (list of file/directory paths)
- [ ] `McpServerDef` model has: `name` (str, required), `required` (bool, default False)
- [ ] `WorkflowManifest` includes `mcp_servers: list[McpServerDef]` field with default `[]`
- [ ] `WorkflowEntry` is a lightweight index model with: `name`, `description`, `path`, `pipeline_type`, `triggers`
- [ ] `RunConfig` model has: `workflow_name`, `project_id`, `specification`, `config_overrides`
- [ ] `PipelineFactory` Protocol with `async def __call__(self, ctx: PipelineContext) -> BaseAgent` — the interface contract for all workflow `create_pipeline` functions
- [ ] `PipelineContext` frozen dataclass with: `registry` (AgentRegistry), `instruction_ctx` (InstructionContext), `manifest` (WorkflowManifest), `skill_library` (SkillLibrary), `toolset` (GlobalToolset), `before_model_callback` (optional). Convenience `build()` classmethod.
- [ ] Pipeline pattern functions conforming to `PipelineFactory`: `single_pass_pipeline(ctx: PipelineContext) -> BaseAgent`, `sequential_pipeline(ctx: PipelineContext) -> BaseAgent`, `batch_parallel_pipeline(ctx: PipelineContext) -> BaseAgent`
- [ ] All enums use `StrEnum` with `VALUE = "VALUE"` convention per engineering standards
- [ ] All models pass pyright strict
- [ ] `app/workflows/__init__.py` re-exports public types
**Validation:**
- `uv run pyright app/workflows/models.py app/models/enums.py`
- `uv run pytest tests/workflows/test_models.py -v`

---

### P7.D2: WorkflowRegistry and Manifest Validation
**Files:** `app/workflows/registry.py`
**Depends on:** P7.D1
**Description:** Implement the WorkflowRegistry class: two-tier directory scanning (built-in + user-level), WORKFLOW.yaml parsing with progressive disclosure validation, deterministic trigger matching (keywords + explicit), ambiguity resolution, manifest retrieval, pipeline instantiation via dynamic `pipeline.py` import, and optional Redis caching. The registry follows the SkillLibrary scan-and-index pattern.
**BOM Components:**
- [ ] `F01` — `WorkflowRegistry` class
- [ ] `F02` — `WorkflowRegistry.match()` (keyword matching)
- [ ] `F03` — `WorkflowRegistry.get()` (explicit lookup)
- [ ] `F04` — `WorkflowRegistry.list_available()`
- [ ] `F05` — `WorkflowRegistry.create_pipeline()`
- [ ] `F08` — Workflow trigger matching (keywords)
- [ ] `F09` — Workflow trigger matching (explicit)
- [ ] `F10` — Workflow ambiguity resolution (user prompt)
- [ ] `F12` — User-level workflow directory (override by name)
- [ ] `F18` — `pipeline.py` interface contract (function signature)
- [ ] `F20` — `WorkflowRegistry.get_manifest()`
- [ ] `F21` — Manifest validation (L1 schema, required/warning/cross-ref)
- [ ] `M24` — Workflow registry cache (long TTL)
**Requirements:**
- [ ] `WorkflowRegistry.__init__(workflows_dir: Path, user_workflows_dir: Path | None = None, redis: ArqRedis | None = None)` stores configuration, does not scan on init
- [ ] `scan()` recursively finds all `WORKFLOW.yaml` files in configured directories, parses and validates manifests, builds `_workflows: dict[str, WorkflowEntry]` index
- [ ] Scan order: built-in directory first, then user-level directory. User-level entries replace built-in entries with same name
- [ ] `match(user_request: str) -> list[WorkflowEntry]` performs deterministic keyword matching against workflow triggers; returns matching entries sorted by specificity (explicit > keyword)
- [ ] Explicit trigger match takes precedence over keyword match
- [ ] When multiple workflows match via keywords, returns all matches (caller/PM resolves ambiguity)
- [ ] `get(name: str) -> WorkflowEntry` returns workflow by explicit name; raises `NotFoundError` if not found
- [ ] `get_manifest(name: str) -> WorkflowManifest` returns full parsed manifest for PM/Director consumption
- [ ] `list_available() -> list[WorkflowEntry]` returns all discovered workflows with descriptions
- [ ] `create_pipeline(workflow_name: str, pipeline_ctx: PipelineContext) -> BaseAgent` dynamically imports `pipeline.py` from workflow directory and calls its `create_pipeline(ctx)` function
- [ ] `pipeline.py` must export an async `create_pipeline(ctx: PipelineContext) -> BaseAgent` function matching the interface contract (DD-4)
- [ ] Missing `pipeline.py` → `NotFoundError` with clear message
- [ ] Invalid `pipeline.py` (import error, missing function) → `ConfigurationError` with clear message
- [ ] Manifest validation: required fields present (`name`, `description`), `name` is kebab-case, `pipeline_type` valid if present, stage names unique, validator names unique across manifest
- [ ] Validation warnings (non-blocking, logged): stages defined but `pipeline_type` is `single_pass`, validator references agents not in stage agent lists
- [ ] No user-level directory configured → operates with built-in workflows only, no error
- [ ] User-level directory doesn't exist → operates with built-in only, no error
- [ ] Redis cache: `save_to_cache()` and `load_from_cache()` serialize/deserialize the index. Cache unavailable → filesystem scan, no error
- [ ] All methods pass pyright strict
**Validation:**
- `uv run pyright app/workflows/registry.py`
- `uv run pytest tests/workflows/test_registry.py -v`

---

### P7.D3: Stage System and Completion Gates
**Files:** `app/workflows/stages.py`, `app/tools/management.py`
**Depends on:** P7.D1
**Description:** Implement stage lifecycle management: state key initialization from manifest, the `reconfigure_stage` FunctionTool for PM-driven stage transitions, `verify_stage_completion` and `verify_taskgroup_completion` deterministic hard gates, and stage lifecycle event types. Stage transitions are state-driven — the PM calls `reconfigure_stage` which updates `pm:current_stage` and related state keys. No agent tree rebuild.
**BOM Components:**
- [ ] `F25` — Stage state keys (`pm:current_stage`, `pm:stage_*`)
- [ ] `F26` — `reconfigure_stage` FunctionTool
- [ ] `F27` — `verify_stage_completion` deterministic gate
- [ ] `F28` — `verify_taskgroup_completion` deterministic gate
- [ ] `F42` — Stage lifecycle events (STAGE_STARTED, STAGE_COMPLETED, etc.)
**Requirements:**
- [ ] `initialize_stage_state(manifest: WorkflowManifest) -> dict[str, object]` returns initial state delta: `pm:current_stage` = first stage name (or empty string if no stages), `pm:stage_index` = 0, `pm:stage_status` = PENDING, `pm:stages_completed` = [], `pm:workflow_stages` = serialized stage schema
- [ ] `reconfigure_stage` FunctionTool accepts `target_stage: str` parameter. Validates target is a valid stage name in the manifest. Updates `pm:current_stage`, `pm:stage_index`, `pm:stage_status` to ACTIVE. Appends previous stage to `pm:stages_completed`. Returns confirmation string.
- [ ] `reconfigure_stage` rejects advancing to a stage that's already completed (no backwards movement)
- [ ] `reconfigure_stage` rejects skipping stages (must advance sequentially)
- [ ] `verify_stage_completion(state: dict, manifest: WorkflowManifest, validator_results: list[ValidatorResult]) -> tuple[bool, list[str]]` checks: all deliverables at required status, all required stage validators passed, approval obtained if required. Returns (passed, list_of_failure_reasons)
- [ ] `verify_taskgroup_completion(state: dict, manifest: WorkflowManifest, validator_results: list[ValidatorResult]) -> tuple[bool, list[str]]` checks: all deliverables within the TaskGroup complete, no pending escalations, all scheduled validators passing. This is a hard gate PM cannot override.
- [ ] `PipelineEventType` enum extended with: `STAGE_STARTED`, `STAGE_COMPLETED`, `STAGE_FAILED`, `VALIDATOR_COMPLETED`
- [ ] Stage state keys are all `pm:` prefixed per Decision #58
- [ ] Stages with `approval: auto`: when `verify_stage_completion()` returns True, `reconfigure_stage` is called automatically (no PM reasoning needed). PM reasoning is only involved for `approval: director` or `approval: ceo` stages.
- [ ] Workflows without stages (empty `stages` list): `reconfigure_stage` is a no-op, `verify_stage_completion` always returns True
- [ ] All functions pass pyright strict
**Validation:**
- `uv run pyright app/workflows/stages.py app/tools/management.py`
- `uv run pytest tests/workflows/test_stages.py -v`

---

### P7.D4: Validator Framework and Standard Validators
**Files:** `app/workflows/validators.py`
**Depends on:** P7.D1, P7.D3
**Description:** Implement the validator framework as an evidence collection system. The `ValidatorRunner` dispatches validator definitions to evaluation strategies: deterministic validators check state keys or query DB; LLM validators check state keys produced by LLM agents; approval validators check approval state. Six standard validators ship: `lint_check`, `test_suite`, `regression_tests`, `code_review` (all evaluate existing agent output state keys), plus `dependency_validation` and `deliverable_status_check` (pure deterministic functions).
**BOM Components:**
- [ ] `F32` — Standard validator: `lint_check`
- [ ] `F33` — Standard validator: `test_suite`
- [ ] `F34` — Standard validator: `regression_tests`
- [ ] `F35` — Standard validator: `code_review`
- [ ] `F36` — Standard validator: `dependency_validation`
- [ ] `F37` — Standard validator: `deliverable_status_check`
**Requirements:**
- [ ] `ValidatorRunner` class with `evaluate(validator: ValidatorDefinition, state: dict[str, object], session: AsyncSession | None = None) -> ValidatorResult` method
- [ ] `ValidatorRunner.evaluate_batch(validators: list[ValidatorDefinition], schedule: ValidatorSchedule, state: dict, session: AsyncSession | None = None) -> list[ValidatorResult]` evaluates all validators matching the given schedule
- [ ] `lint_check` validator: reads `lint_results` from state, passes if no errors reported. Evidence includes error count and details.
- [ ] `test_suite` validator: reads `test_results` from state, passes if all tests pass. Evidence includes pass/fail counts.
- [ ] `regression_tests` validator: reads `regression_results` from state, passes if all regression tests pass. Evidence includes test names and results.
- [ ] `code_review` validator: reads `review_passed` from state, passes if True. Evidence includes review cycle count and final reviewer comments.
- [ ] `dependency_validation` validator: deterministic check on deliverable dependency graph. Passes if graph is acyclic and all dependencies are valid. Evidence includes dependency graph summary.
- [ ] `deliverable_status_check` validator: queries deliverable statuses. Passes if all deliverables at required status (default: COMPLETED). Evidence includes per-deliverable status list.
- [ ] `ValidatorResult` Pydantic model (DTO, distinct from F31 DB table) has: `validator_name`, `passed` (bool), `evidence` (dict[str, object]), `message` (str), `evaluated_at` (datetime)
- [ ] Validators with `required: false` in definition produce results but don't block completion
- [ ] Missing state key (agent hasn't run yet) → validator returns `passed=False` with clear message
- [ ] `generate_completion_report(scope: str, manifest: WorkflowManifest, validator_results: list[ValidatorResult]) -> CompletionReport` assembles validator results into a CompletionReport with verification layers. Uses manifest's `completion_report.layers` if declared, otherwise `DEFAULT_VERIFICATION_LAYERS`. Maps validator results to layers via `evidence_sources` name references.
- [ ] Completion report layers derive pass/fail from referenced validator results (aggregation, not re-evaluation)
- [ ] All functions pass pyright strict
**Validation:**
- `uv run pyright app/workflows/validators.py`
- `uv run pytest tests/workflows/test_validators.py -v`

---

### P7.D5: Database Tables and Migration
**Files:** `app/db/models.py`, `app/db/migrations/versions/NNN_workflow_composition.py`
**Depends on:** P7.D1
**Description:** Add three database tables for workflow composition tracking: `StageExecution` (stage lifecycle within a workflow), `TaskGroupExecution` (PM TaskGroup tracking within stages), and `ValidatorResult` (validator evidence persistence). Create the Alembic migration with sequential numbering.
**BOM Components:**
- [ ] `F29` — `StageExecution` DB table
- [ ] `F30` — `TaskGroupExecution` DB table
- [ ] `F31` — `ValidatorResult` DB table
**Requirements:**
- [ ] `StageExecution` table: `id` (UUID PK), `workflow_id` (UUID FK to `workflows`), `stage_name` (str, indexed), `stage_index` (int), `status` (StageStatus), `started_at` (DateTime), `completed_at` (DateTime nullable), `completion_report` (JSONB nullable). Inherits `TimestampMixin`.
- [ ] `TaskGroupExecution` table: `id` (UUID PK), `stage_execution_id` (UUID FK to `stage_executions`), `taskgroup_number` (int), `status` (str), `started_at` (DateTime), `completed_at` (DateTime nullable), `deliverable_count` (int). Inherits `TimestampMixin`.
- [ ] `ValidatorResult` table: `id` (UUID PK), `workflow_id` (UUID FK to `workflows`), `stage_execution_id` (UUID FK to `stage_executions`, nullable), `validator_name` (str, indexed), `passed` (bool), `evidence` (JSONB), `message` (str nullable), `evaluated_at` (DateTime). Inherits `TimestampMixin`.
- [ ] Migration uses sequential numbering: next available `NNN` after existing migrations
- [ ] Migration is idempotent (uses `if not exists` pattern or Alembic defaults)
- [ ] All models have appropriate indexes: `workflow_id` on all three tables, `stage_name` on StageExecution, `validator_name` on ValidatorResult
- [ ] Foreign key relationships properly defined with SQLAlchemy `relationship()` where appropriate
- [ ] `uv run alembic upgrade head` applies without error on a clean database
**Validation:**
- `uv run pyright app/db/models.py`
- `uv run alembic upgrade head`
- `uv run pytest tests/db/ -v`

---

### P7.D6: auto-code Workflow
**Files:** `app/workflows/auto-code/WORKFLOW.yaml`, `app/workflows/auto-code/pipeline.py`, `app/workflows/auto-code/agents/planner.md`, `app/workflows/auto-code/agents/coder.md`, `app/workflows/auto-code/agents/reviewer.md`
**Depends on:** P7.D1, P7.D2, P7.D3
**Description:** Implement the first concrete workflow. The auto-code WORKFLOW.yaml manifest declares the 5-stage schema (SHAPE → DESIGN → PLAN → BUILD → INTEGRATE) with per-stage agent/tool/skill configuration, validators at appropriate schedules, and the three-layer completion report structure. Migrate the existing `app/agents/pipeline.py` (auto-code-specific composition logic) to `app/workflows/auto-code/pipeline.py`, rewritten using `PipelineContext`. The old file is deleted. The `pipeline.py` exports the `create_pipeline` function that composes the ADK agent tree using the AgentRegistry via PipelineContext. Workflow-scope agent definitions override global agents with auto-code-specific instructions.
**BOM Components:**
- [ ] `F13` — `auto-code/WORKFLOW.yaml` manifest
- [ ] `F14` — `auto-code/pipeline.py` module
- [ ] `F15` — `auto-code/agents/` (planner, coder, reviewer)
- [ ] `F16` — `auto-code/skills/` (workflow-specific)
- [ ] `S31` — Auto-code skill: `test-generation`
**Requirements:**
- [ ] `app/agents/pipeline.py` is deleted. Its logic moves to `app/workflows/auto-code/pipeline.py`, rewritten with `PipelineContext` signature.
- [ ] `PIPELINE_STAGE_NAMES` moves to `app/workflows/auto-code/pipeline.py` as auto-code's node list
- [ ] `create_deliverable_pipeline_from_context()` in `app/workers/adk.py` is deleted (zero backward-compat shims per engineering standards)
- [ ] The auto-code `create_pipeline(ctx: PipelineContext) -> BaseAgent` composes: skill_loader -> memory_loader -> planner -> coder -> formatter -> linter -> tester -> diagnostics -> review_cycle
- [ ] The pipeline reads the current stage's `agents` list from the manifest to filter which nodes are included
- [ ] `WORKFLOW.yaml` validates against `WorkflowManifest` model with all tier-3 fields populated
- [ ] Manifest `name` is `auto-code`, `pipeline_type` is `batch_parallel`
- [ ] Manifest declares 5 stages: `shape`, `design`, `plan`, `build`, `integrate` — each with description, agents, and appropriate validators
- [ ] `shape` stage: agents `[planner]`, validator `spec_completeness` (llm, per_stage), approval `director`
- [ ] `design` stage: agents `[planner, reviewer]`, validator `design_consistency` (llm, per_stage), approval `director`
- [ ] `plan` stage: agents `[planner]`, validator `dependency_validation` (deterministic, per_stage), completion_criteria `all_deliverables_planned`, approval `auto`
- [ ] `build` stage: agents `[coder, reviewer, fixer, formatter, linter, tester, diagnostics]`, validators: `lint_check` (per_deliverable), `test_suite` (per_deliverable), `code_review` (per_deliverable), `regression_tests` (per_batch), approval `auto`
- [ ] `integrate` stage: agents `[tester, reviewer, diagnostics]`, validators: `integration_tests` (deterministic, per_stage, Phase 7b stub returning passed=True), `architecture_conformance` (llm, per_stage, required: false, Phase 7b stub returning passed=True), `final_approval` (approval, per_stage), approval `ceo`
- [ ] Manifest declares `required_tools`: `file_read`, `file_write`, `file_edit`, `bash_exec`, `git_status`, `git_commit`, `git_diff`
- [ ] Manifest declares `default_models` with `PLAN: anthropic/claude-opus-4-6` and `CODE: anthropic/claude-sonnet-4-6`
- [ ] `pipeline.py` exports async `create_pipeline(ctx: PipelineContext) -> BaseAgent` matching the interface contract (DD-4)
- [ ] Three workflow-scope agent definitions: `planner.md`, `coder.md`, `reviewer.md` with auto-code-specific instruction bodies
- [ ] `test-generation` skill at `app/workflows/auto-code/skills/code/test-generation/SKILL.md` with valid frontmatter and triggers for test-related deliverables
- [ ] `.gitkeep` files removed from `app/workflows/auto-code/` and subdirectories
- [ ] `WORKFLOW.yaml` is loadable by `WorkflowRegistry.scan()`
**Validation:**
- `uv run pyright app/workflows/auto-code/pipeline.py`
- `uv run pytest tests/workflows/test_auto_code.py -v`

---

### P7.D7: Gateway, Config, and Lifespan Integration
**Files:** `app/gateway/main.py`, `app/gateway/deps.py`, `app/config/settings.py`
**Depends on:** P7.D2
**Description:** Wire the WorkflowRegistry into the application lifecycle. Add `workflows_dir` setting with `AUTOBUILDER_WORKFLOWS_DIR` env var support. Initialize the registry during gateway lifespan startup (scan both built-in and user-level directories, cache in Redis). Add `get_workflow_registry` dependency injection function. The registry is shared across all requests via `app.state`.
**BOM Components:**
- [ ] *(F12 config aspect — user-level directory wiring)*
**Requirements:**
- [ ] `Settings` gains `workflows_dir: str` field with default `"~/.autobuilder/workflows"`, loaded from `AUTOBUILDER_WORKFLOWS_DIR` env var
- [ ] Gateway lifespan creates `WorkflowRegistry` with built-in dir (`app/workflows/`) and user-level dir (from settings, expanded with `Path.expanduser()`)
- [ ] Registry `scan()` called during startup; if user-level dir doesn't exist, registry operates with built-in only
- [ ] Registry stored on `app.state.workflow_registry`
- [ ] `get_workflow_registry(request: Request) -> WorkflowRegistry` dependency added to `deps.py`
- [ ] Redis cache: `load_from_cache()` attempted first; on miss, `scan()` then `save_to_cache()` (follows SkillLibrary startup pattern)
- [ ] Startup logs: number of discovered workflows, any validation warnings
- [ ] Cache failure is non-fatal (logged, continues with in-memory index)
**Validation:**
- `uv run pyright app/gateway/main.py app/gateway/deps.py app/config/settings.py`
- `uv run pytest tests/gateway/test_health.py -v`

---

### P7.D8: Agent and Skill Three-Tier Integration
**Files:** `app/agents/_registry.py`, `app/skills/library.py`, `app/agents/context_recreation.py`, `app/workers/adk.py`, `app/workers/tasks.py`
**Depends on:** P7.D2, P7.D6
**Description:** Extend the AgentRegistry and SkillLibrary to support the workflow tier. AgentRegistry's `scan()` already accepts workflow-scope directories — ensure it's called with the workflow's `agents/` dir when building a workflow pipeline. SkillLibrary gains an optional `workflow_dir` parameter for three-tier skill merging (global → workflow → project). Decouple `app/agents/context_recreation.py` from the deleted pipeline — remove the `PIPELINE_STAGES` alias and `STAGE_COMPLETION_KEYS` dict, which become workflow-provided configuration. Migrate callers in `app/workers/` to use `WorkflowRegistry.create_pipeline()`. Implement project-scope `tool_role` ceiling validation against the workflow manifest's allowed tools.
**BOM Components:**
- [ ] `S11` — Three-tier merge (+ workflow-specific)
- [ ] `A78b` — Project-scope `tool_role` ceiling validation (against workflow manifest)
**Requirements:**
- [ ] `SkillLibrary.__init__` gains optional `workflow_dir: Path | None = None` parameter
- [ ] `SkillLibrary.scan()` scans three tiers when workflow_dir is provided: global → workflow → project. Workflow skills override global by name; project skills override both.
- [ ] Workflow skills with unique names (not in global set) are added alongside global skills
- [ ] `AgentRegistry.scan()` called with workflow `agents/` directory at `WORKFLOW` scope when building workflow pipelines — this already works via the existing 3-scope cascade
- [ ] Project-scope agent definitions validated against workflow manifest's allowed tool roles: if manifest declares `required_tools` and the agent's `tool_role` would grant access to tools outside that set, emit a warning
- [ ] `app/agents/context_recreation.py` decoupled from pipeline — `PIPELINE_STAGES` alias removed, `determine_remaining_stages` and `recreate_context` receive stages as explicit parameter from the workflow manifest (accessed via `WorkflowRegistry` dependency in the worker context)
- [ ] `STAGE_COMPLETION_KEYS` dict moved out of `context_recreation.py` — becomes workflow-provided configuration
- [ ] `app/workers/adk.py`: `build_work_session_agents()` uses `WorkflowRegistry.create_pipeline(workflow_name, pipeline_ctx)` instead of importing pipeline directly
- [ ] `app/workers/tasks.py`: `run_workflow` uses WorkflowRegistry path instead of `create_deliverable_pipeline_from_context`
**Validation:**
- `uv run pyright app/agents/_registry.py app/skills/library.py app/agents/context_recreation.py app/workers/adk.py`
- `uv run pytest tests/agents/test_registry.py tests/skills/test_library.py tests/agents/test_context_recreation.py -v`

---

### P7.D9: Infrastructure Skills
**Files:** `app/skills/authoring/workflow-quality/SKILL.md`, `app/skills/authoring/workflow-testing/SKILL.md`, `app/workflows/auto-code/skills/code/test-generation/SKILL.md`
**Depends on:** P7.D1
**Description:** Author two new infrastructure skills for the workflow composition system plus one auto-code-specific skill. `workflow-quality` teaches validator design patterns, completion criteria composition, and evidence collection best practices. `workflow-testing` teaches dry run patterns, workflow validation testing, and stage transition testing. Both use `always` trigger with appropriate `applies_to` fields. Note: the three existing Phase 6 authoring skills (workflow-authoring S35, agent-definition S34, skill-authoring S33) already exist and satisfy the roadmap contract's "five infrastructure skills" requirement alongside these two new ones.
**BOM Components:**
- [ ] `S37` — `workflow-quality` skill (validator design patterns)
- [ ] `S38` — `workflow-testing` skill (dry runs, testing patterns)
**Requirements:**
- [ ] `workflow-quality` skill: `always` trigger, `applies_to: [planner, reviewer]`, covers validator types, scheduling, evidence requirements, completion criteria composition, three-layer verification
- [ ] `workflow-testing` skill: `always` trigger, `applies_to: [tester, coder]`, covers workflow validation approaches, stage transition testing, manifest validation, pipeline smoke tests
- [ ] Both skills have valid frontmatter with `name`, `description`, `triggers`, `tags`, `applies_to`
- [ ] Both skills pass `validate_skill_frontmatter()` validation
- [ ] Body content under 3000 words per skill
- [ ] Body content in imperative/instructional style
- [ ] `test-generation` skill placed at `app/workflows/auto-code/skills/code/test-generation/SKILL.md`, triggers on `deliverable_type: test` and `file_pattern: "*/tests/*.py"`, `applies_to: [coder]`. Note: `test-generation` skill file is created in D9; D6 references it in the auto-code manifest.
- [ ] All skills indexed successfully by `SkillLibrary.scan()` when scanning their respective directories
**Validation:**
- `uv run pytest tests/skills/test_skill_files.py -v`

---

## Build Order

```
Batch 1 (sequential): P7.D1
  D1: Enums + Pydantic models — app/models/enums.py, app/workflows/models.py

Batch 2 (parallel): P7.D2, P7.D3, P7.D5, P7.D9
  D2: WorkflowRegistry — app/workflows/registry.py; depends D1
  D3: Stage system + completion gates — app/workflows/stages.py, app/tools/management.py; depends D1
  D5: DB tables + migration — app/db/models.py; depends D1
  D9: Infrastructure skills (2 new) — SKILL.md files; depends D1 (format knowledge)

Batch 3 (parallel): P7.D4, P7.D6, P7.D7
  D4: Validator framework — app/workflows/validators.py; depends D1, D3
  D6: auto-code workflow — WORKFLOW.yaml, pipeline.py (migrated from app/agents/pipeline.py), agents; depends D1, D2, D3
  D7: Gateway + config integration — main.py, deps.py, settings.py; depends D2

Batch 4 (sequential): P7.D8
  D8: Agent/skill three-tier integration + caller migration — _registry.py, library.py, context_recreation.py, workers/adk.py, workers/tasks.py; depends D2, D6
```

## Completion Contract Traceability

### FRD Coverage

*FRD: [frd.md](./frd.md). Full traceability in FRD §Traceability. Requirements also traced via BOM and roadmap contract coverage below.*

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| F01 | `WorkflowRegistry` class | P7.D2 |
| F02 | `WorkflowRegistry.match()` (keyword matching) | P7.D2 |
| F03 | `WorkflowRegistry.get()` (explicit lookup) | P7.D2 |
| F04 | `WorkflowRegistry.list_available()` | P7.D2 |
| F05 | `WorkflowRegistry.create_pipeline()` | P7.D2 |
| F06 | `WorkflowEntry` Pydantic model | P7.D1 |
| F07 | `WORKFLOW.yaml` manifest schema (progressive disclosure) | P7.D1 |
| F08 | Workflow trigger matching (keywords) | P7.D2 |
| F09 | Workflow trigger matching (explicit) | P7.D2 |
| F10 | Workflow ambiguity resolution (user prompt) | P7.D2 |
| F11 | `RunConfig` model | P7.D1 |
| F12 | User-level workflow directory (override by name) | P7.D2, P7.D7 |
| F13 | `auto-code/WORKFLOW.yaml` manifest | P7.D6 |
| F14 | `auto-code/pipeline.py` module | P7.D6 |
| F15 | `auto-code/agents/` (planner, coder, reviewer) | P7.D6 |
| F16 | `auto-code/skills/` (workflow-specific) | P7.D6 |
| F18 | `pipeline.py` interface contract (function signature) | P7.D2 |
| F19 | `WorkflowManifest` Pydantic model (all fields) | P7.D1 |
| F20 | `WorkflowRegistry.get_manifest()` | P7.D2 |
| F21 | Manifest validation (L1 schema, required/warning/cross-ref) | P7.D2 |
| F22 | `StageDef` Pydantic model | P7.D1 |
| F23 | `CompletionCriteria` Pydantic model | P7.D1 |
| F24 | `ValidatorDefinition` Pydantic model | P7.D1 |
| F25 | Stage state keys (`pm:current_stage`, `pm:stage_*`) | P7.D3 |
| F26 | `reconfigure_stage` FunctionTool | P7.D3 |
| F27 | `verify_stage_completion` deterministic gate | P7.D3 |
| F28 | `verify_taskgroup_completion` deterministic gate | P7.D3 |
| F29 | `StageExecution` DB table | P7.D5 |
| F30 | `TaskGroupExecution` DB table | P7.D5 |
| F31 | `ValidatorResult` DB table | P7.D5 |
| F32 | Standard validator: `lint_check` | P7.D4 |
| F33 | Standard validator: `test_suite` | P7.D4 |
| F34 | Standard validator: `regression_tests` | P7.D4 |
| F35 | Standard validator: `code_review` | P7.D4 |
| F36 | Standard validator: `dependency_validation` | P7.D4 |
| F37 | Standard validator: `deliverable_status_check` | P7.D4 |
| F38 | `CompletionReport` Pydantic model | P7.D1 |
| F39 | `StageStatus` enum | P7.D1 |
| F40 | `ValidatorType` enum | P7.D1 |
| F41 | `ValidatorSchedule` enum | P7.D1 |
| F42 | Stage lifecycle events (STAGE_STARTED, STAGE_COMPLETED, etc.) | P7.D3 |
| F43 | `ResourcesDef` validation (credentials, services, knowledge) | P7.D1 |
| F58 | `PipelineContext` frozen dataclass | P7.D1 |
| F59 | `McpServerDef` Pydantic model | P7.D1 |
| S11 | Three-tier merge (+ workflow-specific) | P7.D8 |
| S31 | Auto-code skill: `test-generation` | P7.D6, P7.D9 |
| S37 | `workflow-quality` skill (validator design patterns) | P7.D9 |
| S38 | `workflow-testing` skill (dry runs, testing patterns) | P7.D9 |
| A78b | Project-scope `tool_role` ceiling validation | P7.D8 |
| M24 | Workflow registry cache (long TTL) | P7.D2 |

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | WorkflowRegistry discovers auto-code on startup via directory scan | P7.D2, P7.D6, P7.D7 | `uv run pytest tests/workflows/test_registry.py -v -k discover` |
| 2 | `POST /workflows/run {"workflow": "auto-code"}` resolves and instantiates pipeline | P7.D2, P7.D6 | `uv run pytest tests/workflows/test_registry.py -v -k create_pipeline` |
| 3 | Adding a new workflow = adding a directory + manifest (zero registration code) | P7.D2 | `uv run pytest tests/workflows/test_registry.py -v -k new_workflow` |
| 4 | User-level workflows at `~/.autobuilder/workflows/` override built-in by name | P7.D2, P7.D7 | `uv run pytest tests/workflows/test_registry.py -v -k user_level` |
| 5 | WORKFLOW.yaml validates with progressive disclosure (2-field minimum is valid) | P7.D1, P7.D2 | `uv run pytest tests/workflows/test_models.py tests/workflows/test_registry.py -v -k progressive` |
| 6 | auto-code manifest includes 5-stage schema with per-stage agent/tool/skill config | P7.D6 | `uv run pytest tests/workflows/test_auto_code.py -v -k stages` |
| 7 | Stage completion criteria compose as AND (deliverables + validators + approval) | P7.D3 | `uv run pytest tests/workflows/test_stages.py -v -k completion` |
| 8 | Standard validators (lint, test, regression, review) produce machine evidence | P7.D4 | `uv run pytest tests/workflows/test_validators.py -v` |
| 9 | Three-layer completion reports generated (functional, architectural, contract) | P7.D1, P7.D4 | `uv run pytest tests/workflows/test_validators.py -v -k report` |
| 10 | TaskGroup/stage close conditions enforced deterministically (hard gates) | P7.D3 | `uv run pytest tests/workflows/test_stages.py -v -k verify` |
| 11 | Five infrastructure skills operational (workflow-authoring, agent-definition, skill-authoring, workflow-quality, workflow-testing) | P7.D9 | `uv run pytest tests/skills/test_skill_files.py -v` |

## Research Notes

### Existing Interface Signatures

**AgentRegistry.scan()** (`app/agents/_registry.py`):
```python
def scan(self, *dirs: tuple[Path, DefinitionScope]) -> None:
    """Scan directories for .md agent definition files.
    3-scope cascade: GLOBAL → WORKFLOW → PROJECT
    """
```
Already supports workflow scope — call with `(workflow_agents_dir, DefinitionScope.WORKFLOW)`.

**SkillLibrary.__init__()** (`app/skills/library.py`):
```python
def __init__(
    self,
    global_dir: Path,
    project_dir: Path | None = None,
    redis: ArqRedis | None = None,
) -> None:
```
Needs `workflow_dir: Path | None = None` parameter added for three-tier merge.

**DeliverablePipeline factory** (`app/agents/pipeline.py`) — **migrated/deleted in P7.D6**:
```python
def create_deliverable_pipeline(
    registry: AgentRegistry,
    ctx: InstructionContext,
    skill_library: object,
    memory_service: object,
    before_model_callback: ...,
    stages: list[str] | None = None,
) -> SequentialAgent:
```
This is auto-code's composition logic, not shared infrastructure. In P7.D6, it is rewritten as `app/workflows/auto-code/pipeline.py` with the `create_pipeline(ctx: PipelineContext) -> BaseAgent` signature. The old file and `create_deliverable_pipeline_from_context()` in `app/workers/adk.py` are deleted.

### Enum Convention

All enums must use `StrEnum` with `VALUE = "VALUE"`. Located in `app/models/enums.py`:
```python
class PipelineType(enum.StrEnum):
    SINGLE_PASS = "SINGLE_PASS"
    SEQUENTIAL = "SEQUENTIAL"
    BATCH_PARALLEL = "BATCH_PARALLEL"
```

### Database Migration Numbering

Existing migrations use sequential `NNN` format. Check `app/db/migrations/versions/` for the latest number.

### CustomAgent Pattern

All CustomAgents inherit from `BaseAgent`, override `_run_async_impl()` (async generator yielding Events), and register in `CLASS_REGISTRY` via `app/agents/custom/__init__.py`. Phase 7 validators do NOT use this pattern — they're framework functions, not CustomAgents (DD-2).

### Redis Cache Pattern

SkillLibrary cache uses `autobuilder:skill_index:{scope_hash}`. WorkflowRegistry cache follows: `autobuilder:workflow_index:{scope_hash}`.

### Gateway Lifespan Pattern

```python
# SkillLibrary initialization (Phase 6) — WorkflowRegistry follows same pattern
skill_library = SkillLibrary(global_dir=skills_dir, redis=arq_pool)
cache_hit = await skill_library.load_from_cache()
if not cache_hit:
    skill_library.scan()
    try:
        await skill_library.save_to_cache()
    except Exception:
        logger.debug("Cache save skipped (non-critical)")
app.state.skill_library = skill_library
```

### Stage State Key Authorization

Stage state keys use `pm:` prefix per Decision #58. The EventPublisher's `validate_state_delta()` already enforces tier-based ACL — PM-tier agents can write `pm:` prefixed keys. No additional authorization logic needed.

### Test Patterns for Phase 7

- `tests/workflows/` new directory with `conftest.py`
- Helper: `_write_workflow(base_dir, name, manifest_yaml)` writes WORKFLOW.yaml
- Real Redis/PostgreSQL with skip markers
- `FakeToolContext` for tool unit tests
- `caplog` for logging assertions
- Class-based test organization by feature
