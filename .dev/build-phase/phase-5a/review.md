# Phase 5a Review Report
*Date: 2026-03-11*

## Review Configuration
- **Mode**: Double review (2 passes)
- **Pass 1**: 3 parallel reviewers (files split by group)
- **Pass 2**: 2 reviewers (correctness + spec conformance)

## Pass 1 Findings (Fixed)

### Reviewer A (DB models, assembler, protocols)
| # | Severity | File | Finding | Resolution |
|---|----------|------|---------|------------|
| 1 | MEDIUM | `protocols.py` | Method names `match_skills()`/`load_skill()` didn't match model.md interface (`match()`/`load()`) | Renamed to match model; updated all consumers |
| 2 | LOW | `db/models.py` | `ProjectConfig.active` missing `server_default` | Added `server_default=text("true")` |

### Reviewer B (state_helpers, context_monitor, registry, toolset)
| # | Severity | File | Finding | Resolution |
|---|----------|------|---------|------------|
| 1 | MEDIUM | `_toolset.py` | Backwards-compat shims in AGENT_ROLE_MAP (old Phase 3 names) violate standards | Removed shims, added PM mapping |
| 2 | MEDIUM | `state_helpers.py` | `load_project_config` param named `project_id` but queries `project_name` column | Renamed to `project_name` |
| 3 | LOW | `context_monitor.py` | Hardcoded model string `"claude-sonnet-4-6"` | Extracted to `DEFAULT_FALLBACK_MODEL` constant |
| 4 | LOW | `_registry.py` | Missing `description` kwarg in custom agent `build()` | Added description pass-through |

### Reviewer C (pipeline, workers, custom agents, definition files)
| # | Severity | File | Finding | Resolution |
|---|----------|------|---------|------------|
| 1 | HIGH | `pipeline.py` | LoopAgent used for ReviewCycle — LlmAgents can't produce `escalate` events, cycle never terminates early | Replaced with ReviewCycleAgent (CustomAgent) per DD-6 alternative |
| 2 | HIGH | `custom/diagnostics.py` | Read wrong keys from producer agents (expected `failures`, actual is `output`) | Fixed to match actual LinterAgent/TestRunnerAgent output format |
| 3 | MEDIUM | `custom/dependency_resolver.py` | `litellm/` prefix on direct API calls (ADK convention, not litellm) | Removed prefix |
| 4 | MEDIUM | `workers/tasks.py` | `ContextRecreationRequired` was re-raised (spec says catch and log only) | Removed re-raise |
| 5 | LOW | `reviewer.md` | Verdict format instructions unclear for ReviewCycleAgent parsing | Added explicit `## Verdict: APPROVED` format |

## Pass 2 Findings (Fixed)

### Reviewer D (correctness + test coverage)
| # | Severity | File | Finding | Resolution |
|---|----------|------|---------|------------|
| 1 | MEDIUM | `test_custom_agents.py` | ReviewCycleAgent missing from registration test expected set | Added to expected set |
| 2 | LOW | — | No tests for ReviewCycleAgent | Created `test_review_cycle.py` (15 tests) |

### Reviewer E (spec conformance reflector)
| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| — | — | All 4 checked deliverables (D2, D3, D7, D8) conform to spec | No action needed |

## Verdict: PASS

- **Pass 1**: 11 findings, all fixed (2 HIGH, 4 MEDIUM, 5 LOW)
- **Pass 2**: 2 findings, all fixed (1 MEDIUM, 1 LOW)
- **Unresolved**: 0
- **False positives**: 0

## Quality Gate (post-review)
- ruff check: 0 errors
- ruff format: 0 issues
- pyright: 0 errors
- pytest: 419 passed, 2 pre-existing failures (Phase 4 toolset schema)

## Observations (informational)
1. Spec-to-model terminology drift: spec uses informal field names that differ from model's precise types
2. ADK LoopAgent + LlmAgent incompatibility: escalate mechanism not usable from LLM agents — CustomAgent wrapper is the pattern
3. `litellm/` prefix is ADK-internal, not valid for direct litellm API calls
