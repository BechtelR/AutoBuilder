---
name: security-review
description: This skill provides a security review checklist for code changes, covering input validation, credential handling, injection prevention, and secure defaults.
triggers:
  - tag_match: security
tags: [security, validation, injection, credentials, owasp]
applies_to: [reviewer]
priority: 15
---

# Security Review

This skill provides a focused security review process for AutoBuilder code changes. Apply it to any change that touches data ingestion, authentication, external integrations, or state management.

## Input Validation

All external data enters through Pydantic models at gateway boundaries. Review these points:

- Every route accepts a typed Pydantic request model — never a raw `dict` or `Any`
- String fields have explicit length constraints (`max_length=N`) where the column has a defined size
- Enum fields use AutoBuilder's typed enums — strings rejected by Pydantic before reaching business logic
- Path parameters (`project_id`, `deliverable_id`) are validated as expected format (UUID or slug) before database queries
- File paths supplied by users are resolved and constrained to expected directories — no traversal

Verify `validate_skill_frontmatter()` and similar validators return errors rather than raise uncaught exceptions. Validators must be safe to call on arbitrary user input.

## Credential Handling

- No API keys, tokens, passwords, or connection strings in source code
- Credentials sourced exclusively from environment variables
- No credentials in log output — verify `logger.*` calls don't format secrets
- Database connection strings in `AUTOBUILDER_DB_URL` — never constructed inline from components
- Redis URL in `AUTOBUILDER_REDIS_URL` — never hardcoded
- LLM provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`) from env only

When reviewing agent instructions or skill bodies: confirm no literal credentials appear in SKILL.md files or agent definition frontmatter.

## SQL Injection Prevention

AutoBuilder uses SQLAlchemy with parameterized queries — raw SQL strings are a red flag.

- All database queries use SQLAlchemy ORM or `text()` with bound parameters
- Never concatenate user input into query strings
- `filter(Model.column == user_value)` — correct, parameterized by SQLAlchemy
- `text(f"WHERE name = '{user_value}'")` — injection vector, reject immediately
- Raw `execute()` calls require explicit review — must use `bindparams()`

## XSS and Injection in Generated Content

AutoBuilder generates code and instructions for agents. Review content that could be injected:

- Skill descriptions and agent instructions sourced from database should be treated as untrusted if project-scope
- Project-scope skills have a trust ceiling (Decision #58): `type: llm` only, `tool_role` ceiling applied
- Skill body content loaded into agent context is sandboxed by the session state auth tier prefixes
- Markdown rendered in the dashboard must be sanitized before display

## Secure Defaults

- New API endpoints default to requiring authentication when auth is implemented (Phase 7+) — no `public=True` shortcuts
- New database columns with security implications (e.g., `is_admin`, `role`) default to least-privilege values
- Skill loading respects trust model: project-scope skills gated on trust check, never auto-trusted
- Error responses include structured `{"code": "...", "message": "..."}` — never expose stack traces, internal paths, or database errors to clients

## Audit Trail

Significant state changes must publish to Redis Streams for audit:

- Project creation, deletion, archival
- Director formation state changes
- CEO queue resolutions
- Credential or configuration changes (when implemented)

Verify that new state transitions in services or workers include an event publish call. Silent state changes are an audit gap.

## Dependency and Supply Chain

When adding new dependencies:

- Verify the package is widely used and maintained
- Pin versions in `pyproject.toml` — no floating `>=latest`
- Check for known CVEs before merging
- Prefer packages already in the stack over new introductions

## Checklist

- [ ] All external inputs pass through Pydantic models with explicit types
- [ ] No credentials in source, logs, or error responses
- [ ] SQL uses parameterized queries — no string interpolation
- [ ] Project-scope skills have trust ceiling applied
- [ ] Significant state changes publish to Redis Streams
- [ ] Error responses are structured, not raw exceptions
- [ ] New dependencies are pinned and reviewed for CVEs
