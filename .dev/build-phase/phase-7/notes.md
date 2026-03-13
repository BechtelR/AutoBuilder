# Phase 7: Workflow Composition — Build Notes

Notes for the spec writer. Key patterns, integration points, and resolved design questions from architecture research.

---

## Key Patterns from Research

### 1. Deterministic-Agent-Deterministic Sandwich
All successful agentic systems (Stripe Minions, Shopify ROAST) use deterministic infrastructure wrapping non-deterministic AI. The system controls workflow flow; LLM fills creative gaps within constraints. AutoBuilder's existing architecture is well-aligned with this pattern.

### 2. Configuration Over Code
Workflows defined declaratively (YAML manifests, directory structure), not programmatically. Shopify ROAST uses numbered directories as steps. Our WORKFLOW.yaml + pipeline.py model keeps declaration separate from orchestration code.

### 3. Stages as Configuration Scopes
Stages are NOT new execution primitives. They filter existing infrastructure (agents, skills, tools, quality gates). This is critical — do not introduce new pipeline types or agent wrappers for stages. StageConfig feeds into existing systems via `resolve_stage_config()`.

### 4. Resource Declaration + Pre-Flight
Dagster's resources-as-first-class-citizens pattern. Resources declared in manifest, validated deterministically before execution starts. Failed checks → CEO queue items with resolution hints.

---

## Critical Integration Points

### create_deliverable_pipeline() already has `stages` parameter
`app/agents/pipeline.py` → `create_deliverable_pipeline()` already accepts `stages: list[str] | None` for filtering pipeline stages. StageConfig's `pipeline_stages` feeds directly into this existing parameter. No new pipeline infrastructure needed.

### AgentRegistry needs additive filter
`app/agents/_registry.py` → `AgentRegistry.scan()` uses 3-scope cascade (GLOBAL → WORKFLOW → PROJECT). For stage scoping, add an optional `agent_filter: set[str] | None` parameter or a post-scan filter method. Low impact — additive, does not change existing behavior.

### SkillLibrary match filtering
`app/skills/library.py` → `SkillLibrary.match()` returns matching skills. Stage's `skills` patterns (glob-style, e.g., `code/*`) can post-filter results. SkillLibrary already supports glob patterns in its scan.

### InstructionAssembler fragment injection
`app/agents/assembler.py` → InstructionAssembler already handles 6 fragment types. Stage description → TASK fragment. Workflow standards → GOVERNANCE fragments. No new fragment types needed.

### GlobalToolset tool filtering
`app/tools/_toolset.py` → GlobalToolset already supports per-role tool vending. Stage's `tools` list can further restrict available tools. Already supports filtering pattern.

### Event stream additions
- New event type: `STAGE_TRANSITION` → Redis Streams
- New CEO queue item type: `STAGE_APPROVAL`
- Both are additive to existing enum types in `app/models/enums.py`

### Database addition
- `current_stage` column on project table (nullable string) — one Alembic migration
- `resource_library` table + `project_resources` table — one Alembic migration

---

## Resolved Design Questions

1. **Stage transition approval** → Configurable per-workflow. Each stage declares `approval: ceo | director`. Default: `ceo`. Allows fast-moving workflows to auto-advance intermediate stages while keeping final stages CEO-gated.

2. **SHAPE scope** → Stage within auto-code. Self-contained workflows are the primary use case. The platform supports workflow chaining (completion → next workflow as input) but that's Phase 8+ execution scope.

3. **Resource library** → Build in Phase 7b. Full resource library with DB, API, and Director tool. Enables workflow composition with CEO resources from day one.

4. **Skill location** → Keep code skills at `app/skills/code/` (universal, used by many workflows). Only truly workflow-unique skills go in `app/workflows/auto-code/skills/`.

---

## Build Order Recommendation

### Phase 7a: Core Workflow Infrastructure (Steps 1-6)
1. WorkflowManifest & StageConfig models (`app/workflows/manifest.py`)
2. WorkflowRegistry (`app/workflows/registry.py`)
3. Stage-aware pipeline factory (modify `pipeline.py`, `_registry.py`)
4. auto-code workflow (WORKFLOW.yaml, pipeline.py, standards, validators)
5. Stage transition machinery (enums, migration, worker startup, events)
6. InstructionAssembler stage context (TASK fragment, GOVERNANCE fragments)

### Phase 7b: Authoring, Resources & Validation (Steps 7-10)
7. validate_workflow tool (`app/tools/workflow_validation.py`)
8. Resource library (models, migration, routes, tool) — parallel with Steps 1-6
9. ResourcePreflightAgent (`app/agents/custom/resource_preflight.py`)
10. Director authoring skills (workflow-composition, resource-composition)

---

## What Phase 7 Does NOT Build

- Compound workflow execution (Phase 8)
- Cross-project dependencies (Phase 8+)
- Continuous pipeline type (Phase 11)
- Smoke test validation (Phase 8)
- Workflow marketplace (filesystem is the distribution format)
- Runtime sandboxing (configuration-level isolation sufficient)

---

## Testing Strategy Notes

- WorkflowManifest parsing: test with valid/invalid YAML, missing required fields, stage override resolution
- WorkflowRegistry: test discovery, matching, pipeline creation, custom directory override
- StageConfig resolution: test merge logic (workflow defaults + stage overrides), omitted fields defaulting
- ResourcePreflightAgent: test each check type, required vs optional failures, CEO queue item creation
- validate_workflow: test schema validation, dry-run pipeline construction
- Integration: test full stage transition lifecycle (SHAPE → PLAN → BUILD → VERIFY)

---

## PipelineType Enum
```python
class PipelineType(str, enum.Enum):
    BATCH_PARALLEL = "BATCH_PARALLEL"    # Deliverables in parallel batches (auto-code)
    SEQUENTIAL = "SEQUENTIAL"             # One at a time
    SINGLE_PASS = "SINGLE_PASS"          # No deliverable decomposition
```

---

## ResourceCheckType Enum
```python
class ResourceCheckType(str, enum.Enum):
    PROVIDER_REACHABLE = "PROVIDER_REACHABLE"
    API_KEY_VALID = "API_KEY_VALID"
    GIT_INSTALLED = "GIT_INSTALLED"
    RUNTIME_AVAILABLE = "RUNTIME_AVAILABLE"
    TOOL_AVAILABLE = "TOOL_AVAILABLE"
    FILE_EXISTS = "FILE_EXISTS"
    SERVICE_REACHABLE = "SERVICE_REACHABLE"
    COMMAND_AVAILABLE = "COMMAND_AVAILABLE"
```
