# Phase 5b Review Report
*Date: 2026-03-11*

## Review Configuration
- Mode: `--review=double` (2 passes, 3 reviewers each)
- Files reviewed: 31 (19 source, 12 test)
- Total lines: ~7,400

## Pass 1 (Reviewers A, B, C)

### Fixed
| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `context_recreation.py` | DRY: `PIPELINE_STAGES` duplicated from `pipeline.py` — replaced with import | MEDIUM |
| 2 | `supervision.py` | Magic strings `"COMPLETED"`, `"FAILED"` — replaced with `DeliverableStatus` enum | MEDIUM |
| 3 | `adk.py` | System reminder callback not wired into compose_callbacks chain | HIGH |
| 4 | `ceo_queue.py` (route) | `model_validate(item)` crashed — SQLAlchemy `metadata` attribute collision | HIGH |
| 5 | `ceo_queue.py` (route) | `resume_after_approval` ARQ task undefined — replaced with `run_work_session` | HIGH |
| 6 | `tasks.py` | `flush_violations()` never called — state auth violations never published | HIGH |
| 7 | `constants.py` | `TIER_PREFIX_WRITE_ACCESS` used string literals instead of `AgentTier` enum | MEDIUM |
| 8 | `publisher.py` | Violation metadata used magic string instead of enum | LOW |
| 9 | `ceo_queue.py` (model) | Missing validation: RESOLVE action without resolution | MEDIUM |
| 10 | `adk.py` | Dead `create_director_agent()` stub — removed | LOW |
| 11 | `tasks.py` | `source_project_id` always None in failure handler | MEDIUM |
| 12 | `tasks.py` | Missing error event publication in `run_director_turn` | MEDIUM |
| 13 | `tasks.py` | `process_director_queue` enqueued `run_director_turn` with wrong kwargs | HIGH |

### Flagged (Pass 1)
- State key auth is observation-only, not enforcement — accepted as spec-compliant (DD-2 acknowledges brief in-memory inconsistency window)

## Pass 2 (Reviewers D, E, F)

### Fixed
| # | File | Issue | Severity |
|---|------|-------|----------|
| 14 | `formation.py` | In-memory state dict mutation doesn't persist in DatabaseSessionService | HIGH |
| 15 | `supervision.py` | `after_pm_execution` missing inline Director Queue check per DD-5 | MEDIUM |
| 16 | `tasks.py` | Missing pipeline callbacks (budget monitor, model routing) in `run_work_session` | HIGH |
| 17 | `tasks.py` | Error events published to wrong stream key (chat_id vs adk_session_id) | MEDIUM |
| 18 | `tasks.py` | Approval writeback not implemented in resumed work sessions | HIGH |
| 19 | `chat.py` | Race condition in `_ensure_well_known_session` (concurrent get-or-create) | MEDIUM |
| 20 | `formation.py` | `create_session` on existing ID raises `AlreadyExistsError` — needs delete-then-create | HIGH |

### Flagged (Pass 2)
- `process_director_queue` enqueues `run_work_session` but spec D7 originally said `run_director_turn`. Accepted as pragmatic choice since `run_director_turn` requires chat params that don't exist for cron-triggered queue processing.

## Unresolved Findings
None — all findings resolved.

## Quality Gate (Post-Review)
- ruff check: 0 errors
- ruff format: 0 files to format
- pyright: 0 errors (strict)
- pytest: 539 passed, 0 failed
