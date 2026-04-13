# Phase 7 Delta Report: PRD v7.3 Back-Propagation
*Generated: 2026-04-12*

## Trigger

PRD updated to v7.3. Architecture doc `workflows.md` updated to v5.2. BOM updated to v2.3.0/v2.4.0. Phase 7 is DONE -- this report identifies what changed upstream and what, if anything, Phase 7 artifacts need.

---

## 1. PRD Delta

### PR-4 Expansion (v7.3)

**Before:** PR-4 listed stage schema, agents/tools/skills per stage, validator pipeline, deliverable format, output format, completion report structure.

**After:** PR-4 now includes "permitted **edit operations** (domain-specific modifications issued at any time regardless of project state, e.g., add feature, fix bug, refactor for software)."

**Impact on Phase 7:** LOW. PR-4 is Phase 7's primary traceability target. The new `edit_operations` clause is an additive manifest field. Phase 7 already satisfies all other PR-4 clauses. The edit operations runtime (accepting edits, creating TaskGroups, routing to stages) is Phase 8a scope.

### PR-2 Expansion (v7.3)

**Before:** Projects persist after completion and remain queryable.

**After:** Projects persist after completion and remain "queryable and modifiable. Edit operations can be issued at any time regardless of project state — they queue as new work within accumulated project context."

**Impact on Phase 7:** NONE. Phase 7 does not implement project lifecycle. PR-2 traceability is Phase 8a (X20/X21 project entity, X27 edit request flow).

### Information Architecture Update

The **Workflow** entity description now includes "and its available edit operations." The **Project** entity now includes "edit" in the "User Can" column.

**Impact on Phase 7:** NONE. These are informational; no Phase 7 artifact references the IA table.

---

## 2. Architecture Delta (`workflows.md` v5.2)

### New: `edit_operations` Root Field

Added to the Root Fields table:

```
| edit_operations | list[EditOperationDef] | No | [] | Available edit operations for living projects (Decision D5). |
```

### New: `EditOperationDef` Type Definition

```yaml
EditOperationDef:
  name: string        # Operation identifier (e.g., add_endpoint, refactor_module)
  description: string # What this edit operation does
  entry_stage: string # Which stage the edit begins at
  requires_approval: bool  # Whether CEO/Director approval needed
```

### New: "Living Projects" Section (Section 10)

Documents how projects persist post-completion, how `edit_operations` defines valid modifications, and how edits create new TaskGroups in existing projects. References `execution.md` for entry modes.

### Impact on Phase 7

The `edit_operations` field is a Tier 3 (comprehensive) manifest field -- optional, no impact on existing workflows if absent. This is exactly the progressive disclosure pattern Phase 7 designed for.

**Key question:** Should Phase 7's `WorkflowManifest` Pydantic model include the `edit_operations` field?

**Analysis:**
- Phase 7's manifest model uses `extra="ignore"` (line 128 of `manifest.py`). YAML files containing `edit_operations` parse without error -- the field is silently dropped.
- However, Phase 7's design principle is that the manifest model IS the schema. Fields that exist in the architecture doc should be parseable by the model, even if the runtime ignores them.
- The field is purely declarative (a list of operation definitions). No runtime behavior is needed -- the model just needs to store the parsed data.
- Adding an optional `edit_operations: list[EditOperationDef]` field with `default_factory=lambda: list[EditOperationDef]()` is consistent with how `mcp_servers`, `resources`, and other Tier 3 fields were handled.

**Recommendation:** YES -- add `EditOperationDef` model and `edit_operations` field to `WorkflowManifest`. This is schema completeness, not runtime behavior. The field parses, validates, and stores. Phase 8a consumes it.

---

## 3. BOM Delta

### X26 — `edit_operations` manifest field (Phase 8a)

| ID | Component | Type | Phase | Source |
|----|-----------|------|-------|--------|
| X26 | Workflow-defined edit operations manifest field (`edit_operations` in WORKFLOW.yaml) | config | 8a | workflows.md Workflow Manifest |

**Analysis:** X26 is typed as `config` (not `mechanism` or `workflow`). It is a manifest schema field. Phase 7 owns the manifest schema. The BOM assigns it to 8a because its consumer (the Director's edit routing logic) is Phase 8a. But the schema definition is Phase 7 territory.

**Recommendation:** X26's phase assignment is reasonable -- the component encompasses both schema AND consumption. Phase 7 should add the schema field to the model (progressive disclosure), and X26 remains 8a for the runtime wiring. No BOM change needed; the delta report documents the split responsibility.

### X27 — Project edit request flow (Phase 8a)

| ID | Component | Type | Phase | Source |
|----|-----------|------|-------|--------|
| X27 | Project edit request flow (Director receives edit -> creates new TaskGroup in existing project) | workflow | 8a | execution.md §Director Execution Turn |

**Impact on Phase 7:** NONE. X27 is pure runtime behavior. No Phase 7 artifact references it.

---

## 4. Artifact Changes Required

### frd.md -- NO CHANGE

All 85 FRD requirements (FR-7.01 through FR-7.85) remain valid. The `edit_operations` field does not introduce new functional requirements for Phase 7 -- it is a schema addition covered by existing FR-7.09 (progressive disclosure: "When a manifest contains only a name and description, the system accepts it as valid") and FR-7.09b (additional fields validated against type schemas). No new FR is needed because the field follows the same pattern as `mcp_servers`, `brief_template`, `conventions`, and `director_guidance`.

### spec.md -- ADDENDUM

P7.D1 (Workflow Enums and Pydantic Models) should note that `EditOperationDef` and `edit_operations` field were added post-completion per PRD v7.3 back-propagation. The field follows the same optional-with-default pattern as all other Tier 3 fields.

### model.md -- UPDATE

The `WorkflowManifest` type definition in the Key Types section should include `edit_operations` in its fields list. The `EditOperationDef` type should be added to the types list.

### review.md -- NO CHANGE

The review report documents findings at review time. Post-review changes are documented in delta reports (this file), not retroactively added to review.md.

---

## 5. Remediation Required (Code Changes -- ALL APPLIED 2026-04-12)

### R1: ✓ Add `EditOperationDef` Pydantic model to `app/workflows/manifest.py`

```python
class EditOperationDef(BaseModel):
    """Edit operation definition for living projects (Decision D5)."""
    model_config = ConfigDict(frozen=True)
    name: str
    description: str = ""
    entry_stage: str = ""
    requires_approval: bool = False
```

### R2: ✓ Add `edit_operations` field to `WorkflowManifest`

```python
edit_operations: list[EditOperationDef] = Field(
    default_factory=lambda: list[EditOperationDef]()
)
```

### R3: ✓ Add test for `edit_operations` parsing

A manifest test should verify that `edit_operations` parses correctly and defaults to empty list when omitted. Follow the existing `mcp_servers` test pattern.

### R4: ✓ Update `app/workflows/__init__.py` re-exports

Add `EditOperationDef` to `__all__` and imports.

### Scope

- 4 changes across 3 files (manifest.py, __init__.py, WORKFLOW.yaml)
- Zero runtime behavior change
- 212 existing tests pass, ruff clean, pyright 0 errors
- Applied: 2026-04-12 during Phase 8a shaping session

---

## 6. Summary

| Category | Items | Impact |
|----------|-------|--------|
| PRD delta | PR-4 expanded (edit_operations), PR-2 expanded (modifiable projects) | LOW -- additive field |
| Architecture delta | `edit_operations` root field, `EditOperationDef` type, Living Projects section | MEDIUM -- schema gap |
| BOM delta | X26 (8a), X27 (8a) | NONE -- correct phase assignment |
| FRD changes | None | -- |
| Spec changes | Addendum note on P7.D1 | LOW |
| Model changes | Add EditOperationDef type, add edit_operations to WorkflowManifest fields | LOW |
| Code remediation | 4 changes, 2-3 files, trivial effort | ✓ ALL APPLIED (2026-04-12) |

**Conclusion:** Phase 7 is architecturally sound. The only gap is a missing optional schema field (`edit_operations`) in the `WorkflowManifest` Pydantic model. This is consistent with Phase 7's progressive disclosure principle -- the field should be parseable even though its runtime consumer is Phase 8a. All other Phase 7 deliverables, completion contract items, and FRD requirements remain satisfied.
