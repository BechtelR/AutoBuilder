---
name: project-conventions
description: This skill provides guidance for configuring project-level overrides in AutoBuilder, covering the .agents/ directory structure, agent definition overrides, project-local skills, and configuration patterns. Load when setting up a new project's AutoBuilder configuration, adding project-specific agent overrides, creating project-local skills, or customizing agent behavior for a specific repository.
triggers:
  - always: true
tags: [authoring, project, conventions, configuration]
applies_to: [coder, planner]
priority: 5
---

# Project Conventions Configuration

This skill covers how to configure project-level overrides in AutoBuilder. The `.agents/` directory at the project root is the single place for project-specific customization — agent overrides, local skills, and project conventions that apply only to this repository.

## Directory Structure

```
project-root/
└── .agents/
    ├── agents/              # Project-scope agent definition overrides
    │   ├── coder.md         # Override the global "coder" agent
    │   └── reviewer.md      # Override the global "reviewer" agent
    └── skills/              # Project-local skills
        ├── api-endpoint/    # Override global "api-endpoint" skill
        │   └── SKILL.md
        └── auth-middleware/ # New skill unique to this project
            └── SKILL.md
```

The `.agents/` directory is a project-local namespace. AutoBuilder discovers it at the project root and applies its contents on top of the global and workflow scopes.

## Agent Definition Overrides (`.agents/agents/`)

Place Markdown files with YAML frontmatter in `.agents/agents/` to override agent definitions for this project. The filename (without `.md`) is the agent role name to override.

```yaml
---
# .agents/agents/coder.md
name: coder
type: llm
model_role: CODE
---

You are the Coder agent for this project.

Follow the project's TypeScript conventions documented in CONTRIBUTING.md.
All components use the design system defined in src/design-system/.
Never use inline styles — use CSS modules or design tokens.
```

### Project-Scope Restrictions

Two hard restrictions apply to project-scope agent definitions:

**`type: llm` only** — Project definitions cannot declare `type: custom`. Custom agents require Python code deployed with AutoBuilder. A project cannot inject arbitrary Python execution through agent definitions.

**`tool_role` ceiling** — Project definitions cannot grant a tool role higher than the workflow's declared ceiling. Use this to *restrict* tool access for a project (e.g., `read_only` for a documentation-only project), not to escalate it.

### Partial Override Pattern

To change only the model or tool configuration without rewriting the full instruction body, create a frontmatter-only file (no body content). The instruction body is inherited from the workflow or global scope:

```yaml
---
# .agents/agents/planner.md
# Change the model but keep the global planner instructions
name: planner
type: llm
model_role: PLAN
---
```

## Project-Local Skills (`.agents/skills/`)

Place skill directories in `.agents/skills/` to add or override skills for this project. Each skill follows the standard format — a named directory containing `SKILL.md`.

### Override an Existing Skill

Create a directory matching the global skill's `name` to replace it entirely:

```
.agents/skills/
└── api-endpoint/        # Replaces global "api-endpoint" skill
    └── SKILL.md
```

The project-local `api-endpoint` skill completely replaces the global one — no merging of content or triggers. Write the full skill content for this project's specific conventions.

### Add a New Project-Specific Skill

Create a directory with a unique name to add a skill that has no global equivalent:

```
.agents/skills/
└── auth-middleware/     # No global equivalent — purely additive
    └── SKILL.md
```

New project-local skills are indexed alongside global skills. They match against the same trigger system. A project-local skill is not automatically loaded by any agent — it must have appropriate triggers.

## Configuration Patterns

### When to Override vs When to Request Explicitly

**Override** (place in `.agents/`) when the customization should apply automatically to all relevant deliverables:
- Project uses a specific framework or library with conventions different from the global skill
- Agent instructions need project-specific context (repo structure, key files, team conventions)
- A global skill's guidance is wrong or counterproductive for this project

**Request explicitly** (`requested_skills` in session state) when the customization applies only to specific deliverables, not all:
- A special compliance checklist applies only to payment-related endpoints
- A performance profiling skill applies only to identified bottleneck code
- An experimental pattern is being trialed on one component

### Naming Agent Override Files

Use the canonical agent role names as filenames: `planner.md`, `coder.md`, `reviewer.md`, `fixer.md`, `tester.md`, `linter.md`, `diagnostics.md`, `pm.md`, `director.md`.

Do not create new agent names at project scope. Project-scope definitions only override existing global agent roles.

## Checklist

- `.agents/` directory at project root (not inside `src/` or subdirectory)
- Agent override files named with canonical role names (`coder.md`, not `my-coder.md`)
- All project-scope agent definitions use `type: llm` (not `custom`)
- Skill directory names match the `name` field in their `SKILL.md`
- Project-local skill overrides contain complete skill content (no merging with global)
- New project-local skills have triggers defined so they match when relevant
