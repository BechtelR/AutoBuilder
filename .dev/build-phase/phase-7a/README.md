# Phase 7a: Workflow Composition System — Build Notes

**Status**: Architecture Validated — Build Ready
**Date**: 2026-04-12 (validation), 2026-04-11 (design)

---

## Design Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Manifest design | `.dev/.notes/260312_manifest-design.md` | Complete WORKFLOW.yaml field reference, examples, validation rules |
| Stage schema design | `.dev/.notes/260312_stage-schema-design.md` | Stage system design, PM-driven transitions, completion criteria |
| Director authoring design | `.dev/.notes/260312_director-authoring-design.md` | Director workflow authoring lifecycle, security, resource discovery |
| Authoring skills design | `.dev/.notes/260312_authoring-skills-design.md` | 9 authoring skills taxonomy, quality framework, pipeline patterns |
| External systems research | `.dev/.research/260312_external-agentic-systems.md` | Stripe Minions, Shopify Roast, and 6 others — patterns to adopt/avoid |
| Workflow composition research | `.dev/.research/260312_workflow-composition-patterns.md` | N8N, Temporal, Airflow, K8s — architectural patterns and lessons |

## Architecture Reference

Primary: `.dev/architecture/workflows.md` (v5.0)

## Architecture Decisions

| # | Decision | Summary |
|---|----------|---------|
| 70 | Manifest | Progressive disclosure, stages, validators, completion reports |
| 71 | Stage schema | Organizational groupings, PM-driven transitions, AND-composed criteria |
| 72 | Directory override | User-level overrides built-in by name |
| 73 | Pipeline.py | Generated from scratch by Director, not templated |
| 74 | Validator framework | 6 standard validators (Phase 7a); evidence collection via ValidatorRunner |
| 75 | Quality framework | Three-layer verification, deterministic close conditions |
| 76 | Director authoring | 6-phase lifecycle with staging gate (Phase 7b) |
| 77 | Authoring skills | 9 skills across 4 categories |

## Phase Split

### Phase 7a (Infrastructure)
- WorkflowRegistry with manifest parsing and validation
- Stage schema Pydantic models and state keys
- Standard validator implementations (6 code-focused + universal)
- WORKFLOW.yaml validation (L1-L4)
- auto-code workflow with stage schema
- 5 infrastructure skills (workflow-authoring, agent-definition, skill-authoring, workflow-quality, workflow-testing)
- Directory override model (user-level workflows at `~/.autobuilder/workflows/`)

### Phase 7b (Director Authoring)
- Director resource discovery tools (5 FunctionTools)
- Director filesystem tool scoping (path-restricted)
- Staging directory convention
- Activation gate via CEO queue
- Dry run capability
- 4 Director authoring skills (director-workflow-composition, project-conventions, software-development-patterns, research-patterns)
- Workflow improvement loop

## Key Design Decisions

1. **Stages are NOT execution contexts** — they are organizational groupings within a single PM session (Airflow TaskGroup pattern, not SubDAG)
2. **Progressive disclosure** — a valid manifest has just `name` and `description`. Everything else has sensible defaults.
3. **Pipeline.py from scratch** — Director writes pipeline.py guided by skills. Templates constrain expressiveness; opus can compose from first principles.
4. **Validators are code, not skills** — Skills teach about validators. ValidatorRunner evaluates existing agent output and records machine evidence (DD-2). Not CustomAgent classes.
5. **Override model** — user-level workflows at `~/.autobuilder/workflows/` (configurable via `AUTOBUILDER_WORKFLOWS_DIR`) override built-in by name. Two-tier only — no project-scoped workflows. Workflows are selected for a project, not customized within one.
6. **Resource discovery via thin query tools** — NOT a new Resource Library entity. Five tools over existing registries.

7. **Pipeline migration**: `app/agents/pipeline.py` (auto-code-specific composition logic) migrates to `app/workflows/auto-code/pipeline.py` with PipelineContext rewrite. Old file deleted. `create_deliverable_pipeline_from_context()` in `app/workers/adk.py` also deleted. `context_recreation.py` decoupled — `PIPELINE_STAGES` alias and `STAGE_COMPLETION_KEYS` become workflow-provided configuration instead of imports from the deleted file.

## Pre-Build Validation

### Architecture Validation (2026-04-12) — PASSED

Full validation pipeline built and executed. 208 tests across 7 modules prove the core architecture is sound. See `validation-report.md` for detailed results.

```bash
# Run the full validation suite
uv run pytest tests/workflows/ -v --tb=short
```

**Risks retired**: progressive disclosure, registry discovery, dynamic pipeline import, stage state machine, validator evidence collection, hard completion gates, three-tier skill merge.

**Production code built during validation** (minimal, reusable in full build):
- `app/workflows/manifest.py` — 15 Pydantic models
- `app/workflows/context.py` — PipelineContext + PipelineFactory
- `app/workflows/registry.py` — WorkflowRegistry
- `app/workflows/stages.py` — Stage lifecycle
- `app/workflows/validators.py` — ValidatorRunner, 6 validators, gates, reports
- `app/models/enums.py` — 6 new enums + PipelineEventType extension
- `app/skills/library.py` — Three-tier merge (workflow_dir parameter)

### Readiness Tests (2026-04-11)

```bash
uv run pytest tests/workflows/test_phase7a_readiness.py -v
```

53 tests verify: manifest example well-formed, workflow directories ready, prerequisite infrastructure intact.

## Reference Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Workflow manifest example | `reference/workflow-manifest-example.yaml` | Production-ready Tier 3 manifest (auto-code) |
| Validation report | `validation-report.md` | Architecture validation results and findings |
| Pre-build validation tests | `tests/workflows/test_phase7a_readiness.py` | 53 readiness tests |
| Architecture validation tests | `tests/workflows/test_manifest.py` + 6 more | 208 architecture validation tests |

## Open Questions for Build Phase

1. ~~Validator agents vs validator functions~~ — **Resolved (DD-2)**: ValidatorRunner with evaluation functions, not CustomAgent classes.
2. ~~Case-insensitive YAML enums~~ — **Resolved**: `BeforeValidator(_upper)` on manifest-facing enum fields.
3. ~~Stage status on advance~~ — **Resolved**: ACTIVE (not PENDING) when PM explicitly advances.
4. Stage-scoped skills — additive only (no remove mechanism). If needed, use `applies_to` instead.
5. `allow_stage_overlap` — deferred to Phase 8a+ (concurrency optimization).

## Build Order (Updated Post-Validation)

Validation pipeline built the types + core logic. Full build completes wiring:

1. ~~Enums + Pydantic models~~ — DONE (validation)
2. ~~WorkflowRegistry~~ — DONE (validation)
3. ~~Stage lifecycle functions~~ — DONE (validation)
4. ~~Standard validators + completion gates~~ — DONE (validation)
5. ~~Three-tier skill merge~~ — DONE (validation)
6. Database tables (StageExecution, TaskGroupExecution, ValidatorResult) + migration
7. auto-code WORKFLOW.yaml manifest (with full stage schema)
8. auto-code pipeline.py (migration from `app/agents/pipeline.py`)
9. `reconfigure_stage` as FunctionTool + event publishing
10. Gateway endpoints + config wiring
11. Infrastructure skills (5)
12. Three-tier agent cascade (workflow-scope agent definitions)
