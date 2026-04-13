[← Architecture Overview](../02-ARCHITECTURE.md)

# Skills System

**AutoBuilder Platform**
**Skill-Based Knowledge Injection Reference**

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Design Principles](#design-principles)
3. [Three-Layer Deterministic Model](#three-layer-deterministic-model)
4. [Skill File Format](#skill-file-format)
5. [Trigger Matching](#trigger-matching)
6. [Supervision-Tier Skill Resolution](#supervision-tier-skill-resolution)
7. [ADK Integration](#adk-integration)
8. [Directory Layout](#directory-layout)
9. [Three-Tier Library](#three-tier-library)
10. [Autonomous Skill Creation](#autonomous-skill-creation)
11. [Scope Estimate](#scope-estimate)

---

## The Problem

Agents need specialized knowledge to produce project-appropriate output: conventions, patterns, strategies, design rules, compliance requirements. But loading everything into every prompt wastes tokens and degrades focus.

The naive approach is "give the agent all the context." This fails at scale: an agent implementing a database migration does not need the API endpoint conventions, the security review checklist, or the design system guidelines. An agent writing a research report does not need coding standards. Injecting irrelevant skills burns tokens, dilutes attention, and produces worse results.

The solution is **progressive disclosure**: agents see a lightweight index of available skills and load full content only when relevant to the current task. The skill system is the mechanism for this.

Skills are an early-priority component because agents without skills are generic. Skills produce workflow-appropriate and project-appropriate output from day one.

---

## Design Principles

### 1. Skills Are Just Files

Markdown files with YAML frontmatter. No database, no custom binary format, no compilation step. Human-readable, version-controllable, editable in any text editor.

### 2. Frontmatter Is the Index

Lightweight metadata in YAML frontmatter enables matching without reading the full content. The skill library parses frontmatter to build an in-memory index; full markdown body loads only on match.

### 3. Progressive Disclosure

The skill index is visible to the system. Full skill content loads into agent context only when a skill matches the current task. An agent implementing an API endpoint gets the API conventions skill; an agent writing a database migration gets the migration patterns skill. Neither gets the other.

### 4. Three-Tier Library

Global skills ship with AutoBuilder (workflow-agnostic best practices). Workflow skills live alongside workflow definitions and provide workflow-specific knowledge. Project-local skills live in the user's repo and override both. A project-local `api-endpoint.md` replaces the workflow or global `api-endpoint.md` entirely.

### 5. Composable

Multiple skills can apply to a single task. An API endpoint deliverable might match `api-endpoint`, `authentication-middleware`, and `error-handling` skills simultaneously. All matched skills load into context.

### 6. No LLM in Matching

Skill matching is deterministic pattern matching: exact string comparison, glob matching, set intersection. No LLM call to decide which skills are relevant. This keeps matching fast, predictable, and debuggable.

### 7. Agent Skills Open Standard

The skill file format follows the [Agent Skills open standard](https://agentskills.io/specification) for interoperability. Our matching engine and deterministic loading via `SkillLoaderAgent` are custom -- ADK's experimental `SkillToolset` uses LLM-discretionary loading which does not meet our requirements for guaranteed knowledge injection. We adopt the standard's file format and progressive disclosure model while keeping full control over the runtime.

---

## Three-Layer Deterministic Model

Skill loading across all agent tiers follows a three-layer deterministic model. No tier assigns skill lists to another tier. The work itself -- role, deliverable metadata, or explicit override -- determines the skills. Deterministically, every time.

| Layer | Name | Trigger Mechanism | Scope | Description |
|-------|------|-------------------|-------|-------------|
| **1** | Role-bound | `always` trigger + `applies_to` | All tiers | Structural skills that always load for a given agent role. Director always gets governance skills. PM always gets management skills. Planner always gets decomposition skills. Configured in skill frontmatter, not assigned per-task. |
| **2** | Context-matched | Trigger-matched against deliverable metadata (type, tags, files) | Workers only | Automatic via `SkillLoaderAgent` at pipeline runtime. Not applicable to Director/PM (they don't process deliverables). Five trigger types: `deliverable_type`, `file_pattern`, `tag_match`, `explicit`, `always`. |
| **3** | Explicit override | `requested_skills` in session state, matched via the `explicit` trigger | All tiers (rare) | For edge cases where the supervisor knows something metadata doesn't capture. Additive -- does not replace Layer 1 or 2 results. |

### When Matching Runs

The same `SkillLibrary.match()` engine handles all tiers. The difference is **when** matching runs:

- **Build time** (Director, PM): Skills are resolved when the agent is constructed. Matched skills are static for the session, baked into instructions at agent build time via `InstructionAssembler`. See [Supervision-Tier Skill Resolution](#supervision-tier-skill-resolution).
- **Pipeline runtime** (Workers): Skills are resolved by `SkillLoaderAgent` as the first pipeline step. Matched skills vary per deliverable context. See [ADK Integration](#adk-integration).

---

## Skill File Format

Each skill is a `SKILL.md` file (per the Agent Skills open standard) with YAML frontmatter. The format follows the standard's three-level progressive disclosure model:

- **L1 (Frontmatter metadata):** Lightweight index fields. Standard fields (`name`, `description`) and AutoBuilder extensions (`triggers`, `tags`, `applies_to`, `priority`, `cascades`) all at top level. Parsed for matching without reading the body.
- **L2 (Instructions/body):** Full markdown content -- conventions, patterns, examples. Loaded into agent context only on match.
- **L3 (References/assets/scripts):** Optional supporting files in `references/`, `assets/`, and `scripts/` subdirectories alongside the skill file. Agents access scripts via file tools (`file_read`, `bash_exec`) -- no automatic execution on skill load.

```markdown
---
name: fastapi-endpoint
description: How to implement a REST API endpoint following project conventions
triggers:
  - deliverable_type: api_endpoint
  - file_pattern: "*/routes/*.py"
tags: [api, http, routing, fastapi]
applies_to: [coder, reviewer]
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

**Standard fields** (top-level, per [Agent Skills spec](https://agentskills.io/specification)):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier. Project-local skills with the same name as a global skill override it. |
| `description` | string | Yes | Human-readable summary. Included in skill index for debugging. Also used as keyword fallback for trigger matching when `triggers` is absent (see [Interoperability](#interoperability)). |

**Extension fields** (AutoBuilder-specific, top-level):

Extension fields are placed at the top level alongside `name`/`description`. This keeps `metadata` spec-compliant (string-to-string map for annotations) while other parsers simply ignore unknown top-level keys. The skill parser uses `extra="ignore"` so unrecognized fields are silently dropped.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `triggers` | list | Yes* | One or more trigger conditions. Skill matches if ANY trigger matches (OR logic). *Not required for third-party skills -- see [Interoperability](#interoperability). |
| `tags` | list of strings | No | Additional matching keywords for `tag_match` trigger type. |
| `applies_to` | list of strings | No | Which agents receive this skill's content. If omitted, applies to all agents. |
| `priority` | integer | No | Higher priority skills load first when multiple skills match. Default: 0. |
| `cascades` | list of objects | No | Skills to load alongside this skill when it matches. See [Skill Cascading](#skill-cascading). |

---

## Trigger Matching

Triggers are read from `triggers` in the skill frontmatter. Skills without `triggers` fall back to `description` keyword matching (see [Interoperability](#interoperability)).

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

### Interoperability

Third-party skills following the standard [Agent Skills](https://agentskills.io/specification) format may not include `triggers`. When `triggers` is absent, `SkillLoaderAgent` falls back to keyword matching against the skill's `description` field. This allows community-authored skills to work out of the box without modification, though explicit triggers provide more precise matching.

### Override Rules

Project-local skills with the same `name` as a global skill replace the global skill entirely. There is no merging of content or trigger definitions. The project-local version is the authoritative version.

---

## Supervision-Tier Skill Resolution

Director and PM operate outside the `DeliverablePipeline` -- they run in chat sessions and work sessions where no `SkillLoaderAgent` executes. Yet they need skills just as deterministically as workers do.

The same `SkillLibrary.match()` engine handles all tiers. The difference is **when** matching runs: at build time for Director/PM (skills are static for the session, baked into instructions), at pipeline runtime for workers (skills vary per deliverable). No separate mechanism -- same matching engine, same trigger system, different call site.

### How It Works

When the Director or PM agent is constructed (in `build_chat_session_agent()`, `build_work_session_agents()`, or `run_director_turn()`), the build code calls `skill_library.match()` with a tier-specific context (agent role, no deliverable metadata). Matched skills are passed into the agent's `InstructionContext` and baked into the assembled instructions at construction time.

```python
# Director build-time skill resolution
director_skill_ctx = SkillMatchContext(agent_role="director")
director_skills = skill_library.match(director_skill_ctx)
director_ctx = InstructionContext(loaded_skills=director_skills, ...)

# PM build-time skill resolution (separate context)
pm_skill_ctx = SkillMatchContext(agent_role="pm")
pm_skills = skill_library.match(pm_skill_ctx)
pm_ctx = InstructionContext(loaded_skills=pm_skills, ...)
```

### Key Constraints

- **Director and PM get separate `InstructionContext` instances.** They do not share a single skill context. Each tier's role-bound skills are independently resolved.
- **Role-bound skills with `always` trigger + `applies_to: [director]`** load every time the Director is invoked -- whether for a chat session, work session, or Director queue processing. The skill is part of the Director's operational identity.
- **Skills with `always` trigger and no `applies_to` field** load for ALL agents across all tiers -- Director, PM, and every worker. This is the mechanism for project-wide conventions that apply universally.

---

## ADK Integration

Skills integrate into the agent system at two call sites: build-time resolution for Director/PM (see above) and pipeline-runtime resolution for workers via `SkillLoaderAgent`. The entire skill loading process runs inside worker processes.

### SkillLoaderAgent (Workers Only)

`SkillLoaderAgent` is a deterministic `CustomAgent` that runs as the first step in every `DeliverablePipeline`, before any LLM agent. It resolves skills against the current deliverable's context -- not the Director's or PM's context.

```python
class SkillLoaderAgent(BaseAgent):
    """Deterministic agent that resolves and loads relevant skills into state.
    Runs only in DeliverablePipeline (worker tier). Director/PM receive
    skills at build time via direct SkillLibrary.match() calls."""

    async def _run_async_impl(self, ctx):
        # Build matching context from current deliverable state
        match_context = context_from_state(ctx)

        # Deterministic matching — no LLM call
        matched = skill_library.match(match_context)

        # Load full content for matched skills (with applies_to metadata)
        loaded = [skill_library.load(entry) for entry in matched]

        # Write to state — available to all subsequent agents
        # Content carries applies_to metadata for per-agent filtering
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": {
                    s.entry.name: {"content": s.content, "applies_to": s.entry.applies_to}
                    for s in loaded
                },
                "loaded_skill_names": [s.entry.name for s in loaded],
            })
        )
```

### Why This Approach

| Requirement | How SkillLoaderAgent Satisfies It |
|---|---|
| **Observable** | Skill resolution appears in the event stream. You can see exactly which skills loaded for any deliverable execution. |
| **Deterministic** | Cannot be skipped by LLM judgment. It is a workflow step, not a suggestion. |
| **Load once, use many** | Skills load into session state once. All subsequent agents in the pipeline (`planner`, `coder`, `reviewer`) read from `{loaded_skills}`. |
| **Debuggable** | If an agent produces poor output, check `loaded_skill_names` in state to verify the right skills were loaded. |
| **Traceable** | ADK's event stream captures the skill loading event alongside LLM agent events. Unified observability. |

### How Agents Consume Skills

The `applies_to` field in skill frontmatter controls which agents receive the skill. The `InstructionAssembler` (Decision #50) filters loaded skills during `assemble()` to only include those relevant to the current agent. Filtering happens at assembly time using the `applies_to` metadata stored alongside content in session state. Skills without an `applies_to` field are delivered to all agents. Skills are ordered by priority in the assembled instructions.

For workers, the assembler reads `loaded_skills` from session state (written by `SkillLoaderAgent`) and filters per-agent. For Director/PM, skills are already in the `InstructionContext` from build-time resolution and are filtered identically by the assembler.

The assembler composes SKILL-type fragments from loaded skills alongside IDENTITY, GOVERNANCE, PROJECT, and TASK fragments into the final instruction string.

---

## Directory Layout

Per the Agent Skills open standard, each skill lives in its own directory named after the skill, containing a `SKILL.md` file and optional `references/`, `assets/`, and `scripts/` subdirectories.

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
├── planning/
│   └── task-decomposition/
│       └── SKILL.md
└── authoring/
    ├── agent-definition/
    │   ├── SKILL.md               # How to author agent definition files
    │   └── references/
    │       ├── llm-agent.md       # Template: LlmAgent definition
    │       └── custom-agent.md    # Template: CustomAgent definition
    ├── skill-authoring/
    │   ├── SKILL.md               # How to author skills (SKILL.md format, frontmatter, triggers)
    │   └── references/
    │       └── skill-template.md  # Template: skill file with all frontmatter fields
    ├── workflow-authoring/
    │   ├── SKILL.md               # How to author workflows (WORKFLOW.yaml, pipeline.py, agents/)
    │   └── references/
    │       └── workflow-manifest.yaml  # Template: WORKFLOW.yaml with all fields
    └── project-conventions/
        └── SKILL.md               # How to configure project-level overrides (agents, skills, conventions)
├── files/                          # File-editing skills (Anthropic third-party)
│   ├── docx/
│   │   ├── SKILL.md               # Word document creation, editing, analysis
│   │   └── scripts/               # Helper scripts (unpack, pack, validate, etc.)
│   ├── xlsx/
│   │   ├── SKILL.md               # Spreadsheet creation and editing
│   │   └── scripts/
│   ├── pptx/
│   │   ├── SKILL.md               # Presentation creation and editing
│   │   ├── editing.md             # Editing workflow guide
│   │   ├── pptxgenjs.md           # Creation from scratch guide
│   │   └── scripts/
│   └── pdf/
│       ├── SKILL.md               # PDF processing and form filling
│       ├── forms.md               # PDF form filling guide
│       ├── reference.md           # Advanced PDF operations
│       └── scripts/
└── governance/                     # Supervision-tier role-bound skills
    ├── director-oversight/
    │   └── SKILL.md               # Director governance and oversight (always, applies_to: [director])
    └── pm-management/
        └── SKILL.md               # PM project management (always, applies_to: [pm])
```

### Project-Local Skills (Live in the User's Repo)

```
user-project/.agents/skills/
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

## Three-Tier Library

### Global Tier

Ships with AutoBuilder. Contains framework-agnostic best practices and common patterns:

- How to structure a REST API endpoint (general principles)
- How to write effective unit tests (general patterns)
- How to handle errors consistently (common strategies)
- How to decompose a specification into tasks (planning guidance)
- How to evaluate source quality (research guidance)
- How to structure a deliverable for review (general review patterns)

Global skills are useful out of the box but intentionally generic. They provide a baseline that most projects benefit from.

### Workflow Tier

Lives alongside workflow definitions at `app/workflows/{name}/skills/`. Contains workflow-specific knowledge:

- Coding conventions and patterns specific to auto-code
- Research methodology and citation rules for auto-research
- Domain-specific quality criteria and validation rules

Workflow skills override global skills by name but are overridden by project-local skills. They encode the expertise a workflow accumulates without polluting the global tier.

### Project-Local Tier

Lives in the user's repository at `.agents/skills/`. Contains project-specific conventions:

- "Our API endpoints use FastAPI with async SQLAlchemy and return Pydantic v2 response models"
- "Our tests use pytest with the `conftest.py` fixtures defined in `tests/conftest.py`"
- "All database migrations must be reviewed for backward compatibility"
- "Authentication uses Supabase JWT tokens verified via JWKS endpoint"

### Override Behavior

Skills with the same `name` are replaced entirely by the narrower scope. There is no merging.

| Global Skill | Workflow Skill | Project-Local Skill | Result |
|---|---|---|---|
| `api-endpoint` (generic REST) | `api-endpoint` (auto-code conventions) | `api-endpoint` (FastAPI-specific) | Project-local wins |
| `unit-test-patterns` (general) | *(none)* | *(none)* | Global loads |
| *(none)* | *(none)* | `auth-middleware` (project-specific) | Project-local loads |
| `security-review` (OWASP basics) | `security-review` (workflow compliance) | *(none)* | Workflow wins |

### Scan Order

The skill library scans global skills first, then workflow skills, then project-local skills. Each tier's entries overwrite earlier entries with matching names in the index.

```python
class SkillLibrary:
    def __init__(
        self,
        global_dir: Path,
        workflow_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        self._index: dict[str, SkillEntry] = {}
        self._scan(global_dir)              # Global skills load first
        if workflow_dir:
            self._scan(workflow_dir)          # Workflow skills override global
        if project_dir:
            self._scan(project_dir)          # Project-local skills override all
```

### Caching

The skill index is cached in Redis for fast access across worker invocations. Cache is invalidated when skill files change (detected via file modification timestamps during periodic rescans or explicit cache invalidation via the gateway API).

---

## Skill Cascading

Skills can declare `cascades` in their frontmatter to trigger loading of related reference materials. This keeps individual skills small and focused while enabling rich context through composition.

```yaml
---
name: api-endpoint
description: REST API endpoint conventions
triggers:
  - deliverable_type: api_endpoint
cascades:
  - reference: error-handling
  - reference: project-conventions
---
```

When the `api-endpoint` skill matches, the `SkillLoaderAgent` also loads the `error-handling` and `project-conventions` skills as cascaded dependencies. This avoids duplicating shared guidance across multiple skills.

### Resolution

The `SkillLoaderAgent` resolves cascades after primary matching:

1. Match skills against the current task context (existing trigger logic)
2. Collect `cascades` from all matched skills
3. Load each cascaded skill by name from the skill library
4. Recurse: if cascaded skills themselves declare cascades, resolve those too
5. Circular cascades are prevented by tracking visited skill names during resolution

Cascaded skills respect the same three-tier override rules: a narrower-scope skill overrides a broader-scope skill with the same name, whether loaded directly or via cascade.

---

## Autonomous Skill Creation

Agents (Director, PM, or workers) can create new SKILL.md files during execution, guided by the `skill-authoring` skill. This enables the system to encode learned patterns as reusable knowledge without human intervention.

### How It Works

1. An agent writes a SKILL.md file to the project-local skills directory (`.agents/skills/`) via standard file tools
2. The system validates the file's frontmatter against the same rules used during indexing (required `name` and `description` fields, valid YAML)
3. On the next cache rebuild or explicit invalidation, the new skill is indexed and available to all subsequent pipeline executions
4. Project-local override rules apply normally -- a new skill with the same `name` as a global skill replaces it for that project

### Validation

The frontmatter validation logic is available as a callable function that agents or tools can invoke before writing. This allows pre-validation without requiring a cache rebuild to discover errors.

### The Skill-Authoring Skill

The `skill-authoring` global skill teaches agents how to produce valid SKILL.md files. It covers frontmatter structure, trigger design, progressive disclosure principles (body under 3000 words, detailed content in `references/`), and includes a `references/skill-template.md` with all supported frontmatter fields annotated.

### Constraints

- **No self-updating skills.** Skills cannot edit their own SKILL.md based on performance feedback (deferred to Phase 7a+).
- **No `scripts/` execution.** Skills can include scripts in their directory for reference, but automatic execution is deferred.
- **No marketplace.** The file format is the interop layer. Drop SKILL.md files in the project directory.

---

## Scope Estimate

The core skills implementation is approximately 320-400 lines of Python:

| Component | Estimated Lines | Responsibility |
|---|---|---|
| `SkillEntry` | ~40 | Pydantic model for frontmatter metadata (expanded: triggers, tags, priority, cascades, path) |
| `SkillLibrary` | ~130 | Index building, matching, loading, three-tier scan, Redis caching |
| `SkillLoaderAgent` | ~55 | CustomAgent that runs matching, cascade resolution, and writes state (workers only) |
| `Frontmatter parser` | ~35 | YAML frontmatter extraction from markdown files, validation function |
| `Trigger matchers` | ~60 | Per-type matching logic (exact, glob, set intersection, description keyword fallback) |
| `InstructionAssembler integration` | ~50 | Filter loaded skills by `applies_to` per agent (SKILL fragments), curly brace escaping |
| `Build-time resolution` | ~20 | Director/PM skill matching at agent construction (call sites in build functions) |
| **Total** | **~390** | |

This is disproportionate value for the effort. Skills transform agents from generic LLM wrappers into project-aware specialists. Without skills, deliverable 47 gets the same generic instructions as deliverable 1. With skills, deliverable 47 gets the domain-specific conventions, patterns, and requirements relevant to its type — whether that's API endpoint conventions for code, citation standards for research, or brand guidelines for marketing.

---

## See Also

- [Agents](./agents.md) -- agent architecture, composition, plan/execute separation
- [Tools](./tools.md) -- FunctionTool vs CustomAgent, MCP guidance, tool isolation
- [Workflows](./workflows.md) -- pluggable workflow system, manifests, registry
- [State & Memory](./state.md) -- ADK 4-scope state, session rewind, cross-session memory

---

**Document Version:** 4.1
**Last Updated:** 2026-03-11
**Status:** Phase 6 Complete -- Extension fields updated to top-level placement per DD-1
