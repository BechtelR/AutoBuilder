# Garbage Cleanup

Find dead code, score confidence, prompt for deletion.

## Usage
```
/garbage-cleanup                  # Mode 1: Current git changes (default)
/garbage-cleanup agents           # Mode 2: Named system
/garbage-cleanup --full           # Mode 3: Full codebase (parallel agents)
```

## Scope
{ARGUMENTS}

## Mode Detection

**Mode 1 (default):** No args or unknown arg
- `git diff --name-only` + `git diff --cached --name-only`
- Include same-directory related modules

**Mode 2:** Known system name
| System | Backend | Frontend |
|--------|---------|----------|
| gateway | app/gateway/ | - |
| agents | app/agents/ | - |
| workers | app/workers/ | - |
| events | app/events/ | - |
| models | app/models/, app/db/ | - |
| tools | app/tools/ | - |
| workflows | app/workflows/ | - |
| config | app/config/ | - |
| dashboard | - | dashboard/src/ |
| tests | tests/ | - |

**Mode 3 (`--full`):** Launch parallel garbage-cleanup agents:
1. Backend: app/gateway/, app/models/, app/db/, app/config/
2. Backend: app/agents/, app/workers/, app/tools/, app/workflows/, app/events/
3. Frontend: dashboard/src/
4. Tests: tests/

Aggregate results, dedupe, present unified report.

## Execution

1. **Context:** Read `CLAUDE.md`, `.claude/rules/common-errors.md`
2. **Invoke garbage-cleanup agent** with determined scope
3. **Present findings**, await confirmation
4. **Delete approved**, run validation

## Post-Deletion Validation
```bash
# Backend
uv run ruff check . --fix && uv run pyright && uv run pytest -v --tb=short
# Frontend (from dashboard/)
npm run generate && npm run build
```

If validation fails, restore and investigate.

## Safety
- Never auto-delete without confirmation
- Run validation after deletions
- If uncertain, keep the code
