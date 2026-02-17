# Skills System

**AutoBuilder Platform**
**Skill-Based Knowledge Injection Reference**

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Design Principles](#design-principles)
3. [Skill File Format](#skill-file-format)
4. [Trigger Matching](#trigger-matching)
5. [ADK Integration](#adk-integration)
6. [Directory Layout](#directory-layout)
7. [Two-Tier Library](#two-tier-library)
8. [Scope Estimate](#scope-estimate)

---

## The Problem

Agents need specialized knowledge to produce project-appropriate output: conventions, patterns, strategies, design rules, compliance requirements. But loading everything into every prompt wastes tokens and degrades focus.

The naive approach is "give the agent all the context." This fails at scale: an agent implementing a database migration does not need the API endpoint conventions, the security review checklist, or the design system guidelines. An agent writing a research report does not need coding standards. Injecting irrelevant skills burns tokens, dilutes attention, and produces worse results.

The solution is **progressive disclosure**: agents see a lightweight index of available skills and load full content only when relevant to the current task. The skill system is the mechanism for this.

Skills are a Phase 1 component (Architecture Decision #14) because agents without skills are generic. Skills produce workflow-appropriate and project-appropriate output from day one.

---

## Design Principles

### 1. Skills Are Just Files

Markdown files with YAML frontmatter. No database, no custom binary format, no compilation step. Human-readable, version-controllable, editable in any text editor.

### 2. Frontmatter Is the Index

Lightweight metadata in YAML frontmatter enables matching without reading the full content. The skill library parses frontmatter to build an in-memory index; full markdown body loads only on match.

### 3. Progressive Disclosure

The skill index is visible to the system. Full skill content loads into agent context only when a skill matches the current task. An agent implementing an API endpoint gets the API conventions skill; an agent writing a database migration gets the migration patterns skill. Neither gets the other.

### 4. Two-Tier Library

Global skills ship with AutoBuilder (workflow-agnostic best practices). Project-local skills live in the user's repo and override globals with project-specific conventions. A project-local `api-endpoint.md` replaces the global `api-endpoint.md` entirely.

### 5. Composable

Multiple skills can apply to a single task. An API endpoint feature might match `api-endpoint`, `authentication-middleware`, and `error-handling` skills simultaneously. All matched skills load into context.

### 6. No LLM in Matching

Skill matching is deterministic pattern matching: exact string comparison, glob matching, set intersection. No LLM call to decide which skills are relevant. This keeps matching fast, predictable, and debuggable.

### 7. Agent Skills Open Standard

The skill file format follows the [Agent Skills open standard](https://agentskills.io/specification) for interoperability. Our matching engine and deterministic loading via `SkillLoaderAgent` are custom -- ADK's experimental `SkillToolset` uses LLM-discretionary loading which does not meet our requirements for guaranteed knowledge injection. We adopt the standard's file format and progressive disclosure model while keeping full control over the runtime.

---

## Skill File Format

Each skill is a `SKILL.md` file (per the Agent Skills open standard) with YAML frontmatter. The format follows the standard's three-level progressive disclosure model:

- **L1 (Frontmatter metadata):** Lightweight index fields -- name, description, triggers, tags. Parsed for matching without reading the body.
- **L2 (Instructions/body):** Full markdown content -- conventions, patterns, examples. Loaded into agent context only on match.
- **L3 (References/assets):** Optional supporting files in `references/` and `assets/` subdirectories alongside the skill file.

```markdown
---
name: fastapi-endpoint
description: How to implement a REST API endpoint following project conventions
triggers:
  - deliverable_type: api_endpoint
  - file_pattern: "*/routes/*.py"
tags: [api, http, routing, fastapi]
applies_to: [code_agent, review_agent]
priority: 10
---

## API Endpoint Implementation

### Route Structure

All routes follow the pattern:

```python
@router.post("/resource", response_model=ResourceResponse)
async def create_resource(
    request: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceResponse:
    """Create a new resource."""
    ...
```

### Error Handling

Use the project's standard error response format:
- 400 for validation errors (Pydantic handles automatically)
- 401 for authentication failures
- 403 for authorization failures
- 404 for missing resources
- 500 for unexpected errors (logged, generic message returned)

### Testing Pattern

Every endpoint requires:
1. Happy path test
2. Authentication failure test
3. Authorization failure test (if applicable)
4. Validation error test
5. Not-found test (for resource-specific endpoints)

[... full implementation guide continues ...]
```

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier. Project-local skills with the same name as a global skill override it. |
| `description` | string | Yes | Human-readable summary. Included in skill index for debugging. |
| `triggers` | list | Yes | One or more trigger conditions. Skill matches if ANY trigger matches (OR logic). |
| `tags` | list of strings | No | Additional matching keywords for `tag_match` trigger type. |
| `applies_to` | list of strings | No | Which agents receive this skill's content. If omitted, applies to all agents. |
| `priority` | integer | No | Higher priority skills load first when multiple skills match. Default: 0. |

---

## Trigger Matching

### Trigger Types

| Trigger Type | Matches Against | Match Logic |
|---|---|---|
| `deliverable_type` | `state["current_deliverable_type"]` | Exact string match |
| `file_pattern` | Any file in `state["target_files"]` | Glob pattern match |
| `tag_match` | Any tag in `state["deliverable_tags"]` | Set intersection (any overlap) |
| `explicit` | `state["requested_skills"]` | Named request (agent or user requested this skill by name) |
| `always` | Always matches for specified agents | Unconditional — the skill loads on every invocation for the agents listed in `applies_to` |

### OR Logic

A skill matches if **any** of its triggers match. This is intentional: triggers describe the different contexts where a skill is relevant. An API endpoint skill might trigger on both `deliverable_type: api_endpoint` AND `file_pattern: "*/routes/*.py"` because either condition means the skill is relevant.

```yaml
triggers:
  - deliverable_type: api_endpoint       # Matches if deliverable type is "api_endpoint"
  - file_pattern: "*/routes/*.py"        # OR if any target file is in a routes directory
```

If the deliverable type is `api_endpoint` but no target files exist yet (initial generation), the skill still matches via the first trigger. If the deliverable type is `refactor` but the target files are in `routes/`, the skill still matches via the second trigger.

### Override Rules

Project-local skills with the same `name` as a global skill replace the global skill entirely. There is no merging of content or trigger definitions. The project-local version is the authoritative version.

---

## ADK Integration

Skills are available to all agent tiers — Director loads governance skills, PMs load project management skills, and workers load task-specific skills. Skills integrate into pipelines via `SkillLoaderAgent`, a deterministic `CustomAgent` that runs as the first step before any LLM agent. The entire skill loading process runs inside worker processes as part of the ADK pipeline.

### SkillLoaderAgent Implementation

```python
class SkillLoaderAgent(BaseAgent):
    """Deterministic agent that resolves and loads relevant skills into state."""

    async def _run_async_impl(self, ctx):
        # Build matching context from current session state
        match_context = context_from_state(ctx)

        # Deterministic matching — no LLM call
        matched = skill_library.match(match_context)

        # Load full content for matched skills
        loaded = [skill_library.load(entry) for entry in matched]

        # Write to state — available to all subsequent agents
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": {s.entry.name: s.content for s in loaded},
                "loaded_skill_names": [s.entry.name for s in loaded],
            })
        )
```

### Why This Approach

| Requirement | How SkillLoaderAgent Satisfies It |
|---|---|
| **Observable** | Skill resolution appears in the event stream. You can see exactly which skills loaded for any feature execution. |
| **Deterministic** | Cannot be skipped by LLM judgment. It is a workflow step, not a suggestion. |
| **Load once, use many** | Skills load into session state once. All subsequent agents in the pipeline (`plan_agent`, `code_agent`, `review_agent`) read from `{loaded_skills}`. |
| **Debuggable** | If an agent produces poor output, check `loaded_skill_names` in state to verify the right skills were loaded. |
| **Traceable** | ADK's event stream captures the skill loading event alongside LLM agent events. Unified observability. |

### How Agents Consume Skills

Downstream LLM agents read skills from state via template injection in their instructions:

```python
code_agent = LlmAgent(
    name="code_agent",
    instruction="""
    Implement the feature according to the plan.

    Implementation plan:
    {implementation_plan}

    Project conventions and patterns to follow:
    {loaded_skills}

    Project coding standards:
    {app:coding_standards}
    """,
    output_key="code_output",
)
```

The `applies_to` field in skill frontmatter controls which agents receive the skill. If a skill specifies `applies_to: [code_agent, review_agent]`, the `InstructionProvider` filters loaded skills to only include those relevant to the current agent.

---

## Directory Layout

Per the Agent Skills open standard, each skill lives in its own directory named after the skill, containing a `SKILL.md` file and optional `references/` and `assets/` subdirectories.

### Global Skills (Ship with AutoBuilder)

```
app/skills/
├── code/
│   ├── api-endpoint/
│   │   ├── SKILL.md
│   │   └── references/            # Optional: supporting docs
│   ├── data-model/
│   │   └── SKILL.md
│   └── database-migration/
│       └── SKILL.md
├── research/
│   ├── source-evaluation/
│   │   └── SKILL.md
│   └── citation-standards/
│       └── SKILL.md
├── review/
│   ├── security-review/
│   │   └── SKILL.md
│   └── performance-review/
│       └── SKILL.md
├── test/
│   └── unit-test-patterns/
│       └── SKILL.md
└── planning/
    └── task-decomposition/
        └── SKILL.md
```

### Project-Local Skills (Live in the User's Repo)

```
user-project/.app/skills/
├── code/
│   ├── api-endpoint/
│   │   └── SKILL.md               # Overrides global with project conventions
│   └── auth-middleware/
│       └── SKILL.md               # Project-specific, no global equivalent
└── review/
    └── compliance-review/
        └── SKILL.md               # Project-specific compliance rules
```

### Directory Organization

Top-level subdirectories (`code/`, `review/`, `test/`, `planning/`) are organizational conventions, not functional boundaries. The skill library scans all `SKILL.md` files recursively. These categories help humans navigate the skill library but do not affect matching or loading behavior. Each skill's own directory can contain `references/` and `assets/` subdirs for L3 supporting content.

---

## Two-Tier Library

### Global Tier

Ships with AutoBuilder. Contains framework-agnostic best practices and common patterns:

- How to structure a REST API endpoint (general principles)
- How to write effective unit tests (general patterns)
- How to handle errors consistently (common strategies)
- How to decompose a specification into tasks (planning guidance)
- How to evaluate source quality (research guidance)
- How to structure a deliverable for review (general review patterns)

Global skills are useful out of the box but intentionally generic. They provide a baseline that most projects benefit from.

### Project-Local Tier

Lives in the user's repository at `.app/skills/`. Contains project-specific conventions:

- "Our API endpoints use FastAPI with async SQLAlchemy and return Pydantic v2 response models"
- "Our tests use pytest with the `conftest.py` fixtures defined in `tests/conftest.py`"
- "All database migrations must be reviewed for backward compatibility"
- "Authentication uses Supabase JWT tokens verified via JWKS endpoint"

### Override Behavior

Project-local skills with the same `name` as a global skill replace the global entirely. There is no merging.

| Global Skill | Project-Local Skill | Result |
|---|---|---|
| `api-endpoint` (generic REST patterns) | `api-endpoint` (FastAPI-specific conventions) | Project-local wins |
| `unit-test-patterns` (general testing) | *(none)* | Global loads |
| *(none)* | `auth-middleware` (project-specific) | Project-local loads |
| `security-review` (OWASP basics) | `security-review` (project compliance rules) | Project-local wins |

### Scan Order

The skill library scans global skills first, then project-local skills. Project-local entries overwrite global entries with matching names in the index.

```python
class SkillLibrary:
    def __init__(self, global_dir: Path, project_dir: Path | None = None):
        self._index: dict[str, SkillEntry] = {}
        self._scan(global_dir)              # Global skills load first
        if project_dir:
            self._scan(project_dir)          # Project-local skills override
```

### Caching

The skill index is cached in Redis for fast access across worker invocations. Cache is invalidated when skill files change (detected via file modification timestamps during periodic rescans or explicit cache invalidation via the gateway API).

---

## Scope Estimate

The core skills implementation is approximately 300-400 lines of Python:

| Component | Estimated Lines | Responsibility |
|---|---|---|
| `SkillEntry` | ~30 | Pydantic model for frontmatter metadata |
| `SkillLibrary` | ~120 | Index building, matching, loading, two-tier scan |
| `SkillLoaderAgent` | ~40 | CustomAgent that runs matching and writes state |
| `Frontmatter parser` | ~30 | YAML frontmatter extraction from markdown files |
| `Trigger matchers` | ~60 | Per-type matching logic (exact, glob, set intersection) |
| `InstructionProvider integration` | ~40 | Filter loaded skills by `applies_to` per agent |
| **Total** | **~320** | |

This is disproportionate value for the effort. Skills transform agents from generic LLM wrappers into project-aware specialists. Without skills, deliverable 47 gets the same generic instructions as deliverable 1. With skills, deliverable 47 gets the domain-specific conventions, patterns, and requirements relevant to its type — whether that's API endpoint conventions for code, citation standards for research, or brand guidelines for marketing.

---

**Document Version:** 2.1
**Last Updated:** 2026-02-16
**Status:** Framework Validated -- Prototyping Phase
