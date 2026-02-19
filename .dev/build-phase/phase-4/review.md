# Phase 4 Review Report — Core Toolset

## Review Configuration
- **Mode**: double (2 passes, 6 total reviewers)
- **Pass 1**: 2 reviewers (source code + test code)
- **Pass 2**: 4 reviewers (security/logging, spec conformity, enum/exports, test coverage)

## Pass 1 Findings (Resolved)

### Reviewer 1: Source Code
- **[SECURITY]** Path containment in `validate_path()` used `str.startswith()` — vulnerable to prefix collision (e.g., `/project` matching `/project-evil`). **Fixed**: Changed to `Path.relative_to()`.
- **[STANDARDS]** Management tools used magic string validation sets (`_VALID_PRIORITIES`, etc.) instead of enums. **Fixed**: Added 6 new `StrEnum` types (`EscalationPriority`, `EscalationRequestType`, `CeoItemType`, `DependencyAction`, `PmOverrideAction`, `GitWorktreeAction`) and updated all function signatures.
- **[BUG]** `web_search` read `AUTOBUILDER_SEARCH_PROVIDER` from `os.environ` instead of using `get_settings().search_provider`. **Fixed**.
- **[BUG]** `test_git_branch_switch` tested wrong branch (`master` vs `main`). **Fixed**.
- **[CONFIG]** `@pytest.mark.network` used but not registered. **Fixed**: Added marker to `pyproject.toml`.

### Reviewer 2: Test Code
- Verified test coverage across all 8 test files
- Confirmed FakeToolContext correctly simulates ADK state management

## Pass 2 Findings (Resolved)

### Reviewer 3: Security + Error Handling (aae8c38)
- **[SECURITY]** `http_request` and `web_fetch` had no URL scheme validation — SSRF via `file://`, `gopher://`. **Fixed**: Added `urlparse` check restricting to `http`/`https`.
- **[SILENT-FAILURE]** All 16 `except Exception` blocks in `filesystem.py` silently returned error strings without logging. **Fixed**: Added `logger.warning()` calls to every handler.
- **[SILENT-FAILURE]** `bash_exec` and `http_request` exception handlers lacked logging. **Fixed**.
- **[BUG]** `test_task.py` called `todo_write`/`todo_read` with wrong argument order. **Fixed** all 13 test calls.
- **[BUG]** `test_git_worktree` used `git checkout -b` causing "branch in use" error. **Fixed**: use `git branch` instead.

### Reviewer 4: Spec Conformity (aa4ec81)
- **[CONFORMITY]** `todo_read` signature was `(task_id, tool_context)` — spec says `(tool_context)` returning full list. **Fixed**.
- **[CONFORMITY]** `todo_write` had optional kwargs — spec requires positional params. **Fixed**.
- **[CONFORMITY]** `file_grep.context`, `directory_list.depth`, `git_log.count` used `int` defaults instead of `int | None`. **Fixed**: aligned to spec with internal default resolution.
- **[CONFORMITY]** All 42 docstring first lines aligned to spec "Purpose" column.

### Reviewer 5: Enum + Exports (ac0a1a9, aa5ed7d)
- Verified all 9 new enums properly re-exported from `app/models/__init__.py`
- Verified `ROLE_PERMISSIONS` tool counts match spec (planner:15, coder:27, reviewer:15, fixer:22, pm:12, director:12, default:42)
- Confirmed 42 `FunctionTool` instances created by `GlobalToolset`

### Reviewer 6: Test Coverage (a496732)
- Added 33 new tests across 7 test files:
  - `test_git.py`: +5 (worktree lifecycle, diff edge cases)
  - `test_task.py`: +4 (UPDATE action tests)
  - `test_web.py`: +1 (unknown provider)
  - `test_filesystem.py`: +6 (replace_all, multi_edit edge cases, glob sort, grep context)
  - `test_execution.py`: +4 (cwd, idempotency, cache miss, connection error)
  - `test_management.py`: +13 (all previously untested placeholder tools)

## Flagged (Informational — No Fix Required)

- **[ARCH]** `bash_exec` `cwd` parameter is not validated against project boundary. By design — shell tool intentionally provides full access; real boundary is worker-level isolation (Phase 5+).
- **[SPEC-UPDATE]** Spec uses `str` for enum-typed params across sections 3.4–3.8. Code correctly uses typed enums. Spec should be updated in a future pass.
- **[SPEC-UPDATE]** `web_search` spec shows only `(query: str)` but implementation adds `num_results` and `provider` optional params. Not a breaking change.

## Final State
- **Ruff check**: 0 errors
- **Ruff format**: clean
- **Pyright**: 0 errors
- **Pytest**: 273 passed (153 Phase 4 + 120 Phase 1-3)
