Review code changes using the reviewer agent.

## Usage

```
/review-changes                          # uncommitted and staged changes (git diff)
/review-changes app/gateway/             # specific directory
/review-changes -3                       # use 3 parallel reviewer agents
```

## Scope

{ARGUMENTS} with optional `-N` for N parallel reviewer agents [default: 1]

Default: uncommitted changes via `git diff`

## Instructions

1. Read and summarize key project context:
   - `CLAUDE.md` (architecture, patterns, commands)
   - `.claude/rules/` (standards.md, common-errors.md)

2. Invoke **reviewer** agent with:
   - Full project context summary, architecture, standards
   - Review scope (files/directories)

3. Reviewer fixes issues directly, reports what changed.
