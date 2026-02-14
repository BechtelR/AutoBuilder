# Phase 99 Spec: Build Pipeline Mock Test
*Generated: 2026-02-13*

## Overview

Mock phase to validate the `/build-phase` workflow end-to-end. Three trivial deliverables exercise batch ordering, parallel delegation, context injection, skill matching, validation gates, review, and completion protocol. All deliverables are self-contained in `app/lib/` and `tests/lib/` — no infrastructure dependencies.

## Features

- String utility functions for text normalization
- Unit tests validating the utilities

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 0: Project Scaffold | MET | `app/lib/__init__.py` exists, `uv run pyright` passes |

## Design Decisions

### DD-1: Location
Utilities go in `app/lib/text.py` — a new module within the existing `app/lib/` package. Tests in `tests/lib/test_text.py`.

### DD-2: No Dependencies
Functions are pure Python with no external imports. This keeps the mock isolated.

## Deliverables

### P99.D1: Text Normalization Utility
**Files:** `app/lib/text.py`
**Depends on:** —
**Description:** Create a module with two pure functions: `slugify(text: str) -> str` (lowercase, replace spaces/special chars with hyphens, strip leading/trailing hyphens) and `truncate(text: str, max_length: int, suffix: str = "...") -> str` (truncate with suffix if exceeds max_length, return unchanged if within limit).
**Requirements:** *(what must be true — checked off during build as acceptance criteria)*
- [x] `slugify("Hello World!")` returns `"hello-world"`
- [x] `slugify("  Multiple   Spaces  ")` returns `"multiple-spaces"`
- [x] `truncate("short", 10)` returns `"short"`
- [x] `truncate("this is long text", 10)` returns `"this is..."`
- [x] `truncate("exact len!", 10)` returns `"exact len!"`
- [x] Both functions have full type hints passing pyright strict
- [x] Functions importable from `app.lib`
**Validation:**
- `uv run pyright app/lib/text.py`

---

### P99.D2: Text Utility Tests
**Files:** `tests/lib/test_text.py`
**Depends on:** P99.D1
**Description:** Pytest test suite covering all requirements from P99.D1. Each requirement maps to at least one test case. Use parametrize for edge cases.
**Requirements:** *(what must be true — checked off during build as acceptance criteria)*
- [x] All P99.D1 requirements have corresponding test assertions
- [x] At least one parametrized test
- [x] All tests pass: `uv run pytest tests/lib/test_text.py -v`
**Validation:**
- `uv run pytest tests/lib/test_text.py -v`

---

### P99.D3: Export from app.lib
**Files:** `app/lib/__init__.py`
**Depends on:** P99.D1
**Description:** Export `slugify` and `truncate` from `app.lib` so they're accessible as `from app.lib import slugify, truncate`.
**Requirements:** *(what must be true — checked off during build as acceptance criteria)*
- [x] `from app.lib import slugify, truncate` works
- [x] Pyright passes on `app/lib/__init__.py`
**Validation:**
- `uv run python -c "from app.lib import slugify, truncate; print(slugify('Hello World'))"` prints `hello-world`

---

## Build Order

```
Batch 1: P99.D1
  D1: Text utility functions — app/lib/text.py

Batch 2 (parallel): P99.D2, P99.D3
  D2: Test suite — tests/lib/test_text.py (depends on D1)
  D3: Exports — app/lib/__init__.py (depends on D1)
```

## Completion Contract Traceability

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | `slugify` and `truncate` functions exist with correct behavior | P99.D1 | `uv run pyright app/lib/text.py` |
| 2 | All tests pass | P99.D2 | `uv run pytest tests/lib/test_text.py -v` |
| 3 | Functions importable from `app.lib` | P99.D3 | `uv run python -c "from app.lib import slugify, truncate"` |
| 4 | Quality gates pass | P99.D1, D2, D3 | `uv run ruff check . && uv run pyright && uv run pytest` |

## Research Notes

No research needed — pure Python string operations.
